"""Foundation writes in an owned disposable DB, not the operating app."""
import os
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import create_engine,select,func
import pytest
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS
from tooling.reconciliation_csv.tests.test_reconciliation_bundle import sample,load


@pytest.fixture
def connection():
    engine=create_engine(os.environ['DATABASE_URL'])
    with engine.connect() as c:
        tx=c.begin()
        try:yield c
        finally:tx.rollback()
    engine.dispose()


def test_foundation_is_scoped_idempotent_and_posts_no_financials(connection,tmp_path):
    from tooling.reconciliation_csv.seed_reconciliation_bundle import apply_foundation
    c=connection;bundle=load(sample(tmp_path));tenant=DEMO_IDS['tenant'];actor=DEMO_IDS['demo_user_account']
    trades=c.scalar(select(func.count()).select_from(m.trade))
    first=apply_foundation(c,bundle,tenant,actor,tmp_path/'evidence')
    second=apply_foundation(c,bundle,tenant,actor,tmp_path/'evidence')
    assert first==second
    row=c.execute(select(m.strategy).where(m.strategy.c.strategy_id==first['strategyId'])).mappings().one()
    assert row['tenant_id']==tenant and row['effective_from'].isoformat()=='2026-10-19'
    assert row['strategy_type']=='FUND' and row['status']=='ACTIVE'
    assert c.scalar(select(m.currency.c.currency_code).where(m.currency.c.currency_id==row['base_currency_id']))=='GBP'
    assert c.scalar(select(func.count()).select_from(m.source_payload).where(m.source_payload.c.integration_source_system_id==first['sourceId']))==11
    assert c.scalar(select(func.count()).select_from(m.trade))==trades
    mapping=c.execute(select(m.external_object_mapping).where(m.external_object_mapping.c.external_id_namespace_id==first['namespaceId'])).mappings().one()
    assert mapping['tenant_id']==tenant and mapping['external_id_value']=='2'
    assert mapping['target_object_id']==row['strategy_id'] and mapping['status']=='VERIFIED'
    assert c.scalar(select(m.currency.c.currency_id).where(m.currency.c.currency_code=='SGD'))


def test_unknown_actor_cannot_retain_private_source_or_create_strategy(connection,tmp_path):
    from tooling.reconciliation_csv.seed_reconciliation_bundle import apply_foundation
    from security_master_schema.tenant_workspace import TenantActionForbidden
    c=connection;before=c.scalar(select(func.count()).select_from(m.source_payload))
    with pytest.raises(TenantActionForbidden):
        apply_foundation(c,load(sample(tmp_path)),DEMO_IDS['tenant'],uuid4(),tmp_path/'evidence')
    assert c.scalar(select(func.count()).select_from(m.source_payload))==before
    assert not (tmp_path/'evidence').exists()


def test_preexisting_unowned_strategy_is_not_adopted(connection,tmp_path):
    from tooling.reconciliation_csv.seed_reconciliation_bundle import apply_foundation,strategy_code
    c=connection;bundle=load(sample(tmp_path));tenant=DEMO_IDS['tenant'];actor=DEMO_IDS['demo_user_account']
    c.execute(m.strategy.insert().values(strategy_id=uuid4(),tenant_id=tenant,
        strategy_code=strategy_code(bundle),display_name='Existing user strategy',strategy_type='FUND',status='ACTIVE'))
    with c.begin_nested():
        with pytest.raises(ValueError,match='Unowned strategy'):
            apply_foundation(c,bundle,tenant,actor,tmp_path/'evidence')


def test_later_delivery_reuses_source_strategy_instead_of_creating_daily_strategies(connection,tmp_path):
    from datetime import date
    from tooling.reconciliation_csv.reconciliation import load_bundle
    from tooling.reconciliation_csv.seed_reconciliation_bundle import apply_foundation
    source=sample(tmp_path);c=connection;tenant=DEMO_IDS['tenant'];actor=DEMO_IDS['demo_user_account']
    first=apply_foundation(c,load(source),tenant,actor,tmp_path/'evidence')
    for path in list(source.glob('SAMPLE-2026-10-20-*.csv')):
        path.with_name(path.name.replace('2026-10-20','2026-10-21')).write_bytes(path.read_bytes())
    later=load_bundle(source,'SAMPLE',date(2026,10,21),excluded_trade_ids={'exclude'},amc_ids={'10'})
    second=apply_foundation(c,later,tenant,actor,tmp_path/'evidence')
    assert second['strategyId']==first['strategyId'] and second['namespaceId']==first['namespaceId']
    assert second['bundleHash']!=first['bundleHash']
    assert c.scalar(select(func.count()).select_from(m.external_object_mapping).where(m.external_object_mapping.c.external_id_namespace_id==first['namespaceId']))==1


