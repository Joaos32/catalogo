"""Rotas para arquivos estaticos do frontend."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse


def _resolve_frontend_file(frontend_dir: Path, path: str) -> Path | None:
    """Resolve caminho de arquivo do frontend e bloqueia traversal fora de frontend/."""
    root = frontend_dir.resolve()
    candidate = (root / path).resolve()
    try:
        candidate.relative_to(root)
    except (OSError, RuntimeError, ValueError):
        return None
    if candidate.is_file():
        return candidate
    return None


def register_frontend_routes(app: FastAPI, frontend_dir: Path, index_file: Path) -> None:
    @app.get("/")
    async def index():
        return FileResponse(index_file)

    @app.get("/{full_path:path}")
    async def spa(full_path: str):
        target = _resolve_frontend_file(frontend_dir, full_path)
        if target:
            return FileResponse(target)
        return FileResponse(index_file)
