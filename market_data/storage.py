"""SQL persistence for daily deliveries; transaction ownership stays with callers."""
from sqlalchemy import exists, func, or_, select

from security_master_schema import models as m


def insert_returning(c, table, key, **values):
    return c.scalar(table.insert().values(**values).returning(table.c[key]))


def lock_dataset(c, dataset_id, namespace_id):
    # Serialize publication/idempotency per dataset, not the whole market-data store.
    dataset = c.execute(select(m.dataset).where(m.dataset.c.dataset_id == dataset_id).with_for_update()).mappings().one()
    if dataset['status'] != 'ACTIVE':
        raise PermissionError('Dataset is not active')
    profile = c.execute(select(m.dataset_access_profile).where(m.dataset_access_profile.c.dataset_id == dataset_id)).mappings().one_or_none()
    if not profile or profile['external_id_namespace_id'] != namespace_id:
        raise PermissionError('Dataset source namespace is not configured')
    return dataset, profile


def previous_delivery(c, dataset_id, delivery_key):
    return c.execute(select(m.market_data_ingestion_run).where(
        m.market_data_ingestion_run.c.dataset_id == dataset_id,
        m.market_data_ingestion_run.c.delivery_key == delivery_key)).mappings().one_or_none()


def retain_payload(c, *, namespace_id, profile, delivery_key, digest, received_at):
    namespace = c.execute(select(m.external_id_namespace).where(
        m.external_id_namespace.c.external_id_namespace_id == namespace_id,
        m.external_id_namespace.c.status == 'ACTIVE',
        m.external_id_namespace.c.valid_from <= received_at.date(),
        or_(m.external_id_namespace.c.valid_to.is_(None),
            m.external_id_namespace.c.valid_to >= received_at.date()))).mappings().one_or_none()
    if not namespace:
        raise PermissionError('Source namespace is inactive or outside its effective dates')
    run_id = c.scalar(select(func.uuidv7()))
    source_payload_id = insert_returning(c, m.source_payload, 'source_payload_id',
        integration_source_system_id=namespace['integration_source_system_id'],
        tenant_id=profile['permitted_tenant_id'], payload_format='JSON',
        external_message_reference=delivery_key, payload_locator=f'db://md.market_data_ingestion_run/{run_id}',
        payload_sha256=digest, received_at_utc=received_at, processing_status='RECEIVED')
    return run_id, source_payload_id


def resolve_listing(c, *, namespace_id, symbol, received_at, permitted_tenant_id):
    mappings = c.execute(select(m.external_object_mapping).where(
        m.external_object_mapping.c.external_id_namespace_id == namespace_id,
        m.external_object_mapping.c.external_id_value == symbol,
        m.external_object_mapping.c.external_object_type == 'LISTING',
        m.external_object_mapping.c.target_object_type == 'LISTING',
        m.external_object_mapping.c.tenant_id.is_(None),
        m.external_object_mapping.c.status.in_(['PROPOSED', 'VERIFIED']),
        m.external_object_mapping.c.valid_from <= received_at.date(),
        or_(m.external_object_mapping.c.valid_to.is_(None), m.external_object_mapping.c.valid_to >= received_at.date()))).mappings().all()
    if len(mappings) != 1:
        raise ValueError('Unmapped or ambiguous source listing')
    mapping = mappings[0]
    listing = c.execute(select(m.listing, m.currency.c.currency_code,
        m.market_venue.c.timezone_name, m.market_venue.c.market_calendar_id,
        m.market_venue_identifier.c.identifier_value.label('mic'))
        .select_from(m.listing.join(m.currency, m.listing.c.trading_currency_id == m.currency.c.currency_id)
                     .join(m.market_venue).join(m.market_venue_identifier))
        .where(m.listing.c.listing_node_id == mapping['target_object_id'],
               m.listing.c.status == 'ACTIVE', m.market_venue.c.status == 'ACTIVE',
               m.market_venue_identifier.c.identifier_scheme == 'ISO_10383_MIC',
               m.market_venue_identifier.c.is_primary.is_(True))).mappings().one_or_none()
    if not listing or listing['market_venue_id'] != mapping['context_market_venue_id']:
        raise ValueError('Invalid listing or source venue context')
    for node_id in (listing['listing_node_id'], listing['instrument_node_id']):
        if c.scalar(select(m.financial_reference_node.c.status).where(
                m.financial_reference_node.c.reference_node_id == node_id)) != 'ACTIVE':
            raise ValueError('Listing or parent reference node is inactive')
        node_scope = c.execute(select(m.reference_node_scope).where(
            m.reference_node_scope.c.reference_node_id == node_id)).mappings().one_or_none()
        if node_scope and (node_scope['status'] != 'ACTIVE' or not (
                node_scope['scope_type'] == 'SHARED_CANONICAL' or
                node_scope['scope_type'] == 'TENANT_PRIVATE' and
                node_scope['owner_tenant_id'] == permitted_tenant_id)):
            raise ValueError('Listing or parent is outside the dataset tenant scope')
    return mapping, listing


