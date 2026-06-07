"""Freshness-and-signature verification for mate-time attestation.

Load-bearing logic depends only on enrolled public keys and signatures — never
on a concrete ``Signer`` implementation. Module-side signing stays behind the
``Signer`` interface in attestation_signer.py; verification here uses only the
public key hex supplied by the enrolment registry.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from attestation.attestation_models import AttestationReason, AttestationResult, Challenge


def issue_challenge(module_id: str) -> Challenge:
    """Issue a freshness-bound challenge with a 32-byte CSPRNG nonce."""
    nonce = os.urandom(32)
    return Challenge(
        module_id=module_id,
        nonce_hex=nonce.hex(),
        issued_at=datetime.now(timezone.utc),
    )


def verify_response(
    challenge: Challenge,
    signature: bytes,
    enrolled_public_key_hex: str,
    *,
    now: datetime | None = None,
    ttl_seconds: float = 5,
) -> AttestationResult:
    """Verify freshness first, then the Ed25519 signature against the enrolled key."""
    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")

    verified_at = now
    nonce_bytes = bytes.fromhex(challenge.nonce_hex)

    expiry = challenge.issued_at + timedelta(seconds=ttl_seconds)
    if now > expiry:
        return AttestationResult(
            module_id=challenge.module_id,
            verified=False,
            reason=AttestationReason.CHALLENGE_EXPIRED,
            challenge_nonce_hex=challenge.nonce_hex,
            verified_at=verified_at,
        )

    public_key = Ed25519PublicKey.from_public_bytes(
        bytes.fromhex(enrolled_public_key_hex)
    )
    try:
        public_key.verify(signature, nonce_bytes)
    except InvalidSignature:
        return AttestationResult(
            module_id=challenge.module_id,
            verified=False,
            reason=AttestationReason.SIGNATURE_INVALID,
            challenge_nonce_hex=challenge.nonce_hex,
            verified_at=verified_at,
        )

    return AttestationResult(
        module_id=challenge.module_id,
        verified=True,
        reason=AttestationReason.OK,
        challenge_nonce_hex=challenge.nonce_hex,
        verified_at=verified_at,
    )
