"""Bulk display metadata on owned disposable PostgreSQL only."""
from copy import deepcopy
from datetime import date
from uuid import uuid4
from sqlalchemy import select,event
from apps.reference_api.db import get_engine
from apps.reference_api.instrument_display import load_instrument_displays,decorate_response
from apps.reference_api.contracts import ApiMeta
from apps.reference_api.product_booking_contracts import ProductBookingContextView,ProductBookingSearchResponse
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids


def engine():
    result=get_engine();assert result.url.database.startswith('platform_isolated_tests_');return result


def assign(c,node,scheme,value,**extra):
    scheme_id=c.scalar(select(m.identifier_scheme.c.identifier_scheme_id).where(m.identifier_scheme.c.scheme_code==scheme))
    c.execute(m.financial_reference_identifier.insert().values(reference_node_id=node,identifier_scheme_id=scheme_id,
        identifier_value=value,**extra))


def test_listing_uses_exact_canonical_parent_name_symbol_and_quote_context():
    with engine().connect() as c:
        listing=ids['hsbc_xlon_listing_node'];parent=ids['hsbc_instrument_node']
        display=load_instrument_displays(c,ids['tenant'],[listing])[str(listing)]
        assert display.instrument_id==str(parent)
        assert display.primary_name==c.scalar(select(m.financial_reference_node.c.canonical_name).where(m.financial_reference_node.c.reference_node_id==parent))
        assert display.identifier.scheme=='TICKER' and display.identifier.value=='HSD'
        assert 'GBP quote' in display.context
        assert 'London Stock Exchange' in display.context


def test_current_identifiers_are_filtered_by_validity_priority_and_exact_venue():
    with engine().connect() as c:
        bond=ids['bond_instrument_node']
        assign(c,bond,'ISIN','GB00BSGRV302',is_primary=True)
        assign(c,bond,'ISIN','GB00SECOND00',is_primary=False)
        assign(c,bond,'ISIN','GB00EXPIRED0',is_primary=True,valid_to=date(2000,1,1))
        assign(c,bond,'ISIN','GB00FUTURE00',is_primary=True,valid_from=date(2999,1,1))
        display=load_instrument_displays(c,ids['tenant'],[bond])[str(bond)]
        assert display.identifier.value=='GB00BSGRV302'
        assert 'GBP denomination' in display.context
        assert 'GB00EXPIRED0' not in display.search_text and 'GB00FUTURE00' not in display.search_text
        listing=ids['hsbc_xlon_listing_node']
        c.execute(m.listing.update().where(m.listing.c.listing_node_id==listing).values(instrument_node_id=bond))
        actual_venue=c.scalar(select(m.listing.c.market_venue_id).where(m.listing.c.listing_node_id==listing))
        other=c.scalar(select(m.market_venue.c.market_venue_id).where(m.market_venue.c.market_venue_id!=actual_venue).limit(1))
        assert other is not None
        assign(c,listing,'ISIN','GB00WRONG000',is_primary=True,context_market_venue_id=other)
        assert load_instrument_displays(c,ids['tenant'],[listing])[str(listing)].identifier.value=='GB00BSGRV302'


def test_private_parent_and_denied_scopes_do_not_release_names_or_identifiers():
    with engine().connect() as c:
        parent=ids['hsbc_instrument_node'];listing=ids['hsbc_xlon_listing_node']
        c.execute(m.reference_node_scope.delete().where(m.reference_node_scope.c.reference_node_id==parent))
        c.execute(m.reference_node_scope.insert().values(reference_node_id=parent,scope_type='TENANT_PRIVATE',
            owner_tenant_id=ids['second_tenant'],status='ACTIVE'))
        assign(c,parent,'ISIN','GB00SECRET00',is_primary=True)
        assert load_instrument_displays(c,ids['tenant'],[listing,parent])=={}


