"""Inicializacao e composicao da aplicacao."""

from __future__ import annotations

import logging
import sys

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from catalog.api import register_api_routes, register_frontend_routes
from catalog.core import configure_logging, load_settings


logger = logging.getLogger(__name__)
SECURITY_HEADERS = {
    "Content-Security-Policy": "frame-ancestors 'none'; base-uri 'self'; object-src 'none'",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-Permitted-Cross-Domain-Policies": "none",
}


def _configure_cors(app: FastAPI, allow_origins: list[str], allow_credentials: bool) -> None:
    try:
        from fastapi.middleware.cors import CORSMiddleware
    except Exception:
        logger.warning("fastapi CORS middleware not installed; cross-origin requests may fail.")
        return

    # Navegadores rejeitam origem coringa quando credenciais estao habilitadas.
    if allow_credentials and "*" in allow_origins:
        allow_credentials = False

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _configure_security_headers(app: FastAPI) -> None:
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        for header, value in SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        if request.url.scheme == "https":
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=63072000; includeSubDomains",
            )
        return response


def _register_disabled_docs_routes(app: FastAPI) -> None:
    @app.get("/docs")
    @app.get("/redoc")
    @app.get("/openapi.json")
    async def disabled_api_docs():
        return JSONResponse(status_code=404, content={"error": "API docs disabled"})


def create_app() -> FastAPI:
    # Carrega o .env antes de importar modulos que dependem do ambiente.
    load_dotenv()
    configure_logging()
    settings = load_settings()

    logger.info("Starting Catalogo API with Python executable %s", sys.executable)

    app = FastAPI(
        title="Catalogo API",
        version="1.0.0",
        docs_url="/docs" if settings.api_docs_enabled else None,
        redoc_url="/redoc" if settings.api_docs_enabled else None,
        openapi_url="/openapi.json" if settings.api_docs_enabled else None,
    )
    _configure_cors(
        app,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=settings.cors_allow_credentials,
    )
    _configure_security_headers(app)
    if not settings.api_docs_enabled:
        _register_disabled_docs_routes(app)
    register_api_routes(app)
    register_frontend_routes(
        app,
        frontend_dir=settings.frontend_dir,
        index_file=settings.frontend_index,
    )
    return app
