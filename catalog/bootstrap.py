"""Inicializacao e composicao da aplicacao."""

from __future__ import annotations

import sys

from dotenv import load_dotenv
from fastapi import FastAPI

from catalog.api import register_api_routes, register_frontend_routes
from catalog.core import load_settings


def _configure_cors(app: FastAPI, allow_origins: list[str], allow_credentials: bool) -> None:
    try:
        from fastapi.middleware.cors import CORSMiddleware
    except Exception:
        print("WARNING: fastapi CORS middleware not installed; cross-origin requests may fail.")
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


def create_app() -> FastAPI:
    # Carrega o .env antes de importar modulos que dependem do ambiente.
    load_dotenv()
    settings = load_settings()

    print(f"[startup] using python executable: {sys.executable}")

    app = FastAPI(
        title="Catalogo API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    _configure_cors(
        app,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=settings.cors_allow_credentials,
    )
    register_api_routes(app)
    register_frontend_routes(
        app,
        frontend_dir=settings.frontend_dir,
        index_file=settings.frontend_index,
    )
    return app