def test_unsupported_id_does_not_inherit_a_derivative_underlyings_isin():
    with engine().connect() as c:
        assign(c,ids['hsbc_instrument_node'],'ISIN','GB00UNDERLY0',is_primary=True)
        # This swap references the bond; neither underlying identity is a swap ID.
        swap=ids['bond_total_return_swap_node']
        result=load_instrument_displays(c,ids['tenant'],[swap,'not-a-uuid',uuid4()])
        assert set(result)=={str(swap)}
        assert result[str(swap)].identifier is None or result[str(swap)].identifier.value!='GB00UNDERLY0'


def test_more_than_500_references_are_complete_with_bounded_query_count():
    with engine().connect() as c:
        node=c.execute(select(m.financial_reference_node)).mappings().first()
        nodes=[dict(reference_node_id=uuid4(),reference_node_type_id=node['reference_node_type_id'],
            canonical_name=f'Example {i}',internal_code='DISP_'+uuid4().hex,status='ACTIVE',is_tradable=False) for i in range(501)]
        c.execute(m.financial_reference_node.insert(),nodes)
        statements=[]
        def count(conn,cursor,statement,parameters,context,executemany):statements.append(statement)
        event.listen(c,'before_cursor_execute',count)
        try:result=load_instrument_displays(c,ids['tenant'],[n['reference_node_id'] for n in nodes])
        finally:event.remove(c,'before_cursor_execute',count)
        assert len(result)==501
        assert len(statements)==4  # two reference batches, two identifier batches; no per-row reads
        assert result[str(nodes[-1]['reference_node_id'])].identifier is None


def test_response_sidecar_cannot_change_the_booking_context_saved_in_financial_evidence():
    with engine().connect() as c:
        frozen=ProductBookingContextView(instrumentId=ids['bond_instrument_node'],name='Original frozen business name',kind='BOND',executionRoute='OTC')
        response=ProductBookingSearchResponse(data=[frozen],meta=ApiMeta(tenantContext=str(ids['tenant']),source='test',apiVersion='test',correlationId='test'))
        original=response.model_dump(mode='json',by_alias=True);snapshot=frozen.model_dump_json(by_alias=True)
        result=decorate_response(c,ids['tenant'],response,[frozen.instrument_id])
        assert result.data[0].model_dump_json(by_alias=True)==snapshot
        assert response.model_dump(mode='json',by_alias=True)==original
        assert 'instrumentDisplays' not in original['meta']
        assert str(frozen.instrument_id) in result.model_dump(mode='json',by_alias=True)['meta']['instrumentDisplays']
        assert result.data[0].name=='Original frozen business name'


def test_catalogue_and_history_envelopes_use_the_same_read_only_display_contract():
    from tests.test_api_reference_authority import request
    with engine().connect() as c:
        assign(c,ids['bond_instrument_node'],'ISIN','GB00BSGRV302',is_primary=True)
        response=request(c,'GET','/v1/instruments/catalogue?q=BOND_DEMO_2031').json()
        display=response['meta']['instrumentDisplays'][str(ids['bond_instrument_node'])]
        assert display['identifier']==dict(scheme='ISIN',value='GB00BSGRV302')
        assert 'BOND_DEMO_2031' not in display['primaryName']
        assert 'BOND_DEMO_2031' in display['searchText']
        trades=request(c,'GET','/v1/trades?limit=100').json()
        assert trades['data']
        assert set(trades['meta']['instrumentDisplays'])<={row['subjectReferenceNodeId'] for row in trades['data']}
        trade=trades['data'][0]
        detail=request(c,'GET',f"/v1/trades/{trade['tradeId']}").json()
        assert detail['meta']['instrumentDisplays'][trade['subjectReferenceNodeId']]==trades['meta']['instrumentDisplays'][trade['subjectReferenceNodeId']]


def test_display_denied_valuation_never_resolves_current_names(monkeypatch):
    from apps.reference_api import valuation_presentation as presentation
    def denied(*args):raise AssertionError('Display-denied evidence reached the name resolver')
    monkeypatch.setattr(presentation,'load_instrument_displays',denied)
    batch={'summary':{'evidenceAccess':'DENIED'},'items':[]}
    assert presentation.decorate_batch(None,ids['tenant'],batch) is batch