def test_user_named_company_keeps_operational_identity_without_inventing_lei(connection,tmp_path):
    from tooling.reconciliation_csv.seed_reconciliation_bundle import apply_foundation,apply_confirmed_company
    c=connection;bundle=load(sample(tmp_path));tenant=DEMO_IDS['tenant'];actor=DEMO_IDS['demo_user_account']
    foundation=apply_foundation(c,bundle,tenant,actor,tmp_path/'evidence')
    first=apply_confirmed_company(c,bundle,tenant,actor,foundation,'21','Example Custodian')
    assert apply_confirmed_company(c,bundle,tenant,actor,foundation,'21','Example Custodian')==first
    org=c.execute(select(m.organisation).where(m.organisation.c.organisation_id==first)).mappings().one()
    assert org['display_name']=='Example Custodian' and org['legal_name'] is None
    assert c.scalar(select(func.count()).select_from(m.organisation_identifier).where(m.organisation_identifier.c.organisation_id==first))==0
    assert c.scalar(select(func.count()).select_from(m.trade).where(m.trade.c.strategy_id==foundation['strategyId']))==0
    with pytest.raises(ValueError,match='not present'):apply_confirmed_company(c,bundle,tenant,actor,foundation,'999','Not a source company')


def test_bond_staging_approves_only_consistent_zero_coupon_and_replays(connection,tmp_path):
    import csv
    from datetime import date
    from tooling.reconciliation_csv.reconciliation import load_bundle
    from tooling.reconciliation_csv.reconciliation_bonds import stage_bonds
    from tooling.reconciliation_csv.seed_reconciliation_bundle import apply_foundation
    source=sample(tmp_path)
    instrument_file=source/'SAMPLE-2026-10-20-all_instruments.csv'
    instrument_file.write_text(instrument_file.read_text().replace('10,FUND,GBP','10,BOND,GBP'))
    # Test-only synthetic terms. The original source file is retained by foundation.
    rows=[dict(instrument_id='10',id_isin='TESTRECON001',security_des='Example zero',
        cpn_typ='ZERO COUPON',cpn='0',issue_dt='2026-01-01',maturity='2027-02-08',
        crncy='GBP',redemp_val='100',cpn_freq='',day_cnt_des='',px_dirty_clean='CLEAN')]
    with (source/'SAMPLE-2026-10-20-bonds.csv').open('w',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    bundle=load_bundle(source,'SAMPLE',date(2026,10,20),excluded_trade_ids={'exclude'})
    c=connection;tenant=DEMO_IDS['tenant'];actor=DEMO_IDS['demo_user_account']
    foundation=apply_foundation(c,bundle,tenant,actor,tmp_path/'evidence')
    before=c.scalar(select(func.count()).select_from(m.trade))
    prepared=stage_bonds(c,bundle,tenant,actor,foundation)
    assert prepared[0]['status']=='PENDING' and prepared[0]['instrumentId'] is None
    approved=stage_bonds(c,bundle,tenant,actor,foundation,approve_ready=True)
    assert approved[0]['status']=='APPROVED' and approved[0]['instrumentId']
    assert stage_bonds(c,bundle,tenant,actor,foundation,approve_ready=True)==approved
    node=approved[0]['instrumentId']
    terms=c.execute(select(m.bond_terms).where(m.bond_terms.c.instrument_node_id==node)).mappings().one()
    assert terms['coupon_type']=='ZERO' and terms['redemption_amount_per_par']==100
    assert terms['par_amount'] is None
    scope=c.execute(select(m.reference_node_scope).where(m.reference_node_scope.c.reference_node_id==node)).mappings().one()
    assert scope['owner_tenant_id']==tenant and scope['scope_type']=='TENANT_PRIVATE'
    assert c.scalar(select(func.count()).select_from(m.trade))==before
    from security_master_schema.tenant_workspace import TenantActionForbidden
    with pytest.raises(TenantActionForbidden):stage_bonds(c,bundle,tenant,uuid4(),foundation,approve_ready=True)


def test_reviewed_gilt_supersedes_pending_request_without_rewriting_source(connection,tmp_path):
    import csv,json
    from datetime import date
    from tooling.reconciliation_csv.reconciliation import load_bundle
    from tooling.reconciliation_csv.reconciliation_bonds import stage_bonds,approve_reviewed_gilts
    from tooling.reconciliation_csv.seed_reconciliation_bundle import apply_foundation
    source=sample(tmp_path)
    instruments=source/'SAMPLE-2026-10-20-all_instruments.csv'
    instruments.write_text(instruments.read_text().replace('10,FUND,GBP','10,BOND,GBP'))
    row=dict(instrument_id='10',id_isin='GB00BPSNB460',security_des='Incorrect legacy name',
        cpn_typ='FIXED',cpn='3.75',issue_dt='2024-01-11',maturity='2027-03-07',crncy='GBP',
        redemp_val='100',cpn_freq='2',day_cnt_des='ACT/ACT',px_dirty_clean='CLEAN')
    with (source/'SAMPLE-2026-10-20-bonds.csv').open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(row));writer.writeheader();writer.writerow(row)
    bundle=load_bundle(source,'SAMPLE',date(2026,10,20),excluded_trade_ids={'exclude'})
    c=connection;tenant=DEMO_IDS['tenant'];actor=DEMO_IDS['demo_user_account']
    foundation=apply_foundation(c,bundle,tenant,actor,tmp_path/'evidence')
    staged=stage_bonds(c,bundle,tenant,actor,foundation)
    old=c.execute(select(m.reference_data_proposal).where(m.reference_data_proposal.c.reference_data_proposal_id==staged[0]['proposalId'])).mappings().one()
    result=approve_reviewed_gilts(c,bundle,tenant,actor,foundation)
    assert result[0]['status']=='APPROVED' and result[0]['instrumentId']
    assert approve_reviewed_gilts(c,bundle,tenant,actor,foundation)==result
    retained=c.execute(select(m.reference_data_proposal).where(m.reference_data_proposal.c.reference_data_proposal_id==staged[0]['proposalId'])).mappings().one()
    assert retained['status']=='REJECTED' and retained['proposed_payload']==old['proposed_payload']
    assert 'dayCountConvention' not in json.loads(retained['proposed_payload'])
    terms=c.execute(select(m.bond_terms).where(m.bond_terms.c.instrument_node_id==result[0]['instrumentId'])).mappings().one()
    assert str(terms['coupon_rate'])=='0.037500000000' and terms['day_count_convention']=='ACT_ACT_ICMA'
    assert c.scalar(select(func.count()).select_from(m.trade).where(m.trade.c.strategy_id==foundation['strategyId']))==0


