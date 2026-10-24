"""Reconciliation-only complete mockup terms; production contracts unchanged."""
from decimal import Decimal,localcontext,ROUND_HALF_EVEN
from .reconciliation import source_id


def amc_seed_record(bundle,item):
    """Retain the owner's product classification, without inventing an ETP route."""
    trades=[r for r in bundle.positions if source_id(r['instrument_id'])==source_id(item['instrument_id'])]
    start=min(r['trade_datetime_utc'][:10] for r in trades)
    return dict(instrumentType='ACTIVELY_MANAGED_CERTIFICATE',displayName=item['short_name']+' [AMC]',
        effectiveFrom=start,isin=item.get('isin') or None,currency=item['currency'])


def amc_request(bundle,item,currency,issuer):
    """Complete booking dimensions, without inventing optional legal/price facts."""
    from .reconciliation import source_id
    from apps.reference_api.amc_contracts import AmcProposalRequest
    if item['price_type']!='unit':raise ValueError('Source AMC quote basis must be reviewed explicitly')
    identifier=source_id(item['instrument_id']);record=amc_seed_record(bundle,item)
    evidence='Reconciliation source '+identifier+'; bundle SHA256 '+bundle.digest+'. Owner-classified AMC; source per-unit quotes and currency. Missing redemption, adviser, collateral and publication details remain UNKNOWN/null. Decimal booking precision is a reconciliation convention, not confirmed dealing minimum.'
    return AmcProposalRequest(canonicalName=record['displayName'],isin=record['isin'],issuerOrganisationId=issuer,
        baseCurrencyId=currency,effectiveFrom=record['effectiveFrom'],redemptionModel='UNKNOWN',distributionPolicy='UNKNOWN',
        sourceReference=evidence,idempotencyKey='recon-native-amc:'+bundle.digest+':'+identifier,
        convention=dict(kind='ACTIVELY_MANAGED_CERTIFICATE',effectiveFrom=record['effectiveFrom'],priceCurrencyId=currency,
            sourceReference=evidence,funding='FULLY_FUNDED',quantityUnit='UNITS',priceBasis='UNIT_PRICE',quoteFactor='1',
            quantityMinimum='0.000000000001',quantityIncrement='0.000000000001',accrual='NONE',otcAllowed=True))


def normalized_option_request(bundle,item,underlying,currency):
    """Source-normalized premium units, not an assertion of exchange contract size."""
    import re
    from apps.reference_api.contracts import OptionProposalRequest
    trades=[r for r in bundle.positions if source_id(r['instrument_id'])==source_id(item['instrument_id'])]
    start=min(r['trade_datetime_utc'][:10] for r in trades)
    match=re.fullmatch(r'(Put|Call) SPX Index @ ([0-9.]+) - (\d{4}-\d{2}-\d{2})',item['long_name'])
    if not match or match[3]!=item['maturity_date']:raise ValueError('Supported SPX option description and maturity required')
    multipliers={Decimal(r['unit_multiplier']) for r in trades}
    if multipliers!={Decimal(1)}:raise ValueError('Source-normalized option requires explicit unit multiplier 1')
    return OptionProposalRequest(canonicalName=item['short_name']+' [source-normalized mockup contract]',
        effectiveFrom=start,underlyingId=underlying,optionType='PUT' if match[1]=='Put' else 'CALL',strike=match[2],
        strikeCurrencyId=currency,premiumCurrencyId=currency,premiumMultiplier='1',deliverableUnits='1',
        expiryDate=match[3],lastTradingAtUtc=match[3]+'T21:00:00Z',exerciseStyle='EUROPEAN',settlementMethod='CASH',
        idempotencyKey='recon-option:'+bundle.digest+':'+item['instrument_id'])


