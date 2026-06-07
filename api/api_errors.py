"""HTTP error mapping for the API gateway — no business logic."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from attestation import AttestationError, DuplicateEnrolmentError, UnknownModuleError
from ledger import ChainBrokenError, LedgerError
from policy import ClearanceError, MissingModuleSignerError


def register_exception_handlers(app: FastAPI) -> None:
    """Wire component exceptions to structured HTTP responses."""

    @app.exception_handler(DuplicateEnrolmentError)
    async def duplicate_enrolment_handler(
        _request: Request, exc: DuplicateEnrolmentError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={
                "error": "duplicate_enrolment",
                "message": str(exc),
                "module_id": exc.module_id,
            },
        )

    @app.exception_handler(UnknownModuleError)
    async def unknown_module_handler(
        _request: Request, exc: UnknownModuleError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={
                "error": "unknown_module",
                "message": str(exc),
                "module_id": exc.module_id,
            },
        )

    @app.exception_handler(MissingModuleSignerError)
    async def missing_module_signer_handler(
        _request: Request, exc: MissingModuleSignerError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={
                "error": "missing_module_signer",
                "message": str(exc),
                "module_id": exc.module_id,
            },
        )

    @app.exception_handler(AttestationError)
    async def attestation_error_handler(
        _request: Request, exc: AttestationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"error": "attestation_error", "message": str(exc)},
        )

    @app.exception_handler(ClearanceError)
    async def clearance_error_handler(
        _request: Request, exc: ClearanceError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"error": "clearance_error", "message": str(exc)},
        )

    @app.exception_handler(ChainBrokenError)
    async def chain_broken_handler(
        _request: Request, exc: ChainBrokenError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "error": "chain_broken",
                "message": str(exc),
                "first_broken_seq": exc.seq,
            },
        )

    @app.exception_handler(LedgerError)
    async def ledger_error_handler(
        _request: Request, exc: LedgerError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"error": "ledger_error", "message": str(exc)},
        )
