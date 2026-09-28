"""Tests for the generic, effective-dated fee model."""

from security_master_schema import models as m


def test_fee_contract_tables_are_centralised_and_generic() -> None:
    expected = {
        "fee.fee_type",
        "fee.fee_rule",
        "fee.fee_rule_target",
    }

    assert expected.issubset(m.metadata.tables)

    rule = m.metadata.tables["fee.fee_rule"]
    assert {
        "fee_type_id",
        "calculation_method",
        "calculation_basis",
        "rate_value",
        "rate_unit",
        "parameters_json",
        "valid_from",
        "valid_to",
        "version_no",
    }.issubset(rule.c.keys())


def test_fee_rule_target_supports_reference_nodes_and_strategies() -> None:
    target = m.metadata.tables["fee.fee_rule_target"]

    assert {
        "target_reference_node_id",
        "target_strategy_id",
        "application_mode",
        "priority",
        "payer_organisation_id",
        "recipient_organisation_id",
        "effective_from",
        "effective_to",
    }.issubset(target.c.keys())

    assert any(
        constraint.name == "ck_fee_rule_target_exactly_one_target"
        for constraint in target.constraints
    )
    assert {
        "secm.financial_reference_node.reference_node_id",
        "trd.strategy.strategy_id",
    }.issubset(
        {
            foreign_key.target_fullname
            for column in target.c
            for foreign_key in column.foreign_keys
        }
    )


def test_trade_fee_can_reference_the_contractual_fee_rule() -> None:
    trade_fee = m.metadata.tables["trd.trade_fee"]

    assert "fee_rule_id" in trade_fee.c
    assert "fee.fee_rule.fee_rule_id" in {
        foreign_key.target_fullname
        for foreign_key in trade_fee.c.fee_rule_id.foreign_keys
    }
