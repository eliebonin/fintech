"""Disclosed local estimates for absent historical settlement-only accrual.

Never changes supplied clean execution prices, quantities or source CSV rows.
These estimates are not confirmations of actual settlement cash or inflation
index ratios/ex-dividend entitlement. Market P&L uses the supplied clean marks.
"""
from datetime import date
from decimal import Decimal,localcontext
from dateutil.relativedelta import relativedelta
from sqlalchemy import select,func
from security_master_schema import models as m
from security_master_schema.access_management import audit
from .reconciliation import source_id
from .reconciliation_precision import native_decimal


def estimated_settlement_accrual(row,bond):
    if row.get('accrued_interests'):return None
    rate=Decimal(bond['cpn'])/100
    if rate==0:return dict(value='0',method='SOURCE_ZERO_COUPON_RATE',estimated=False)
    frequency=int(Decimal(bond['cpn_freq']));months=12//frequency
    if frequency not in (1,2,4,12):raise ValueError('Unsupported regular coupon frequency')
    settlement=date.fromisoformat(row['settlement_date']);maturity=date.fromisoformat(bond['maturity'])
    end=maturity
    while end-relativedelta(months=months)>settlement:end-=relativedelta(months=months)
    previous=end-relativedelta(months=months)
    if settlement==end:previous=end;end=end+relativedelta(months=months)
    start=max(previous,date.fromisoformat(bond.get('int_acc_dt') or bond['issue_dt']))
    with localcontext() as ctx:
        ctx.prec=100
        if settlement<start:raise ValueError('Settlement precedes sourced interest accrual start')
        per_nominal=rate/Decimal(frequency)*Decimal((settlement-start).days)/Decimal((end-previous).days)
        amount=Decimal(row['quantity'])*per_nominal
        # The legacy export stores bought accrual as a negative cash flow.
        cashflow=-amount
        result=native_decimal(format(cashflow,'f'))
    return dict(value=result['value'],method='ESTIMATED_REGULAR_ACT_ACT_COUPON_AT_SETTLEMENT',estimated=True,
        periodStart=str(start),periodEnd=str(end),settlementDate=str(settlement),normalization=result,
        limitations='Unconfirmed ex-dividend entitlement and inflation indexation. Settlement-only reconciliation estimate, not an actual cash confirmation.')


def request_factory(bundle):
    from .reconciliation_postings import booking_request
    bonds={source_id(r['instrument_id']):r for r in bundle.tables['bonds']}
    def make(row,node,strategy,counterparty,source,context,properties):
        estimate=estimated_settlement_accrual(row,bonds[source_id(row['instrument_id'])]) if context.kind=='BOND' else None
        normalized=dict(row,accrued_interests=estimate['value']) if estimate else row
        request,proof=booking_request(normalized,node,strategy,counterparty,source,context,properties)
        if context.kind=='BOND':
            # Keep nominal unchanged and the maximum quote precision whose
            # consideration fits the existing native fixed-scale contract.
            with localcontext() as ctx:
                ctx.prec=100
                for places in range(12,-1,-1):
                    candidate=native_decimal(row['price'],scale='100',decimal_places=places)
                    amount=request.quantity*Decimal(candidate['value'])/100
                    if amount==amount.quantize(Decimal('1e-12')):
                        if abs(Decimal(candidate['delta']))>Decimal('1e-9'):
                            raise ValueError('Native bond consideration would require material quote truncation')
                        request.execution_price=Decimal(candidate['value'])
                        proof['price']=dict(candidate,reason='MAXIMUM_QUOTE_PRECISION_WITH_UNCHANGED_NOMINAL_AND_12DP_CONSIDERATION')
                        break
                else:raise ValueError('No exact native bond consideration preserving nominal')
        if estimate:
            proof['missingSourceAccrualCompletion']=estimate
            request.settlement_evidence+=' '+('ESTIMATED historical accrued interest from sourced regular coupon terms; not confirmed settlement cash.' if estimate['estimated'] else 'Missing source accrued confirmed zero from sourced coupon rate zero.')
            request.comment+=' Missing source settlement accrual completed using '+estimate['method']+'.'
        return request,proof
    return make


def extend_when_issued(c,bundle,tenant,actor,foundation,nodes):
    """Append unchanged terms for an evidenced pre-issue/when-issued execution.

    Issue and settlement facts are not backdated. All original definitions and
    booked evidence remain retained. Only Treasury bills with actual settlement
    on/after issue qualify for this narrowly bounded local completion.
    """
    from apps.reference_api.product_booking import submit_proposal,decide_proposal
    from apps.reference_api.product_booking_contracts import ConventionProposalRequest
    import json
    rows={source_id(r['instrument_id']):r for r in bundle.tables['bonds']}
    for iid,node in nodes.items():
        source=rows[iid];trades=[r for r in bundle.positions if source_id(r['instrument_id'])==iid]
        if not trades:continue
        first=min(date.fromisoformat(r['trade_datetime_utc'][:10]) for r in trades)
        instrument=c.execute(select(m.instrument).where(m.instrument.c.instrument_node_id==node).with_for_update()).mappings().one()
        if instrument['effective_from']<=first:continue
        if source['cpn_typ']!='ZERO COUPON' or not source['id_isin'].startswith('GB') or any(date.fromisoformat(r['settlement_date'])<date.fromisoformat(source['issue_dt']) for r in trades):
            raise ValueError('Historical bond date requires separate review: '+iid)
        for table,pk in ((m.instrument_definition_version,'instrument_definition_version_id'),(m.bond_terms,'bond_terms_id')):
            current=c.execute(select(table).where(table.c.instrument_node_id==node,table.c.is_current).with_for_update()).mappings().one()
            c.execute(table.update().where(table.c[pk]==current[pk]).values(is_current=False,**({'status':'SUPERSEDED'} if 'status' in table.c else {})))
            fields=dict(current);fields.pop(pk);fields.update(sequence_no=current['sequence_no']+1,effective_from=first)
            if 'status' in fields:fields.update(status='APPROVED',approved_by_user_account_id=actor,approved_at_utc=c.scalar(select(func.now())))
            c.execute(table.insert().values(**fields))
            if table is m.instrument_definition_version:c.execute(m.instrument.update().where(m.instrument.c.instrument_node_id==node).values(effective_from=first,sequence_no=fields['sequence_no']))
        prior=c.execute(select(m.instrument_booking_convention).where(m.instrument_booking_convention.c.instrument_node_id==node).order_by(m.instrument_booking_convention.c.version_no.desc()).limit(1)).mappings().one()
        convention=json.loads(prior['convention_payload']);convention.update(effectiveFrom=str(first),sourceReference='Evidenced when-issued execution; actual issue/settlement retained. Bundle '+bundle.digest)
        p=submit_proposal(c,tenant,actor,ConventionProposalRequest(instrumentId=node,convention=convention,idempotencyKey='fcpgf-when-issued:'+bundle.digest+':'+iid))
        if p.status=='PENDING':decide_proposal(c,tenant,actor,p.proposal_id,'APPROVED','Source Treasury-bill when-issued execution; preserve true issue date and settled-on/after-issue checks.')
        audit(c,actor,tenant,'RECONCILIATION_WHEN_ISSUED_COVERAGE',dict(sourceId=str(foundation['sourceId']),bundleHash=bundle.digest,
            instrumentId=str(node),firstExecution=str(first),actualIssueDate=source['issue_dt'],oldEffectiveFrom=str(instrument['effective_from']),oldEvidenceRewritten=False))
