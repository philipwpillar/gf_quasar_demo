"""Tests for the curated single-task policy rule set."""

from __future__ import annotations

from policy.policy_rules import SUPPORTED_TASK_CLASS, evaluate_policy


def test_valid_task_class_and_zone_passes() -> None:
    passed, reasons = evaluate_policy(
        task_class=SUPPORTED_TASK_CLASS,
        zone="zone_b",
        module_ids=["mod-001", "mod-002"],
    )

    assert passed is True
    assert any("policy rules passed" in reason for reason in reasons)


def test_unknown_task_class_is_refused() -> None:
    passed, reasons = evaluate_policy(
        task_class="warehouse_picking",
        zone="zone_a",
        module_ids=["mod-001"],
    )

    assert passed is False
    assert any("not supported" in reason for reason in reasons)


def test_disallowed_zone_is_refused() -> None:
    passed, reasons = evaluate_policy(
        task_class=SUPPORTED_TASK_CLASS,
        zone="zone_restricted",
        module_ids=["mod-001"],
    )

    assert passed is False
    assert any("not permitted" in reason for reason in reasons)
