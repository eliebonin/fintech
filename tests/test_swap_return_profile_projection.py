from types import SimpleNamespace
from uuid import uuid4

from apps.reference_api.repository import list_return_profiles


def test_return_profiles_project_governed_financing_facts():
    row = SimpleNamespace(return_profile_id=uuid4(), profile_code='CUSTOM_EXCESS', display_name='Custom excess',
        description='Governed financing', base_return_basis='TOTAL', income_treatment='GROSS',
        financing_treatment='SUBTRACT_REFERENCE_RATE', requires_financing_reference=True)
    class Result:
        def mappings(self): return self
        def all(self): return [row]
    class Connection:
        def execute(self, statement):
            assert 'financing_treatment' in str(statement)
            assert 'requires_financing_reference' in str(statement)
            return Result()
    projected = list_return_profiles(Connection(), uuid4(), 'v1', 'test').data[0].model_dump(by_alias=True)
    assert projected['financingTreatment'] == 'SUBTRACT_REFERENCE_RATE'
    assert projected['requiresFinancingReference'] is True
