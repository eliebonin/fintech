"""Explicit source bond mapping; incomplete/conflicting terms stay proposals.

This adapter does not book trades or invent quote-unit denominations. Customer
quotes are fractions of par, explicitly confirmed by the owner on 23 October.
"""
from datetime import date
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from .reconciliation import source_id


def reviewed_gilt_request(request):
    """ISIN-bound public DMO facts; never overwrite the original source request.

    ACT_ACT_ICMA is our mapping of the DMO's actual/quasi-coupon-period formula,
    not a claim that the input's unspecified ACT/ACT identified that variant.
    """
    from hashlib import sha256
    from .reconciliation import document
    from apps.reference_api.contracts import BondProposalRequest
    facts={
        'GB00BPSNB460':('3.75% Treasury Gilt 2027','2027-03-07','0.0375'),
        'GB00B16NNR78':('4.25% Treasury Gilt 2027','2027-12-07','0.0425'),
        'GB00BSQNRC93':('4.375% Treasury Gilt 2028','2028-03-07','0.04375'),
    }
    if request.isin not in facts:raise ValueError('No reviewed DMO facts for this ISIN')
    name,maturity,coupon=facts[request.isin]
    if request.coupon_type!='FIXED' or request.coupon_rate!=Decimal(coupon) or request.coupon_frequency_per_year!=2:
        raise ValueError('Source coupon conflicts with reviewed DMO terms')
    review=dict(reviewedOn='2026-10-23',isin=request.isin,canonicalName=name,
        maturityDate=maturity,couponRate=coupon,couponFrequencyPerYear=2,dayCountConvention='ACT_ACT_ICMA',
        dayCountMapping='INFERRED_FROM_DMO_QUASI_COUPON_FORMULA',sources=[
            'https://dmo.gov.uk/media/44gmcfe2/jan-mar-2025.pdf',
            'https://dmo.gov.uk/media/334d05fo/yldeqns_v4.pdf'])
    if request.isin=='GB00BPSNB460':review['sources'].append('https://www.dmo.gov.uk/media/5p2hfyex/prosp030124.pdf')
    intent=request.model_dump(mode='json',by_alias=True)
    intent.update({k:review[k] for k in ('canonicalName','maturityDate','dayCountConvention')})
    intent['idempotencyKey']='dmo-reviewed:'+sha256(document(dict(originalKey=request.idempotency_key,review=review))).hexdigest()
    return BondProposalRequest.model_validate(intent),review


def percentage_price(value):
    """Retain the exact source text and disclose any native 12-place rounding."""
    with localcontext() as context:
        context.prec=80
        original=Decimal(value)
        if not original.is_finite() or original<0:raise ValueError('Invalid bond price')
        exact=original*100
        result=exact.quantize(Decimal('0.000000000001'),rounding=ROUND_HALF_EVEN)
        if result>=Decimal('1e18'):raise ValueError('Price exceeds native precision')
        return dict(sourceValue=value,value=format(result,'f'),operation='MULTIPLY_BY_100',
            rounding='ROUND_HALF_EVEN_12DP',rounded=exact!=result)


