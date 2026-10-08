"""Partial retries must not become clean successes or expand source windows."""
from datetime import date
import pytest


@pytest.mark.parametrize('report,want', [
    ({'accepted':4,'duplicates':0,'rejected':0}, 'COMPLETE'),
    ({'accepted':0,'duplicates':4,'rejected':0}, 'COMPLETE'),
    ({'accepted':4,'duplicates':0,'rejected':2}, 'PARTIAL'),
    ({'accepted':0,'duplicates':4,'rejected':2}, 'PARTIAL'),
    ({'accepted':0,'duplicates':0,'rejected':1}, 'FAILED'),
    ({'accepted':0,'duplicates':0,'rejected':0}, 'FAILED'),
])
def test_delivery_outcome_preserves_partial_and_duplicate_results(report,want):
    from market_data.outcomes import delivery_outcome
    assert delivery_outcome(report)==want


@pytest.mark.parametrize('states,want,code', [
    (['COMPLETE','PARTIAL'],'PARTIAL',3),
    (['COMPLETE','FAILED'],'PARTIAL',3),
    (['FAILED'],'FAILED',1),
    (['COMPLETE','BLOCKED'],'BLOCKED',1),
    (['COMPLETE','COMPLETE'],'COMPLETE',0),
    (['COMPLETE','ABORTED'],'ABORTED',1),
    ([], 'FAILED',1),
])
def test_job_outcome_is_consistent_on_resume(states,want,code):
    from market_data.outcomes import job_outcome,exit_code
    assert job_outcome(states)==want
    assert exit_code(want)==code


def test_gap_retry_uses_only_explicit_rejected_dates_within_request():
    from market_data.outcomes import gap_windows
    report={'rejections':[
        {'marketDate':'2025-11-12','reason':'Missing or malformed equity price'},
        {'marketDate':'2025-11-12','reason':'Missing or malformed equity price'},
        {'marketDate':'2025-11-13','reason':'Missing or malformed equity price'},
        {'marketDate':'2025-11-17','reason':'Missing or malformed equity price'},
        {'marketDate':'2025-11-10','reason':'Outside requested market date window'},
        {'reason':'Source identity does not match'},
    ]}
    assert gap_windows(report,date(2025,11,11),date(2025,11,17))==[
        (date(2025,11,12),date(2025,11,13)),(date(2025,11,17),date(2025,11,17))]
    assert gap_windows(report,date(2025,11,14),date(2025,11,16))==[]
