"""Additive, local-only mock swap input setup; default is a rollback rehearsal.

Uses retained INVENTED index paths under existing owned mock-data rights, not
third-party index feeds. Adds a separately named strategy policy and uses already
permitted Yahoo FX. Never changes grants, old policies, trades, marks or valuations.
"""
import argparse
from datetime import date,datetime,timezone
from decimal import Decimal as D,localcontext
from hashlib import sha256
import json
from pathlib import Path
import sys
from uuid import UUID

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from security_master_schema.database_config import local_workspace_database
from apps.reference_api.valuation_policy_contracts import PolicyCreate,PolicyRuleInput

BASE=UUID('01a13ec5-72e8-7a80-b62e-0346389dae1b')
USD_GBP_SERIES=UUID('01a11cdb-ef19-7c06-b5ae-1b967c54dcaf')
POLICY_CODE='MOCK_STRAT_TEST_MEASURES_20261015'
AS_OF=date(2026,10,8)  # Existing USD/GBP valuation coverage starts here.
SWAPS={'SPX':UUID('01a13f2d-cc60-7316-aa77-0aa199354d2e'),
    'UKX':UUID('01a13f2d-d2d1-7414-b277-3c25693caf19')}


def validate_history(history):
    if (history.get('synthetic') is not True or history.get('code') not in ('SPX','UKX')
        or history.get('quote')!='WHOLE_SWAP_MTM_PER_UNIT' or history.get('quoteFactor')!='1'):
        raise ValueError('Only the retained synthetic per-unit histories are allowed')
    points=history.get('prices') or []
    if not points:raise ValueError('Synthetic history is empty')
    previous=None
    for point in points:
        day=date.fromisoformat(point['date']);stamp=datetime.fromisoformat(point['observedAt'].replace('Z','+00:00'))
        if stamp.utcoffset() is None or stamp.astimezone(timezone.utc).date()!=day or previous and day<=previous:
            raise ValueError('Unique ordered dates and explicit matching timestamps required')
        for field in ('close','indexLevel'):
            if not isinstance(point[field],str):raise ValueError('Exact decimal strings required')
            value=D(point[field])
            if not value.is_finite() or field=='indexLevel' and value<=0:raise ValueError('Invalid synthetic value')
        previous=day
    return points


def build_policy(base,strategy,pairs,fx):
    # Preserve copied base semantics without updating the retained base version.
    rules=list(base.rules);sequence=max([r.rule_sequence for r in rules+base.defaultRules]+[0])+1
    for pair in pairs:
        for subject,series,kind,basis in ((pair['subject'],pair['markSeries'],'CLOSE','RAW'),
            (pair['index'],pair['indexSeries'],'INDEX_LEVEL','INDEX_LEVEL')):
            rules.append(PolicyRuleInput(ruleSequence=sequence,subjectReferenceNodeId=subject,marketDataSeriesId=series,
                datasetId=pair['dataset'],seriesType=kind,valueBasis=basis,pricingConvention='EXPLICIT_TIME',
                pricingCutId=pair['cut'],marketCalendarId=pair['calendar'],selectionMethod='LAST_BEFORE_CUT',maxStalenessBusinessDays=0))
            sequence+=1
    rules.append(fx.model_copy(update={'rule_sequence':sequence}))
    return PolicyCreate(policyCode=POLICY_CODE,displayName='MOCK ONLY — Strat Testing measures (synthetic swaps)',
        strategyId=strategy,valuationCutId=base.valuationCutId,selectionMode=base.selectionMode,
        validFrom=max(base.validFrom,AS_OF),validTo=date(2026,12,31),rules=rules,defaultRules=base.defaultRules)


