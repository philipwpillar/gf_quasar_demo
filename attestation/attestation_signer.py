"""Key-custody abstraction for mate-time attestation signing.

This module is the pivot point between software Ed25519 and a real secure
element. The attestation protocol depends solely on the ``Signer`` interface;
only key custody changes when we move to hardware.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


class Signer(ABC):
    """Sign a fresh nonce inside key custody.

    ``sign`` and ``public_key_hex`` are the only operations the attestation
    protocol needs from the module side. A future secure-element implementation
    satisfies this same interface; the challenge/verify flow does not change.
    """

    @abstractmethod
    def sign(self, nonce: bytes) -> bytes:
        """Return an Ed25519 signature over *nonce* (32 bytes)."""

    @abstractmethod
    def public_key_hex(self) -> str:
        """Return the enrolled Ed25519 public key as lowercase hex (32 bytes)."""


class SoftwareEd25519Signer(Signer):
    """In-process Ed25519 signer for development and automated tests.

    A future ``SecureElementSigner`` (ATECC608 / TPM 2.0 dev board) will
    satisfy the same ``Signer`` interface. ONLY key custody changes — the
    mate-time challenge-response protocol does not.

    Trust boundary (honest scope): this holds a real Ed25519 private key in
    process memory. It is suitable for protocol development and CI. It is NOT
    non-extractable hardware custody and does NOT constitute a full hardware
    root-of-trust tied to secure boot or firmware provenance.
    """

    def __init__(self, private_key: Ed25519PrivateKey | None = None) -> None:
        self._private_key = private_key or Ed25519PrivateKey.generate()

    def sign(self, nonce: bytes) -> bytes:
        return self._private_key.sign(nonce)

    def public_key_hex(self) -> str:
        raw = self._private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return raw.hex()


# TODO: SecureElementSigner(Signer) — drop-in for ATECC608 / TPM 2.0 dev board.
# Contract (same interface, different custody):
#   - sign(nonce: bytes) -> bytes  : delegate to the element; private key never
#     leaves the secure element.
#   - public_key_hex() -> str       : return the element's enrolled public key.
# The attestation_core and attestation_service layers must not change when this
# lands. Real secure element, real attestation protocol — not a full RoT claim.
