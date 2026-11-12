"""Scoped, date-valid forward terms shared by booking, replay and lifecycle."""
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.engine import Connection
from . import models as m
from .errors import RepositoryNotFound
from .fx_forward_booking import FxForwardBookingTerms, FxForwardBookingError, resolve_fx_forward_settlement

def _contract_query(tenant_id):
    from .reference_visibility import joined_scope_clause as _visible_node_clause
    base, quote = m.currency.alias("fx_base"), m.currency.alias("fx_quote")
    return select(m.instrument.c.instrument_node_id, m.instrument.c.is_current, m.instrument.c.effective_from, m.instrument.c.effective_to,
        m.instrument_definition_version.c.status.label("definition_status"),m.instrument_definition_version.c.effective_from.label("definition_from"),m.instrument_definition_version.c.effective_to.label("definition_to"),
        m.instrument_definition_version.c.base_currency_id.label("definition_base_id"),m.instrument_definition_version.c.instrument_type_id.label("definition_type_id"),m.instrument.c.instrument_type_id,
        m.instrument.c.base_currency_id.label("instrument_base_id"), m.financial_reference_node.c.canonical_name, m.financial_reference_node.c.status,m.financial_reference_node.c.is_tradable,m.instrument_type.c.status.label("type_status"),
        m.fx_forward_terms.c.base_currency_id, m.fx_forward_terms.c.quote_currency_id, m.fx_forward_terms.c.quote_convention,
        m.fx_forward_terms.c.agreed_forward_rate, m.fx_forward_terms.c.settlement_type, m.instrument_dates.c.maturity_date,
        m.instrument_dates.c.settlement_date, m.instrument_dates.c.cash_settlement_date, m.instrument_dates.c.final_settlement_date,
        base.c.currency_code.label("base_currency"), quote.c.currency_code.label("quote_currency"),
        base.c.status.label("base_status"), quote.c.status.label("quote_status"))\
        .select_from(m.instrument.join(m.financial_reference_node, m.instrument.c.instrument_node_id == m.financial_reference_node.c.reference_node_id)
        .join(m.instrument_type, m.instrument.c.instrument_type_id == m.instrument_type.c.instrument_type_id)
        .outerjoin(m.instrument_definition_version,and_(m.instrument_definition_version.c.instrument_node_id==m.instrument.c.instrument_node_id,m.instrument_definition_version.c.is_current.is_(True),m.instrument_definition_version.c.status=="APPROVED"))
        .outerjoin(m.reference_node_scope, m.reference_node_scope.c.reference_node_id == m.instrument.c.instrument_node_id)
        .outerjoin(m.fx_forward_terms, m.fx_forward_terms.c.instrument_node_id == m.instrument.c.instrument_node_id)
        .outerjoin(m.instrument_dates, m.instrument_dates.c.instrument_node_id == m.instrument.c.instrument_node_id)
        .outerjoin(base, base.c.currency_id == m.fx_forward_terms.c.base_currency_id)
        .outerjoin(quote, quote.c.currency_id == m.fx_forward_terms.c.quote_currency_id))\
        .where(_visible_node_clause(tenant_id), m.instrument_type.c.type_code == "FX_FORWARD")


def _terms(row, as_of=None):
    today = as_of or datetime.now(timezone.utc).date()
    if row.definition_status!="APPROVED" or not row.definition_from or row.definition_from>today or (row.definition_to and row.definition_to<today) or row.definition_base_id!=row.base_currency_id or row.definition_type_id!=row.instrument_type_id:
        raise FxForwardBookingError("fx_forward.unapproved_definition","instrumentId","The current approved definition must cover the execution date and agree with FX terms.")
    if not row.base_currency_id or not row.quote_currency_id or row.agreed_forward_rate is None or not row.maturity_date or row.instrument_base_id != row.base_currency_id:
        raise FxForwardBookingError("fx_forward.invalid_terms", "instrumentId", "The approved contract needs complete, consistent currencies, rate and maturity.")
    if row.status != "ACTIVE" or not row.is_tradable or row.type_status!="ACTIVE" or not row.is_current or row.base_status != "ACTIVE" or row.quote_status != "ACTIVE":
        raise FxForwardBookingError("fx_forward.inactive_contract", "instrumentId", "The contract and its currencies must be active.")
    if (row.effective_from and row.effective_from > today) or (row.effective_to and row.effective_to < today):
        raise FxForwardBookingError("fx_forward.inactive_contract", "instrumentId", "The contract does not cover the execution date.")
    terms = FxForwardBookingTerms(row.instrument_node_id, row.base_currency_id, row.quote_currency_id, row.base_currency, row.quote_currency, row.quote_convention, row.settlement_type, row.agreed_forward_rate, row.maturity_date, row.settlement_date, row.cash_settlement_date, row.final_settlement_date)
    resolve_fx_forward_settlement(terms)
    return terms


def load_fx_forward_booking_terms(connection: Connection, tenant_id: UUID, instrument_id: UUID, *, for_update: bool = False, as_of=None) -> FxForwardBookingTerms:
    statement = _contract_query(tenant_id).where(m.instrument.c.instrument_node_id == instrument_id)
    if for_update:
        statement = statement.with_for_update(of=[m.instrument, m.financial_reference_node])
    row = connection.execute(statement).mappings().first()
    if row is None: raise RepositoryNotFound("Visible FX-forward instrument does not exist")
    if for_update:
        # Scope is an optional outer join, so lock it separately and recheck below.
        # The reference-node FOR UPDATE lock also blocks a new scope's FK check
        # for legacy unscoped nodes until this booking transaction ends.
        connection.execute(select(m.reference_node_scope).where(
            m.reference_node_scope.c.reference_node_id == instrument_id).with_for_update()).all()
        # Lock optional terms/dates independently: PostgreSQL cannot lock nullable outer joins.
        for table in (m.fx_forward_terms, m.instrument_dates, m.instrument_definition_version):
            connection.execute(select(table).where(table.c.instrument_node_id == instrument_id).with_for_update()).all()
        connection.execute(select(m.currency).where(m.currency.c.currency_id.in_([row.base_currency_id, row.quote_currency_id])).order_by(m.currency.c.currency_id).with_for_update()).all()
        row = connection.execute(statement).mappings().first()
        if row is None: raise RepositoryNotFound("Visible FX-forward instrument does not exist")
    return _terms(row, as_of)


class FxForwardTermBatch:
    """One tenant/transaction's native terms candidates for discovery only."""
    def __init__(self,connection,tenant_id,instrument_ids):
        self.connection,self.tenant=connection,tenant_id
        self.identities=set(instrument_ids);self.rows={}
        identities=sorted(self.identities,key=str)
        for start in range(0,len(identities),500):
            for row in connection.execute(_contract_query(tenant_id).where(m.instrument.c.instrument_node_id.in_(identities[start:start+500]))).mappings():
                self.rows.setdefault(row.instrument_node_id,[]).append(row)
        self.transaction=connection.get_transaction()

    def get(self,connection,tenant_id,instrument_id,*,as_of=None):
        if connection is not self.connection or tenant_id!=self.tenant or connection.get_transaction() is not self.transaction or instrument_id not in self.identities:
            raise ValueError('Forward terms belong to a different discovery read scope.')
        rows=self.rows.get(instrument_id,[])
        if not rows:raise RepositoryNotFound('Visible FX-forward instrument does not exist')
        if len(rows)>1:
            # Preserve the native loader's existing first-row selection on
            # ambiguous legacy reference data rather than invent a new rule.
            return load_fx_forward_booking_terms(connection,tenant_id,instrument_id,as_of=as_of)
        return _terms(rows[0],as_of)
