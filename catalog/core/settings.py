"""Configuracoes de execucao da aplicacao de catalogo."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _parse_csv_env(value: str | None, default: list[str]) -> list[str]:
    if not value:
        return default
    parsed = [item.strip() for item in value.split(",")]
    values = [item for item in parsed if item]
    return values or default


def _parse_bool_env(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _optional_env(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _default_cors_origins() -> list[str]:
    """Origens locais seguras para desenvolvimento por padrao."""
    return [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:5000",
        "http://localhost:5000",
    ]


def _resolve_frontend_paths(base_dir: Path) -> tuple[Path, Path]:
    frontend_root = base_dir / "frontend"

    dist_index = frontend_root / "dist" / "index.html"
    if dist_index.is_file():
        return dist_index.parent, dist_index

    legacy_index = frontend_root / "legacy" / "index.html"
    if legacy_index.is_file():
        return legacy_index.parent, legacy_index

    default_index = frontend_root / "index.html"
    return frontend_root, default_index


@dataclass(frozen=True)
class Settings:
    base_dir: Path
    frontend_dir: Path
    frontend_index: Path
    host: str
    port: int
    api_docs_enabled: bool
    cors_allow_origins: list[str]
    cors_allow_credentials: bool
    erp_admin_token: str | None


def load_settings() -> Settings:
    base_dir = Path(__file__).resolve().parents[2]
    frontend_dir, frontend_index = _resolve_frontend_paths(base_dir)
    return Settings(
        base_dir=base_dir,
        frontend_dir=frontend_dir,
        frontend_index=frontend_index,
        host=os.getenv("CATALOG_HOST", "127.0.0.1"),
        port=int(os.getenv("CATALOG_PORT", "8000")),
        api_docs_enabled=_parse_bool_env(os.getenv("CATALOG_ENABLE_API_DOCS"), default=True),
        cors_allow_origins=_parse_csv_env(
            os.getenv("CATALOG_CORS_ALLOW_ORIGINS"),
            default=_default_cors_origins(),
        ),
        cors_allow_credentials=_parse_bool_env(
            os.getenv("CATALOG_CORS_ALLOW_CREDENTIALS"),
            default=True,
        ),
        erp_admin_token=_optional_env(os.getenv("CATALOG_ERP_ADMIN_TOKEN")),
    )
