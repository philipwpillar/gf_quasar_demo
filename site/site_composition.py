"""Tier 2 robot composition — trust verdict from attested module refs."""

from __future__ import annotations

from ledger import EntryKind, Ledger
from policy.policy_models import ModuleAttestationRef

from .site_models import RobotComposition


def compose_robot(
    ledger: Ledger,
    *,
    robot_id: str,
    vendor_key_id: str,
    module_refs: list[ModuleAttestationRef],
) -> RobotComposition:
    """Compose a robot identity and append ``robot_composed`` to the ledger.

    A robot is trustworthy only when EVERY constituent module attested true.
    Each ``module_ref`` carries the ledger sequence of its attestation entry.
    """
    composed = all(ref.attested for ref in module_refs)
    reasons: list[str] = []

    if composed:
        reasons.append(
            f"robot {robot_id} composed from {len(module_refs)} attested module(s)"
        )
    else:
        for ref in module_refs:
            if not ref.attested:
                reasons.append(
                    f"robot {robot_id} not trusted: module {ref.module_id} "
                    f"failed attestation (ledger seq {ref.ledger_seq})"
                )

    entry = ledger.append(
        EntryKind.ROBOT_COMPOSED,
        robot_id,
        {
            "robot_id": robot_id,
            "vendor_key_id": vendor_key_id,
            "module_refs": [ref.model_dump(mode="json") for ref in module_refs],
            "composed": composed,
            "reasons": reasons,
        },
    )

    chain_head = entry.entry_hash
    assert chain_head is not None

    return RobotComposition(
        robot_id=robot_id,
        vendor_key_id=vendor_key_id,
        module_refs=module_refs,
        composed=composed,
        reasons=reasons,
        ledger_seq=entry.seq,
        chain_head=chain_head,
    )


def composition_from_ledger_entry(
    ledger: Ledger, robot_composed_seq: int
) -> RobotComposition:
    """Reconstruct ``RobotComposition`` from a ``robot_composed`` ledger entry."""
    entry = ledger.get(robot_composed_seq)
    payload = entry.payload
    module_refs = [
        ModuleAttestationRef.model_validate(ref) for ref in payload["module_refs"]
    ]
    chain_head = entry.entry_hash
    assert chain_head is not None
    return RobotComposition(
        robot_id=payload["robot_id"],
        vendor_key_id=payload["vendor_key_id"],
        module_refs=module_refs,
        composed=payload["composed"],
        reasons=list(payload["reasons"]),
        ledger_seq=entry.seq,
        chain_head=chain_head,
    )
