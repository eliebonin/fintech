"""Local FCPGF source completion, never a product onboarding interface.

Only missing contractual metadata is synthetic. Original executions and marks
are retained by the calling operator. Normal native approvals remain in force.
"""
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID
from sqlalchemy import select, func
from security_master_schema import models as m
from security_master_schema.access_management import audit
from security_master_schema.reference_authority import require_reference_action
from .reconciliation import source_id


def source_instruments(bundle):
    return {source_id(r['instrument_id']):r for r in bundle.tables['all_instruments']}


def receipt(c,bundle,foundation,kind):
    return c.scalar(select(m.source_payload.c.source_payload_id).where(
        m.source_payload.c.integration_source_system_id==foundation['sourceId'],
        m.source_payload.c.external_message_reference==bundle.digest+':'+kind))


def catalogue(c,table,code_column,id_column):
    return dict(c.execute(select(table.c[code_column],table.c[id_column]).where(table.c.status=='ACTIVE')).all())


def native_reference(c,tenant,actor,foundation,bundle,identifier,kind,name,currency,start,*,tradable=True):
    """Guarded private seed for types without a public creation command.

    It cannot adopt an arbitrary node or overwrite an approved definition.
    Financial executions still go through native booking commands.
    """
    require_reference_action(c,tenant,actor,'REFERENCE_APPROVE')
    code='RECON_'+foundation['sourceId'].hex+'_'+kind+'_'+identifier
    node=c.scalar(select(m.financial_reference_node.c.reference_node_id).where(m.financial_reference_node.c.internal_code==code))
    if node:
        c.execute(select(m.reference_node_scope).where(m.reference_node_scope.c.reference_node_id==node,
            m.reference_node_scope.c.owner_tenant_id==tenant,m.reference_node_scope.c.scope_type=='TENANT_PRIVATE',m.reference_node_scope.c.status=='ACTIVE')).one()
        current=c.execute(select(m.instrument,m.instrument_type.c.type_code).join(m.instrument_type).where(m.instrument.c.instrument_node_id==node)).mappings().one()
        if current['type_code']!=kind or current['base_currency_id']!=currency or current['effective_from']!=start:
            raise ValueError('Existing private reference differs from requested source facts')
        return node
    types=catalogue(c,m.reference_node_type,'type_code','reference_node_type_id')
    node=c.scalar(m.financial_reference_node.insert().values(reference_node_type_id=types['INSTRUMENT'],
        canonical_name=name[:500],internal_code=code,status='ACTIVE',is_tradable=tradable).returning(m.financial_reference_node.c.reference_node_id))
    c.execute(m.reference_node_scope.insert().values(reference_node_id=node,scope_type='TENANT_PRIVATE',owner_tenant_id=tenant,status='ACTIVE'))
    instrument_types=catalogue(c,m.instrument_type,'type_code','instrument_type_id')
    values=dict(instrument_node_id=node,instrument_type_id=instrument_types[kind],asset_class='FUND' if kind=='FUND_SHARE_CLASS' else 'DERIVATIVE',
        base_currency_id=currency,effective_from=start,is_current=True,sequence_no=1)
    c.execute(m.instrument.insert().values(**values))
    c.execute(m.instrument_definition_version.insert().values(**values,status='APPROVED',source_payload_id=receipt(c,bundle,foundation,'all_instruments'),
        approved_by_user_account_id=actor,approved_at_utc=datetime.now(timezone.utc)))
    audit(c,actor,tenant,'RECONCILIATION_PRIVATE_REFERENCE_CREATED',dict(sourceId=str(foundation['sourceId']),bundleHash=bundle.digest,
        strategyId=str(foundation['strategyId']),sourceInstrumentId=identifier,instrumentId=str(node),kind=kind,
        tradable=tradable,completion='SOURCE_IDENTITY_WITH_DISCLOSED_RECONCILIATION_METADATA'))
    return node