def validate_series(c, *, listing, dataset_id, provider):
    existing_series = c.execute(select(m.market_data_series).where(
        m.market_data_series.c.reference_node_id == listing['listing_node_id'],
        m.market_data_series.c.default_dataset_id == dataset_id,
        m.market_data_series.c.series_type.in_(provider.series_types))).mappings().all()
    if any(s['status'] != 'ACTIVE' or s['currency_id'] != listing['trading_currency_id']
           or s['value_type'] != 'PRICE' or s['source_system_id'] != provider.source_system_id
           for s in existing_series):
        raise ValueError('Existing series identity differs; explicit series review is required')


def validate_dimensions(c,listing_id,dataset_id,parsed):
    expected={p.series_type:{'SOURCE_FIELD':p.field,'VALUE_BASIS':p.value_basis,
        'TIMESTAMP_SEMANTICS':parsed.timestamp_semantics} for p in parsed.points}
    series=c.execute(select(m.market_data_series).where(
        m.market_data_series.c.reference_node_id==listing_id,
        m.market_data_series.c.default_dataset_id==dataset_id,
        m.market_data_series.c.series_type.in_(expected))).mappings().all()
    for row in series:
        stored=dict(c.execute(select(m.market_data_series_dimension.c.dimension_code,
            m.market_data_series_dimension.c.dimension_value).where(
            m.market_data_series_dimension.c.market_data_series_id==row['market_data_series_id'])).all())
        if any(stored.get(k)!=v for k,v in expected[row['series_type']].items()):
            raise ValueError('Existing series dimensions differ; explicit series review is required')


