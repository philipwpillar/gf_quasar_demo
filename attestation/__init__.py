"""Module identity + mate-time attestation.  [REAL — load-bearing]

Freshness-bound challenge-response verified against a secure element.
Ed25519 in software for the demo; signing step swaps onto an
ATECC608 / TPM 2.0 dev board without changing the protocol.
We claim a real secure element and a real attestation protocol.
We do NOT claim a full hardware root-of-trust.
"""
