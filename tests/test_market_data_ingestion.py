"""Database publication must retain provenance and never mutate accepted marks."""
from datetime import date, datetime, timezone
from decimal import Decimal
import json

import pytest
from sqlalchemy import func, select

from apps.reference_api.db import get_engine
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS
from tests.test_yahoo_market_data import chart


def setup_dataset(c):
    dataset = c.scalar(m.dataset.insert().values(
        provider_product_id=c.scalar(select(m.provider_product.c.provider_product_id).limit(1)),
        dataset_code='YAHOO_TEST', display_name='Synthetic Yahoo-shaped test', data_domain='MARKET_DATA',
        valid_from=date(2026, 10, 1)).returning(m.dataset.c.dataset_id))
    org = c.scalar(select(m.tenant.c.owning_organisation_id).where(m.tenant.c.tenant_id == DEMO_IDS['tenant']))
    c.execute(m.dataset_access_profile.insert().values(dataset_id=dataset, licensee_organisation_id=org,
        permitted_tenant_id=DEMO_IDS['tenant'], usage_scope='PERSONAL', provider_enabled=True,
        activation_reference='Synthetic test declaration', status='ACTIVE'))
    licence = c.scalar(m.data_licence.insert().values(licensor_organisation_id=org,
        licensee_organisation_id=org, licence_code='YAHOO_TEST_DECLARATION', display_name='Test only',
        permitted_use_description='Synthetic data only', valid_from=date(2026, 10, 1)).returning(m.data_licence.c.data_licence_id))
    assignment = c.scalar(m.dataset_licence_assignment.insert().values(dataset_id=dataset,
        data_licence_id=licence, licence_role='ACQUISITION', valid_from=date(2026, 10, 1)).returning(m.dataset_licence_assignment.c.dataset_licence_assignment_id))
    for activity in ('ACQUIRE', 'STORE', 'DISPLAY'):
        c.execute(m.licence_activity_grant.insert().values(dataset_licence_assignment_id=assignment,
            activity=activity, usage_scope='PERSONAL', evidence_basis='PERSONAL_DECLARATION',
            evidence_reference='Synthetic test declaration', valid_from=date(2026, 10, 1)))
        c.execute(m.dataset_right_requirement.insert().values(dataset_id=dataset, activity=activity,
            requirement_code='SOURCE_TERMS', dataset_licence_assignment_id=assignment))
    source = c.scalar(select(m.integration_source_system.c.integration_source_system_id).limit(1))
    namespace = c.scalar(m.external_id_namespace.insert().values(integration_source_system_id=source,
        namespace_code='YAHOO_TEST', external_object_type='LISTING', valid_from=date(2026, 10, 1)).returning(m.external_id_namespace.c.external_id_namespace_id))
    c.execute(m.dataset_access_profile.update().where(m.dataset_access_profile.c.dataset_id == dataset).values(external_id_namespace_id=namespace))
    listing = DEMO_IDS['mvp_us_equity_listing']
    c.execute(m.external_object_mapping.insert().values(external_id_namespace_id=namespace,
        external_object_type='LISTING', external_id_value='AAPL', target_object_type='LISTING',
        target_object_id=listing, context_market_venue_id=c.scalar(select(m.listing.c.market_venue_id).where(m.listing.c.listing_node_id == listing)),
        mapping_method='RULE', status='PROPOSED', valid_from=date(2026, 10, 1)))
    # Test listing's existing venue is NYSE; independently pin the expected source context.
    return dataset, namespace, listing


def fixture_payload():
    payload = chart()
    payload['chart']['result'][0]['meta']['exchangeName'] = 'NYQ'
    return json.dumps(payload)


def ingest(c, dataset, namespace, key='run-1', raw=None):
    from apps.market_data_ingestor.yahoo import ingest_chart
    return ingest_chart(c, dataset_id=dataset, namespace_id=namespace, symbol='AAPL',
        raw_payload=raw or fixture_payload(), delivery_key=key,
        received_at=datetime(2026, 10, 7, 8, tzinfo=timezone.utc),
        start=date(2026, 10, 5), end=date(2026, 10, 6))