def swap_plan(bundle,instrument,source,references,currencies,total_profile,day_counts):
    """Complete normal GenericSwapTerms with owner-authorized mockup metadata.

    Actual executions/marks are not transformed here. Every nonsourced contract
    convention is returned for durable audit and is disclosed on the contract.
    """
    from apps.reference_api.swap_creation_contracts import SwapProposalRequest
    identifier=source_id(source['instrument_id']);assumptions={}
    frequency={'1':'ANNUAL','4':'QUARTERLY','12':'MONTHLY'}.get(source.get('swap_payment_per_year'))
    if not frequency:raise ValueError('Unsupported source payment frequency')
    kind=instrument['price_type'];unit='NOMINAL' if kind=='notional' else 'UNITS'
    if kind not in ('notional','unit','unitlev'):raise ValueError('Unknown swap quantity basis')
    with localcontext() as ctx:
        ctx.prec=80
        supplied=bool(source.get('notional'))
        if supplied:notional=Decimal(source['notional'])
        else:
            trades=[r for r in bundle.positions if source_id(r['instrument_id'])==identifier]
            if not trades:raise ValueError('Mock contract size requires an observed trade')
            units=abs(Decimal(trades[0]['quantity'])).quantize(Decimal('0.000000000001'),rounding=ROUND_HALF_EVEN)
            notional=units*(100 if unit=='UNITS' else 1)
            assumptions['contractualNotional']='MOCKUP from first observed absolute booking, 12-place metadata precision; reference notional 100 per unit, before leverage.'
        if not notional.is_finite() or notional<=0:raise ValueError('Positive finite contract notional required')
        values={}
        if unit=='UNITS':
            values=dict(contractualUnits=str(notional/100),notionalPerUnit='100')
            assumptions['notionalPerUnit']='MOCKUP reference denomination of 100 in quote currency; not a provider fact or exposure reconciliation.'
            assumptions['contractualUnits']='MOCKUP contract size = contractual notional / 100; separate from actual booked quantities.'
    currency=currencies[instrument['currency']]
    spread=Decimal(source.get('floating_spread_bps') or '0')/10000
    funding=source_id(source.get('funding_instrument_id'))
    if not funding and spread:
        fallback={'USD':'1396','GBP':'1048'}.get(instrument['currency'])
        if not fallback:raise ValueError('No configured mockup funding reference for currency')
        funding=fallback;assumptions['fundingReferenceId']='MOCKUP currency-appropriate overnight index; source omitted funding identity.'
    assumptions.update(performanceDirection='MOCKUP RECEIVE; actual buy/sell sign stays on each original trade.',
        performanceResetFrequency='INFERRED from source payment count, not a confirmed reset schedule.',
        redemptionRule='MOCKUP TERMINATE on the supplied maturity date.')
    funding_values={}
    if funding:
        funding_values=dict(fundingReferenceId=references[funding],fundingSpread=str(spread),fundingNotionalBasis='LEVERAGED_NOMINAL',
            dayCountConventionId=day_counts['ACT_365F' if funding=='1048' else 'ACT_360'],
            interestCalculationMethod='MOCKUP compounded overnight in arrears; no source fixing or funding schedule confirmed.',
            fundingObservationDescription='MOCKUP no observation lag. No funding cash flows or benchmark observations generated.',
            fundingResetFrequency=frequency,fundingPaymentFrequency=frequency)
        assumptions.update(fundingNotionalBasis='MOCKUP LEVERAGED_NOMINAL',dayCountConventionId='MOCKUP ACT/365F for SONIA; ACT/360 otherwise.',
            interestCalculationMethod='MOCKUP overnight compounded in arrears without observation lag.',
            fundingResetFrequency='INFERRED from source payment count.',fundingPaymentFrequency='INFERRED same frequency as source swap payments.')
    if source.get('funded_return_type')=='PR' or not source.get('return_type'):
        assumptions['returnBasis']='MOCKUP TOTAL performance of the supplied index variant; source return descriptors retained independently, no payoff/model equivalence claimed.'
    terms=dict(schemaVersion=1,tenantIdentifier=bundle.name+'-SOURCE-SWAP-'+identifier,
        performanceReferenceId=references[source_id(source['funded_instrument_id'])],contractualNotional=str(notional),
        quantityUnit=unit,notionalCurrencyId=currency,effectiveDate=instrument['effective_date'],maturityDate=instrument['maturity_date'],
        performanceDirection='RECEIVE',returnBasis='TOTAL',returnProfileId=total_profile,leverage=source['leverage'],
        quoteCurrencyId=currency,quoteFactor='1',sourceReference='RECONCILIATION MOCKUP TERMS; source '+identifier+'; bundle SHA256 '+bundle.digest+
            '. Owner authorized inferred/invented missing metadata. Supplied trade quantities/quotes remain separate. See retained RECONCILIATION_PRODUCTS_SEEDED audit.',
        financingTreatment='SEPARATE' if funding else 'NONE',performanceResetFrequency=frequency,redemptionRule='TERMINATE',**values,**funding_values)
    request=SwapProposalRequest(canonicalName=instrument['short_name']+' [mockup terms]',terms=terms,
        idempotencyKey='recon-swap:'+bundle.digest+':'+identifier)
    return dict(request=request,assumptions=assumptions,sourceTerms=dict(source))