def classify(c,tenant,actor,bundle,foundation,node,code,start):
    domain='RECON_SOURCE_PRODUCT'
    tax=c.scalar(select(m.taxonomy.c.taxonomy_id).where(m.taxonomy.c.taxonomy_code==domain))
    if not tax:tax=c.scalar(m.taxonomy.insert().values(taxonomy_code=domain,display_name='Reconciliation source product',
        description='Source classification retained separately from the native economic instrument type.',applies_to='INSTRUMENT').returning(m.taxonomy.c.taxonomy_id))
    value=c.scalar(select(m.taxonomy_value.c.taxonomy_value_id).where(m.taxonomy_value.c.taxonomy_id==tax,m.taxonomy_value.c.value_code==code))
    if not value:value=c.scalar(m.taxonomy_value.insert().values(taxonomy_id=tax,value_code=code,display_name=code,
        description='Owner-supplied reconciliation taxonomy; not a replacement native instrument type.').returning(m.taxonomy_value.c.taxonomy_value_id))
    old=c.scalar(select(m.instrument_taxonomy_assignment.c.instrument_taxonomy_assignment_id).where(
        m.instrument_taxonomy_assignment.c.instrument_node_id==node,m.instrument_taxonomy_assignment.c.taxonomy_value_id==value))
    if not old:
        c.execute(m.instrument_taxonomy_assignment.insert().values(instrument_node_id=node,taxonomy_value_id=value,
            effective_from=start,source_system_id=str(foundation['sourceId'])))
        audit(c,actor,tenant,'RECONCILIATION_SOURCE_TAXONOMY',dict(bundleHash=bundle.digest,instrumentId=str(node),taxonomyCode=code))


def seed_bonds(c,bundle,tenant,actor,foundation):
    from apps.reference_api.contracts import BondProposalRequest
    from apps.reference_api.repository import submit_bond_proposal,decide_bond_proposal
    from apps.reference_api.product_booking import submit_proposal,decide_proposal
    from apps.reference_api.product_booking_contracts import ConventionProposalRequest
    ins=source_instruments(bundle);currencies=catalogue(c,m.currency,'currency_code','currency_id');nodes={}
    for row in bundle.tables['bonds']:
        iid=source_id(row['instrument_id']);item=ins[iid]
        if item['instrument_type']!='BOND':continue
        isin=row.get('id_isin') or item.get('isin')
        # Existing same-tenant bonds may be reused after economic agreement checks.
        existing=c.execute(select(m.instrument.c.instrument_node_id).join(m.financial_reference_identifier,
            m.financial_reference_identifier.c.reference_node_id==m.instrument.c.instrument_node_id).join(m.reference_node_scope,
            m.reference_node_scope.c.reference_node_id==m.instrument.c.instrument_node_id).where(
            m.financial_reference_identifier.c.identifier_value==isin,m.reference_node_scope.c.owner_tenant_id==tenant,
            m.reference_node_scope.c.scope_type=='TENANT_PRIVATE',m.instrument.c.base_currency_id==currencies[item['currency']])).scalars().all()
        if len(set(existing))>1:raise ValueError('Ambiguous private bond identity: '+isin)
        kind='ZERO' if row['cpn_typ']=='ZERO COUPON' else 'FIXED'
        rate=Decimal(row['cpn'])/100 if kind=='FIXED' else None
        maturity=date.fromisoformat(row['maturity'])
        if existing:
            node=existing[0]
            terms=c.execute(select(m.bond_terms).where(m.bond_terms.c.instrument_node_id==node,m.bond_terms.c.is_current)).mappings().one()
            dates=c.execute(select(m.instrument_dates).where(m.instrument_dates.c.instrument_node_id==node)).mappings().one()
            if dates['maturity_date']!=maturity or terms['coupon_type']!=kind or (rate is not None and terms['coupon_rate']!=rate):
                raise ValueError('Existing bond terms disagree with source: '+isin)
        else:
            start=min([row['issue_dt']]+[r['trade_datetime_utc'][:10] for r in bundle.positions if source_id(r['instrument_id'])==iid])
            # ACT/ACT variant is inferred for local reconciliation, not asserted
            # to have been supplied by the incomplete source descriptor.
            req=BondProposalRequest(canonicalName=row.get('security_des') or item['short_name'],internalCode='RECON_'+foundation['sourceId'].hex+'_BOND_'+iid,
                isin=isin,baseCurrencyId=currencies[item['currency']],effectiveFrom=start,issueDate=row['issue_dt'],maturityDate=row['maturity'],
                interestAccrualDate=row.get('int_acc_dt') or None,firstCouponDate=row.get('first_cpn_dt') or None,couponType=kind,
                couponRate=rate,couponFrequencyPerYear=int(Decimal(row['cpn_freq'])) if kind=='FIXED' else None,
                dayCountConvention='ACT_ACT_ICMA' if kind=='FIXED' else 'ACT_365F',parAmount='.01',redemptionAmountPerPar='100',
                sourceSystemId=foundation['sourceId'],sourcePayloadId=receipt(c,bundle,foundation,'bonds'),sourceNamespace='RECON_'+foundation['sourceId'].hex+'_BOND',
                sourceExternalId=iid,submissionMode='AUTOMATED',idempotencyKey='fcpgf-bond:'+bundle.digest+':'+iid)
            view=submit_bond_proposal(c,tenant,actor,req)
            if view.status=='PENDING':view=decide_bond_proposal(c,tenant,actor,view.proposal_id,'APPROVED',
                'Owner-authorized reconciliation. Source coupon, ISIN, issue/maturity retained; ACT_ACT_ICMA is inferred from source ACT/ACT. Penny nominal unit is mock dealing metadata, not independently verified eligibility. CLEAN source price x100.')
            if view.status!='APPROVED':raise ValueError('Bond not approved: '+iid)
            node=view.instrument_id
        start=c.scalar(select(m.instrument.c.effective_from).where(m.instrument.c.instrument_node_id==node))
        cv=dict(kind='BOND',effectiveFrom=str(start),priceCurrencyId=str(currencies[item['currency']]),quoteFactor='100',
            sourceReference='Owner-confirmed CLEAN fraction-of-par prices x100; nominal unchanged. Source bundle '+bundle.digest,
            quantityUnit='NOMINAL',priceBasis='PCT_OF_PAR',principalBasis='UNADJUSTED_NOMINAL',quantityMinimum='.01',quantityIncrement='.01',accrual='MANUAL_CONFIRMATION',otcAllowed=True)
        proposal=submit_proposal(c,tenant,actor,ConventionProposalRequest(instrumentId=node,convention=cv,idempotencyKey='fcpgf-bond-cv:'+bundle.digest+':'+iid))
        if proposal.status=='PENDING':proposal=decide_proposal(c,tenant,actor,proposal.proposal_id,'APPROVED','Reconciliation nominal bond convention; actual prices and settlements retained.')
        nodes[iid]=node
    return nodes