def bond_requests(bundle,currencies,source,payload):
    """Known terms only. Variant-free ACT/ACT is intentionally not guessed."""
    from apps.reference_api.contracts import BondProposalRequest
    instruments={source_id(r['instrument_id']):r for r in bundle.tables['all_instruments']}
    results=[]
    for bond in bundle.bonds:
        identifier=source_id(bond['instrument_id']);instrument=instruments[identifier]
        if instrument.get('instrument_type')!='BOND':raise ValueError('Bond classification conflicts: '+identifier)
        if instrument.get('currency')!=bond['crncy']:raise ValueError('Bond currency conflicts: '+identifier)
        issues=[];maturity=bond.get('maturity') or instrument.get('maturity_date')
        if bond.get('maturity') and instrument.get('maturity_date') and bond['maturity']!=instrument['maturity_date']:
            issues.append('MATURITY_CONFLICT');maturity=None
        if bond.get('id_isin') and instrument.get('isin') and bond['id_isin']!=instrument['isin']:
            raise ValueError('Bond ISIN conflicts between source files: '+identifier)
        kind={'ZERO COUPON':'ZERO','FIXED':'FIXED'}.get(bond.get('cpn_typ'))
        if not kind:raise ValueError('Unsupported source bond coupon type: '+identifier)
        if kind=='ZERO' and Decimal(bond['cpn'])!=0:raise ValueError('Zero coupon has nonzero source rate: '+identifier)
        if kind=='FIXED':issues.append('DAY_COUNT_VARIANT_REQUIRED')
        start=bond.get('issue_dt')
        if not start:raise ValueError('Missing bond issue date: '+identifier)
        if maturity and date.fromisoformat(maturity)<date.fromisoformat(start):raise ValueError('Maturity precedes issue')
        req=BondProposalRequest(canonicalName=bond.get('security_des') or instrument.get('long_name') or instrument['short_name'],
            internalCode='RECON_'+source.hex[:12]+'_BOND_'+identifier,
            baseCurrencyId=currencies[bond['crncy']],effectiveFrom=start,issueDate=start,
            maturityDate=maturity,interestAccrualDate=bond.get('int_acc_dt') or None,
            firstCouponDate=bond.get('first_cpn_dt') or None,
            isin=bond.get('id_isin') or instrument.get('isin') or None,
            couponType=kind,couponRate=Decimal(bond['cpn'])/100 if kind=='FIXED' else None,
            couponFrequencyPerYear=int(Decimal(bond['cpn_freq'])) if kind=='FIXED' and bond.get('cpn_freq') else None,
            redemptionAmountPerPar=bond.get('redemp_val') or None,
            sourceSystemId=source,sourcePayloadId=payload,
            sourceNamespace='RECON_'+source.hex+'_BOND',sourceExternalId=identifier,
            submissionMode='AUTOMATED',idempotencyKey='recon-bond:'+bundle.digest+':'+identifier)
        results.append(dict(sourceId=identifier,request=req,issues=issues))
    return results


def stage_bonds(c,bundle,tenant,actor,foundation,approve_ready=False):
    """Use normal proposal/decision services, caller-owned transaction and audit.

    Approval is restricted to unambiguous zero-coupon definitions. No price,
    booking convention, position, cash, entitlement or valuation is written.
    """
    from sqlalchemy import select
    from security_master_schema import models as m
    from security_master_schema.strategy_access import require_strategy_action
    from security_master_schema.reference_authority import require_reference_action
    from security_master_schema.access_management import audit
    from apps.reference_api.repository import submit_bond_proposal,decide_bond_proposal
    require_reference_action(c,tenant,actor,'REFERENCE_PROPOSE')
    require_strategy_action(c,tenant,actor,'STRATEGY_WRITE',foundation['strategyId'])
    if approve_ready:require_reference_action(c,tenant,actor,'REFERENCE_APPROVE')
    source=c.execute(select(m.integration_source_system).where(
        m.integration_source_system.c.integration_source_system_id==foundation['sourceId'],
        m.integration_source_system.c.tenant_id==tenant,m.integration_source_system.c.status=='ACTIVE')).mappings().one()
    if foundation['bundleHash']!=bundle.digest:raise ValueError('Bundle differs from retained foundation')
    payload=c.scalar(select(m.source_payload.c.source_payload_id).where(
        m.source_payload.c.integration_source_system_id==source['integration_source_system_id'],
        m.source_payload.c.tenant_id==tenant,m.source_payload.c.external_message_reference==bundle.digest+':bonds'))
    if not payload:raise ValueError('Retained source bond file required')
    currencies=dict(c.execute(select(m.currency.c.currency_code,m.currency.c.currency_id).where(m.currency.c.status=='ACTIVE')).all())
    result=[]
    for item in bond_requests(bundle,currencies,foundation['sourceId'],payload):
        req=item['request'];view=submit_bond_proposal(c,tenant,actor,req)
        if view.status=='PENDING' and approve_ready and not item['issues'] and req.coupon_type=='ZERO':
            # Never create a second canonical bond with an existing identifier.
            existing=c.scalar(select(m.financial_reference_identifier.c.reference_node_id).where(
                m.financial_reference_identifier.c.identifier_value==req.isin)) if req.isin else None
            if existing:item['issues'].append('EXISTING_IDENTIFIER_REQUIRES_MATCH_REVIEW')
            else:
                view=decide_bond_proposal(c,tenant,actor,view.proposal_id,'APPROVED',
                    'Owner-authorized reconciliation import; consistent source zero-coupon terms. No bookings or market-data rights inferred.')
        row=dict(sourceId=item['sourceId'],proposalId=str(view.proposal_id),instrumentId=str(view.instrument_id) if view.instrument_id else None,
            status=view.status,issues=item['issues'])
        event='RECONCILIATION_BOND_'+view.status
        if not c.scalar(select(m.access_audit_event.c.event_id).where(m.access_audit_event.c.tenant_id==tenant,
            m.access_audit_event.c.action==event,m.access_audit_event.c.details['proposalId'].as_string()==str(view.proposal_id))):
            audit(c,actor,tenant,event,dict(bundleHash=bundle.digest,strategyId=str(foundation['strategyId']),**row))
        result.append(row)
    return result


