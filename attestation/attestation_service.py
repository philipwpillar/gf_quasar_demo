"""Orchestration: mate-time attestation wired to the forensic ledger."""

from __future__ import annotations

from datetime import datetime, timezone

from ledger import EntryKind, Ledger

from attestation.attestation_core import issue_challenge, verify_response
from attestation.attestation_errors import DuplicateEnrolmentError
from attestation.attestation_models import (
    AttestationReason,
    AttestationResult,
    ModuleIdentity,
)
from attestation.attestation_signer import Signer


def _result_to_payload(result: AttestationResult) -> dict:
    return {
        "module_id": result.module_id,
        "verified": result.verified,
        "reason": result.reason.value,
        "challenge_nonce_hex": result.challenge_nonce_hex,
        "verified_at": result.verified_at.isoformat(),
    }


class AttestationService:
    """Mate-time attestation orchestrator backed by the append-only ledger.

    Enrolment registry is in-memory for the demo; production persists enrolled
    identities while preserving the same ledger write contract.
    """

    def __init__(self, ledger: Ledger, *, config_id: str) -> None:
        self._ledger = ledger
        self._config_id = config_id
        self._registry: dict[str, ModuleIdentity] = {}

    @property
    def registry(self) -> dict[str, ModuleIdentity]:
        """Read-only view of enrolled module identities (demo in-memory store)."""
        return dict(self._registry)

    def is_enrolled(self, module_id: str) -> bool:
        return module_id in self._registry

    def enrol(self, module_id: str, signer: Signer) -> ModuleIdentity:
        """Register a module's public key and append ``module_enrolled`` to the ledger."""
        if module_id in self._registry:
            raise DuplicateEnrolmentError(module_id)

        identity = ModuleIdentity(
            module_id=module_id,
            public_key_hex=signer.public_key_hex(),
        )
        self._ledger.append(
            EntryKind.MODULE_ENROLLED,
            self._config_id,
            {
                "module_id": identity.module_id,
                "public_key_hex": identity.public_key_hex,
            },
        )
        self._registry[module_id] = identity
        return identity

    def attest(self, module_id: str, signer: Signer) -> AttestationResult:
        """Run mate-time challenge-response and append an ``attestation`` ledger entry."""
        verified_at = datetime.now(timezone.utc)

        identity = self._registry.get(module_id)
        if identity is None:
            result = AttestationResult(
                module_id=module_id,
                verified=False,
                reason=AttestationReason.UNKNOWN_MODULE,
                challenge_nonce_hex="",
                verified_at=verified_at,
            )
            self._append_attestation(result)
            return result

        challenge = issue_challenge(module_id)
        nonce_bytes = bytes.fromhex(challenge.nonce_hex)
        signature = signer.sign(nonce_bytes)
        result = verify_response(
            challenge,
            signature,
            identity.public_key_hex,
            now=verified_at,
        )
        self._append_attestation(result)
        return result

    def _append_attestation(self, result: AttestationResult) -> None:
        self._ledger.append(
            EntryKind.ATTESTATION,
            self._config_id,
            _result_to_payload(result),
            occurred_at=result.verified_at,
        )