def seed_funds(c,bundle,tenant,actor,foundation):
    currencies=catalogue(c,m.currency,'currency_code','currency_id');types=catalogue(c,m.reference_node_type,'type_code','reference_node_type_id')
    ins=source_instruments(bundle);nodes={};listings={}
    venue_name='Reconciliation OTC fund dealing (synthetic routing metadata)'
    venues=c.execute(select(m.market_venue).where(m.market_venue.c.status=='ACTIVE',m.market_venue.c.venue_type=='OTC_VENUE',m.market_venue.c.display_name==venue_name)).mappings().all()
    if not venues:
        venue=c.scalar(m.market_venue.insert().values(venue_type='OTC_VENUE',display_name=venue_name,status='ACTIVE').returning(m.market_venue.c.market_venue_id))
        audit(c,actor,tenant,'RECONCILIATION_OTC_DEALING_VENUE',dict(venueId=str(venue),assumption='Synthetic OTC subscription/redemption route. No exchange, MIC or actual execution venue asserted.'))
    else:venue=venues[0]['market_venue_id']
    for row in bundle.tables['funds']:
        iid=source_id(row['instrument_id']);item=ins[iid]
        observed=[r['trade_datetime_utc'][:10] for r in bundle.positions if source_id(r['instrument_id'])==iid]
        start=date.fromisoformat(min([row.get('launched_date') or min(observed)]+observed))
        node=native_reference(c,tenant,actor,foundation,bundle,iid,'FUND_SHARE_CLASS',item['long_name'] or item['short_name'],currencies[item['currency']],start)
        existing=c.scalar(select(m.fund_share_class_terms.c.fund_reference_node_id).where(m.fund_share_class_terms.c.instrument_node_id==node,m.fund_share_class_terms.c.is_current))
        if not existing:
            parent=c.scalar(m.financial_reference_node.insert().values(reference_node_type_id=types['FUND'],canonical_name=row['fund_name'],
                internal_code='RECON_'+foundation['sourceId'].hex+'_FUND_VEHICLE_'+iid,status='ACTIVE',is_tradable=False).returning(m.financial_reference_node.c.reference_node_id))
            c.execute(m.reference_node_scope.insert().values(reference_node_id=parent,scope_type='TENANT_PRIVATE',owner_tenant_id=tenant,status='ACTIVE'))
            c.execute(m.fund.insert().values(fund_reference_node_id=parent,fund_kind='STANDALONE',status='ACTIVE'))
            c.execute(m.fund_share_class_terms.insert().values(instrument_node_id=node,fund_reference_node_id=parent,
                share_class_code=(row.get('class_code') or iid)[:100],share_currency_id=currencies[item['currency']],
                income_treatment='DISTRIBUTION' if row.get('is_distribution')=='True' else 'ACCUMULATION',
                dealing_frequency='DAILY',nav_frequency='DAILY',nav_publication_lag_business_days=1,effective_from=start))
            if item.get('isin'):
                scheme=c.scalar(select(m.identifier_scheme.c.identifier_scheme_id).where(m.identifier_scheme.c.scheme_code=='ISIN'))
                c.execute(m.financial_reference_identifier.insert().values(reference_node_id=node,identifier_scheme_id=scheme,identifier_value=item['isin'],is_primary=True,valid_from=start))
        listing=c.scalar(select(m.listing.c.listing_node_id).where(m.listing.c.instrument_node_id==node))
        if not listing:
            listing=c.scalar(m.financial_reference_node.insert().values(reference_node_type_id=types['LISTING'],canonical_name=item['short_name']+' — OTC dealing',
                internal_code='RECON_'+foundation['sourceId'].hex+'_FUND_LISTING_'+iid,status='ACTIVE',is_tradable=True).returning(m.financial_reference_node.c.reference_node_id))
            c.execute(m.reference_node_scope.insert().values(reference_node_id=listing,scope_type='TENANT_PRIVATE',owner_tenant_id=tenant,status='ACTIVE'))
            fields=dict(listing_node_id=listing,instrument_node_id=node,market_venue_id=venue,trading_currency_id=currencies[item['currency']],
                trading_symbol=item.get('isin') or iid,quote_factor=Decimal(1),unit_multiplier=Decimal(1),is_primary_listing=True,effective_from=start)
            c.execute(m.listing.insert().values(**fields,status='ACTIVE'))
            definition={k:v for k,v in fields.items() if k not in {'instrument_node_id','is_primary_listing'}}
            c.execute(m.listing_definition_version.insert().values(**definition,sequence_no=1,is_current=True,status='APPROVED',
                source_payload_id=receipt(c,bundle,foundation,'funds'),approved_by_user_account_id=actor,approved_at_utc=datetime.now(timezone.utc)))
        nodes[iid]=node;listings[iid]=listing
    audit(c,actor,tenant,'RECONCILIATION_FUND_METADATA',dict(bundleHash=bundle.digest,sourceId=str(foundation['sourceId']),
        strategyId=str(foundation['strategyId']),assumptions='Separate source share classes; fund vehicle relationship, daily dealing/NAV, T+1 publication and OTC dealing route are reconciliation assumptions. No exchange listing or legal fund verification claimed.',
        instruments={k:str(v) for k,v in nodes.items()}))
    return nodes,listings


