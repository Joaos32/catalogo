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
    cors_allow_origins: list[str]
    cors_allow_credentials: bool


def load_settings() -> Settings:
    base_dir = Path(__file__).resolve().parents[2]
    frontend_dir, frontend_index = _resolve_frontend_paths(base_dir)
    return Settings(
        base_dir=base_dir,
        frontend_dir=frontend_dir,
        frontend_index=frontend_index,
        host=os.getenv("CATALOG_HOST", "127.0.0.1"),
        port=int(os.getenv("CATALOG_PORT", "8000")),
        cors_allow_origins=_parse_csv_env(
            os.getenv("CATALOG_CORS_ALLOW_ORIGINS"),
            default=["*"],
        ),
        cors_allow_credentials=os.getenv("CATALOG_CORS_ALLOW_CREDENTIALS", "true").lower()
        not in {"0", "false", "no"},
    )
