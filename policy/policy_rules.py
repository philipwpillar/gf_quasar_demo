"""Curated, single-task clearance rules.  [STUBBED — breadth]

This module deliberately implements a narrow, readable rule set for ONE task
class (``industrial_inspection``) and a small set of permitted zones. The full
configuration-space optimiser is out of scope and disclosed as stubbed via
``policy_mode`` on every verdict. At least one rule can refuse clearance.
"""

from __future__ import annotations

SUPPORTED_TASK_CLASS = "industrial_inspection"
PERMITTED_ZONES = frozenset({"zone_a", "zone_b"})


def evaluate_policy(
    *,
    task_class: str,
    zone: str,
    module_ids: list[str],
) -> tuple[bool, list[str]]:
    """Return ``(rules_passed, reasons)`` for the curated single-task rule set.

    Attestation outcomes are gated separately in ``ClearanceService``; this
    function covers task-class and zone policy only.
    """
    reasons: list[str] = []

    if task_class != SUPPORTED_TASK_CLASS:
        reasons.append(
            f"not cleared: task class '{task_class}' is not supported "
            f"(stub supports '{SUPPORTED_TASK_CLASS}' only)"
        )
        return False, reasons

    if not module_ids:
        reasons.append("not cleared: configuration has no modules")
        return False, reasons

    if zone not in PERMITTED_ZONES:
        reasons.append(
            f"not cleared: zone '{zone}' is not permitted for "
            f"{SUPPORTED_TASK_CLASS} (allowed: {', '.join(sorted(PERMITTED_ZONES))})"
        )
        return False, reasons

    reasons.append(
        f"policy rules passed for {SUPPORTED_TASK_CLASS} in {zone}"
    )
    return True, reasons
