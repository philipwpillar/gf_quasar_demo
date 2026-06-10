"""Key-custody abstraction for mate-time attestation signing.

This module is the pivot point between software signers and a real secure
element. The attestation protocol depends solely on the ``Signer`` interface;
verification dispatches on ``key_algorithm`` recorded at enrolment time.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

from attestation.attestation_models import KeyAlgorithm


class Signer(ABC):
    """Sign a fresh nonce inside key custody.

    ``sign``, ``public_key_hex``, and ``key_algorithm`` are the operations the
    attestation protocol needs from the module side. A future secure-element
    implementation satisfies this same interface; verification dispatches on
    the enrolled algorithm.
    """

    @property
    @abstractmethod
    def key_algorithm(self) -> KeyAlgorithm:
        """Algorithm this signer uses for mate-time signatures."""

    @abstractmethod
    def sign(self, nonce: bytes) -> bytes:
        """Return a signature over *nonce* (32 bytes)."""

    @abstractmethod
    def public_key_hex(self) -> str:
        """Return the enrolled public key as lowercase hex."""


class SoftwareEd25519Signer(Signer):
    """In-process Ed25519 signer for development and automated tests.

    Trust boundary (honest scope): this holds a real Ed25519 private key in
    process memory. It is suitable for protocol development and CI. It is NOT
    non-extractable hardware custody and does NOT constitute a full hardware
    root-of-trust tied to secure boot or firmware provenance.
    """

    @property
    def key_algorithm(self) -> KeyAlgorithm:
        return KeyAlgorithm.ED25519

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


class SoftwareP256Signer(Signer):
    """Software ECDSA P-256 signer that pins the ATECC608 byte contract.

    Signs the 32-byte nonce directly as the digest input (no additional hashing).
    Returns raw 64-byte R||S across the ``Signer`` boundary; public keys are
    uncompressed SEC1 points (0x04||X||Y). Custody is software — this signer
    exists to prove the P-256 verification path before element custody lands.
    """

    @property
    def key_algorithm(self) -> KeyAlgorithm:
        return KeyAlgorithm.ECDSA_P256

    def __init__(self, private_key: ec.EllipticCurvePrivateKey | None = None) -> None:
        self._private_key = private_key or ec.generate_private_key(ec.SECP256R1())

    def sign(self, nonce: bytes) -> bytes:
        der_sig = self._private_key.sign(
            nonce,
            ec.ECDSA(utils.Prehashed(hashes.SHA256())),
        )
        r, s = decode_dss_signature(der_sig)
        return r.to_bytes(32, "big") + s.to_bytes(32, "big")

    def public_key_hex(self) -> str:
        numbers = self._private_key.public_key().public_numbers()
        return (b"\x04" + numbers.x.to_bytes(32, "big") + numbers.y.to_bytes(32, "big")).hex()


# TODO: SecureElementSigner(Signer) — custody swap arrives in step 8b (ATECC608).
# Algorithm-aware verification dispatch is ready; only key custody changes when
# the element lands. Contract (same interface, element custody):
#   - key_algorithm -> ECDSA_P256
#   - sign(nonce: bytes) -> bytes  : element signs the 32-byte nonce as digest;
#     returns raw 64-byte R||S (not DER).
#   - public_key_hex() -> str       : uncompressed SEC1 point (130 hex chars).
# attestation_core and attestation_service must not change when this lands.
