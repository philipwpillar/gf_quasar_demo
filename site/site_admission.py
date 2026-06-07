"""Tier 3 site admission — attest-and-clear gate, never task dispatch."""

from __future__ import annotations

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from attestation.attestation_signer import Signer
from ledger import EntryKind, Ledger
from policy.policy_models import POLICY_MODE_STUB
from policy.policy_rules import SUPPORTED_TASK_CLASS, evaluate_policy
from shared.canonical_hashing import canonical_bytes

from .site_models import RobotComposition, SiteAdmissionRequest, SiteAdmissionVerdict


def verdict_hashable_view(
    *,
    robot_id: str,
    admitted: bool,
    reasons: list[str],
    robot_composed_seq: int,
    task_class: str,
    zone: str,
    policy_mode: str,
) -> dict:
    """Return the dict whose canonical bytes are signed and verified offline."""
    return {
        "robot_id": robot_id,
        "admitted": admitted,
        "reasons": reasons,
        "robot_composed_seq": robot_composed_seq,
        "task_class": task_class,
        "zone": zone,
        "policy_mode": policy_mode,
    }


def verify_site_verdict(verdict: SiteAdmissionVerdict) -> bool:
    """Recompute canonical bytes and verify the site-authority signature offline."""
    message = canonical_bytes(
        verdict_hashable_view(
            robot_id=verdict.robot_id,
            admitted=verdict.admitted,
            reasons=verdict.reasons,
            robot_composed_seq=verdict.robot_composed_seq,
            task_class=verdict.task_class,
            zone=verdict.zone,
            policy_mode=verdict.policy_mode,
        )
    )
    public_key = Ed25519PublicKey.from_public_bytes(
        bytes.fromhex(verdict.authority_public_key_hex)
    )
    try:
        public_key.verify(bytes.fromhex(verdict.signature_hex), message)
    except InvalidSignature:
        return False
    return True


def admit(
    ledger: Ledger,
    authority_signer: Signer,
    request: SiteAdmissionRequest,
    robot_composition: RobotComposition,
) -> SiteAdmissionVerdict:
    """Decide site admission and append ``site_admission`` to the ledger.

    Tier 3 attests and clears only — this is a provenance/compliance gate,
    not task scheduling or site orchestration.
    """
    reasons: list[str] = []

    if not robot_composition.composed:
        reasons.extend(robot_composition.reasons)
        admitted = False
    else:
        rules_passed, rule_reasons = evaluate_policy(
            task_class=request.task_class,
            zone=request.zone,
            module_ids=[ref.module_id for ref in robot_composition.module_refs],
        )
        if not rules_passed:
            reasons.extend(rule_reasons)
            admitted = False
        else:
            reasons.append(
                f"admitted for {SUPPORTED_TASK_CLASS} in {request.zone}"
            )
            admitted = True

    signature_hex = authority_signer.sign(
        canonical_bytes(
            verdict_hashable_view(
                robot_id=request.robot_id,
                admitted=admitted,
                reasons=reasons,
                robot_composed_seq=robot_composition.ledger_seq,
                task_class=request.task_class,
                zone=request.zone,
                policy_mode=POLICY_MODE_STUB,
            )
        )
    ).hex()

    authority_public_key_hex = authority_signer.public_key_hex()

    entry = ledger.append(
        EntryKind.SITE_ADMISSION,
        request.robot_id,
        {
            "robot_id": request.robot_id,
            "task_class": request.task_class,
            "zone": request.zone,
            "admitted": admitted,
            "reasons": reasons,
            "robot_composed_seq": robot_composition.ledger_seq,
            "policy_mode": POLICY_MODE_STUB,
            "authority_public_key_hex": authority_public_key_hex,
            "signature_hex": signature_hex,
        },
    )

    chain_head = entry.entry_hash
    assert chain_head is not None

    return SiteAdmissionVerdict(
        robot_id=request.robot_id,
        admitted=admitted,
        reasons=reasons,
        robot_composed_seq=robot_composition.ledger_seq,
        task_class=request.task_class,
        zone=request.zone,
        policy_mode=POLICY_MODE_STUB,
        authority_public_key_hex=authority_public_key_hex,
        signature_hex=signature_hex,
        ledger_seq=entry.seq,
        chain_head=chain_head,
    )
