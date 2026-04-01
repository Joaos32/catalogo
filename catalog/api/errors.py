"""Helpers para respostas de erro seguras da API."""

from __future__ import annotations

from fastapi.responses import JSONResponse


INTERNAL_SERVER_ERROR_MESSAGE = "internal server error"


def internal_server_error_response() -> JSONResponse:
    """Retorna uma resposta padronizada sem vazar detalhes internos."""
    return JSONResponse(
        status_code=500,
        content={"error": INTERNAL_SERVER_ERROR_MESSAGE},
    )
