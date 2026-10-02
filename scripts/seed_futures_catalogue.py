"""Add reviewed CME sample reference data through audited approval workflows.

Local only. Preview rolls the transaction back; --apply commits atomically.
Existing seed identities are verified and reused, never overwritten.
"""
import argparse
from datetime import date
from decimal import Decimal
import json
from pathlib import Path
import sys
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select, func
from sqlalchemy.engine import make_url
from apps.reference_api.config import Settings
from apps.reference_api.db import get_engine
from apps.reference_api import product_booking as products
from apps.reference_api import repository
from apps.reference_api.contracts import IndexProposalRequest, EquityListingCreateProposalRequest
from apps.reference_api.product_booking_contracts import FutureFamilyProposalRequest, FutureProposalRequest
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS
from security_master_schema.tenant_workspace import resolve_tenant_workspace, require_tenant_action

EFFECTIVE = date(2026, 10, 2)
MICRO_SOURCE = 'https://www.cmegroup.com/trading/equity-index/files/cme-micro-e-mini-futures-fact-card.pdf'
ES_SOURCE = 'https://www.cmegroup.com/markets/equities/sp/e-mini-sandp500.contractSpecs.html'
EXPIRIES = [('2026-12-01', '2026-12-18', '2026-12-18T14:30:00Z', 'Z6', 'December 2026'),
            ('2027-03-01', '2027-03-19', '2027-03-19T13:30:00Z', 'H7', 'March 2027')]
FAMILIES = [('ES', 'E-mini S&P 500', 'SP500', '50', ES_SOURCE),
            ('MES', 'Micro E-mini S&P 500', 'SP500', '5', MICRO_SOURCE),
            ('MNQ', 'Micro E-mini Nasdaq-100', 'NASDAQ100', '2', MICRO_SOURCE)]


def same(actual, expected, label):
    if actual != expected:
        raise ValueError(f'Existing {label} differs from the reviewed seed; refusing overwrite.')


def approve(connection, tenant, actor, proposal):
    result = repository.decide_reference_data_proposal(connection, tenant, actor,
        proposal.proposal_id, 'APPROVED',
        'User-requested local CME reference-data seed; official specification checked 2026-10-02. '
        'No execution, market data, margin or valuation is created.')
    return result.reference_node_id


