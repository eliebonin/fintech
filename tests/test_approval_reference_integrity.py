"""Submission checks cannot authorize materialization after references change."""
from uuid import uuid4
import pytest
from sqlalchemy import select, update, func, text
from apps.reference_api.db import get_engine
from apps.reference_api import repository as r
from apps.reference_api.contracts import FxForwardProposalRequest, BondProposalRequest, EtpProposalRequest
from security_master_schema import models as m
from security_master_schema.demo_data import DEMO_IDS as ids


@pytest.fixture
def connection():
    with get_engine().connect() as c:
        transaction = c.begin()
        try:
            yield c
        finally:
            transaction.rollback()


def proposal(c, kind):
    common = dict(canonicalName=f'Integrity {kind} {uuid4()}', effectiveFrom='2026-09-01')
    if kind == 'fx':
        request = FxForwardProposalRequest(**common, baseCurrencyId=ids['eur_currency'], quoteCurrencyId=ids['usd_currency'],
            quoteConvention='USD_PER_EUR', agreedForwardRate='1.1', settlementType='DELIVERABLE', maturityDate='2026-12-15', fixingCurrencyId=ids['gbp_currency'])
        return r.submit_fx_forward_proposal(c, ids['tenant'], ids['demo_user_account'], request), r.decide_fx_forward_proposal
    if kind == 'bond':
        request = BondProposalRequest(**common, baseCurrencyId=ids['gbp_currency'], issuerOrganisationId=ids['hsbc_organisation'],
            couponType='ZERO', maturityDate='2027-12-15', parAmount='1000', redemptionAmountPerPar='100', dayCountConvention='ACT_365F')
        return r.submit_bond_proposal(c, ids['tenant'], ids['demo_user_account'], request), r.decide_bond_proposal
    request = EtpProposalRequest(**common, baseCurrencyId=ids['gbp_currency'], issuerOrganisationId=ids['hsbc_organisation'],
        etpKind='ETF', legalForm='FUND', redemptionModel='CASH', referenceNodeId=ids['hsbc_instrument_node'])
    return r.submit_etp_proposal(c, ids['tenant'], ids['demo_user_account'], request), r.decide_etp_proposal


@pytest.mark.parametrize('kind,table,key,identifier', [
    ('fx', m.currency, 'currency_id', 'eur_currency'), ('fx', m.currency, 'currency_id', 'usd_currency'),
    ('fx', m.currency, 'currency_id', 'gbp_currency'),
    ('bond', m.currency, 'currency_id', 'gbp_currency'), ('bond', m.organisation, 'organisation_id', 'hsbc_organisation'),
    ('etp', m.currency, 'currency_id', 'gbp_currency'), ('etp', m.organisation, 'organisation_id', 'hsbc_organisation'),
])
def test_approval_refuses_retired_dependencies_without_fragments(connection, kind, table, key, identifier):
    proposed, decide = proposal(connection, kind)
    connection.execute(update(table).where(table.c[key] == ids[identifier]).values(status='INACTIVE'))
    before = connection.scalar(select(func.count()).select_from(m.financial_reference_node))
    with pytest.raises(r.RepositoryNotFound):
        decide(connection, ids['tenant'], ids['demo_user_account'], proposed.proposal_id, 'APPROVED', 'Integrity test')
    assert connection.scalar(select(m.reference_data_proposal.c.status).where(m.reference_data_proposal.c.reference_data_proposal_id == proposed.proposal_id)) == 'PENDING'
    assert connection.scalar(select(func.count()).select_from(m.financial_reference_node)) == before
    assert connection.scalar(select(func.count()).select_from(m.reference_data_approval).where(m.reference_data_approval.c.reference_data_proposal_id == proposed.proposal_id)) == 0


