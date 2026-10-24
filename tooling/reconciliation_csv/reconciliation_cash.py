"""Exact-date source cash balances through native account/revision writers."""
from datetime import datetime
from hashlib import sha256
from uuid import UUID
from .reconciliation import source_id,document
from .reconciliation_precision import native_decimal


def account_key(row):
    # The source comment distinguishes ordinary cash, wash and variation margin.
    # Retain it in identity rather than coalescing rows by company/currency/date.
    return (source_id(row['counterparty_id']),row.get('agent') or 'UNSPECIFIED',
        source_id(row['instrument_id']),row.get('comment') or '',row['trade_currency'])


def post_cash(c,bundle,tenant,actor,foundation,companies):
    from sqlalchemy import select
    from security_master_schema import models as m
    from security_master_schema.access_management import audit
    from valuation.cash_snapshots import scoped_strategy,create_account,upload
    from apps.reference_api.cash_snapshot_contracts import CashAccountCreate,CashUpload
    scoped_strategy(c,tenant,actor,foundation['strategyId'],True)
    if foundation['bundleHash']!=bundle.digest:raise ValueError('Source bundle differs')
    payload=c.scalar(select(m.source_payload.c.source_payload_id).join(m.integration_source_system).where(
        m.source_payload.c.tenant_id==tenant,m.source_payload.c.integration_source_system_id==foundation['sourceId'],
        m.integration_source_system.c.tenant_id==tenant,m.integration_source_system.c.status=='ACTIVE',
        m.source_payload.c.external_message_reference==bundle.digest+':cash_balances'))
    if not payload:raise ValueError('Owned retained cash source required')
    currencies=dict(c.execute(select(m.currency.c.currency_code,m.currency.c.currency_id).where(m.currency.c.status=='ACTIVE')).all())
    result=dict(snapshots=0,accounts=0);accounts={};rows=[];evidence=[]
    for row in sorted(bundle.tables['cash_balances'],key=lambda r:r['trade_id']):
        key=account_key(row);company,agent,instrument,comment,currency=key
        if row.get('active','True')!='True':raise ValueError('Inactive source cash row')
        if currency not in currencies or company not in companies:raise ValueError('Cash currency/company mapping missing')
        if row.get('price') and row['price'] not in ('1','1.0'):raise ValueError('Cash balance must be a currency amount, not a priced position')
        if key not in accounts:
            identity=sha256(document(key)).hexdigest()[:16]
            label=('RECON '+bundle.name+' / '+agent+' / '+currency+' / '+identity)[:100]
            accounts[key]=create_account(c,tenant,actor,CashAccountCreate(strategyId=foundation['strategyId'],
                companyId=companies[company],label=label,accountType='CUSTODY'))
        amount=native_decimal(row['quantity'])
        rows.append(dict(accountId=str(accounts[key]),currencyId=str(currencies[currency]),
            valueDate=str(datetime.fromisoformat(row['trade_datetime_utc']).date()),amount=amount['value'],
            sourceReference=str(payload)+':'+row['trade_id'],
            note=('Imported source company '+company+', agent '+agent+'. '+comment+
                ' Reporting company does not establish the underlying third-party venue legal identity.')[:2000]))
        evidence.append(dict(sourceTradeId=row['trade_id'],accountId=str(accounts[key]),sourceAccountKey=key,normalization=amount))
    if not rows:return result
    upload(c,tenant,actor,CashUpload(strategyId=foundation['strategyId'],rows=rows),
        'recon-cash:'+bundle.digest)
    result=dict(snapshots=len(rows),accounts=len(accounts))
    existing=c.scalar(select(m.access_audit_event.c.event_id).where(m.access_audit_event.c.tenant_id==tenant,
        m.access_audit_event.c.action=='RECONCILIATION_CASH_IMPORTED',m.access_audit_event.c.details['bundleHash'].as_string()==bundle.digest,
        m.access_audit_event.c.details['sourceId'].as_string()==str(foundation['sourceId'])))
    if not existing:
        audit(c,actor,tenant,'RECONCILIATION_CASH_IMPORTED',dict(bundleHash=bundle.digest,sourceId=str(foundation['sourceId']),
            strategyId=str(foundation['strategyId']),sourcePayloadId=str(payload),**result,rows=evidence,
            accountTypeAssumption='CUSTODY means source-reporting custody bucket, not verified legal venue ownership',
            balanceTreatment='EXACT_DATE_ONLY_NO_CARRY_NO_NETTING_NO_TRADE_POSTING'))
    return result