def seed(connection, tenant, actor):
    workspace = resolve_tenant_workspace(connection, tenant, actor, date.today())
    require_tenant_action(workspace, 'TRADE_WRITE')
    if workspace.membership_role != 'TENANT_ADMIN':
        raise ValueError('An active tenant administrator is required.')
    # Serialize the shared venue and this small seed bundle, including retries.
    connection.execute(select(func.pg_advisory_xact_lock(202610020058)))
    usd = connection.scalar(select(m.currency.c.currency_id).where(
        m.currency.c.currency_code == 'USD', m.currency.c.status == 'ACTIVE'))
    profile = connection.scalar(select(m.return_profile.c.return_profile_id).where(
        m.return_profile.c.profile_code == 'PRICE_RETURN', m.return_profile.c.status == 'ACTIVE'))
    if not usd or not profile:
        raise ValueError('Active USD and PRICE_RETURN catalogues are required.')
    indices = {}
    for key, name in [('SP500', 'S&P 500 Price Return'), ('NASDAQ100', 'Nasdaq-100 Price Return')]:
        code = f'CME_SEED_{tenant.hex}_{key}'
        node = connection.scalar(select(m.financial_reference_node.c.reference_node_id).where(
            m.financial_reference_node.c.internal_code == code))
        if node is None:
            proposal = repository.submit_index_proposal(connection, tenant, actor,
                IndexProposalRequest(canonicalName=name, internalCode=code, effectiveFrom=EFFECTIVE,
                    indexKind='PUBLIC', returnProfileId=profile, baseCurrencyId=usd,
                    methodologyReference='Underlying identity only; no licensed observations or full methodology seeded.',
                    methodologyDocumentUri=ES_SOURCE if key == 'SP500' else
                    'https://www.cmegroup.com/markets/equities/nasdaq/micro-e-mini-nasdaq-100.contractSpecs.html'))
            node = approve(connection, tenant, actor, proposal)
        products.require_owned(connection, tenant, node)
        terms = connection.execute(select(m.index_terms).where(m.index_terms.c.index_node_id == node)).mappings().one()
        same((terms.status, terms.base_currency_id, terms.return_profile_id), ('ACTIVE', usd, profile), name)
        indices[key] = node
    venue = connection.scalar(select(m.market_venue_identifier.c.market_venue_id).where(
        m.market_venue_identifier.c.identifier_scheme == 'ISO_10383_MIC',
        m.market_venue_identifier.c.identifier_value == 'XCME'))
    if venue is None:
        venue = connection.scalar(m.market_venue.insert().values(display_name='Chicago Mercantile Exchange',
            venue_type='EXCHANGE', country_code='USA', city='Chicago', timezone_name='America/Chicago',
            status='ACTIVE').returning(m.market_venue.c.market_venue_id))
        connection.execute(m.market_venue_identifier.insert().values(market_venue_id=venue,
            identifier_scheme='ISO_10383_MIC', identifier_value='XCME', is_primary=True))
    venue_row = connection.execute(select(m.market_venue).where(m.market_venue.c.market_venue_id == venue)).mappings().one()
    same((venue_row.status, venue_row.timezone_name), ('ACTIVE', 'America/Chicago'), 'XCME venue')
    result = {'tenantId': str(tenant), 'venueId': str(venue), 'indices': {k: str(v) for k, v in indices.items()}, 'families': []}
    for root, name, index, multiplier, source in FAMILIES:
        code = 'CME_' + root
        spec = dict(underlyingKind='INDEX', symbolRoot=root, yearDigits=1, deliveryMonths=[3, 6, 9, 12],
            settlementMethod='CASH', priceBasis='INDEX_POINTS', monetaryMultiplier=multiplier,
            quoteFactor='1', tickSize='0.25', allowNegativePrice=False)
        expected = FutureFamilyProposalRequest(canonicalName=name+' futures family', familyCode=code,
            underlyingId=indices[index], contractCurrencyId=usd,
            sourceReference=source+'; checked 2026-10-02; outright contracts only.', specification=spec)
        found, _ = products.search_families(connection, tenant, code, 100, 0)
        found = [f for f in found if f.family_code == code]
        if not found:
            approve(connection, tenant, actor, products.submit_proposal(connection, tenant, actor, expected))
            found, _ = products.search_families(connection, tenant, code, 100, 0)
            found = [f for f in found if f.family_code == code]
        family = found[0]
        same((family.underlying_id, family.contract_currency_id, family.specification),
            (expected.underlying_id, usd, expected.specification), code)
        item = {'code': code, 'familyId': str(family.family_id), 'contracts': []}
        for month, final, cutoff, suffix, label in EXPIRIES:
            convention = dict(kind='FUTURE', effectiveFrom=EFFECTIVE.isoformat(), quantityUnit='CONTRACTS',
                priceBasis='INDEX_POINTS', priceCurrencyId=str(usd), monetaryMultiplier=multiplier,
                quoteFactor='1', tickSize='0.25', allowNegativePrice=False, settlementMethod='CASH',
                lastTradingAtUtc=cutoff, finalSettlementDate=final,
                sourceReference=source+'; third Friday, 08:30 America/Chicago; checked 2026-10-02.')
            request = FutureProposalRequest(canonicalName=name+' '+label, familyId=family.family_id,
                familyCode=code, underlyingId=indices[index], contractMonth=month, convention=convention)
            node = connection.scalar(select(m.future_terms.c.instrument_node_id).where(
                m.future_terms.c.future_family_id == family.family_id,
                m.future_terms.c.contract_month == date.fromisoformat(month)))
            if node is None:
                node = approve(connection, tenant, actor, products.submit_proposal(connection, tenant, actor, request))
            products.require_owned(connection, tenant, node)
            context = products.load_context(connection, tenant, node, as_of=EFFECTIVE)
            same(context.convention, request.convention, root+' '+month)
            symbol = root + suffix
            listing = connection.execute(select(m.listing).where(m.listing.c.market_venue_id == venue,
                m.listing.c.trading_symbol == symbol)).mappings().first()
            if listing is None:
                proposal = repository.submit_equity_listing_proposal(connection, tenant, actor,
                    EquityListingCreateProposalRequest(instrumentId=node, listing=dict(marketVenueId=venue,
                        tradingSymbol=symbol, tradingCurrencyId=usd, quoteFactor='1', unitMultiplier='1',
                        isPrimaryListing=True, effectiveFrom=EFFECTIVE)))
                approve(connection, tenant, actor, proposal)
                listing = connection.execute(select(m.listing).where(m.listing.c.instrument_node_id == node,
                    m.listing.c.market_venue_id == venue, m.listing.c.trading_symbol == symbol)).mappings().one()
            same((listing.instrument_node_id, listing.trading_currency_id, listing.quote_factor,
                listing.unit_multiplier, listing.status), (node, usd, Decimal(1), Decimal(1), 'ACTIVE'), symbol)
            booked = products.load_context(connection, tenant, node, listing.listing_node_id, EFFECTIVE)
            if not booked.booking_eligible:
                raise ValueError(f'{symbol} is not eligible for the existing index-future ticket.')
            item['contracts'].append(dict(instrumentId=str(node), listingId=str(listing.listing_node_id),
                symbol=symbol, contractMonth=month, finalSettlementDate=final, lastTradingAtUtc=cutoff))
        result['families'].append(item)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tenant', type=UUID, default=DEMO_IDS['tenant'])
    parser.add_argument('--actor', type=UUID, default=DEMO_IDS['demo_user_account'])
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    settings = Settings.from_environment()
    url = make_url(settings.database_url)
    if settings.environment != 'local' or url.host not in ('localhost', '127.0.0.1') or url.database != 'fortem_secm':
        raise SystemExit('This command is restricted to the local fortem_secm workspace.')
    with get_engine(settings).connect() as connection:
        transaction = connection.begin()
        try:
            result = seed(connection, args.tenant, args.actor)
            if args.apply: transaction.commit()
            else: transaction.rollback()
        except Exception:
            transaction.rollback()
            raise
    print(json.dumps({'committed': args.apply, **result}, indent=2))


if __name__ == '__main__': main()
