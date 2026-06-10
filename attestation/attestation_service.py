"""Orchestration: mate-time attestation wired to the forensic ledger."""

from __future__ import annotations

from datetime import datetime, timezone

from ledger import EntryKind, Ledger, LedgerEntry

from attestation.attestation_core import issue_challenge, verify_response
from attestation.attestation_errors import (
    DuplicateEnrolmentError,
    ModuleAlreadyRevokedError,
    UnknownModuleError,
)
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
        self._revoked: set[str] = set()

    @property
    def registry(self) -> dict[str, ModuleIdentity]:
        """Read-only view of enrolled module identities (demo in-memory store)."""
        return dict(self._registry)

    def is_enrolled(self, module_id: str) -> bool:
        return module_id in self._registry

    def is_revoked(self, module_id: str) -> bool:
        return module_id in self._revoked

    def revoke(self, module_id: str, reason: str) -> LedgerEntry:
        """Administratively revoke a module — registry status + forensic ledger record.

        This is governance deprovisioning: the enrolled module is marked revoked
        and a ``decommission`` entry is appended. It does NOT prove the physical
        module is disabled; that requires a future kill-and-prove-dead protocol.
        """
        if module_id not in self._registry:
            raise UnknownModuleError(module_id)
        if module_id in self._revoked:
            raise ModuleAlreadyRevokedError(module_id)

        revoked_at = datetime.now(timezone.utc)
        entry = self._ledger.append(
            EntryKind.DECOMMISSION,
            self._config_id,
            {
                "module_id": module_id,
                "reason": reason,
                "revoked_at": revoked_at.isoformat(),
            },
            occurred_at=revoked_at,
        )
        self._revoked.add(module_id)
        return entry

    def enrol(self, module_id: str, signer: Signer) -> ModuleIdentity:
        """Register a module's public key and append ``module_enrolled`` to the ledger."""
        if module_id in self._registry:
            raise DuplicateEnrolmentError(module_id)

        identity = ModuleIdentity(
            module_id=module_id,
            public_key_hex=signer.public_key_hex(),
            key_algorithm=signer.key_algorithm,
        )
        self._ledger.append(
            EntryKind.MODULE_ENROLLED,
            self._config_id,
            {
                "module_id": identity.module_id,
                "public_key_hex": identity.public_key_hex,
                "key_algorithm": identity.key_algorithm.value,
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

        if module_id in self._revoked:
            result = AttestationResult(
                module_id=module_id,
                verified=False,
                reason=AttestationReason.MODULE_REVOKED,
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
            key_algorithm=identity.key_algorithm,
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