def test_delivery_replay_correction_and_frozen_provenance():
    with get_engine().connect() as c:
        tx = c.begin()
        try:
            dataset, namespace, listing = setup_dataset(c)
            first = ingest(c, dataset, namespace)
            assert first['accepted'] == 4 and first['duplicates'] == first['rejected'] == 0
            replay = ingest(c, dataset, namespace)
            assert replay['runId'] == first['runId'] and replay['replayed']
            second = ingest(c, dataset, namespace, 'run-2')
            assert second['accepted'] == 0 and second['duplicates'] == 4
            payload = json.loads(fixture_payload())
            payload['chart']['result'][0]['indicators']['quote'][0]['close'][0] = 251.5
            changed = ingest(c, dataset, namespace, 'run-3', json.dumps(payload))
            assert changed['accepted'] == 1 and changed['duplicates'] == 3
            observations = c.execute(select(m.market_data_observation).where(m.market_data_observation.c.dataset_id == dataset)).mappings().all()
            assert len(observations) == 5
            correction = next(o for o in observations if o['supersedes_observation_id'])
            original = next(o for o in observations if o['market_data_observation_id'] == correction['supersedes_observation_id'])
            assert original['value'] == Decimal('250.25') and correction['value'] == Decimal('251.5')
            assert original['quality_status'] == 'ACCEPTED'
            retained = c.execute(select(m.market_data_ingestion_run).where(m.market_data_ingestion_run.c.run_id == first['runId'])).mappings().one()
            assert retained['raw_payload'] == fixture_payload()
            assert {e['activity'] for e in retained['rights_evidence']} == {'ACQUIRE', 'STORE'}
            assert all(o['market_data_vintage_id'] and o['source_payload_id'] for o in observations)
            with pytest.raises(ValueError, match='different content'):
                ingest(c, dataset, namespace, 'run-1', json.dumps(payload))
        finally:
            tx.rollback()


def test_mismatch_is_retained_as_rejection_without_verified_mapping():
    with get_engine().connect() as c:
        tx = c.begin()
        try:
            dataset, namespace, listing = setup_dataset(c)
            payload = json.loads(fixture_payload())
            payload['chart']['result'][0]['meta']['currency'] = 'EUR'
            report = ingest(c, dataset, namespace, raw=json.dumps(payload))
            assert report['accepted'] == 0 and report['rejected'] == 1
            assert c.scalar(select(func.count()).select_from(m.market_data_observation).where(m.market_data_observation.c.dataset_id == dataset)) == 0
            assert c.scalar(select(m.external_object_mapping.c.status).where(m.external_object_mapping.c.external_id_namespace_id == namespace)) == 'PROPOSED'
            assert c.scalar(select(m.market_data_ingestion_run.c.raw_payload).where(m.market_data_ingestion_run.c.dataset_id == dataset)) == json.dumps(payload)
        finally:
            tx.rollback()


def test_missing_storage_right_denies_before_publication():
    with get_engine().connect() as c:
        tx = c.begin()
        try:
            dataset, namespace, listing = setup_dataset(c)
            c.execute(m.licence_activity_grant.delete().where(m.licence_activity_grant.c.activity == 'STORE'))
            with pytest.raises(PermissionError, match='STORE'):
                ingest(c, dataset, namespace)
            assert c.scalar(select(func.count()).select_from(m.market_data_ingestion_run).where(m.market_data_ingestion_run.c.dataset_id == dataset)) == 0
        finally:
            tx.rollback()


def test_retained_delivery_is_immutable_at_database_boundary():
    from sqlalchemy.exc import DBAPIError
    with get_engine().connect() as c:
        tx = c.begin()
        try:
            dataset, namespace, listing = setup_dataset(c)
            report = ingest(c, dataset, namespace)
            savepoint = c.begin_nested()
            with pytest.raises(DBAPIError, match='immutable'):
                c.execute(m.market_data_ingestion_run.update().where(m.market_data_ingestion_run.c.run_id == report['runId']).values(raw_payload='{}'))
            savepoint.rollback()
            assert c.scalar(select(m.market_data_ingestion_run.c.raw_payload).where(m.market_data_ingestion_run.c.run_id == report['runId'])) == fixture_payload()
        finally:
            tx.rollback()


