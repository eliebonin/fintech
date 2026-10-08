from uuid import UUID
import pytest

def test_batch_evidence_dataset_identity_is_required():
    from valuation.evidence_access import batch_datasets
    with pytest.raises(PermissionError):
        batch_datasets({'items':[{'evidence':{'selections':[{'selected_value':'100'}]}}]})

def test_batch_evidence_collects_all_datasets():
    from valuation.evidence_access import batch_datasets
    assert batch_datasets({'items':[{'evidence':{'selections':[
        {'dataset_id':str(UUID(int=1))}, {'dataset_id':str(UUID(int=2))}]}}]}) == {UUID(int=1),UUID(int=2)}

def test_empty_population_cannot_disclose_retained_summary_without_source_rights():
    from valuation.evidence_access import batch_datasets
    with pytest.raises(PermissionError):
        batch_datasets({'items':[],'summary':{'marketPnl':'100'}})

def test_malformed_v2_zero_quantities_fail_closed_as_permission_denial():
    from valuation.evidence_access import batch_datasets
    with pytest.raises(PermissionError):
        batch_datasets({'items':[{'position_key':'position','evidence':{'selections':[],
            'resultFormat':'POSITION_V2','noMarketMarksRequired':True,
            'identity':{'bucket':{'opening_quantity':'invalid','closing_quantity':'0'},'facts':[{}]}}}]})
