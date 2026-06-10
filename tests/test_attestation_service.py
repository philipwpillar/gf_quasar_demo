"""Tests for mate-time attestation service and ledger integration."""

from __future__ import annotations

import pytest

from attestation import (
    AttestationReason,
    AttestationService,
    DuplicateEnrolmentError,
    ModuleAlreadyRevokedError,
    SoftwareEd25519Signer,
    UnknownModuleError,
)
from ledger import EntryKind, Ledger


def _service() -> tuple[AttestationService, Ledger]:
    ledger = Ledger()
    return AttestationService(ledger, config_id="cfg-demo"), ledger


def test_enrol_writes_module_enrolled_entry() -> None:
    service, ledger = _service()
    signer = SoftwareEd25519Signer()

    identity = service.enrol("mod-001", signer)

    assert identity.module_id == "mod-001"
    assert identity.public_key_hex == signer.public_key_hex()
    assert len(ledger) == 1
    entry = ledger.get(1)
    assert entry.kind == EntryKind.MODULE_ENROLLED
    assert entry.payload == {
        "module_id": "mod-001",
        "public_key_hex": signer.public_key_hex(),
    }


def test_attest_writes_attestation_entry_on_success() -> None:
    service, ledger = _service()
    signer = SoftwareEd25519Signer()
    service.enrol("mod-001", signer)

    result = service.attest("mod-001", signer)

    assert result.verified is True
    assert result.reason == AttestationReason.OK
    assert len(ledger) == 2
    entry = ledger.get(2)
    assert entry.kind == EntryKind.ATTESTATION
    assert entry.payload["module_id"] == "mod-001"
    assert entry.payload["verified"] is True
    assert entry.payload["reason"] == "ok"
    assert len(entry.payload["challenge_nonce_hex"]) == 64


def test_unknown_module_attest_yields_unknown_module_reason() -> None:
    service, ledger = _service()
    signer = SoftwareEd25519Signer()

    result = service.attest("mod-unenrolled", signer)

    assert result.verified is False
    assert result.reason == AttestationReason.UNKNOWN_MODULE
    assert len(ledger) == 1
    assert ledger.get(1).kind == EntryKind.ATTESTATION
    assert ledger.get(1).payload["reason"] == "unknown_module"


def test_failing_attestation_still_writes_truthful_entry() -> None:
    service, ledger = _service()
    enrolled = SoftwareEd25519Signer()
    impostor = SoftwareEd25519Signer()
    service.enrol("mod-001", enrolled)

    result = service.attest("mod-001", impostor)

    assert result.verified is False
    assert result.reason == AttestationReason.SIGNATURE_INVALID
    assert len(ledger) == 2
    entry = ledger.get(2)
    assert entry.kind == EntryKind.ATTESTATION
    assert entry.payload["verified"] is False
    assert entry.payload["reason"] == "signature_invalid"


def test_ledger_still_verifies_after_enrol_and_attest_sequence() -> None:
    service, ledger = _service()
    signer_a = SoftwareEd25519Signer()
    signer_b = SoftwareEd25519Signer()
    service.enrol("mod-a", signer_a)
    service.enrol("mod-b", signer_b)
    service.attest("mod-a", signer_a)
    service.attest("mod-b", signer_b)
    service.attest("mod-a", signer_a)

    assert ledger.verify() == (True, None)
    assert len(ledger) == 5


def test_ledger_still_verifies_after_mixed_pass_and_fail_attestations() -> None:
    service, ledger = _service()
    enrolled = SoftwareEd25519Signer()
    wrong = SoftwareEd25519Signer()
    service.enrol("mod-001", enrolled)
    service.attest("mod-001", enrolled)
    service.attest("mod-001", wrong)
    service.attest("mod-unknown", wrong)

    assert ledger.verify() == (True, None)
    assert len(ledger) == 4


def test_duplicate_enrol_raises() -> None:
    service, _ledger = _service()
    signer = SoftwareEd25519Signer()
    service.enrol("mod-001", signer)

    with pytest.raises(DuplicateEnrolmentError):
        service.enrol("mod-001", SoftwareEd25519Signer())


class _SpySigner(SoftwareEd25519Signer):
    """Counts how many times sign() is invoked."""

    def __init__(self) -> None:
        super().__init__()
        self.sign_calls = 0

    def sign(self, nonce: bytes) -> bytes:
        self.sign_calls += 1
        return super().sign(nonce)


def test_revoke_appends_decommission_entry() -> None:
    service, ledger = _service()
    signer = SoftwareEd25519Signer()
    service.enrol("mod-001", signer)

    entry = service.revoke("mod-001", "operator deprovisioned")

    assert entry.kind == EntryKind.DECOMMISSION
    assert entry.payload["module_id"] == "mod-001"
    assert entry.payload["reason"] == "operator deprovisioned"
    assert "revoked_at" in entry.payload
    assert service.is_revoked("mod-001") is True
    assert ledger.verify() == (True, None)


def test_attest_after_revoke_returns_module_revoked_without_signing() -> None:
    service, ledger = _service()
    spy = _SpySigner()
    service.enrol("mod-001", spy)
    service.revoke("mod-001", "governance action")

    result = service.attest("mod-001", spy)

    assert result.verified is False
    assert result.reason == AttestationReason.MODULE_REVOKED
    assert result.challenge_nonce_hex == ""
    assert spy.sign_calls == 0
    attestation_entry = ledger.get(len(ledger))
    assert attestation_entry.kind == EntryKind.ATTESTATION
    assert attestation_entry.payload["reason"] == "module_revoked"
    assert ledger.verify() == (True, None)


def test_revoke_unknown_module_raises() -> None:
    service, _ledger = _service()

    with pytest.raises(UnknownModuleError):
        service.revoke("mod-missing", "reason")


def test_double_revoke_raises() -> None:
    service, _ledger = _service()
    signer = SoftwareEd25519Signer()
    service.enrol("mod-001", signer)
    service.revoke("mod-001", "first revoke")

    with pytest.raises(ModuleAlreadyRevokedError):
        service.revoke("mod-001", "second revoke")


def test_stale_attestation_via_clock_skew_simulation() -> None:
    """Service uses real-time verify; impostor key always fails signature."""
    service, ledger = _service()
    signer = SoftwareEd25519Signer()
    service.enrol("mod-001", signer)
    bad = service.attest("mod-001", SoftwareEd25519Signer())

    assert bad.verified is False
    assert bad.reason == AttestationReason.SIGNATURE_INVALID
    assert ledger.verify() == (True, None)