def test_database_price_precision_does_not_create_false_corrections():
    with get_engine().connect() as c:
        tx = c.begin()
        try:
            dataset, namespace, _ = setup_dataset(c)
            payload = json.loads(fixture_payload())
            payload['chart']['result'][0]['indicators']['quote'][0]['close'][0] = 250.1234567890123
            raw = json.dumps(payload)
            assert ingest(c, dataset, namespace, 'precision-1', raw)['accepted'] == 4
            replay = ingest(c, dataset, namespace, 'precision-2', raw)
            assert replay['accepted'] == 0 and replay['duplicates'] == 4
        finally:
            tx.rollback()


def test_resume_matches_request_and_skips_only_successful_deliveries():
    from apps.market_data_ingestor.yahoo import completed_request
    with get_engine().connect() as c:
        tx = c.begin()
        try:
            dataset, namespace, _ = setup_dataset(c)
            assert completed_request(c, dataset, namespace, 'AAPL', date(2026,10,5), date(2026,10,6)) is None
            ingest(c, dataset, namespace)
            assert completed_request(c, dataset, namespace, 'AAPL', date(2026,10,5), date(2026,10,6))['accepted'] == 4
            assert completed_request(c, dataset, namespace, 'MSFT', date(2026,10,5), date(2026,10,6)) is None
            assert completed_request(c, dataset, namespace, 'AAPL', date(2026,10,4), date(2026,10,6)) is None
            assert completed_request(c, dataset, namespace, 'AAPL', date(2026,10,5), date(2026,10,7)) is None
            # A retained rejection on its own is never resumable success.
            from apps.market_data_ingestor.yahoo import ingest_chart
            rejected = ingest_chart(c, dataset_id=dataset, namespace_id=namespace, symbol='MSFT',
                raw_payload=fixture_payload(), delivery_key='failed-only',
                received_at=datetime(2026,10,7,8,tzinfo=timezone.utc),
                start=date(2026,10,5), end=date(2026,10,6))
            assert rejected['accepted'] == 0 and rejected['rejected'] == 1
            assert completed_request(c, dataset, namespace, 'MSFT', date(2026,10,5), date(2026,10,6)) is None
        finally:
            tx.rollback()


def test_backfill_coverage_counts_current_points_not_superseded_revisions():
    from apps.market_data_ingestor.yahoo import dataset_coverage
    with get_engine().connect() as c:
        tx = c.begin()
        try:
            dataset, namespace, _ = setup_dataset(c)
            ingest(c, dataset, namespace)
            payload = json.loads(fixture_payload())
            payload['chart']['result'][0]['indicators']['quote'][0]['close'][0] = 251
            ingest(c, dataset, namespace, 'changed', json.dumps(payload))
            coverage = dataset_coverage(c, dataset, date(2026,10,5), date(2026,10,6))
            assert {r['series_type']: r['observations'] for r in coverage} == {'CLOSE': 2, 'ADJUSTED_CLOSE': 2}
        finally:
            tx.rollback()


def test_historical_publication_batches_database_round_trips():
    from datetime import timedelta
    from sqlalchemy import event
    from apps.market_data_ingestor.yahoo import ingest_chart
    engine = get_engine()
    statements = []
    def record_sql(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)
    with engine.connect() as c:
        tx = c.begin()
        try:
            dataset, namespace, _ = setup_dataset(c)
            payload = json.loads(fixture_payload())
            result = payload['chart']['result'][0]
            result['timestamp'] = [int((datetime(2025,1,1,13,30,tzinfo=timezone.utc) + timedelta(days=i)).timestamp()) for i in range(300)]
            result['indicators']['quote'][0]['close'] = [250.25] * 300
            result['indicators']['adjclose'][0]['adjclose'] = [249.75] * 300
            event.listen(c, 'before_cursor_execute', record_sql)
            report = ingest_chart(c, dataset_id=dataset, namespace_id=namespace, symbol='AAPL',
                raw_payload=json.dumps(payload), delivery_key='batch-history', received_at=datetime(2026,10,7,8,tzinfo=timezone.utc),
                start=date(2025,1,1), end=date(2025,10,27))
            event.remove(c, 'before_cursor_execute', record_sql)
            assert report['accepted'] == 600 and report['rejected'] == report['duplicates'] == 0
            assert c.scalar(select(func.count()).select_from(m.market_data_observation).where(m.market_data_observation.c.dataset_id == dataset)) == 600
            assert len(statements) < 100, 'Daily history must not issue per-point database round trips'
        finally:
            if event.contains(c, 'before_cursor_execute', record_sql):
                event.remove(c, 'before_cursor_execute', record_sql)
            tx.rollback()