def autocall_request(bundle,item,swap,start,underlying,currency,calendar,source,payload):
    """Explicit synthetic annual autocall; never used to manufacture price marks."""
    from apps.reference_api.structured_product_contracts import AutocallDraftRequest,validate_autocall_draft
    from dateutil.relativedelta import relativedelta
    maturity=date.fromisoformat(item['maturity_date']);day=date.fromisoformat(start)+relativedelta(years=1);rows=[];n=0
    while day<maturity:
        n+=1
        rows.append(dict(rowId='call-'+str(n),rowKind='ACTION',groupCode='AUTOCALL_ACTION',componentKind='PARENT_ACTION',conditionRole='AUTOCALL',
            conditionOperator='GE',conditionScope='SINGLE',observationDate=str(day),paymentDate=str(day),conditionLevel='100',conditionLevelBasis='PCT_OF_INITIAL',actionCode='REDEEM_PARENT',actionTarget='PARENT'))
        day=day+relativedelta(years=1)
    rows.append(dict(rowId='final',rowKind='ACTION',groupCode='FINAL',componentKind='PARENT_ACTION',conditionRole='FINAL_REDEMPTION',
        conditionOperator='GE',conditionScope='SINGLE',conditionLevel='0',observationDate=str(maturity),paymentDate=str(maturity),conditionLevelBasis='PCT_OF_INITIAL',actionCode='FINAL_REDEMPTION',actionTarget='PARENT'))
    return validate_autocall_draft(AutocallDraftRequest(canonicalName=item['short_name']+' [SYNTHETIC payoff terms]',
        internalCode='RECON_'+source.hex+'_AUTOCALL_'+source_id(item['instrument_id']),effectiveFrom=start,productSubtype='AUTOCALL',issueCurrencyId=currency,
        scope='SINGLE',observationStyle='DISCRETE',memoryMode='NONE',calendarId=calendar,startDate=start,maturityDate=str(maturity),frequency='ANNUAL',
        includeKip=False,includeConsolation=False,paymentDateConvention='EXPLICIT',explicitScheduleReason='SYNTHETIC annual dates and immediate payment. Source payoff/schedule absent; not verified contractual terms.',
        underlyings=[dict(referenceNodeId=underlying,initialFixing='100',fixingDate=start,fixingBasis='PERCENT_OF_INITIAL',fixingSource='MANUAL',label='SYNTHETIC single SPX reference / base 100')],
        rows=rows,submissionMode='AUTOMATED',sourceSystemId=source,sourcePayloadId=payload,idempotencyKey='fcpgf-autocall:'+bundle.digest+':'+item['instrument_id']))


