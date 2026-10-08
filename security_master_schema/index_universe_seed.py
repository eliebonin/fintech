"""Offline, operator-authorized public reference seed; never a tenant API write path.

The caller owns the transaction. Existing identities are checked, not repaired.
"""
from datetime import date, datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re

from sqlalchemy import select, func

from . import models as m

MANIFEST = Path(__file__).parent / 'data' / 'index_universe_2026_10_06.json'
VENUES = {
    'XNAS': ('Nasdaq', 'USA', 'New York', 'America/New_York'),
    'XNYS': ('New York Stock Exchange', 'USA', 'New York', 'America/New_York'),
    'BATS': ('Cboe BZX U.S. Equities Exchange', 'USA', 'Chicago', 'America/New_York'),
    'XPAR': ('Euronext Paris', 'FRA', 'Paris', 'Europe/Paris'),
    'XAMS': ('Euronext Amsterdam', 'NLD', 'Amsterdam', 'Europe/Amsterdam'),
}
UNIVERSES = {'SP500': (503, 'USD', 'S&P 500 Price Return'), 'CAC40': (40, 'EUR', 'CAC 40 Price Return')}


def validate_manifest(bundle):
    if bundle.get('asOf') != '2026-10-06' or not bundle.get('sources'):
        raise ValueError('A dated, sourced October 6 reference bundle is required.')
    counts = {key: 0 for key in UNIVERSES}
    identities, tickers = set(), set()
    for row in bundle['securities']:
        isin = row['isin']
        if not re.fullmatch(r'[A-Z]{2}[A-Z0-9]{9}[0-9]', isin):
            raise ValueError('Invalid ISIN format.')
        digits = ''.join(str(int(c, 36)) if c.isalpha() else c for c in isin)
        total = sum((v * 2 // 10 + v * 2 % 10) if i % 2 else v
                    for i, v in enumerate(map(int, reversed(digits))))
        if total % 10 or isin in identities:
            raise ValueError('Invalid ISIN checksum or duplicate economic identity.')
        universe = row['universe']
        if universe not in UNIVERSES or row['currency'] != UNIVERSES[universe][1]:
            raise ValueError('Unknown universe or inconsistent listing currency.')
        if row['mic'] not in VENUES or (universe == 'SP500') != (row['mic'] in {'XNAS', 'XNYS', 'BATS'}):
            raise ValueError('Unverified listing venue.')
        ticker = (row['mic'], row['symbol'])
        if ticker in tickers or not row['symbol'].strip() or not row['name'].strip():
            raise ValueError('Missing name/symbol or duplicate venue ticker.')
        identities.add(isin)
        tickers.add(ticker)
        counts[universe] += 1
    if counts != {key: value[0] for key, value in UNIVERSES.items()}:
        raise ValueError('Incomplete constituent universe.')


def load_manifest():
    bundle = json.loads(MANIFEST.read_text(encoding='utf-8'))
    validate_manifest(bundle)
    return bundle


def _same(actual, expected, label):
    if actual != expected:
        raise ValueError(f'Existing {label} differs from the reviewed seed; refusing overwrite.')


def _insert(connection, table, key, **values):
    return connection.scalar(table.insert().values(**values).returning(table.c[key]))


def _shared(connection, node, node_type, tradable):
    row = connection.execute(select(m.reference_node_scope).where(
        m.reference_node_scope.c.reference_node_id == node)).mappings().one_or_none()
    _same((row.scope_type, row.owner_tenant_id, row.status) if row else None,
          ('SHARED_CANONICAL', None, 'ACTIVE'), 'reference scope')
    state = connection.execute(select(m.financial_reference_node).where(
        m.financial_reference_node.c.reference_node_id == node)).mappings().one()
    _same((state.status, state.reference_node_type_id, state.is_tradable),
          ('ACTIVE', node_type, tradable), 'reference state')


def _node(connection, node_types, kind, name, code):
    node = _insert(connection, m.financial_reference_node, 'reference_node_id',
                   reference_node_type_id=node_types[kind], canonical_name=name,
                   internal_code=code, is_tradable=kind != 'INDEX', status='ACTIVE')
    connection.execute(m.reference_node_scope.insert().values(
        reference_node_id=node, scope_type='SHARED_CANONICAL', status='ACTIVE'))
    return node


def _identifier(connection, schemes, node, scheme, value, effective, venue=None):
    matches = connection.execute(select(m.financial_reference_identifier).where(
        m.financial_reference_identifier.c.identifier_scheme_id == schemes[scheme],
        m.financial_reference_identifier.c.identifier_value == value,
        m.financial_reference_identifier.c.context_market_venue_id == venue)).mappings().all()
    if matches:
        _same([(r.reference_node_id, r.valid_to) for r in matches], [(node, None)], scheme + ' identity')
        if matches[0].valid_from is not None and matches[0].valid_from > effective:
            raise ValueError('Identifier is not effective on snapshot date; refusing overwrite.')
    else:
        connection.execute(m.financial_reference_identifier.insert().values(
            reference_node_id=node, identifier_scheme_id=schemes[scheme], identifier_value=value,
            context_market_venue_id=venue, valid_from=effective, is_primary=True))


def seed(connection, actor):
    bundle = load_manifest()
    effective = date.fromisoformat(bundle['asOf'])
    if connection.scalar(select(m.user_account.c.status).where(m.user_account.c.user_account_id == actor)) != 'ACTIVE':
        raise ValueError('An active recorded seed operator account is required.')
    connection.execute(select(func.pg_advisory_xact_lock(2026100650040)))
    node_types = dict(connection.execute(select(m.reference_node_type.c.type_code,
        m.reference_node_type.c.reference_node_type_id).where(m.reference_node_type.c.status == 'ACTIVE')).all())
    schemes = dict(connection.execute(select(m.identifier_scheme.c.scheme_code, m.identifier_scheme.c.identifier_scheme_id)).all())
    currencies = dict(connection.execute(select(m.currency.c.currency_code, m.currency.c.currency_id).where(m.currency.c.status == 'ACTIVE')).all())
    equity = connection.scalar(select(m.instrument_type.c.instrument_type_id).where(
        m.instrument_type.c.type_code == 'EQUITY', m.instrument_type.c.status == 'ACTIVE'))
    profile = connection.scalar(select(m.return_profile.c.return_profile_id).where(
        m.return_profile.c.profile_code == 'PRICE_RETURN', m.return_profile.c.status == 'ACTIVE'))
    if not equity or not profile or not {'USD', 'EUR'} <= currencies.keys() or not {'INSTRUMENT', 'LISTING', 'INDEX'} <= node_types.keys() or not {'ISIN', 'TICKER', 'SEDOL', 'CUSIP'} <= schemes.keys():
        raise ValueError('Active reference catalogues must be seeded first.')
    source_code = 'PUBLIC_INDEX_UNIVERSE_SEED'
    source = connection.execute(select(m.integration_source_system).where(
        m.integration_source_system.c.system_code == source_code)).mappings().one_or_none()
    if source:
        _same((source.tenant_id, source.source_kind, source.environment, source.status),
              (None, 'INTERNAL', 'SANDBOX', 'ACTIVE'), 'seed source')
        source_id = source.integration_source_system_id
    else:
        source_id = _insert(connection, m.integration_source_system, 'integration_source_system_id',
            system_code=source_code, display_name='Curated public index reference universe',
            source_kind='INTERNAL', environment='SANDBOX', status='ACTIVE')
    digest = sha256(MANIFEST.read_bytes()).hexdigest()
    payload = connection.execute(select(m.source_payload).where(
        m.source_payload.c.integration_source_system_id == source_id,
        m.source_payload.c.external_message_reference == 'index-universe-2026-10-06')).mappings().one_or_none()
    if payload:
        _same((payload.payload_sha256, payload.tenant_id, payload.processing_status),
              (digest, None, 'VALIDATED'), 'seed payload')
        payload_id = payload.source_payload_id
    else:
        payload_id = _insert(connection, m.source_payload, 'source_payload_id',
            integration_source_system_id=source_id, payload_format='JSON',
            external_message_reference='index-universe-2026-10-06', payload_locator=str(MANIFEST.resolve()),
            payload_sha256=digest, processing_status='VALIDATED')
    venues = {}
    for mic, (name, country, city, tz) in VENUES.items():
        venue = connection.scalar(select(m.market_venue_identifier.c.market_venue_id).where(
            m.market_venue_identifier.c.identifier_scheme == 'ISO_10383_MIC',
            m.market_venue_identifier.c.identifier_value == mic))
        if venue is None:
            venue = _insert(connection, m.market_venue, 'market_venue_id', display_name=name,
                venue_type='EXCHANGE', country_code=country, city=city, timezone_name=tz, status='ACTIVE')
            connection.execute(m.market_venue_identifier.insert().values(
                market_venue_id=venue, identifier_scheme='ISO_10383_MIC', identifier_value=mic, is_primary=True))
        state = connection.execute(select(m.market_venue).where(m.market_venue.c.market_venue_id == venue)).mappings().one()
        _same((state.status, state.timezone_name), ('ACTIVE', tz), mic + ' venue')
        venues[mic] = venue
    result = dict(asOf=bundle['asOf'], createdInstruments=0, reusedInstruments=0,
                  createdListings=0, reusedListings=0, snapshots={}, sourcePayloadId=str(payload_id))
    members = {key: [] for key in UNIVERSES}
    approved = dict(status='APPROVED', is_current=True, sequence_no=1,
                    effective_from=effective, source_payload_id=payload_id,
                    approved_by_user_account_id=actor, approved_at_utc=datetime.now(timezone.utc))
    for row in bundle['securities']:
        currency, venue = currencies[row['currency']], venues[row['mic']]
        matches = connection.execute(select(m.financial_reference_identifier.c.reference_node_id).where(
            m.financial_reference_identifier.c.identifier_scheme_id == schemes['ISIN'],
            m.financial_reference_identifier.c.identifier_value == row['isin'])).scalars().all()
        if len(matches) > 1:
            raise ValueError('Ambiguous existing ISIN; refusing overwrite.')
        node = matches[0] if matches else None
        facts = dict(instrument_type_id=equity, asset_class='EQUITY', base_currency_id=currency)
        if node is None:
            node = _node(connection, node_types, 'INSTRUMENT', row['name'], 'PUBLIC_EQ_' + row['isin'])
            connection.execute(m.instrument.insert().values(instrument_node_id=node, effective_from=effective, **facts))
            connection.execute(m.instrument_definition_version.insert().values(instrument_node_id=node, **facts, **approved))
            result['createdInstruments'] += 1
        else:
            _shared(connection, node, node_types['INSTRUMENT'], True)
            instrument = connection.execute(select(m.instrument).where(m.instrument.c.instrument_node_id == node)).mappings().one_or_none()
            _same(tuple(instrument[k] for k in facts) if instrument else None, tuple(facts.values()), row['isin'])
            _same((instrument.is_current, instrument.effective_to), (True, None), 'instrument lifecycle')
            if instrument.effective_from is not None and instrument.effective_from > effective:
                raise ValueError('Instrument is not effective on snapshot date; refusing overwrite.')
            definitions = connection.execute(select(m.instrument_definition_version).where(
                m.instrument_definition_version.c.instrument_node_id == node,
                m.instrument_definition_version.c.is_current.is_(True))).mappings().all()
            if len(definitions) != 1 or definitions[0].status != 'APPROVED' or definitions[0].effective_from > effective or definitions[0].effective_to is not None:
                raise ValueError('Missing active approved instrument definition; refusing overwrite.')
            _same(tuple(definitions[0][k] for k in facts), tuple(facts.values()), 'instrument definition')
            result['reusedInstruments'] += 1
        for scheme, key in [('ISIN', 'isin'), ('SEDOL', 'sedol'), ('CUSIP', 'cusip')]:
            if row.get(key): _identifier(connection, schemes, node, scheme, row[key], effective)
        listing_facts = dict(market_venue_id=venue, trading_currency_id=currency,
                             trading_symbol=row['symbol'], quote_factor=1, unit_multiplier=1)
        listings = connection.execute(select(m.listing).where(m.listing.c.instrument_node_id == node,
            m.listing.c.market_venue_id == venue, m.listing.c.trading_currency_id == currency)).mappings().all()
        if not listings:
            listing = _node(connection, node_types, 'LISTING', row['name'] + ' — ' + row['symbol'],
                            'PUBLIC_LIST_' + row['isin'] + '_' + row['mic'])
            connection.execute(m.listing.insert().values(listing_node_id=listing, instrument_node_id=node,
                is_primary_listing=True, effective_from=effective, status='ACTIVE', **listing_facts))
            connection.execute(m.listing_definition_version.insert().values(listing_node_id=listing, **listing_facts, **approved))
            result['createdListings'] += 1
        else:
            if len(listings) != 1: raise ValueError('Ambiguous existing listing; refusing overwrite.')
            existing = listings[0]
            listing = existing.listing_node_id
            _shared(connection, listing, node_types['LISTING'], True)
            _same(tuple(existing[k] for k in listing_facts), tuple(listing_facts.values()), 'listing economics')
            _same((existing.status, existing.effective_to), ('ACTIVE', None), 'listing lifecycle')
            definitions = connection.execute(select(m.listing_definition_version).where(
                m.listing_definition_version.c.listing_node_id == listing,
                m.listing_definition_version.c.is_current.is_(True))).mappings().all()
            if len(definitions) != 1 or definitions[0].status != 'APPROVED' or definitions[0].effective_from > effective or definitions[0].effective_to is not None:
                raise ValueError('Missing active approved listing definition; refusing overwrite.')
            _same(tuple(definitions[0][k] for k in listing_facts), tuple(listing_facts.values()), 'listing definition')
            result['reusedListings'] += 1
        _identifier(connection, schemes, listing, 'TICKER', row['symbol'], effective, venue)
        members[row['universe']].append(node)
    for universe, (_, currency_code, name) in UNIVERSES.items():
        code = 'PUBLIC_INDEX_' + universe
        owner = connection.scalar(select(m.financial_reference_node.c.reference_node_id).where(m.financial_reference_node.c.internal_code == code))
        if owner is None:
            owner = _node(connection, node_types, 'INDEX', name, code)
            connection.execute(m.index_terms.insert().values(index_node_id=owner, index_kind='PUBLIC', return_profile_id=profile,
                base_currency_id=currencies[currency_code], methodology_reference='Membership identity only; no index levels, weights or methodology seeded.', status='ACTIVE'))
        else:
            _shared(connection, owner, node_types['INDEX'], False)
            terms = connection.execute(select(m.index_terms).where(m.index_terms.c.index_node_id == owner)).mappings().one_or_none()
            _same((terms.index_kind, terms.base_currency_id, terms.return_profile_id, terms.status) if terms else None,
                  ('PUBLIC', currencies[currency_code], profile, 'ACTIVE'), 'snapshot owner')
        snapshot = connection.execute(select(m.reference_constituent_snapshot).where(
            m.reference_constituent_snapshot.c.owner_reference_node_id == owner,
            m.reference_constituent_snapshot.c.snapshot_date == effective,
            m.reference_constituent_snapshot.c.snapshot_kind == 'INDEX_MEMBERSHIP')).mappings().one_or_none()
        if snapshot:
            _same((snapshot.status, snapshot.source_payload_id), ('ACTIVE', payload_id), 'membership snapshot')
            snapshot_id = snapshot.reference_constituent_snapshot_id
            items = connection.execute(select(m.reference_constituent_snapshot_item).where(
                m.reference_constituent_snapshot_item.c.reference_constituent_snapshot_id == snapshot_id)
                .order_by(m.reference_constituent_snapshot_item.c.sequence_no)).mappings().all()
            _same([(i.constituent_reference_node_id, i.sequence_no, i.weight, i.quantity, i.cash_component) for i in items],
                  [(node, i, None, None, None) for i, node in enumerate(members[universe], 1)], 'snapshot members')
        else:
            snapshot_id = _insert(connection, m.reference_constituent_snapshot, 'reference_constituent_snapshot_id',
                owner_reference_node_id=owner, snapshot_date=effective, snapshot_kind='INDEX_MEMBERSHIP', source_payload_id=payload_id, status='ACTIVE')
            connection.execute(m.reference_constituent_snapshot_item.insert(), [dict(
                reference_constituent_snapshot_id=snapshot_id, constituent_reference_node_id=node, sequence_no=i)
                for i, node in enumerate(members[universe], 1)])
        result['snapshots'][universe] = str(snapshot_id)
    return result