def test_reconciliation_products_use_existing_contracts_private_scope_and_safe_replay(connection,tmp_path):
    from tooling.reconciliation_csv.tests.test_reconciliation_products import product_bundle
    from tooling.reconciliation_csv.reconciliation_products import seed_products
    from tooling.reconciliation_csv.seed_reconciliation_bundle import apply_foundation
    from apps.reference_api.generic_swap_booking import load_generic_swap_context
    from datetime import date
    bundle=product_bundle(tmp_path);c=connection;tenant=DEMO_IDS['tenant'];actor=DEMO_IDS['demo_user_account']
    foundation=apply_foundation(c,bundle,tenant,actor,tmp_path/'evidence')
    first=seed_products(c,bundle,tenant,actor,foundation)
    assert seed_products(c,bundle,tenant,actor,foundation)==first
    assert set(first['references'])=={'11','1048','1396'} and set(first['swaps'])=={'10'}
    node=first['swaps']['10']
    context,maturity=load_generic_swap_context(c,tenant,node,date(2026,10,19))
    assert context.generic_terms.contractual_notional==1000000 and maturity==date(2027,1,4)
    assert context.generic_terms.funding_spread==Decimal('0.001')
    assert 'MOCKUP' in context.generic_terms.source_reference
    scope=c.execute(select(m.reference_node_scope).where(m.reference_node_scope.c.reference_node_id==node)).mappings().one()
    assert scope['scope_type']=='TENANT_PRIVATE' and scope['owner_tenant_id']==tenant
    audit=c.execute(select(m.access_audit_event).where(m.access_audit_event.c.action=='RECONCILIATION_PRODUCTS_SEEDED',m.access_audit_event.c.tenant_id==tenant)).mappings().all()
    assert len(audit)==1 and audit[0]['details']['assumptions']['10']['notionalPerUnit']
    assert c.scalar(select(func.count()).select_from(m.trade).where(m.trade.c.strategy_id==foundation['strategyId']))==0


