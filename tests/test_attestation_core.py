"""Tests for mate-time attestation core (freshness + signature verification)."""

from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from attestation import (
    AttestationReason,
    SoftwareEd25519Signer,
    issue_challenge,
    verify_response,
)


def test_fresh_nonce_signs_and_verifies_ok() -> None:
    signer = SoftwareEd25519Signer()
    challenge = issue_challenge("mod-alpha")
    nonce_bytes = bytes.fromhex(challenge.nonce_hex)
    signature = signer.sign(nonce_bytes)

    result = verify_response(
        challenge,
        signature,
        signer.public_key_hex(),
    )

    assert result.verified is True
    assert result.reason == AttestationReason.OK
    assert result.challenge_nonce_hex == challenge.nonce_hex


def test_stale_challenge_returns_challenge_expired() -> None:
    signer = SoftwareEd25519Signer()
    issued_at = datetime(2026, 6, 7, 12, 0, 0, tzinfo=timezone.utc)
    challenge = issue_challenge("mod-alpha").model_copy(update={"issued_at": issued_at})
    nonce_bytes = bytes.fromhex(challenge.nonce_hex)
    signature = signer.sign(nonce_bytes)
    now = issued_at + timedelta(seconds=6)

    result = verify_response(
        challenge,
        signature,
        signer.public_key_hex(),
        now=now,
        ttl_seconds=5,
    )

    assert result.verified is False
    assert result.reason == AttestationReason.CHALLENGE_EXPIRED


def test_tampered_signature_returns_signature_invalid_without_raising() -> None:
    signer = SoftwareEd25519Signer()
    challenge = issue_challenge("mod-alpha")
    nonce_bytes = bytes.fromhex(challenge.nonce_hex)
    signature = bytearray(signer.sign(nonce_bytes))
    signature[0] ^= 0xFF

    result = verify_response(
        challenge,
        bytes(signature),
        signer.public_key_hex(),
    )

    assert result.verified is False
    assert result.reason == AttestationReason.SIGNATURE_INVALID


def test_signature_for_different_nonce_returns_signature_invalid() -> None:
    signer = SoftwareEd25519Signer()
    challenge = issue_challenge("mod-alpha")
    other_nonce = bytes.fromhex(issue_challenge("mod-alpha").nonce_hex)
    signature = signer.sign(other_nonce)

    result = verify_response(
        challenge,
        signature,
        signer.public_key_hex(),
    )

    assert result.verified is False
    assert result.reason == AttestationReason.SIGNATURE_INVALID


def test_wrong_module_key_fails_against_enrolled_key() -> None:
    enrolled_signer = SoftwareEd25519Signer()
    impostor_signer = SoftwareEd25519Signer()
    challenge = issue_challenge("mod-alpha")
    nonce_bytes = bytes.fromhex(challenge.nonce_hex)
    signature = impostor_signer.sign(nonce_bytes)

    result = verify_response(
        challenge,
        signature,
        enrolled_signer.public_key_hex(),
    )

    assert result.verified is False
    assert result.reason == AttestationReason.SIGNATURE_INVALID


def test_nonce_is_32_bytes_and_differs_across_challenges() -> None:
    first = issue_challenge("mod-a")
    second = issue_challenge("mod-a")

    assert len(first.nonce_hex) == 64
    assert len(bytes.fromhex(first.nonce_hex)) == 32
    assert first.nonce_hex != second.nonce_hex


def test_verify_response_uses_public_key_only_no_signer_object() -> None:
    """Verifier path: public key hex + signature, no Signer instance."""
    signer = SoftwareEd25519Signer()
    public_key_hex = signer.public_key_hex()
    challenge = issue_challenge("mod-alpha")
    signature = signer.sign(bytes.fromhex(challenge.nonce_hex))

    result = verify_response(challenge, signature, public_key_hex)

    assert result.verified is True
    assert result.reason == AttestationReason.OK


def test_attestation_core_does_not_import_software_signer() -> None:
    """Custody-swap guard: core must not depend on SoftwareEd25519Signer."""
    core_path = Path(__file__).resolve().parents[1] / "attestation" / "attestation_core.py"
    module = ast.parse(core_path.read_text(encoding="utf-8"))
    imported_names: set[str] = set()
    for node in ast.walk(module):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_names.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.add(node.module)
            for alias in node.names:
                imported_names.add(f"{node.module}.{alias.name}")

    forbidden = {
        "attestation.attestation_signer",
        "attestation.attestation_signer.SoftwareEd25519Signer",
        "SoftwareEd25519Signer",
    }
    assert imported_names.isdisjoint(forbidden)


def test_freshness_checked_before_signature() -> None:
    """Expired challenges fail fast with challenge_expired even if signature is valid."""
    signer = SoftwareEd25519Signer()
    issued_at = datetime(2026, 6, 7, 12, 0, 0, tzinfo=timezone.utc)
    challenge = issue_challenge("mod-alpha").model_copy(update={"issued_at": issued_at})
    signature = signer.sign(bytes.fromhex(challenge.nonce_hex))
    now = issued_at + timedelta(seconds=10)

    result = verify_response(
        challenge,
        signature,
        signer.public_key_hex(),
        now=now,
    )

    assert result.reason == AttestationReason.CHALLENGE_EXPIRED


def test_naive_now_raises() -> None:
    signer = SoftwareEd25519Signer()
    challenge = issue_challenge("mod-alpha")
    signature = signer.sign(bytes.fromhex(challenge.nonce_hex))
    naive_now = datetime(2026, 6, 7, 12, 0, 0)

    with pytest.raises(ValueError, match="timezone-aware"):
        verify_response(challenge, signature, signer.public_key_hex(), now=naive_now)