def seed_products(c,bundle,tenant,actor,foundation):
    """Caller-owned, audited local seed using existing creation/approval paths.

    Rate identities use the established guarded seed pattern; no rate observations,
    source rights, trades, valuations or application validation changes occur.
    """
    from sqlalchemy import select
    from security_master_schema import models as m
    from security_master_schema.reference_authority import require_reference_action
    from security_master_schema.strategy_access import require_strategy_action
    from security_master_schema.access_management import audit
    from apps.reference_api.contracts import IndexProposalRequest
    from apps.reference_api.repository import submit_index_proposal,decide_index_proposal
    from apps.reference_api.product_booking import submit_proposal,decide_proposal
    require_reference_action(c,tenant,actor,'REFERENCE_PROPOSE')
    require_reference_action(c,tenant,actor,'REFERENCE_APPROVE')
    require_strategy_action(c,tenant,actor,'STRATEGY_WRITE',foundation['strategyId'])
    source=c.execute(select(m.integration_source_system).where(m.integration_source_system.c.integration_source_system_id==foundation['sourceId'],
        m.integration_source_system.c.tenant_id==tenant,m.integration_source_system.c.status=='ACTIVE')).mappings().one()
    if foundation['bundleHash']!=bundle.digest:raise ValueError('Source bundle differs')
    payload=c.scalar(select(m.source_payload.c.source_payload_id).where(m.source_payload.c.tenant_id==tenant,
        m.source_payload.c.integration_source_system_id==foundation['sourceId'],m.source_payload.c.external_message_reference==bundle.digest+':all_instruments'))
    if not payload:raise ValueError('Retained source instrument file required')
    currencies=dict(c.execute(select(m.currency.c.currency_code,m.currency.c.currency_id).where(m.currency.c.status=='ACTIVE')).all())
    profiles=dict(c.execute(select(m.return_profile.c.profile_code,m.return_profile.c.return_profile_id).where(m.return_profile.c.status=='ACTIVE')).all())
    counts=dict(c.execute(select(m.day_count_convention.c.code,m.day_count_convention.c.day_count_convention_id).where(m.day_count_convention.c.status=='ACTIVE')).all())
    instruments={source_id(r['instrument_id']):r for r in bundle.tables['all_instruments']}
    prefix='RECON_'+source['integration_source_system_id'].hex
    references={};swaps={};assumptions={};source_terms={}
    for identifier,item in instruments.items():
        if item['instrument_type']!='INDEX':continue
        if identifier in ('1048','1396'):
            code=prefix+'_RATE_'+identifier
            node=c.scalar(select(m.financial_reference_node.c.reference_node_id).where(m.financial_reference_node.c.internal_code==code))
            if node:
                c.execute(select(m.reference_node_scope).where(m.reference_node_scope.c.reference_node_id==node,
                    m.reference_node_scope.c.owner_tenant_id==tenant,m.reference_node_scope.c.scope_type=='TENANT_PRIVATE',m.reference_node_scope.c.status=='ACTIVE')).one()
            else:
                kind=c.scalar(select(m.reference_node_type.c.reference_node_type_id).where(m.reference_node_type.c.type_code=='RATE_INDEX',m.reference_node_type.c.status=='ACTIVE'))
                if kind is None:raise ValueError('Active rate-index catalogue required')
                node=c.scalar(m.financial_reference_node.insert().values(reference_node_type_id=kind,
                    canonical_name=item['short_name']+' [reconciliation reference]',internal_code=code,status='ACTIVE',is_tradable=False)
                    .returning(m.financial_reference_node.c.reference_node_id))
                c.execute(m.reference_node_scope.insert().values(reference_node_id=node,scope_type='TENANT_PRIVATE',owner_tenant_id=tenant,status='ACTIVE'))
            references[identifier]=node
            continue
        uses=[r for r in bundle.tables['swaps'] if source_id(r['funded_instrument_id'])==identifier]
        descriptors={r.get('funded_return_type') or r.get('return_type') or 'TR' for r in uses}
        if len(descriptors)>1:raise ValueError('Conflicting source index return profiles: '+identifier)
        descriptor=next(iter(descriptors),'TR')
        if descriptor not in ('TR','PR'):raise ValueError('Unsupported source index return descriptor')
        profile=profiles['PRICE_RETURN' if descriptor=='PR' else 'GROSS_TOTAL_RETURN']
        req=IndexProposalRequest(canonicalName=item['short_name']+' [reconciliation]',internalCode=prefix+'_INDEX_'+identifier,
            effectiveFrom=bundle.manifest['earliestTradeDate'],indexKind='QIS',returnProfileId=profile,
            baseCurrencyId=currencies[item['currency']],methodologyReference='Reconciliation export. QIS classification inferred; return-profile mapping from supplied swap descriptors. Not a validated provider methodology.',
            submissionMode='AUTOMATED',sourceSystemId=foundation['sourceId'],sourcePayloadId=payload,
            sourceExternalId=identifier,sourceNamespace=prefix+'_REFERENCE',idempotencyKey='recon-index:'+bundle.digest+':'+identifier)
        view=submit_index_proposal(c,tenant,actor,req)
        if view.status=='PENDING':view=decide_index_proposal(c,tenant,actor,view.proposal_id,'APPROVED',
            'Owner-authorized reconciliation seed. Source identity/currency retained; QIS/return-profile mapping disclosed as inferred metadata. No provider rights granted.')
        if view.status!='APPROVED' or not view.index_id:raise ValueError('Reconciliation index is not approved')
        references[identifier]=view.index_id
    for row in bundle.tables['swaps']:
        identifier=source_id(row['instrument_id'])
        plan=swap_plan(bundle,instruments[identifier],row,references,currencies,profiles['GROSS_TOTAL_RETURN'],counts)
        view=submit_proposal(c,tenant,actor,plan['request'])
        if view.status=='PENDING':view=decide_proposal(c,tenant,actor,view.proposal_id,'APPROVED',
            'Owner-authorized MOCKUP completion of missing source terms. Existing complete swap model and validators unchanged. No actual contractual confirmation or valuation support claimed.')
        if view.status!='APPROVED' or not view.reference_node_id:raise ValueError('Reconciliation swap is not approved')
        swaps[identifier]=view.reference_node_id;assumptions[identifier]=plan['assumptions'];source_terms[identifier]=plan['sourceTerms']
    event='RECONCILIATION_PRODUCTS_SEEDED'
    result=dict(references=references,swaps=swaps)
    if not c.scalar(select(m.access_audit_event.c.event_id).where(m.access_audit_event.c.tenant_id==tenant,
        m.access_audit_event.c.action==event,m.access_audit_event.c.details['bundleHash'].as_string()==bundle.digest)):
        audit(c,actor,tenant,event,dict(bundleHash=bundle.digest,sourceId=str(foundation['sourceId']),strategyId=str(foundation['strategyId']),
            instrumentSourcePayloadId=str(payload),references={k:str(v) for k,v in references.items()},swaps={k:str(v) for k,v in swaps.items()},
            assumptions=assumptions,originalSwapTerms=source_terms,financialPostingStatus='NOT_POSTED',productModelsChanged=False))
    return result


