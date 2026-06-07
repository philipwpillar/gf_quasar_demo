"""Clearance orchestration: attestation gate + curated rules + signed verdict.

Contract: ``clear`` always runs a fresh mate-time attestation for every
``module_id`` via ``AttestationService.attest`` (never accepts stale refs).
Each module's ``ledger_seq`` is the sequence of that attestation entry — the
provenance link back to Tier 1 mate-time verification.

Policy breadth is STUBBED (``stub_curated_single_task``); attestation and
ledger writes remain REAL.
"""

from __future__ import annotations

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from attestation import AttestationService
from attestation.attestation_signer import Signer
from ledger import EntryKind, Ledger
from shared.canonical_hashing import canonical_bytes

from policy.policy_errors import MissingModuleSignerError
from policy.policy_models import (
    POLICY_MODE_STUB,
    ClearanceRequest,
    ClearanceVerdict,
    ModuleAttestationRef,
)
from policy.policy_rules import SUPPORTED_TASK_CLASS, evaluate_policy


def verdict_hashable_view(
    *,
    config_id: str,
    cleared: bool,
    reasons: list[str],
    attestation_refs: list[ModuleAttestationRef],
    policy_mode: str,
) -> dict:
    """Return the dict whose canonical bytes are signed and verified offline."""
    return {
        "config_id": config_id,
        "cleared": cleared,
        "reasons": reasons,
        "attestation_refs": [
            {
                "module_id": ref.module_id,
                "attested": ref.attested,
                "ledger_seq": ref.ledger_seq,
            }
            for ref in attestation_refs
        ],
        "policy_mode": policy_mode,
    }


def verify_verdict(verdict: ClearanceVerdict) -> bool:
    """Recompute canonical bytes and verify the authority signature offline."""
    message = canonical_bytes(
        verdict_hashable_view(
            config_id=verdict.config_id,
            cleared=verdict.cleared,
            reasons=verdict.reasons,
            attestation_refs=verdict.attestation_refs,
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


class ClearanceService:
    """Turn attestation results + curated rules into a signed ledger verdict."""

    def __init__(
        self,
        ledger: Ledger,
        attestation: AttestationService,
        authority_signer: Signer,
    ) -> None:
        self._ledger = ledger
        self._attestation = attestation
        self._authority_signer = authority_signer

    def clear(
        self,
        request: ClearanceRequest,
        signers: dict[str, Signer],
    ) -> ClearanceVerdict:
        attestation_refs: list[ModuleAttestationRef] = []

        for module_id in request.module_ids:
            signer = signers.get(module_id)
            if signer is None:
                raise MissingModuleSignerError(module_id)

            result = self._attestation.attest(module_id, signer)
            ledger_seq = len(self._ledger)
            attestation_refs.append(
                ModuleAttestationRef(
                    module_id=module_id,
                    attested=result.verified,
                    ledger_seq=ledger_seq,
                )
            )

        all_attested = all(ref.attested for ref in attestation_refs)
        rules_passed, rule_reasons = evaluate_policy(
            task_class=request.task_class,
            zone=request.zone,
            module_ids=request.module_ids,
        )

        cleared = all_attested and rules_passed
        reasons: list[str] = []

        if not all_attested:
            for ref in attestation_refs:
                if not ref.attested:
                    reasons.append(
                        f"not cleared: module {ref.module_id} failed attestation"
                    )

        if not rules_passed:
            reasons.extend(rule_reasons)
        elif cleared:
            reasons.append(
                f"cleared for {SUPPORTED_TASK_CLASS} in {request.zone}"
            )

        signature_hex = self._authority_signer.sign(
            canonical_bytes(
                verdict_hashable_view(
                    config_id=request.config_id,
                    cleared=cleared,
                    reasons=reasons,
                    attestation_refs=attestation_refs,
                    policy_mode=POLICY_MODE_STUB,
                )
            )
        ).hex()

        authority_public_key_hex = self._authority_signer.public_key_hex()

        entry = self._ledger.append(
            EntryKind.CLEARANCE_DECISION,
            request.config_id,
            {
                "config_id": request.config_id,
                "cleared": cleared,
                "reasons": reasons,
                "attestation_refs": [
                    ref.model_dump(mode="json") for ref in attestation_refs
                ],
                "policy_mode": POLICY_MODE_STUB,
                "authority_public_key_hex": authority_public_key_hex,
                "signature_hex": signature_hex,
            },
        )

        chain_head = entry.entry_hash
        assert chain_head is not None

        return ClearanceVerdict(
            config_id=request.config_id,
            cleared=cleared,
            reasons=reasons,
            attestation_refs=attestation_refs,
            policy_mode=POLICY_MODE_STUB,
            authority_public_key_hex=authority_public_key_hex,
            signature_hex=signature_hex,
            ledger_seq=entry.seq,
            chain_head=chain_head,
        )