def test_repeated_adapter_point_preserves_sequential_duplicate_semantics():
    from market_data.contracts import DailyPoint, ParsedDelivery
    from market_data.providers.yahoo.adapter import YAHOO_DAILY_EQUITY
    from market_data.ingestion import ingest_delivery
    with get_engine().connect() as c:
        tx = c.begin()
        try:
            dataset, namespace, _ = setup_dataset(c)
            point = DailyPoint('CLOSE', date(2026,10,5), datetime(2026,10,5,13,30,tzinfo=timezone.utc),
                Decimal('250.25'), 'SPLIT_ADJUSTED', 'CLOSE')
            report = ingest_delivery(c, provider=YAHOO_DAILY_EQUITY,
                parser=lambda payload, **kwargs: ParsedDelivery((point, point), (), 'SPLIT_ADJUSTED', 'TEST_TIMESTAMP'),
                dataset_id=dataset, namespace_id=namespace, symbol='AAPL', raw_payload=fixture_payload(),
                delivery_key='repeated-point', received_at=datetime(2026,10,7,8,tzinfo=timezone.utc),
                start=date(2026,10,5), end=date(2026,10,6))
            assert report['accepted'] == 1 and report['duplicates'] == 1 and report['rejected'] == 0
            assert c.scalar(select(func.count()).select_from(m.market_data_observation).where(m.market_data_observation.c.dataset_id == dataset)) == 1
        finally:
            tx.rollback()


@pytest.mark.parametrize('target', ['LISTING_NODE', 'PARENT_NODE'])
def test_inactive_reference_is_rejected_before_publication(target):
    with get_engine().connect() as c:
        tx = c.begin()
        try:
            dataset, namespace, listing = setup_dataset(c)
            node = listing if target == 'LISTING_NODE' else c.scalar(select(m.listing.c.instrument_node_id).where(m.listing.c.listing_node_id == listing))
            c.execute(m.financial_reference_node.update().where(m.financial_reference_node.c.reference_node_id == node).values(status='INACTIVE'))
            report = ingest(c, dataset, namespace)
            assert report['accepted'] == 0 and report['rejected'] == 1
        finally:
            tx.rollback()


def test_series_dimensions_cannot_silently_change():
    with get_engine().connect() as c:
        tx=c.begin()
        try:
            dataset,namespace,_=setup_dataset(c)
            ingest(c,dataset,namespace)
            series=c.scalar(select(m.market_data_series.c.market_data_series_id).where(
                m.market_data_series.c.default_dataset_id==dataset,m.market_data_series.c.series_type=='CLOSE'))
            c.execute(m.market_data_series_dimension.update().where(
                m.market_data_series_dimension.c.market_data_series_id==series,
                m.market_data_series_dimension.c.dimension_code=='VALUE_BASIS').values(dimension_value='RAW'))
            report=ingest(c,dataset,namespace,'wrong-basis')
            assert report['accepted']==report['duplicates']==0 and report['rejected']==1
            assert 'dimensions' in report['rejections'][0]['reason']
        finally:
            tx.rollback()


