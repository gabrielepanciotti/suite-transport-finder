"""Finder-compatible API error envelopes."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def install_error_handlers(app: FastAPI) -> None:
    """Install compatibility-preserving errors for HTTP and validation failures."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException,
    ) -> JSONResponse:
        del request
        if exc.status_code == 404:
            code, message = "not_found", "Risorsa non trovata"
        else:
            code, message = f"http_{exc.status_code}", str(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": code, "message": message, "field": None}, "detail": exc.detail},
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError,
    ) -> JSONResponse:
        del request
        errors = exc.errors()
        location = errors[0].get("loc", ()) if errors else ()
        field = str(location[-1]) if location else None
        message = "Dati della richiesta non validi"
        if field is not None:
            message = f"Il campo '{field}' non è valido"
        return JSONResponse(
            status_code=422,
            content={
                "error": {"code": "validation_error", "message": message, "field": field},
                "detail": errors,
            },
        )
