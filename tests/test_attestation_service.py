"""Tests for mate-time attestation service and ledger integration."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from api.api_main import create_app
from attestation import (
    AttestationReason,
    AttestationService,
    DuplicateEnrolmentError,
    KeyAlgorithm,
    ModuleAlreadyRevokedError,
    SoftwareEd25519Signer,
    SoftwareP256Signer,
    UnknownModuleError,
    issue_challenge,
    verify_response,
)
from ledger import EntryKind, Ledger
from policy import ClearanceVerdict, verify_verdict


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
        "key_algorithm": "ed25519",
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


def test_p256_enrol_writes_key_algorithm_in_payload() -> None:
    service, ledger = _service()
    signer = SoftwareP256Signer()

    identity = service.enrol("mod-p256", signer)

    assert identity.key_algorithm == KeyAlgorithm.ECDSA_P256
    entry = ledger.get(1)
    assert entry.payload["key_algorithm"] == "ecdsa_p256"


def test_p256_attest_happy_path() -> None:
    service, ledger = _service()
    signer = SoftwareP256Signer()
    service.enrol("mod-p256", signer)

    result = service.attest("mod-p256", signer)

    assert result.verified is True
    assert result.reason == AttestationReason.OK
    assert ledger.verify() == (True, None)


def test_p256_tampered_signature_via_service() -> None:
    service, ledger = _service()
    enrolled = SoftwareP256Signer()
    impostor = SoftwareP256Signer()
    service.enrol("mod-p256", enrolled)

    result = service.attest("mod-p256", impostor)

    assert result.verified is False
    assert result.reason == AttestationReason.SIGNATURE_INVALID
    assert ledger.verify() == (True, None)


def test_p256_expired_challenge_without_signature_check() -> None:
    service, _ledger = _service()
    signer = SoftwareP256Signer()
    service.enrol("mod-p256", signer)
    issued_at = datetime(2026, 6, 7, 12, 0, 0, tzinfo=timezone.utc)
    challenge = issue_challenge("mod-p256").model_copy(update={"issued_at": issued_at})
    now = issued_at + timedelta(seconds=6)

    result = verify_response(
        challenge,
        signer.sign(bytes.fromhex(challenge.nonce_hex)),
        signer.public_key_hex(),
        key_algorithm=KeyAlgorithm.ECDSA_P256,
        now=now,
        ttl_seconds=5,
    )

    assert result.reason == AttestationReason.CHALLENGE_EXPIRED


class _P256SpySigner(SoftwareP256Signer):
    def __init__(self) -> None:
        super().__init__()
        self.sign_calls = 0

    def sign(self, nonce: bytes) -> bytes:
        self.sign_calls += 1
        return super().sign(nonce)


def test_revoked_p256_module_never_signs() -> None:
    service, ledger = _service()
    spy = _P256SpySigner()
    service.enrol("mod-p256", spy)
    service.revoke("mod-p256", "governance action")

    result = service.attest("mod-p256", spy)

    assert result.verified is False
    assert result.reason == AttestationReason.MODULE_REVOKED
    assert spy.sign_calls == 0
    assert ledger.verify() == (True, None)


def test_p256_ledger_export_round_trip() -> None:
    service, ledger = _service()
    signer = SoftwareP256Signer()
    service.enrol("mod-p256", signer)
    service.attest("mod-p256", signer)

    exported = ledger.export()
    assert exported[0]["payload"]["key_algorithm"] == "ecdsa_p256"
    assert ledger.verify() == (True, None)


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_api_enrol_ecdsa_p256_returns_200(client: TestClient) -> None:
    response = client.post(
        "/modules/enrol",
        json={"module_id": "mod-p256-api", "key_algorithm": "ecdsa_p256"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["module_id"] == "mod-p256-api"
    assert body["key_algorithm"] == "ecdsa_p256"
    assert len(body["public_key_hex"]) == 130
    assert body["public_key_hex"].startswith("04")


def test_api_enrol_invalid_key_algorithm_returns_422(client: TestClient) -> None:
    response = client.post(
        "/modules/enrol",
        json={"module_id": "mod-bad", "key_algorithm": "rsa4096"},
    )
    assert response.status_code == 422


def test_mixed_algorithm_fleet_clears_composes_and_admits(client: TestClient) -> None:
    ed25519_response = client.post(
        "/modules/enrol",
        json={"module_id": "mod-ed25519", "key_algorithm": "ed25519"},
    )
    p256_response = client.post(
        "/modules/enrol",
        json={"module_id": "mod-p256", "key_algorithm": "ecdsa_p256"},
    )
    assert ed25519_response.status_code == 200
    assert p256_response.status_code == 200

    client.post("/attest", json={"module_id": "mod-ed25519"})
    client.post("/attest", json={"module_id": "mod-p256"})

    clearance_response = client.post(
        "/clearance",
        json={
            "config_id": "robot-mixed",
            "module_ids": ["mod-ed25519", "mod-p256"],
            "task_class": "industrial_inspection",
            "zone": "zone_b",
        },
    )
    assert clearance_response.status_code == 200
    verdict = ClearanceVerdict.model_validate(clearance_response.json())
    assert verdict.cleared is True
    assert verify_verdict(verdict) is True

    client.post("/vendors/enrol", json={"vendor_id": "vendor_alpha"})
    compose_response = client.post(
        "/robots/compose",
        json={
            "robot_id": "robot-mixed",
            "vendor_id": "vendor_alpha",
            "module_ids": ["mod-ed25519", "mod-p256"],
        },
    )
    assert compose_response.status_code == 200
    composition = compose_response.json()
    assert composition["composed"] is True

    admit_response = client.post(
        "/site/admit",
        json={
            "robot_id": "robot-mixed",
            "task_class": "industrial_inspection",
            "zone": "zone_b",
            "robot_composed_seq": composition["ledger_seq"],
        },
    )
    assert admit_response.status_code == 200
    admission = admit_response.json()
    assert admission["admitted"] is True

    verify_response_api = client.get("/ledger/verify")
    assert verify_response_api.status_code == 200
    assert verify_response_api.json() == {"intact": True, "first_broken_seq": None}

    export_response = client.get("/ledger/export")
    assert export_response.status_code == 200
    assert len(export_response.json()) > 0