@pytest.mark.parametrize('bad', ['NAN','OUTSIDE','NAIVE','INCONSISTENT','PRECISION'])
def test_generic_parser_contract_rejects_invalid_normalized_points(bad):
    from market_data.contracts import DailyPoint,ParsedDelivery
    from market_data.providers.yahoo.adapter import YAHOO_DAILY_EQUITY
    from market_data.ingestion import ingest_delivery
    with get_engine().connect() as c:
        tx=c.begin()
        try:
            dataset,namespace,_=setup_dataset(c)
            point=DailyPoint('CLOSE',date(2026,10,5),datetime(2026,10,5,13,30,tzinfo=timezone.utc),Decimal('250.25'),'SPLIT_ADJUSTED','CLOSE')
            from dataclasses import replace
            if bad=='NAN': point=replace(point,value=Decimal('NaN'))
            if bad=='OUTSIDE': point=replace(point,market_date=date(2025,1,1))
            if bad=='NAIVE': point=replace(point,observed_at=datetime(2026,10,5,13,30))
            if bad=='PRECISION': point=replace(point,value=Decimal('0.0000000000001'))
            points=(point,replace(point,value_basis='RAW')) if bad=='INCONSISTENT' else (point,)
            report=ingest_delivery(c,provider=YAHOO_DAILY_EQUITY,
                parser=lambda payload,**kw:ParsedDelivery(points,(),'TEST','DAILY_BAR'),dataset_id=dataset,
                namespace_id=namespace,symbol='AAPL',raw_payload=fixture_payload(),delivery_key='invalid-normalized',
                received_at=datetime(2026,10,7,8,tzinfo=timezone.utc),start=date(2026,10,5),end=date(2026,10,6))
            assert report['accepted']==0 and report['rejected']==1
        finally:
            tx.rollback()


def test_source_alias_change_supersedes_same_series_date_instead_of_double_counting():
    with get_engine().connect() as c:
        tx=c.begin()
        try:
            dataset,namespace,listing=setup_dataset(c)
            ingest(c,dataset,namespace)
            c.execute(m.external_object_mapping.insert().values(external_id_namespace_id=namespace,
                external_object_type='LISTING',external_id_value='NEW',target_object_type='LISTING',target_object_id=listing,
                context_market_venue_id=c.scalar(select(m.listing.c.market_venue_id).where(m.listing.c.listing_node_id==listing)),mapping_method='RULE',status='PROPOSED',valid_from=date(2026,10,1)))
            payload=json.loads(fixture_payload())
            payload['chart']['result'][0]['meta']['symbol']='NEW'
            payload['chart']['result'][0]['indicators']['quote'][0]['close'][0]=251.5
            from apps.market_data_ingestor.yahoo import ingest_chart,dataset_coverage
            result=ingest_chart(c,dataset_id=dataset,namespace_id=namespace,symbol='NEW',raw_payload=json.dumps(payload),
                delivery_key='new-alias',received_at=datetime(2026,10,7,9,tzinfo=timezone.utc),start=date(2026,10,5),end=date(2026,10,6))
            assert result['accepted']==1 and result['duplicates']==3
            assert {r['series_type']:r['observations'] for r in dataset_coverage(c,dataset,date(2026,10,5),date(2026,10,6))}=={'CLOSE':2,'ADJUSTED_CLOSE':2}
        finally:
            tx.rollback()


def test_expired_dataset_blocks_acquisition_and_display():
    from market_data.rights import load_rights
    with get_engine().connect() as c:
        tx = c.begin()
        try:
            dataset, namespace, _ = setup_dataset(c)
            c.execute(m.dataset.update().where(m.dataset.c.dataset_id == dataset).values(valid_to=date(2026, 10, 2)))
            assert not load_rights(c, dataset, 'DISPLAY', date(2026, 10, 7)).allowed
            with pytest.raises(PermissionError):
                ingest(c, dataset, namespace)
        finally:
            tx.rollback()


@pytest.mark.parametrize('mismatch', ['CURRENCY', 'INACTIVE'])
def test_existing_series_cannot_silently_change_its_identity(mismatch):
    with get_engine().connect() as c:
        tx = c.begin()
        try:
            dataset, namespace, _ = setup_dataset(c)
            ingest(c, dataset, namespace)
            changes = {'status':'INACTIVE'} if mismatch == 'INACTIVE' else {'currency_id': DEMO_IDS['eur_currency']}
            c.execute(m.market_data_series.update().where(m.market_data_series.c.default_dataset_id == dataset).values(**changes))
            result = ingest(c, dataset, namespace, 'changed-series')
            assert result['accepted'] == result['duplicates'] == 0 and result['rejected'] == 1
            assert c.scalar(select(func.count()).select_from(m.market_data_ingestion_run).where(m.market_data_ingestion_run.c.dataset_id == dataset)) == 2
        finally:
            tx.rollback()