def test_extra_seed_creates_certificate_and_normalized_option_without_financial_writes(connection,tmp_path):
    from tooling.reconciliation_csv.tests.test_reconciliation_products import additional_bundle
    from tooling.reconciliation_csv.reconciliation_products import seed_additional
    from tooling.reconciliation_csv.seed_reconciliation_bundle import apply_foundation
    bundle=additional_bundle(tmp_path);c=connection;tenant=DEMO_IDS['tenant'];actor=DEMO_IDS['demo_user_account']
    foundation=apply_foundation(c,bundle,tenant,actor,tmp_path/'evidence')
    first=seed_additional(c,bundle,tenant,actor,foundation)
    assert seed_additional(c,bundle,tenant,actor,foundation)==first
    assert set(first['certificates'])=={'1857'} and not first['pending'] and set(first['options'])=={'20265'}
    assert c.scalar(select(m.instrument_type.c.type_code).join(m.instrument).where(
        m.instrument.c.instrument_node_id==first['certificates']['1857']))=='ACTIVELY_MANAGED_CERTIFICATE'
    # An ETI catalogue entry must never turn an AMC into an ETI.
    c.execute(m.instrument_type.insert().values(type_code='ETI',display_name='Synthetic ETI catalogue fixture',default_asset_class='STRUCTURED_PRODUCT',status='ACTIVE'))
    completed=seed_additional(c,bundle,tenant,actor,foundation)
    assert seed_additional(c,bundle,tenant,actor,foundation)==completed
    assert completed==first
    assert completed['options']==first['options']
    assert c.scalar(select(func.count()).select_from(m.reference_data_proposal).where(
        m.reference_data_proposal.c.tenant_id==tenant,m.reference_data_proposal.c.proposal_type=='CREATE_ETP'))==0
    option=c.execute(select(m.option_terms).where(m.option_terms.c.instrument_node_id==first['options']['20265'])).mappings().one()
    assert option['strike_value']==5800 and option['premium_multiplier']==1
    assert c.scalar(select(func.count()).select_from(m.trade).where(m.trade.c.strategy_id==foundation['strategyId']))==0


def test_amc_correction_rejects_legacy_eti_without_rewriting_its_evidence(connection,tmp_path):
    from tooling.reconciliation_csv.tests.test_reconciliation_products import additional_bundle
    from tooling.reconciliation_csv.reconciliation_products import seed_additional
    from tooling.reconciliation_csv.seed_reconciliation_bundle import apply_foundation
    from apps.reference_api.contracts import EtpProposalRequest
    from apps.reference_api.repository import submit_etp_proposal
    c=connection;bundle=additional_bundle(tmp_path);tenant=DEMO_IDS['tenant'];actor=DEMO_IDS['demo_user_account']
    foundation=apply_foundation(c,bundle,tenant,actor,tmp_path/'evidence')
    payload=c.scalar(select(m.source_payload.c.source_payload_id).where(
        m.source_payload.c.integration_source_system_id==foundation['sourceId'],
        m.source_payload.c.external_message_reference==bundle.digest+':all_instruments'))
    currency=c.scalar(select(m.currency.c.currency_id).where(m.currency.c.currency_code=='USD'))
    legacy=submit_etp_proposal(c,tenant,actor,EtpProposalRequest(canonicalName='Wrong ETI mapping',
        baseCurrencyId=currency,effectiveFrom='2024-09-16',etpKind='ETI',legalForm='CERTIFICATE',redemptionModel='OPEN_ENDED',
        sourceSystemId=foundation['sourceId'],sourcePayloadId=payload,submissionMode='AUTOMATED',
        idempotencyKey='recon-amc:'+bundle.digest+':1857'))
    original=c.scalar(select(m.reference_data_proposal.c.proposed_payload).where(m.reference_data_proposal.c.reference_data_proposal_id==legacy.proposal_id))
    result=seed_additional(c,bundle,tenant,actor,foundation)
    assert not result['pending'] and result['certificates']['1857']
    row=c.execute(select(m.reference_data_proposal).where(m.reference_data_proposal.c.reference_data_proposal_id==legacy.proposal_id)).mappings().one()
    assert row['status']=='REJECTED' and row['proposed_payload']==original and row['reference_node_id'] is None
    assert seed_additional(c,bundle,tenant,actor,foundation)==result
    assert c.scalar(select(func.count()).select_from(m.trade).where(m.trade.c.strategy_id==foundation['strategyId']))==0
