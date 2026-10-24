"""Small native AMC materializer; portfolio management and fund identity stay separate."""
from datetime import datetime,timezone
from sqlalchemy import select,func
from security_master_schema import models as m
from .product_booking import ProductBookingError,require_visible,append_convention

KIND='ACTIVELY_MANAGED_CERTIFICATE'


def validate_amc_references(c,tenant,request,*,lock=False):
    def active(table,column,value,label):
        query=select(table).where(column==value)
        row=c.execute(query.with_for_update() if lock else query).mappings().one_or_none()
        if row is None or row['status']!='ACTIVE':raise ProductBookingError(f'An active {label} is required')
        return row
    currency=active(m.currency,m.currency.c.currency_id,request.base_currency_id,'currency')
    if currency['reference_node_id']:require_visible(c,tenant,currency['reference_node_id'])
    for organisation in sorted({request.issuer_organisation_id,request.adviser_organisation_id}-{None},key=str):
        # Canonical organisations are shared; tenant-private labels/notes are not
        # copied. This does not grant trading-counterparty eligibility.
        active(m.organisation,m.organisation.c.organisation_id,organisation,'issuer/adviser organisation')
    if request.reference_node_id:
        from .approval_reference_integrity import _etp_reference
        if lock:_etp_reference(c,tenant,request.reference_node_id)
        else:require_visible(c,tenant,request.reference_node_id)
    active(m.instrument_type,m.instrument_type.c.type_code,KIND,'AMC catalogue')
    active(m.reference_node_type,m.reference_node_type.c.type_code,'INSTRUMENT','instrument catalogue')
    if request.isin:
        # Serialize the global identity, but never disclose another tenant's node.
        from .booking_controls import booking_lock_key
        from uuid import UUID
        c.execute(select(func.pg_advisory_xact_lock(booking_lock_key(UUID(int=0),'amc-isin',request.isin))))
        scheme=c.scalar(select(m.identifier_scheme.c.identifier_scheme_id).where(m.identifier_scheme.c.scheme_code=='ISIN'))
        if not scheme:raise ProductBookingError('ISIN identifier scheme is required')
        if c.scalar(select(m.financial_reference_identifier.c.reference_node_id).where(
                m.financial_reference_identifier.c.identifier_scheme_id==scheme,
                m.financial_reference_identifier.c.identifier_value==request.isin)):
            raise ProductBookingError('This ISIN already has a canonical instrument; resolve its identity before creating another')


def materialize_amc(c,tenant,actor,request):
    validate_amc_references(c,tenant,request,lock=True)
    node=c.scalar(m.financial_reference_node.insert().values(
        reference_node_type_id=c.scalar(select(m.reference_node_type.c.reference_node_type_id).where(m.reference_node_type.c.type_code=='INSTRUMENT')),
        canonical_name=request.canonical_name,is_tradable=True,status='ACTIVE').returning(m.financial_reference_node.c.reference_node_id))
    fields=dict(instrument_type_id=c.scalar(select(m.instrument_type.c.instrument_type_id).where(m.instrument_type.c.type_code==KIND)),
        asset_class='STRUCTURED_PRODUCT',issuer_organisation_id=request.issuer_organisation_id,base_currency_id=request.base_currency_id,
        effective_from=request.effective_from,sequence_no=1,is_current=True)
    c.execute(m.instrument.insert().values(instrument_node_id=node,**fields))
    c.execute(m.instrument_definition_version.insert().values(instrument_node_id=node,**fields,status='APPROVED',
        approved_by_user_account_id=actor,approved_at_utc=datetime.now(timezone.utc)))
    c.execute(m.reference_node_scope.insert().values(reference_node_id=node,scope_type='TENANT_PRIVATE',owner_tenant_id=tenant,status='ACTIVE'))
    c.execute(m.instrument_dates.insert().values(instrument_node_id=node,effective_date=request.effective_from,maturity_date=request.maturity_date))
    values=request.model_dump(include={'adviser_organisation_id','reference_node_id','redemption_model','distribution_policy',
        'collateralisation_type','strategy_description','fee_description','pricing_frequency','publication_lag_business_days','source_reference','effective_from'})
    c.execute(m.amc_terms.insert().values(instrument_node_id=node,**values))
    if request.isin:
        from .repository import _insert_reference_identifier
        _insert_reference_identifier(c,node,'ISIN',request.isin,request.effective_from)
    append_convention(c,node,request.convention,actor)
    return node


def inspection_terms(c,tenant,node,version):
    require_visible(c,tenant,node)
    row=c.execute(select(m.amc_terms).where(m.amc_terms.c.instrument_node_id==node,m.amc_terms.c.sequence_no==version)).mappings().one()
    adviser=c.scalar(select(m.organisation.c.display_name).where(m.organisation.c.organisation_id==row['adviser_organisation_id'])) if row['adviser_organisation_id'] else None
    reference=require_visible(c,tenant,row['reference_node_id']).canonical_name if row['reference_node_id'] else None
    maturity=c.scalar(select(m.instrument_dates.c.maturity_date).where(m.instrument_dates.c.instrument_node_id==node))
    return dict(row) | dict(adviser_name=adviser,reference_name=reference,maturity_date=maturity)
