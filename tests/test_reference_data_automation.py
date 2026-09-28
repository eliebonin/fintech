"""Structural tests for policy-mediated reference-data automation."""

from security_master_schema import models as m


def test_automation_policy_catalogue_is_versioned_and_source_bound() -> None:
    assert "secm.reference_data_automation_policy" in m.metadata.tables
    policy = m.metadata.tables["secm.reference_data_automation_policy"]
    assert {
        "source_system_id",
        "target_object_type",
        "operation_type",
        "min_confidence",
        "required_identifier_schemes",
        "criteria_json",
        "auto_approve",
        "tenant_id",
        "valid_from",
        "valid_to",
        "version_no",
        "status",
    }.issubset(policy.c.keys())
    assert {
        "ing.integration_source_system.integration_source_system_id",
        "ten.tenant.tenant_id",
    }.issubset({fk.target_fullname for column in policy.c for fk in column.foreign_keys})


def test_reference_data_proposal_records_automated_submission_and_idempotency() -> None:
    proposal = m.metadata.tables["secm.reference_data_proposal"]
    assert {
        "submission_mode",
        "source_system_id",
        "automation_policy_id",
        "idempotency_key",
        "match_status",
        "confidence_score",
        "payload_schema_version",
    }.issubset(proposal.c.keys())
    assert any(c.name == "ck_reference_data_proposal_confidence" for c in proposal.constraints)
    assert any(c.name == "ck_reference_data_proposal_submission_mode" for c in proposal.constraints)


def test_reference_data_approval_records_automated_decision_evidence() -> None:
    approval = m.metadata.tables["secm.reference_data_approval"]
    assert {
        "decision_method",
        "automation_policy_id",
        "decision_evidence_json",
    }.issubset(approval.c.keys())
    assert any(c.name == "ck_reference_data_approval_decision_method" for c in approval.constraints)


def test_automation_lookup_indexes_are_present() -> None:
    index_names = {
        index.name
        for table in m.metadata.tables.values()
        for index in table.indexes
    }
    assert {
        "ix_reference_data_proposal_idempotency",
        "ix_reference_data_automation_policy_source_target",
    }.issubset(index_names)