def seed_swaps(c,bundle,tenant,actor,foundation,bonds):
    from dataclasses import replace
    from apps.reference_api.contracts import IndexProposalRequest
    from apps.reference_api.repository import submit_index_proposal,decide_index_proposal,submit_structured_product_proposal,decide_structured_product_proposal
    from apps.reference_api.product_booking import submit_proposal,decide_proposal
    from .reconciliation_products import seed_products,swap_plan
    from .reconciliation_eligibility import _calendar
    ins=source_instruments(bundle);currencies=catalogue(c,m.currency,'currency_code','currency_id')
    profiles=catalogue(c,m.return_profile,'profile_code','return_profile_id');days=catalogue(c,m.day_count_convention,'code','day_count_convention_id')
    divergent=[r for r in bundle.tables['swaps'] if ins[source_id(r['instrument_id'])]['instrument_type']=='DIVER OTC']
    subset=replace(bundle,tables=dict(bundle.tables,swaps=divergent))
    base=seed_products(c,subset,tenant,actor,foundation);refs=base['references'];swaps=base['swaps'];autocalls={};unsupported={}
    req=IndexProposalRequest(canonicalName='SPX [synthetic autocall underlying assumption]',internalCode='RECON_'+foundation['sourceId'].hex+'_MOCK_SPX',
        effectiveFrom=bundle.manifest['earliestTradeDate'],indexKind='PUBLIC',returnProfileId=profiles['PRICE_RETURN'],baseCurrencyId=currencies['USD'],
        methodologyReference='SYNTHETIC payoff reference assumption. Source autocall composition was not supplied. Not a verified underlying or market quote.',
        submissionMode='AUTOMATED',sourceSystemId=foundation['sourceId'],sourcePayloadId=receipt(c,bundle,foundation,'all_instruments'),idempotencyKey='fcpgf-mock-spx:'+bundle.digest)
    idx=submit_index_proposal(c,tenant,actor,req)
    if idx.status=='PENDING':idx=decide_index_proposal(c,tenant,actor,idx.proposal_id,'APPROVED','Owner authorized missing EQUITYOTC details to be completed with disclosed synthetic assumptions.')
    all_maturities=[date.fromisoformat(i['maturity_date']) for i in ins.values() if i.get('maturity_date')]
    calendar=_calendar(c,actor,date.fromisoformat(bundle.manifest['earliestTradeDate']),max(all_maturities))
    groups=defaultdict(list)
    for row in bundle.tables['swaps']:groups[source_id(row['instrument_id'])].append(row)
    assumptions={}
    for iid,rows in groups.items():
        item=ins[iid];kind=item['instrument_type']
        if kind=='DIVER OTC':continue
        trades=[r for r in bundle.positions if source_id(r['instrument_id'])==iid]
        start=min([item['effective_date']] + [r['trade_datetime_utc'][:10] for r in trades]) if item.get('effective_date') else min(r['trade_datetime_utc'][:10] for r in trades)
        item=dict(item,effective_date=start)
        if kind=='EQUITY OTC':
            if len(rows)!=1:raise ValueError('Ambiguous EQUITYOTC source terms')
            row=dict(rows[0]);underlying=source_id(row['funded_instrument_id']);autocall=dict(ins[underlying])
            if not autocall.get('maturity_date'):autocall['maturity_date']=item['maturity_date']
            request=autocall_request(bundle,autocall,row,start,idx.index_id,currencies[item['currency']],calendar,foundation['sourceId'],receipt(c,bundle,foundation,'all_instruments'))
            view=submit_structured_product_proposal(c,tenant,actor,request)
            if view.status=='PENDING':view=decide_structured_product_proposal(c,tenant,actor,view.proposal_id,'APPROVED',
                'SYNTHETIC annual single-SPX autocall payoff, initial 100, 100% call barrier, no KIP or coupon. Source supplied only funded-autocall identity/currency/maturity. Whole-swap source marks stay unchanged; no payoff valuation or cash flows generated.')
            underlying_id=view.instrument_id
            refs[underlying]=underlying_id;autocalls[underlying]=underlying_id
        elif kind=='ASWAP':
            bond_legs=[r for r in rows if source_id(r.get('funding_instrument_id')) in bonds]
            rate_legs=[r for r in rows if source_id(r.get('funding_instrument_id')) in {'1048','1396'}]
            if len(bond_legs)!=1 or len(rate_legs)!=1:
                unsupported[iid]='TWO_RATE_LEG_ASSET_SWAP_NOT_A_SUPPORTED_PERFORMANCE_SWAP; original legs retained, no proxy instrument invented'
                continue
            bond_leg,rate_leg=bond_legs[0],rate_legs[0]
            row=dict(rate_leg,funded_instrument_id=bond_leg['funding_instrument_id'],leverage=str(abs(Decimal(bond_leg['leverage']))))
            refs[source_id(bond_leg['funding_instrument_id'])]=bonds[source_id(bond_leg['funding_instrument_id'])]
        else:raise ValueError('Unhandled source swap category: '+kind)
        row['swap_payment_per_year']=source_id(row['swap_payment_per_year'])
        plan=swap_plan(bundle,item,row,refs,currencies,profiles['GROSS_TOTAL_RETURN'],days)
        if kind=='ASWAP' and Decimal(bond_leg['leverage'])<0:
            plan['request'].terms.performance_direction='PAY'
        view=submit_proposal(c,tenant,actor,plan['request'])
        if view.status=='PENDING':view=decide_proposal(c,tenant,actor,view.proposal_id,'APPROVED',
            'Owner-authorized reconciliation completion; missing metadata is mockup. Source execution quantities and whole-contract marks unchanged. Original multi-leg source rows retained separately.')
        swaps[iid]=view.reference_node_id
        classify(c,tenant,actor,bundle,foundation,view.reference_node_id,'EQUITYOTC' if kind=='EQUITY OTC' else 'ASWAP',date.fromisoformat(start))
        assumptions[iid]=dict(completion=plan['assumptions'],originalSwapRows=rows)
    audit(c,actor,tenant,'RECONCILIATION_FCPGF_SWAP_COMPLETION',dict(sourceId=str(foundation['sourceId']),bundleHash=bundle.digest,
        strategyId=str(foundation['strategyId']),assumptions=assumptions,unsupported=unsupported,syntheticAutocalls={k:str(v) for k,v in autocalls.items()},
        noSourceFinancialMarksInvented=True,noPayoffCashflowsGenerated=True))
    return dict(swaps=swaps,references=refs,autocalls=autocalls,unsupported=unsupported)