@pytest.mark.parametrize('change', ['foreign', 'inactive_scope', 'inactive_node', 'not_current'])
def test_etp_approval_rechecks_reference_integrity(connection, change):
    proposed, decide = proposal(connection, 'etp')
    if change in {'foreign', 'inactive_scope'}:
        values = dict(scope_type='TENANT_PRIVATE', owner_tenant_id=ids['second_tenant']) if change == 'foreign' else dict(status='INACTIVE')
        connection.execute(update(m.reference_node_scope).where(m.reference_node_scope.c.reference_node_id == ids['hsbc_instrument_node']).values(**values))
    elif change == 'inactive_node':
        connection.execute(update(m.financial_reference_node).where(m.financial_reference_node.c.reference_node_id == ids['hsbc_instrument_node']).values(status='INACTIVE'))
    else:
        connection.execute(update(m.instrument).where(m.instrument.c.instrument_node_id == ids['hsbc_instrument_node']).values(is_current=False))
    before = connection.scalar(select(func.count()).select_from(m.financial_reference_node))
    with pytest.raises((r.RepositoryNotFound, r.InvalidWorkflowState)):
        decide(connection, ids['tenant'], ids['demo_user_account'], proposed.proposal_id, 'APPROVED', 'Integrity test')
    assert connection.scalar(select(func.count()).select_from(m.financial_reference_node)) == before


def test_bond_day_count_failure_does_not_leave_materialized_nodes(connection):
    proposed, decide = proposal(connection, 'bond')
    connection.execute(update(m.day_count_convention).where(m.day_count_convention.c.code == 'ACT_365F').values(status='INACTIVE'))
    before = connection.scalar(select(func.count()).select_from(m.financial_reference_node))
    with pytest.raises(r.RepositoryNotFound):
        decide(connection, ids['tenant'], ids['demo_user_account'], proposed.proposal_id, 'APPROVED', 'Integrity test')
    assert connection.scalar(select(func.count()).select_from(m.financial_reference_node)) == before


@pytest.mark.parametrize('kind,table,key,identifier', [
    ('fx', m.currency, 'currency_id', 'usd_currency'),
    ('bond', m.organisation, 'organisation_id', 'hsbc_organisation'),
    ('etp', m.reference_node_scope, 'reference_node_id', 'hsbc_instrument_node'),
])
def test_approved_dependencies_stay_locked_until_commit(connection, kind, table, key, identifier):
    from sqlalchemy.exc import OperationalError
    proposed, decide = proposal(connection, kind)
    decide(connection, ids['tenant'], ids['demo_user_account'], proposed.proposal_id, 'APPROVED', 'Integrity test')
    with get_engine().begin() as other:
        other.execute(text("SET LOCAL lock_timeout = '200ms'"))
        with pytest.raises(OperationalError) as error:
            other.execute(update(table).where(table.c[key] == ids[identifier]).values(status='INACTIVE'))
        assert error.value.orig.sqlstate == '55P03'


def test_rejection_does_not_require_still_active_dependencies(connection):
    proposed, decide = proposal(connection, 'fx')
    connection.execute(update(m.currency).where(m.currency.c.currency_id == ids['usd_currency']).values(status='INACTIVE'))
    assert decide(connection, ids['tenant'], ids['demo_user_account'], proposed.proposal_id, 'REJECTED', 'Reference changed').status == 'REJECTED'


def test_sparse_etp_optional_references_remain_optional(connection):
    request = EtpProposalRequest(canonicalName='Sparse ETF '+str(uuid4()), effectiveFrom='2026-09-01', etpKind='ETF', legalForm='FUND', redemptionModel='CASH')
    proposed = r.submit_etp_proposal(connection, ids['tenant'], ids['demo_user_account'], request)
    approved = r.decide_etp_proposal(connection, ids['tenant'], ids['demo_user_account'], proposed.proposal_id, 'APPROVED', 'Sparse reference accepted')
    assert approved.status == 'APPROVED'


def test_late_approval_failure_rolls_back_decision_and_aggregate(connection, monkeypatch):
    proposed, decide = proposal(connection, 'etp')
    before = connection.scalar(select(func.count()).select_from(m.financial_reference_node))
    def fail_after_materialization(*args, **kwargs):
        raise RuntimeError('Injected response failure after approval writes')
    monkeypatch.setattr(r, '_etp_view', fail_after_materialization)
    with pytest.raises(RuntimeError, match='Injected response failure'):
        decide(connection, ids['tenant'], ids['demo_user_account'], proposed.proposal_id, 'APPROVED', 'Atomicity test')
    assert connection.scalar(select(func.count()).select_from(m.financial_reference_node)) == before
    assert connection.scalar(select(m.reference_data_proposal.c.status).where(m.reference_data_proposal.c.reference_data_proposal_id == proposed.proposal_id)) == 'PENDING'
    assert connection.scalar(select(func.count()).select_from(m.reference_data_approval).where(m.reference_data_approval.c.reference_data_proposal_id == proposed.proposal_id)) == 0