def seed_additional(c,bundle,tenant,actor,foundation):
    """Create AMC and option through their normal governed approval services."""
    from sqlalchemy import select
    from security_master_schema import models as m
    from security_master_schema.reference_authority import require_reference_action
    from security_master_schema.strategy_access import require_strategy_action
    from security_master_schema.access_management import audit
    from apps.reference_api.contracts import IndexProposalRequest
    from apps.reference_api.repository import decide_etp_proposal,submit_index_proposal,decide_index_proposal
    from apps.reference_api.option_onboarding import submit_option_proposal,decide_option_proposal
    require_reference_action(c,tenant,actor,'REFERENCE_PROPOSE')
    require_reference_action(c,tenant,actor,'REFERENCE_APPROVE')
    require_strategy_action(c,tenant,actor,'STRATEGY_WRITE',foundation['strategyId'])
    if foundation['bundleHash']!=bundle.digest:raise ValueError('Source bundle differs')
    payload=c.scalar(select(m.source_payload.c.source_payload_id).join(m.integration_source_system).where(
        m.source_payload.c.integration_source_system_id==foundation['sourceId'],m.source_payload.c.tenant_id==tenant,
        m.integration_source_system.c.tenant_id==tenant,m.integration_source_system.c.status=='ACTIVE',
        m.source_payload.c.external_message_reference==bundle.digest+':all_instruments'))
    if not payload:raise ValueError('Retained owned instrument file required')
    currencies=dict(c.execute(select(m.currency.c.currency_code,m.currency.c.currency_id).where(m.currency.c.status=='ACTIVE')).all())
    amcs=set(bundle.manifest['amcSourceIds']);certificates={};options={};assumptions={};pending={}
    for item in bundle.tables['all_instruments']:
        identifier=source_id(item['instrument_id'])
        if identifier in amcs:
            record=amc_seed_record(bundle,item)
            legacy=c.execute(select(m.reference_data_proposal).where(
                m.reference_data_proposal.c.tenant_id==tenant,
                m.reference_data_proposal.c.source_system_id==foundation['sourceId'],
                m.reference_data_proposal.c.idempotency_key=='recon-amc:'+bundle.digest+':'+identifier,
                m.reference_data_proposal.c.proposal_type=='CREATE_ETP').with_for_update()).mappings().one_or_none()
            if legacy and legacy['status']=='APPROVED':
                raise ValueError('AMC was already materialized through the wrong ETP route; explicit remediation required')
            if legacy and legacy['status']=='PENDING':
                decide_etp_proposal(c,tenant,actor,legacy['reference_data_proposal_id'],'REJECTED',
                    'Incorrect import mapping superseded: owner classifies this product as ACTIVELY_MANAGED_CERTIFICATE (AMC), not ETI. Original payload retained; no instrument created.')
            issuer_name=(item.get('issuer') or '').strip()
            if not issuer_name:
                pending[identifier]=dict(**record,reason='AMC_SOURCE_ISSUER_MISSING')
                continue
            # Source-derived operational identity, not a guessed LEI/legal name.
            code='SRC_'+foundation['sourceId'].hex+'_AMC_ISSUER_'+identifier
            issuer=c.scalar(select(m.organisation.c.organisation_id).join(m.entity).where(m.entity.c.entity_code==code))
            if issuer is None:
                entity=c.scalar(m.entity.insert().values(entity_code=code,display_name=issuer_name,status='ACTIVE').returning(m.entity.c.entity_id))
                issuer=c.scalar(m.organisation.insert().values(entity_id=entity,organisation_type='OPERATIONAL_REFERENCE',
                    display_name=issuer_name,status='ACTIVE').returning(m.organisation.c.organisation_id))
            elif c.scalar(select(m.organisation.c.display_name).where(m.organisation.c.organisation_id==issuer))!=issuer_name:
                raise ValueError('Source AMC issuer label changed; explicit reconciliation required')
            from apps.reference_api.product_booking import submit_proposal,decide_proposal
            native=submit_proposal(c,tenant,actor,amc_request(bundle,item,currencies[item['currency']],issuer))
            if native.status=='PENDING':native=decide_proposal(c,tenant,actor,native.proposal_id,'APPROVED',
                'Owner-confirmed AMC. Source identity, issuer label, currency and unit quote retained. Issuer legal identity unverified. Decimal minimum/increment are mockup reconciliation configuration; no adviser, redemption, fee or publication facts invented.')
            if native.status!='APPROVED' or not native.reference_node_id:raise ValueError('Native AMC is not approved')
            certificates[identifier]=native.reference_node_id
            assumptions[identifier]=dict(classification='OWNER_CONFIRMED AMC; not ETI, fund or bond.',
                effectiveFrom='First observed source execution; not a confirmed issue date.',issuer=str(issuer),
                issuerIdentity='Source operational name only; legal identity and LEI unverified.',
                bookingPrecision='MOCKUP 12-decimal unit minimum/increment; not a confirmed dealing restriction.',
                supersededProposalId=str(legacy['reference_data_proposal_id']) if legacy else None)
        elif item['instrument_type']=='VANILLA':
            profile=c.scalar(select(m.return_profile.c.return_profile_id).where(m.return_profile.c.profile_code=='PRICE_RETURN',m.return_profile.c.status=='ACTIVE'))
            start=min(r['trade_datetime_utc'][:10] for r in bundle.positions if source_id(r['instrument_id'])==identifier)
            index_request=IndexProposalRequest(canonicalName='SPX Index [reconciliation reference]',internalCode='RECON_'+foundation['sourceId'].hex+'_SPX',
                effectiveFrom=start,indexKind='PUBLIC',returnProfileId=profile,baseCurrencyId=currencies['USD'],
                methodologyReference='SPX identity inferred from source option description. No provider index prices or rights created.',
                submissionMode='AUTOMATED',sourceSystemId=foundation['sourceId'],sourcePayloadId=payload,
                idempotencyKey='recon-spx:'+bundle.digest)
            index=submit_index_proposal(c,tenant,actor,index_request)
            if index.status=='PENDING':index=decide_index_proposal(c,tenant,actor,index.proposal_id,'APPROVED',
                'Private SPX reference identity for source option; no provider data or rights seeded.')
            if index.status!='APPROVED' or not index.index_id:raise ValueError('SPX reference not approved')
            request=normalized_option_request(bundle,item,index.index_id,currencies[item['currency']])
            view=submit_option_proposal(c,tenant,actor,request)
            if view.status=='PENDING':view=decide_option_proposal(c,tenant,actor,view.proposal_id,'APPROVED',
                'MOCKUP source-normalized option, multiplier/deliverable 1 to preserve exported unit economics; not an exchange-standard SPX contract. European/cash and 21:00 UTC expiry cutoff are seed assumptions. Effective availability uses first observed trade.')
            if view.status!='APPROVED' or not view.reference_node_id:raise ValueError('Option not approved')
            options[identifier]=view.reference_node_id
            assumptions[identifier]=dict(premiumMultiplier='Source-normalized 1; not an exchange-standard SPX contract multiplier.',
                deliverableUnits='MOCKUP 1',exerciseStyle='MOCKUP EUROPEAN',settlementMethod='MOCKUP CASH',
                lastTradingAtUtc='MOCKUP expiry date at 21:00 UTC',effectiveFrom='First observed trade; source effective date incorrectly equals expiry.')
    from hashlib import sha256
    from .reconciliation import document
    result=dict(certificates=certificates,options=options,pending=pending);event='RECONCILIATION_ADDITIONAL_INSTRUMENTS_SEEDED'
    result_hash=sha256(document(dict(certificates={k:str(v) for k,v in certificates.items()},options={k:str(v) for k,v in options.items()},pending=pending))).hexdigest()
    if not c.scalar(select(m.access_audit_event.c.event_id).where(m.access_audit_event.c.tenant_id==tenant,
        m.access_audit_event.c.action==event,m.access_audit_event.c.details['bundleHash'].as_string()==bundle.digest,
        m.access_audit_event.c.details['resultHash'].as_string()==result_hash)):
        audit(c,actor,tenant,event,dict(bundleHash=bundle.digest,resultHash=result_hash,sourceId=str(foundation['sourceId']),strategyId=str(foundation['strategyId']),
            sourcePayloadId=str(payload),certificates={k:str(v) for k,v in certificates.items()},options={k:str(v) for k,v in options.items()},
            pending=pending,assumptions=assumptions,financialPostingStatus='NOT_POSTED',productModelsChanged=False))
    return result