def prepare(c,artifact):
    from sqlalchemy import select,func
    from security_master_schema import models as m
    from security_master_schema.strategy_access import require_strategy_action
    from security_master_schema.access_management import audit
    from scripts.seed_mock_unit_swaps import PREFIX,STRATEGY,REFS,SPECS
    from scripts.seed_mock_bond_strategy import TENANT,ACTOR
    from apps.reference_api.valuation_policies import authority,policy_view,create_policy
    from market_data.rights import load_rights
    from market_data.display_access import assert_dataset_display
    from apps.reference_api.strategy_workspace import snapshot,position_rows
    from valuation.service import ValuationRequest
    from valuation.measure_inputs import preview_measures

    authority(c,TENANT,ACTOR,True)
    for action in ('STRATEGY_WRITE','TRADE_READ','VALUATION_READ','VALUATION_RUN'):
        require_strategy_action(c,TENANT,ACTOR,action,STRATEGY)
    strategy=c.execute(select(m.strategy).where(m.strategy.c.strategy_id==STRATEGY,m.strategy.c.tenant_id==TENANT,
        m.strategy.c.strategy_code=='STRAT-TEST',m.strategy.c.display_name=='Strat Testing')).mappings().one()
    c.execute(select(func.pg_advisory_xact_lock(int.from_bytes(sha256(POLICY_CODE.encode()).digest()[:8],'big',signed=True))))
    content=artifact.read_bytes();digest=sha256(content).hexdigest();data=json.loads(content)
    if data.get('synthetic') is not True or data.get('methodologyVersion')!=1 or set(data['history'])!={'SPX','UKX'}:
        raise ValueError('Expected the explicitly owned two-swap fixture')
    for code,history in data['history'].items():
        if history['code']!=code:raise ValueError('Fixture code mismatch')
        validate_history(history)
    source=c.execute(select(m.source_payload).join(m.integration_source_system).where(
        m.integration_source_system.c.tenant_id==TENANT,m.integration_source_system.c.system_code==PREFIX,
        m.source_payload.c.tenant_id==TENANT,m.source_payload.c.external_message_reference==PREFIX)).mappings().one()
    if source['payload_sha256']!=digest:raise ValueError('Retained artifact hash mismatch; refusing writes')
    dataset=c.execute(select(m.dataset).select_from(m.dataset.join(m.provider_product,
        m.dataset.c.provider_product_id==m.provider_product.c.provider_product_id).join(m.data_provider,
        m.provider_product.c.data_provider_id==m.data_provider.c.data_provider_id)).where(
        m.dataset.c.dataset_code==PREFIX,m.data_provider.c.owner_tenant_id==TENANT)).mappings().one()
    dataset_id=dataset['dataset_id']
    for activity in ('ACQUIRE','STORE','DISPLAY','NON_DISPLAY'):
        if not load_rights(c,dataset_id,activity,date.today(),'PERSONAL').allowed:raise PermissionError('Owned mock rights missing: '+activity)
    licence=c.scalar(select(m.data_licence.c.data_licence_id).where(m.data_licence.c.licence_code==PREFIX))
    now=c.scalar(select(func.clock_timestamp()));pairs=[]
    for code,history in data['history'].items():
        mark=c.execute(select(m.market_data_series).join(m.financial_reference_node).where(
            m.market_data_series.c.default_dataset_id==dataset_id,m.market_data_series.c.series_type=='CLOSE',
            m.market_data_series.c.reference_node_id==SWAPS[code])).mappings().one()
        name=c.scalar(select(m.financial_reference_node.c.canonical_name).where(m.financial_reference_node.c.reference_node_id==SWAPS[code]))
        if not name.startswith('MOCK - '+code+' / '):raise ValueError('Expected the named mock swap, not an operating contract')
        calendar=c.execute(select(m.market_calendar).where(m.market_calendar.c.logical_code==('XNYS_TRADING_2026' if code=='SPX' else 'XLON_TRADING_2026'),
            m.market_calendar.c.sealed,m.market_calendar.c.tenant_id.is_(None),m.market_calendar.c.status=='ACTIVE')
            .order_by(m.market_calendar.c.version_no.desc()).limit(1)).mappings().one()
        measure=c.scalar(select(m.series_measure_definition.c.series_measure_definition_id).where(m.series_measure_definition.c.measure_code=='INDEX_LEVEL'))
        index=c.scalar(select(m.market_data_series.c.market_data_series_id).where(m.market_data_series.c.reference_node_id==REFS[code],
            m.market_data_series.c.default_dataset_id==dataset_id,m.market_data_series.c.series_type=='INDEX_LEVEL'))
        if index is None:
            index=c.scalar(m.market_data_series.insert().values(reference_node_id=REFS[code],default_dataset_id=dataset_id,
                series_type='INDEX_LEVEL',value_type='INDEX_LEVEL',measure_definition_id=measure,currency_id=mark['currency_id'],
                valuation_cut_id=mark['valuation_cut_id'],expected_frequency_code='BUSINESS_DAILY',expected_market_calendar_id=calendar['market_calendar_id'],
                coverage_start_date=date.fromisoformat(history['prices'][0]['date']),coverage_end_date=date.fromisoformat(history['prices'][-1]['date']),
                source_system_id=PREFIX,is_official=False,status='ACTIVE').returning(m.market_data_series.c.market_data_series_id))
            c.execute(m.market_data_series_dimension.insert().values(market_data_series_id=index,dimension_code='DATA_ORIGIN',dimension_value='SYNTHETIC_MOCK'))
        existing={row['market_date']:row for row in c.execute(select(m.market_data_observation).where(m.market_data_observation.c.market_data_series_id==index)).mappings()}
        rows=[]
        for point in history['prices']:
            day=date.fromisoformat(point['date']);stamp=datetime.fromisoformat(point['observedAt'])
            old=existing.get(day)
            if old:
                if old['value']!=D(point['indexLevel']) or old['value_basis']!='INDEX_LEVEL' or old['observed_at_utc']!=stamp:
                    raise ValueError('Existing mock index observation differs; refusing overwrite')
                continue
            rows.append(dict(market_data_series_id=index,dataset_id=dataset_id,acquisition_licence_id=licence,
                source_payload_id=source['source_payload_id'],market_date=day,valuation_cut_id=mark['valuation_cut_id'],
                observed_at_utc=stamp,received_at_utc=now,source_published_at_utc=now,value=D(point['indexLevel']),value_basis='INDEX_LEVEL',
                quality_status='ACCEPTED',source_observation_key=PREFIX+'-INDEX-'+code+'-'+str(day),source_payload_reference=artifact.as_uri()))
        if rows:c.execute(m.market_data_observation.insert(),rows)
        assert_dataset_display(c,TENANT,{dataset_id},series_contexts=[(dataset_id,index)])
        pairs.append(dict(subject=mark['reference_node_id'],index=REFS[code],markSeries=mark['market_data_series_id'],indexSeries=index,
            dataset=dataset_id,cut=mark['valuation_cut_id'],calendar=calendar['market_calendar_id']))
    base=policy_view(c,TENANT,BASE)
    fx_series=c.execute(select(m.market_data_series).where(m.market_data_series.c.market_data_series_id==USD_GBP_SERIES)).mappings().one()
    if fx_series['series_type']!='FX_SPOT' or fx_series['source_system_id']!='YAHOO_FINANCE_PERSONAL':raise ValueError('Unexpected FX series')
    fx=next(r for r in base.rules if r.series_type=='FX_SPOT').model_copy(update=dict(
        subject_reference_node_id=fx_series['reference_node_id'],market_data_series_id=USD_GBP_SERIES,dataset_id=fx_series['default_dataset_id'],
        pricing_cut_id=fx_series['valuation_cut_id']))
    payload=build_policy(base,STRATEGY,pairs,fx)
    payload=payload.model_copy(update={'valid_from':max(payload.valid_from,strategy['effective_from'])})
    if payload.valid_from>AS_OF:raise ValueError('Requested mock date precedes strategy validity')
    policy=create_policy(c,TENANT,ACTOR,payload,POLICY_CODE+'-V1')
    projection,descriptions,information=snapshot(c,TENANT,STRATEGY,AS_OF,'EXECUTED',None)
    from datetime import time,timedelta
    closing=datetime.combine(AS_OF,time.max,timezone.utc)
    request=ValuationRequest(TENANT,STRATEGY,policy.valuationPolicyId,policy.valuationCutId,strategy['base_currency_id'],closing-timedelta(days=1),closing,information)
    result=preview_measures(c,request,projection,descriptions,[r for r in position_rows(projection,descriptions) if r['direction']!='FLAT'])
    if any(v['status']!='AVAILABLE' for row in result['items'] for v in row['measures'].values()):
        raise ValueError('Preview has missing inputs: '+json.dumps({r['name']:r['evidence']['issues'] for r in result['items'] if r['evidence']['issues']}))
    # Independently authored formula checks, not calls back into the measure kernel.
    checked=[]
    with localcontext() as ctx:
        ctx.prec=512
        for code,spec in SPECS.items():
            pair=next(p for p in pairs if p['index']==REFS[code])
            row=next(r for r in result['items'] if r['subjectId']==str(pair['subject']))
            point=next(p for p in data['history'][code]['prices'] if p['date']==str(AS_OF))
            expected=dict(referenceNotional=D(spec['units'])*D(spec['initial']),
                economicExposure=D(spec['units'])*D(point['indexLevel'])*D(spec['leverage']),marketValue=D(spec['units'])*D(point['close']))
            for name,amount in expected.items():
                if D(row['measures'][name]['localAmount'])!=amount:raise ValueError('Mock formula differs: '+code+'/'+name)
                proof=row['evidence']['selections'][name+'Fx']
                rate=D(1) if proof['method']=='IDENTITY' else c.scalar(select(m.market_data_observation.c.value).where(
                    m.market_data_observation.c.market_data_observation_id==UUID(proof['selection']['market_data_observation_id'])))
                if proof['method'] not in ('IDENTITY','DIRECT') or D(row['measures'][name]['strategyAmount'])!=amount*rate:
                    raise ValueError('Reporting FX differs: '+code+'/'+name)
            checked.append(dict(code=code,measures=row['measures'],evidenceHash=row['evidenceHash']))
    audit(c,ACTOR,TENANT,'MOCK_SWAP_MEASURES_PREPARED',dict(strategyId=str(STRATEGY),policyId=str(policy.valuationPolicyId),
        basePolicyId=str(BASE),artifactHash=digest,indexSeriesIds=[str(p['indexSeries']) for p in pairs],synthetic=True))
    return dict(policyId=str(policy.valuationPolicyId),policyCode=policy.policyCode,version=policy.versionNo,
        strategyId=str(STRATEGY),asOf=str(AS_OF),positions=len(result['items']),checked=checked)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    from sqlalchemy import create_engine
    from apps.reference_api.config import Settings
    settings=Settings.from_environment();engine=create_engine(settings.database_url)
    if settings.environment!='local' or engine.url.host not in ('localhost','127.0.0.1') or engine.url.port!=54329 or engine.url.database!=local_workspace_database():
        raise ValueError('Only the named local app database is permitted')
    try:
        with engine.connect() as c:
            transaction=c.begin()
            try:
                result=prepare(c,ROOT/'data/mock-unit-swaps-20261015.json')
                if args.apply:transaction.commit()
                else:transaction.rollback()
                print(json.dumps(result|dict(applied=args.apply,mode='APPLIED' if args.apply else 'ROLLED_BACK_REHEARSAL'),indent=2))
            except BaseException:
                if transaction.is_active:transaction.rollback()
                raise
    finally:engine.dispose()


if __name__=='__main__':main()
