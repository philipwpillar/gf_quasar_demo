"""FastAPI gateway — pydantic-validated boundaries for the Quasar demo.

The front end and console go through this gateway only; they never import
``AttestationService``, ``ClearanceService``, or ``Ledger`` directly.
Pydantic validates every request/response shape (422 on shape errors).
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")  # repo root; never committed

import os

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from attestation import AttestationService, SoftwareEd25519Signer
from corpus import CorpusService
from ledger import Ledger
from narrator import NarratorService
from policy import ClearanceService
from bootstrap_site_package import ensure_quasar_site_package

ensure_quasar_site_package()
from quasar_site import SiteService

from api.api_errors import register_exception_handlers
from api.api_routes_attestation import router as attestation_router
from api.api_routes_clearance import router as clearance_router
from api.api_routes_corpus import router as corpus_router
from api.api_routes_ledger import router as ledger_router
from api.api_routes_narrator import router as narrator_router
from api.api_routes_site import router as site_router


def _load_clearance_authority_signer() -> SoftwareEd25519Signer:
    """Load clearance-authority key from env, or generate ephemerally if unset."""
    key_hex = os.environ.get("QUASAR_CLEARANCE_AUTHORITY_KEY_HEX", "").strip()
    if key_hex:
        private_key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(key_hex))
        return SoftwareEd25519Signer(private_key=private_key)
    # Ephemeral demo key when unset — not persisted across restarts; never logged.
    return SoftwareEd25519Signer()


def _load_site_authority_signer() -> SoftwareEd25519Signer:
    """Load site-authority key from env, or generate ephemerally if unset."""
    key_hex = os.environ.get("QUASAR_SITE_AUTHORITY_KEY_HEX", "").strip()
    if key_hex:
        private_key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(key_hex))
        return SoftwareEd25519Signer(private_key=private_key)
    return SoftwareEd25519Signer()


def create_app(*, config_id: str = "cfg-demo") -> FastAPI:
    """Construct the gateway with fresh in-memory singletons (demo wiring)."""
    app = FastAPI(
        title="GravitonForge Quasar Demo API",
        description=(
            "Trust-and-provenance gateway. Attestation and ledger are REAL; "
            "policy breadth is STUBBED (curated single-task rules)."
        ),
    )

    ledger = Ledger()
    attestation = AttestationService(ledger, config_id=config_id)
    authority_signer = _load_clearance_authority_signer()
    clearance = ClearanceService(ledger, attestation, authority_signer)
    site_authority_signer = _load_site_authority_signer()
    site = SiteService(ledger, attestation, site_authority_signer)
    corpus = CorpusService(ledger)
    narrator = NarratorService(ledger)

    # Demo key management: module signers created at enrol time in process memory.
    # Real deployment uses secure elements per the Signer swap — private keys are
    # never logged or serialised.
    app.state.ledger = ledger
    app.state.attestation = attestation
    app.state.clearance = clearance
    app.state.site = site
    app.state.corpus = corpus
    app.state.narrator = narrator
    app.state.module_signers: dict[str, SoftwareEd25519Signer] = {}
    app.state.new_module_signer = SoftwareEd25519Signer

    register_exception_handlers(app)

    if os.environ.get("QUASAR_ENABLE_CORS", "1").lower() in ("1", "true", "yes"):
        cors_origin = os.environ.get(
            "QUASAR_CORS_ORIGIN", "http://localhost:5173"
        ).strip()
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[cors_origin],
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type"],
        )

    app.include_router(attestation_router)
    app.include_router(clearance_router)
    app.include_router(site_router)
    app.include_router(ledger_router)
    app.include_router(corpus_router)
    app.include_router(narrator_router)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