def publish_points(c, *, parsed, provider, dataset, listing, mapping, symbol,
                   delivery_key, digest, source_payload_id, received_at, evidence, report):
    dataset_id = dataset['dataset_id']
    c.execute(m.external_object_mapping.update().where(
        m.external_object_mapping.c.external_object_mapping_id == mapping['external_object_mapping_id'],
        m.external_object_mapping.c.status == 'PROPOSED').values(
            status='VERIFIED', verified_at_utc=received_at, source_payload_id=source_payload_id))
    provider_id = c.scalar(select(m.provider_product.c.data_provider_id).where(
        m.provider_product.c.provider_product_id == dataset['provider_product_id']))
    vintage_id = insert_returning(c, m.market_data_vintage, 'market_data_vintage_id',
        dataset_id=dataset_id, data_provider_id=provider_id, source_vintage_key=delivery_key,
        received_at_utc=received_at, value_basis=parsed.vintage_value_basis, content_hash=digest,
        source_payload_id=source_payload_id)
    # Legacy single reference is deterministic, not the complete layered permission proof.
    primary=sorted((e for e in evidence if e['activity']=='ACQUIRE'),key=lambda e:(
        e['requirement']!='PERSONAL_SOURCE_TERMS_DECLARATION',e['requirement'],e['assignmentId']))[0]
    acquisition_licence = c.scalar(select(m.dataset_licence_assignment.c.data_licence_id).where(
        m.dataset_licence_assignment.c.dataset_licence_assignment_id == primary['assignmentId']))
    series_ids = {}
    for point in parsed.points:
        if point.series_type in series_ids:
            continue
        series_id = c.scalar(select(m.market_data_series.c.market_data_series_id).where(
            m.market_data_series.c.reference_node_id == listing['listing_node_id'],
            m.market_data_series.c.default_dataset_id == dataset_id,
            m.market_data_series.c.series_type == point.series_type))
        if not series_id:
            series_id = insert_returning(c, m.market_data_series, 'market_data_series_id',
                reference_node_id=listing['listing_node_id'], default_dataset_id=dataset_id,
                series_type=point.series_type, value_type='PRICE', currency_id=listing['trading_currency_id'],
                measure_definition_id=c.scalar(select(m.series_measure_definition.c.series_measure_definition_id).where(
                    m.series_measure_definition.c.measure_code == 'PRICE')),
                expected_frequency_code='BUSINESS_DAILY', expected_market_calendar_id=listing['market_calendar_id'],
                source_system_id=provider.source_system_id, is_official=False)
            for dimension, value in (('SOURCE_FIELD', point.field), ('VALUE_BASIS', point.value_basis),
                                     ('TIMESTAMP_SEMANTICS', parsed.timestamp_semantics)):
                c.execute(m.market_data_series_dimension.insert().values(market_data_series_id=series_id,
                    dimension_code=dimension, dimension_value=value))
        series_ids[point.series_type] = series_id
    # A validated Yahoo delivery has one point per source field/date. Preserve
    # the original sequential semantics for adapters with repeated identities.
    identities=[(p.series_type,p.market_date) for p in parsed.points]
    batched = len(set(identities)) == len(identities)
    newer = m.market_data_observation.alias('newer_ingested_point')
    current = select(m.market_data_observation).where(
        m.market_data_observation.c.dataset_id == dataset_id,
        m.market_data_observation.c.quality_status == 'ACCEPTED',
        ~exists(select(1).select_from(newer).where(
            newer.c.supersedes_observation_id == m.market_data_observation.c.market_data_observation_id,
            newer.c.quality_status == 'ACCEPTED')))
    previous_points = {}
    if batched:
        for row in c.execute(current.where(m.market_data_observation.c.market_data_series_id.in_(list(series_ids.values())),
                m.market_data_observation.c.market_date.in_({p.market_date for p in parsed.points}))).mappings():
            identity = (row['market_data_series_id'], row['market_date'])
            if identity in previous_points:
                raise ValueError('Ambiguous current source observation')
            previous_points[identity] = row
    pending = []
    for point in parsed.points:
        series_id = series_ids[point.series_type]
        key = f'{symbol}:{point.field}:{point.market_date.isoformat()}'
        previous = (previous_points.get((series_id, point.market_date)) if batched else c.execute(current.where(
            m.market_data_observation.c.market_data_series_id == series_id,
            m.market_data_observation.c.market_date == point.market_date)).mappings().one_or_none())
        if previous and previous['value'] == point.value and previous['value_basis'] == point.value_basis:
            report['duplicates'] += 1
            continue
        if previous and received_at < previous['received_at_utc']:
            raise ValueError('Correction receipt cannot precede its predecessor')
        values = dict(market_data_series_id=series_id,
            dataset_id=dataset_id, market_data_vintage_id=vintage_id, acquisition_licence_id=acquisition_licence,
            source_payload_id=source_payload_id, market_date=point.market_date,
            observed_at_utc=point.observed_at, source_timestamp_utc=point.observed_at,
            received_at_utc=received_at, value=point.value, value_basis=point.value_basis,
            source_observation_key=key, quality_status='ACCEPTED',
            supersedes_observation_id=previous['market_data_observation_id'] if previous else None)
        if batched:
            pending.append(values)
        else:
            c.execute(m.market_data_observation.insert().values(**values))
        report['accepted'] += 1
    for offset in range(0, len(pending), 1000):
        c.execute(m.market_data_observation.insert(), pending[offset:offset + 1000])


def finish_delivery(c, *, run_id, dataset_id, source_payload_id, delivery_key, digest,
                    raw_payload, received_at, evidence, report):
    report['rejected'] = len(report['rejections'])
    report['runId'] = str(run_id)
    c.execute(m.source_payload.update().where(m.source_payload.c.source_payload_id == source_payload_id).values(
        processing_status='REJECTED' if not report['accepted'] and report['rejected'] else 'VALIDATED'))
    c.execute(m.market_data_ingestion_run.insert().values(run_id=run_id, dataset_id=dataset_id,
        source_payload_id=source_payload_id, delivery_key=delivery_key, content_sha256=digest,
        raw_payload=raw_payload, received_at_utc=received_at, rights_evidence=evidence, report=report))