def approve_reviewed_gilts(c,bundle,tenant,actor,foundation):
    """Append reviewed proposals and retire old pending requests atomically.

    Retain raw source receipts/payloads unchanged. All public enrichment and its
    interpretation are retained in the transaction's audit, tied to both requests.
    """
    import json
    from uuid import UUID
    from sqlalchemy import select
    from security_master_schema import models as m
    from security_master_schema.reference_authority import require_reference_action
    from security_master_schema.access_management import audit
    from apps.reference_api.repository import submit_bond_proposal,decide_bond_proposal
    from apps.reference_api.contracts import BondProposalRequest
    from apps.reference_api.proposal_retries import proposal_request_payload
    require_reference_action(c,tenant,actor,'REFERENCE_APPROVE')
    original_rows=stage_bonds(c,bundle,tenant,actor,foundation)
    result=[]
    for original in original_rows:
        if original['status']=='APPROVED':continue
        row=c.execute(select(m.reference_data_proposal).where(
            m.reference_data_proposal.c.reference_data_proposal_id==UUID(original['proposalId']),
            m.reference_data_proposal.c.tenant_id==tenant,
            m.reference_data_proposal.c.source_system_id==foundation['sourceId']).with_for_update()).mappings().one()
        request=BondProposalRequest.model_validate(proposal_request_payload(json.loads(row['proposed_payload'])))
        if request.isin not in {'GB00BPSNB460','GB00B16NNR78','GB00BSQNRC93'}:continue
        revised,review=reviewed_gilt_request(request)
        view=submit_bond_proposal(c,tenant,actor,revised)
        if view.status=='PENDING':
            exists=c.scalar(select(m.financial_reference_identifier.c.reference_node_id).where(
                m.financial_reference_identifier.c.identifier_value==request.isin))
            if exists:raise ValueError('Existing gilt identifier requires match review')
            view=decide_bond_proposal(c,tenant,actor,view.proposal_id,'APPROVED',
                'Public DMO terms verified on 23 October 2026. ACT_ACT_ICMA mapped from actual/quasi-coupon formula; original source retained.')
        if view.status!='APPROVED':raise ValueError('Reviewed gilt proposal is not approved')
        if row['status']=='PENDING':
            decide_bond_proposal(c,tenant,actor,row['reference_data_proposal_id'],'REJECTED',
                'Superseded by separately DMO-reviewed proposal '+str(view.proposal_id)+'; original payload retained unchanged.')
        elif row['status']!='REJECTED':raise ValueError('Original gilt request has unexpected status')
        event='RECONCILIATION_GILT_REVIEW_APPLIED'
        output=dict(sourceId=original['sourceId'],proposalId=str(view.proposal_id),
            originalProposalId=original['proposalId'],instrumentId=str(view.instrument_id),status=view.status)
        if not c.scalar(select(m.access_audit_event.c.event_id).where(m.access_audit_event.c.tenant_id==tenant,
            m.access_audit_event.c.action==event,m.access_audit_event.c.details['proposalId'].as_string()==str(view.proposal_id))):
            audit(c,actor,tenant,event,dict(bundleHash=bundle.digest,strategyId=str(foundation['strategyId']),
                originalSourcePayloadId=str(request.source_payload_id),review=review,**output))
        result.append(output)
    return result