@pytest.mark.parametrize('series_type', ['OFFICIAL_CLOSE', 'UNDECLARED_TYPE'])
def test_normalized_non_yahoo_delivery_uses_provider_source_and_series(series_type):
    from market_data.contracts import DailyPoint, ParsedDelivery, ProviderSpec
    from market_data.ingestion import ingest_delivery

    def parse_synthetic(payload, *, symbol, listing, start, end, received_at):
        assert symbol == 'AAPL'
        assert listing.currency == 'USD' and listing.mic == 'XNYS'
        assert payload == {'final': '123.5'}
        return ParsedDelivery((DailyPoint('FINAL', date(2026, 10, 5),
            datetime(2026, 10, 5, 20, tzinfo=timezone.utc), Decimal('123.5'),
            'RAW', series_type),), (), 'RAW', 'PROVIDER_EOD_TIMESTAMP')

    with get_engine().connect() as c:
        tx = c.begin()
        try:
            dataset, namespace, listing = setup_dataset(c)
            provider = ProviderSpec('SYNTHETIC_OTHER_SOURCE', ('OFFICIAL_CLOSE',), 4096, 30)
            report = ingest_delivery(c, provider=provider, parser=parse_synthetic,
                dataset_id=dataset, namespace_id=namespace, symbol='AAPL',
                raw_payload='{"final":"123.5"}', delivery_key='other-source',
                received_at=datetime(2026, 10, 7, 8, tzinfo=timezone.utc),
                start=date(2026, 10, 5), end=date(2026, 10, 6))
            if series_type == 'UNDECLARED_TYPE':
                assert report['accepted'] == 0 and report['rejected'] == 1
                assert c.scalar(select(func.count()).select_from(m.market_data_observation).where(
                    m.market_data_observation.c.dataset_id == dataset)) == 0
                assert c.scalar(select(m.external_object_mapping.c.status).where(
                    m.external_object_mapping.c.external_id_namespace_id == namespace)) == 'PROPOSED'
                assert c.scalar(select(m.market_data_ingestion_run.c.raw_payload).where(
                    m.market_data_ingestion_run.c.dataset_id == dataset)) == '{"final":"123.5"}'
                return
            assert report['accepted'] == 1 and report['duplicates'] == report['rejected'] == 0
            series = c.execute(select(m.market_data_series).where(
                m.market_data_series.c.default_dataset_id == dataset)).mappings().one()
            assert series['series_type'] == 'OFFICIAL_CLOSE'
            assert series['source_system_id'] == 'SYNTHETIC_OTHER_SOURCE'
            assert series['reference_node_id'] == listing
            observation = c.execute(select(m.market_data_observation).where(
                m.market_data_observation.c.dataset_id == dataset)).mappings().one()
            assert observation['value'] == Decimal('123.5')
            assert observation['source_observation_key'] == 'AAPL:FINAL:2026-10-05'
            assert observation['value_basis'] == 'RAW'
            assert c.scalar(select(m.market_data_vintage.c.value_basis).where(
                m.market_data_vintage.c.market_data_vintage_id == observation['market_data_vintage_id'])) == 'RAW'
            dimensions = dict(c.execute(select(m.market_data_series_dimension.c.dimension_code,
                m.market_data_series_dimension.c.dimension_value).where(
                m.market_data_series_dimension.c.market_data_series_id == series['market_data_series_id'])).all())
            assert dimensions == {'SOURCE_FIELD': 'FINAL', 'VALUE_BASIS': 'RAW',
                                  'TIMESTAMP_SEMANTICS': 'PROVIDER_EOD_TIMESTAMP'}
        finally:
            tx.rollback()
