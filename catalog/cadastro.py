"""Processa exportacoes locais de CADASTRO.html e fornece dados por codigo."""

from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path
from threading import Lock
from typing import Dict


_CODE_PATTERN = re.compile(r"\b(?P<code>\d{3,8})\b")
_CACHE_LOCK = Lock()
_CACHE: Dict[str, object] = {"path": "", "mtime": -1.0, "records": {}}


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _candidate_paths() -> list[Path]:
    explicit = os.getenv("CATALOG_CADASTRO_HTML")
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))

    root = _project_root()
    candidates.extend(
        [
            root / "CADASTRO.html",
            root / "cadastro.html",
            root / "Cadastro.html",
        ]
    )
    return candidates


def resolve_cadastro_path(path_override: str | None = None) -> str | None:
    if path_override:
        candidate = Path(path_override)
        return str(candidate.resolve()) if candidate.is_file() else None

    for candidate in _candidate_paths():
        if candidate.is_file():
            return str(candidate.resolve())
    return None


def _repair_mojibake(value: str) -> str:
    # Alguns arquivos exportados contem UTF-8 interpretado como latin-1.
    if not value or not any(marker in value for marker in ("Ã", "Â", "â")):
        return value
    try:
        repaired = value.encode("latin1").decode("utf-8")
        return repaired
    except Exception:
        return value


def _clean_cell(value: str) -> str:
    cleaned = _repair_mojibake(value or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if cleaned in {"***", "-", "—"}:
        return ""
    return cleaned


def _normalize_header(value: str) -> str:
    normalized = unicodedata.normalize("NFD", _clean_cell(value))
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return normalized.upper()


def _first_nonempty(*values: str) -> str:
    for value in values:
        cleaned = _clean_cell(value)
        if cleaned:
            return cleaned
    return ""


def _record_score(record: Dict[str, str]) -> tuple[int, int]:
    fields = ("name", "description", "specs", "category")
    filled = sum(1 for field in fields if record.get(field))
    richness = sum(len(record.get(field, "")) for field in fields)
    return filled, richness


def _parse_cadastro_html(path: str) -> Dict[str, Dict[str, str]]:
    try:
        from bs4 import BeautifulSoup
    except Exception:
        return {}

    with open(path, "r", encoding="utf-8", errors="ignore") as handle:
        soup = BeautifulSoup(handle.read(), "html.parser")

    rows = soup.select("table.waffle tr")
    if not rows:
        return {}

    header_row_idx: int | None = None
    for idx, row in enumerate(rows[:25]):
        headers = [_normalize_header(cell.get_text(" ", strip=True)) for cell in row.find_all(["th", "td"])]
        if "CODIGO" in headers and "CATEGORIA" in headers:
            header_row_idx = idx
            break
    if header_row_idx is None:
        return {}

    header_cells = rows[header_row_idx].find_all(["th", "td"])
    header_lookup = {
        _normalize_header(cell.get_text(" ", strip=True)): index
        for index, cell in enumerate(header_cells)
        if _normalize_header(cell.get_text(" ", strip=True))
    }

    def _idx(*keys: str, default: int | None = None) -> int | None:
        for key in keys:
            resolved = header_lookup.get(_normalize_header(key))
            if resolved is not None:
                return resolved
        return default

    idx_code = _idx("CODIGO", default=2)
    idx_category = _idx("CATEGORIA", default=1)
    idx_description = _idx("DESCRICAO", default=3)
    idx_title = _idx("TITULO E-COMMERCE", default=9)
    idx_description_ecommerce = _idx("DESCRICAO E-COMMERCE", default=10)
    idx_description_commercial = _idx("DESCRICAO COMERCIAL", default=12)
    idx_specs = _idx("FICHA TECNICA", default=13)

    records: Dict[str, Dict[str, str]] = {}
    scores: Dict[str, tuple[int, int]] = {}
    for row in rows[header_row_idx + 1 :]:
        cells = [_clean_cell(cell.get_text(" ", strip=True)) for cell in row.find_all(["th", "td"])]
        if not cells:
            continue
        if idx_code is None or idx_code >= len(cells):
            continue

        match = _CODE_PATTERN.search(cells[idx_code])
        if not match:
            continue
        code = match.group("code")

        category = cells[idx_category] if idx_category is not None and idx_category < len(cells) else ""
        description = (
            cells[idx_description] if idx_description is not None and idx_description < len(cells) else ""
        )
        title = cells[idx_title] if idx_title is not None and idx_title < len(cells) else ""
        description_ecommerce = (
            cells[idx_description_ecommerce]
            if idx_description_ecommerce is not None and idx_description_ecommerce < len(cells)
            else ""
        )
        description_commercial = (
            cells[idx_description_commercial]
            if idx_description_commercial is not None and idx_description_commercial < len(cells)
            else ""
        )
        specs = cells[idx_specs] if idx_specs is not None and idx_specs < len(cells) else ""

        record = {
            "code": code,
            "category": _clean_cell(category),
            "name": _first_nonempty(title, description, description_commercial),
            "description": _first_nonempty(description_ecommerce, description_commercial),
            "specs": _clean_cell(specs),
        }

        score = _record_score(record)
        previous_score = scores.get(code)
        if previous_score is None or score > previous_score:
            records[code] = record
            scores[code] = score

    return records


def load_cadastro_index(path_override: str | None = None) -> Dict[str, Dict[str, str]]:
    resolved_path = resolve_cadastro_path(path_override)
    if not resolved_path:
        return {}

    try:
        mtime = os.path.getmtime(resolved_path)
    except OSError:
        return {}

    with _CACHE_LOCK:
        cached_path = str(_CACHE.get("path", ""))
        cached_mtime = float(_CACHE.get("mtime", -1.0))
        if cached_path == resolved_path and cached_mtime == mtime:
            cached_records = _CACHE.get("records", {})
            return dict(cached_records) if isinstance(cached_records, dict) else {}

        parsed = _parse_cadastro_html(resolved_path)
        _CACHE["path"] = resolved_path
        _CACHE["mtime"] = mtime
        _CACHE["records"] = parsed
        return dict(parsed)
