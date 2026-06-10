"""Tier 2 robot composition — trust verdict from attested module refs.

Vendor signatures are REAL Ed25519 over canonical bytes. In this demo, vendor
key custody is server-side software signers (same as module signers). In
production each vendor custodies its own key.
"""

from __future__ import annotations

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from attestation.attestation_signer import Signer
from ledger import EntryKind, Ledger
from policy.policy_models import ModuleAttestationRef
from shared.canonical_hashing import canonical_bytes

from .site_models import RobotComposition


def composition_hashable_view(
    *,
    robot_id: str,
    vendor_id: str,
    module_refs: list[ModuleAttestationRef],
) -> dict:
    """Return the dict whose canonical bytes the vendor signs and verifies offline."""
    return {
        "robot_id": robot_id,
        "vendor_id": vendor_id,
        "module_refs": [ref.model_dump(mode="json") for ref in module_refs],
    }


def verify_composition(
    composition: RobotComposition, enrolled_public_key_hex: str
) -> bool:
    """Recompute canonical bytes and verify the vendor signature offline."""
    message = canonical_bytes(
        composition_hashable_view(
            robot_id=composition.robot_id,
            vendor_id=composition.vendor_id,
            module_refs=composition.module_refs,
        )
    )
    public_key = Ed25519PublicKey.from_public_bytes(
        bytes.fromhex(enrolled_public_key_hex)
    )
    try:
        public_key.verify(
            bytes.fromhex(composition.vendor_signature_hex), message
        )
    except InvalidSignature:
        return False
    return True


def compose_robot(
    ledger: Ledger,
    *,
    robot_id: str,
    vendor_id: str,
    vendor_signer: Signer,
    module_refs: list[ModuleAttestationRef],
) -> RobotComposition:
    """Compose a robot identity and append ``robot_composed`` to the ledger.

    A robot is trustworthy only when EVERY constituent module attested true.
    Each ``module_ref`` carries the ledger sequence of its attestation entry.
    The vendor signs the canonical composition view with its enrolled key.
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

    vendor_public_key_hex = vendor_signer.public_key_hex()
    vendor_signature_hex = vendor_signer.sign(
        canonical_bytes(
            composition_hashable_view(
                robot_id=robot_id,
                vendor_id=vendor_id,
                module_refs=module_refs,
            )
        )
    ).hex()

    entry = ledger.append(
        EntryKind.ROBOT_COMPOSED,
        robot_id,
        {
            "robot_id": robot_id,
            "vendor_id": vendor_id,
            "vendor_signature_hex": vendor_signature_hex,
            "vendor_public_key_hex": vendor_public_key_hex,
            "module_refs": [ref.model_dump(mode="json") for ref in module_refs],
            "composed": composed,
            "reasons": reasons,
        },
    )

    chain_head = entry.entry_hash
    assert chain_head is not None

    return RobotComposition(
        robot_id=robot_id,
        vendor_id=vendor_id,
        vendor_signature_hex=vendor_signature_hex,
        vendor_public_key_hex=vendor_public_key_hex,
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
        vendor_id=payload["vendor_id"],
        vendor_signature_hex=payload["vendor_signature_hex"],
        vendor_public_key_hex=payload["vendor_public_key_hex"],
        module_refs=module_refs,
        composed=payload["composed"],
        reasons=list(payload["reasons"]),
        ledger_seq=entry.seq,
        chain_head=chain_head,
    )
