"""Importacao e mesclagem de produtos vindos de arquivo JSON do ERP."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import unicodedata
from urllib.parse import quote
from typing import Any, Dict, List


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_ERP_JSON_PATH = BASE_DIR / "reports" / "erp_products.json"
DEFAULT_ERP_INBOX_DIR = BASE_DIR / "reports" / "erp_inbox"
DEFAULT_ERP_DROP_DIR = BASE_DIR / "catalog" / "json"
PRODUCT_CONTAINER_KEYS = (
    "produtos",
    "products",
    "itens",
    "items",
    "registros",
    "records",
    "data",
)
CODE_PATTERN = re.compile(r"\d{3,12}")
NUMERIC_TEXT_PATTERN = re.compile(r"\d+(?:[.,]\d+)?")
DISCOVERY_PATTERNS = (
    "erp*.json",
    "pcprodut*.json",
    "*produto*.json",
    "*produt*.json",
    "*catalog*.json",
)
JSON_TEXT_ENCODINGS = ("utf-8-sig", "utf-16", "latin-1")

CODE_ALIASES = (
    "Codigo",
    "Code",
    "SKU",
    "cod",
    "id",
    "codigo_produto",
    "CODPROD",
    "CODIGO",
    "CODPRODPRINC",
)
NAME_ALIASES = (
    "Nome",
    "Name",
    "Produto",
    "Descricao",
    "Description",
    "Titulo",
    "title",
    "DESCRICAO",
)
DESCRIPTION_ALIASES = ("Descricao", "Description", "Resumo", "Detalhes", "DescricaoCurta", "DESCRICAO")
CATEGORY_ALIASES = (
    "Categoria",
    "Category",
    "Grupo",
    "Familia",
    "Linha",
    "Tipo",
    "Department",
    "Departamento",
    "Secao",
)
SPECS_ALIASES = ("Especificacoes", "Especificacao", "Specs", "FichaTecnica", "Atributos")
WHITE_IMAGE_ALIASES = ("FotoBranco", "white_background", "WhiteBackground", "ImagemBranca")
AMBIENT_IMAGE_ALIASES = ("FotoAmbient", "ambient", "Ambient", "ImagemAmbient")
MEASURES_IMAGE_ALIASES = ("FotoMedidas", "measures", "Measures", "ImagemMedidas")
COVER_IMAGE_ALIASES = (
    "URLFoto",
    "Imagem",
    "Image",
    "Foto",
    "URL",
    "Capa",
    "Cover",
    "FotoPrincipal",
)
DEPT_ALIASES = ("CODEPTO", "CODDEPTO", "DEPTO", "DEPARTAMENTO")
SECTION_ALIASES = ("CODSEC", "CODSECAO", "SEC", "SECAO")
DEPT_SECTION_CATEGORY_MAP: Dict[tuple[str, str], str] = {
    ("101", "107"): "MANGUEIRAS E DECORATIVOS LED",
    ("102", "105"): "ACESSORIOS ELETRICOS",
    ("102", "108"): "CONECTORES E EMENDAS",
    ("102", "120"): "RELES E SENSORES",
    ("103", "112"): "LAMPADAS BULBO",
    ("103", "115"): "ILUMINACAO PUBLICA",
    ("104", "116"): "TARTARUGAS LED",
    ("104", "121"): "SPOTS EXTERNOS",
    ("105", "117"): "MOVEIS E UTILIDADES",
    ("106", "122"): "RODIZIOS E MOVIMENTACAO",
    ("107", "123"): "SUPRIMENTOS E OPERACAO",
}
DEPT_CATEGORY_MAP: Dict[str, str] = {
    "101": "ILUMINACAO INTERNA",
    "102": "ACESSORIOS ELETRICOS",
    "103": "LAMPADAS E ILUMINACAO PUBLICA",
    "104": "ILUMINACAO EXTERNA",
    "105": "MOVEIS E UTILIDADES",
    "106": "RODIZIOS E MOVIMENTACAO",
    "107": "SUPRIMENTOS E OPERACAO",
}
BUSINESS_CATEGORY_MAP: Dict[str, str] = {
    "iluminacao decorativa": "ILUMINACAO DECORATIVA",
    "iluminacao tecnica": "ILUMINACAO TECNICA",
    "iluminacao externa e publica": "ILUMINACAO EXTERNA E PUBLICA",
    "lampadas e fitas": "LAMPADAS E FITAS",
    "componentes e acessorios": "COMPONENTES E ACESSORIOS",
    "utilidades e operacao": "UTILIDADES E OPERACAO",
    "outros itens erp": "OUTROS ITENS ERP",
    "abajur": "ILUMINACAO DECORATIVA",
    "arandela": "ILUMINACAO DECORATIVA",
    "espelho": "ILUMINACAO DECORATIVA",
    "lustre": "ILUMINACAO DECORATIVA",
    "pendente": "ILUMINACAO DECORATIVA",
    "painel": "ILUMINACAO TECNICA",
    "plafon": "ILUMINACAO TECNICA",
    "perfil": "ILUMINACAO TECNICA",
    "trilho": "ILUMINACAO TECNICA",
    "luminaria": "ILUMINACAO TECNICA",
    "balizador": "ILUMINACAO EXTERNA E PUBLICA",
    "espeto": "ILUMINACAO EXTERNA E PUBLICA",
    "spots externos": "ILUMINACAO EXTERNA E PUBLICA",
    "tartarugas led": "ILUMINACAO EXTERNA E PUBLICA",
    "iluminacao publica": "ILUMINACAO EXTERNA E PUBLICA",
    "refletor": "ILUMINACAO EXTERNA E PUBLICA",
    "lampadas bulbo": "LAMPADAS E FITAS",
    "lampada": "LAMPADAS E FITAS",
    "fita led": "LAMPADAS E FITAS",
    "mangueiras e decorativos led": "LAMPADAS E FITAS",
    "componentes eletricos": "COMPONENTES E ACESSORIOS",
    "acessorios eletricos": "COMPONENTES E ACESSORIOS",
    "conectores e emendas": "COMPONENTES E ACESSORIOS",
    "reles e sensores": "COMPONENTES E ACESSORIOS",
    "driver/fonte": "COMPONENTES E ACESSORIOS",
    "utilidades e operacao": "UTILIDADES E OPERACAO",
    "moveis e utilidades": "UTILIDADES E OPERACAO",
    "rodizios e movimentacao": "UTILIDADES E OPERACAO",
    "suprimentos e operacao": "UTILIDADES E OPERACAO",
}
NAME_KEYWORD_PRIORITY: List[tuple[str, set[str]]] = [
    (
        "ILUMINACAO DECORATIVA",
        {"pendente", "pendentes", "lustre", "lustres", "arandela", "arandelas", "abajur", "espelho"},
    ),
    (
        "ILUMINACAO EXTERNA E PUBLICA",
        {
            "refletor",
            "refletores",
            "publica",
            "publico",
            "balizador",
            "balizadores",
            "espeto",
            "espeto",
            "tartaruga",
            "tartarugas",
        },
    ),
    (
        "ILUMINACAO TECNICA",
        {"luminaria", "luminarias", "plafon", "plafons", "trilho", "trilhos", "perfil", "perfis", "painel", "paineis", "spot", "spots"},
    ),
    (
        "LAMPADAS E FITAS",
        {"lampada", "lampadas", "fita", "fitas", "mangueira", "mangueiras", "bulbo", "bulbos"},
    ),
    (
        "COMPONENTES E ACESSORIOS",
        {
            "rele",
            "reles",
            "sensor",
            "sensores",
            "conector",
            "conectores",
            "emenda",
            "emendas",
            "driver",
            "drivers",
            "fonte",
            "fontes",
            "bocal",
            "bocais",
            "rabicho",
            "rabichos",
            "base",
            "bases",
            "fotocelula",
            "fotocelulas",
        },
    ),
    (
        "UTILIDADES E OPERACAO",
        {
            "rodizio",
            "rodizios",
            "cadeira",
            "cadeiras",
            "paleteira",
            "paleteiras",
            "suprimento",
            "suprimentos",
            "operacao",
            "operacoes",
        },
    ),
]


def _env_flag(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def get_max_upload_size_bytes() -> int:
    value = os.getenv("CATALOG_ERP_MAX_UPLOAD_BYTES", "").strip()
    if not value:
        return 10 * 1024 * 1024
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError("CATALOG_ERP_MAX_UPLOAD_BYTES must be an integer") from exc
    if parsed <= 0:
        raise ValueError("CATALOG_ERP_MAX_UPLOAD_BYTES must be positive")
    return parsed


def _normalized_tokens(text: str) -> List[str]:
    normalized = re.sub(r"[^a-z0-9\s]", " ", _normalize_text(text or ""))
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized.split() if normalized else []


def _token_to_category(token: str, next_token: str = "") -> str | None:
    token_upper = (token or "").upper()
    next_upper = (next_token or "").upper()
    if not token_upper:
        return None

    if token_upper.startswith("ARANDEL"):
        return "ARANDELA"
    if token_upper.startswith("ABAJUR"):
        return "ABAJUR"
    if token_upper.startswith("PENDENTE"):
        return "PENDENTE"
    if token_upper.startswith("LUSTRE"):
        return "LUSTRE"
    if token_upper.startswith("PAINEL"):
        return "PAINEL"
    if token_upper.startswith("PLAFON"):
        return "PLAFON"
    if token_upper == "MINI" and next_upper.startswith("TRILHO"):
        return "TRILHO"
    if token_upper.startswith("TRILHO"):
        return "TRILHO"
    if token_upper.startswith("PERFIL"):
        return "PERFIL"
    if token_upper.startswith("SENSOR"):
        return "SENSOR"
    if token_upper.startswith("BOCAL"):
        return "BOCAL"
    if token_upper.startswith("ESPETO"):
        return "ESPETO"
    if token_upper.startswith("BALIZADOR"):
        return "BALIZADOR"
    if token_upper.startswith("ESPELHO"):
        return "ESPELHO"
    if token_upper.startswith("REFLET") or token_upper.startswith("HOLOFOTE"):
        return "REFLETOR"
    if token_upper.startswith("LAMP"):
        return "LAMPADA"
    if token_upper.startswith("DRIVER") or token_upper.startswith("FONTE"):
        return "DRIVER/FONTE"
    if token_upper == "FITA":
        return "FITA LED"
    if token_upper.startswith("LUMINARIA") or token_upper in {"LUMI", "LUM", "LUMIN"}:
        return "LUMINARIA"
    return None


def _is_numeric_text(value: str) -> bool:
    return bool(NUMERIC_TEXT_PATTERN.fullmatch(value or ""))


def _build_dept_category(dept_code: str, sec_code: str) -> str:
    dept = str(dept_code or "").strip()
    sec = str(sec_code or "").strip()
    mapped_pair = DEPT_SECTION_CATEGORY_MAP.get((dept, sec))
    if mapped_pair:
        return mapped_pair
    mapped_dept = DEPT_CATEGORY_MAP.get(dept)
    if mapped_dept:
        return mapped_dept
    if dept and sec:
        return f"DEPTO {dept} / SEC {sec}"
    if dept:
        return f"DEPTO {dept}"
    if sec:
        return f"SEC {sec}"
    return "Sem categoria"


def _infer_category(
    name: str,
    description: str,
    fallback_category: str,
    dept_code: str,
    sec_code: str,
) -> str:
    fallback = str(fallback_category or "").strip()
    if fallback and fallback.lower() != "sem categoria" and not _is_numeric_text(fallback):
        return fallback

    for candidate in (name, description):
        tokens = _normalized_tokens(candidate)
        if not tokens:
            continue
        if "iluminacao" in tokens and "publica" in tokens:
            return "ILUMINACAO PUBLICA"
        if "fita" in tokens and "led" in tokens:
            return "FITA LED"

        for idx, token in enumerate(tokens):
            mapped = _token_to_category(token, tokens[idx + 1] if idx + 1 < len(tokens) else "")
            if mapped:
                return mapped

    return _build_dept_category(dept_code, sec_code)


def _to_business_category(category: str, name: str = "", description: str = "") -> str:
    normalized = _normalize_text(category).strip()
    name_desc_tokens = set(_normalized_tokens(f"{name} {description}"))

    # Prioriza termos explicitos do nome/descricao para evitar itens "fora" da categoria esperada.
    for mapped_category, keywords in NAME_KEYWORD_PRIORITY:
        if any(token in name_desc_tokens for token in keywords):
            return mapped_category

    if normalized in BUSINESS_CATEGORY_MAP and normalized != "sem categoria":
        return BUSINESS_CATEGORY_MAP[normalized]

    tokens = set(_normalized_tokens(f"{category} {name} {description}"))
    for mapped_category, keywords in NAME_KEYWORD_PRIORITY:
        if any(token in tokens for token in keywords):
            return mapped_category

    return "OUTROS ITENS ERP"


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value or "")
    without_accents = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )
    return without_accents.lower()


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", _normalize_text(value or ""))


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value).strip()


def resolve_erp_inbox_dir() -> Path:
    configured = os.getenv("CATALOG_ERP_INBOX_DIR", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if not candidate.is_absolute():
            candidate = BASE_DIR / candidate
        return candidate
    return DEFAULT_ERP_INBOX_DIR


def _resolve_erp_source_dirs() -> List[Path]:
    configured = os.getenv("CATALOG_ERP_SOURCE_DIRS", "").strip()
    source_dirs: List[Path] = [BASE_DIR, BASE_DIR / "reports", resolve_erp_inbox_dir(), DEFAULT_ERP_DROP_DIR]

    if configured:
        for item in configured.split(","):
            value = item.strip()
            if not value:
                continue
            candidate = Path(value).expanduser()
            if not candidate.is_absolute():
                candidate = BASE_DIR / candidate
            source_dirs.append(candidate)

    unique_dirs: dict[Path, Path] = {}
    for directory in source_dirs:
        unique_dirs[directory.resolve(strict=False)] = directory
    return list(unique_dirs.values())


def _resolve_json_target_path() -> Path:
    configured = os.getenv("CATALOG_ERP_JSON_PATH", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if not candidate.is_absolute():
            candidate = BASE_DIR / candidate
        return candidate
    return DEFAULT_ERP_JSON_PATH


def _resolve_json_path() -> Path:
    target = _resolve_json_target_path()
    configured = os.getenv("CATALOG_ERP_JSON_PATH", "").strip()
    if configured and target.is_file():
        return target

    if not configured and target.is_file():
        return target

    if not _env_flag("CATALOG_ERP_AUTO_DISCOVERY", default=True):
        return target

    candidates: List[Path] = []
    for root in _resolve_erp_source_dirs():
        if not root.is_dir():
            continue
        for pattern in DISCOVERY_PATTERNS:
            candidates.extend(
                item
                for item in root.glob(pattern)
                if item.is_file()
            )

    if candidates:
        unique_candidates = {item.resolve(): item for item in candidates}
        ordered = sorted(
            unique_candidates.values(),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        return ordered[0]

    return target


def _build_lookup(record: Dict[str, Any]) -> Dict[str, Any]:
    lookup: Dict[str, Any] = {}
    for key, value in record.items():
        lookup[_normalize_key(str(key))] = value
    return lookup


def _pick_value(lookup: Dict[str, Any], aliases: tuple[str, ...]) -> Any:
    for alias in aliases:
        value = lookup.get(_normalize_key(alias))
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _normalize_code(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, float) and value.is_integer():
        text = str(int(value))
    else:
        text = str(value).strip()

    if not text:
        return None

    if re.fullmatch(r"\d+(?:\.0+)?", text):
        return text.split(".")[0]

    match = CODE_PATTERN.search(text)
    if not match:
        return None
    return match.group(0)


def _extract_records(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if isinstance(payload, dict):
        for key in PRODUCT_CONTAINER_KEYS:
            values = payload.get(key)
            if isinstance(values, list):
                return [item for item in values if isinstance(item, dict)]

        if payload and all(isinstance(value, dict) for value in payload.values()):
            records: List[Dict[str, Any]] = []
            for fallback_code, value in payload.items():
                item = dict(value)
                item.setdefault("Codigo", fallback_code)
                records.append(item)
            return records

    raise ValueError("invalid ERP payload: expected array or object with product list")


def _normalize_erp_record(record: Dict[str, Any]) -> Dict[str, Any] | None:
    lookup = _build_lookup(record)

    code = _normalize_code(_pick_value(lookup, CODE_ALIASES))
    if not code:
        return None

    name = _stringify(_pick_value(lookup, NAME_ALIASES)) or f"Produto {code}"
    description = _stringify(_pick_value(lookup, DESCRIPTION_ALIASES))
    dept_code = _stringify(_pick_value(lookup, DEPT_ALIASES))
    sec_code = _stringify(_pick_value(lookup, SECTION_ALIASES))
    category = _infer_category(
        name=name,
        description=description,
        fallback_category=_stringify(_pick_value(lookup, CATEGORY_ALIASES)),
        dept_code=dept_code,
        sec_code=sec_code,
    )
    specs = _stringify(_pick_value(lookup, SPECS_ALIASES))

    cover_url = _stringify(_pick_value(lookup, COVER_IMAGE_ALIASES))
    white_url = _stringify(_pick_value(lookup, WHITE_IMAGE_ALIASES)) or cover_url
    ambient_url = _stringify(_pick_value(lookup, AMBIENT_IMAGE_ALIASES))
    measures_url = _stringify(_pick_value(lookup, MEASURES_IMAGE_ALIASES))

    normalized: Dict[str, Any] = {
        "Codigo": code,
        "Nome": name,
        "Descricao": description,
        "Categoria": category,
        "Especificacoes": specs,
        "URLFoto": cover_url or white_url,
        "FotoBranco": white_url or cover_url,
        "FotoAmbient": ambient_url,
        "FotoMedidas": measures_url,
    }

    for key, value in record.items():
        if key in normalized:
            continue
        rendered = _stringify(value)
        if not rendered:
            continue
        normalized[key] = value

    return normalized


def _build_index(payload: Any) -> Dict[str, Dict[str, Any]]:
    records = _extract_records(payload)
    index: Dict[str, Dict[str, Any]] = {}
    for record in records:
        normalized = _normalize_erp_record(record)
        if not normalized:
            continue
        index[str(normalized["Codigo"])] = normalized
    return index


def _parse_json_bytes(content: bytes) -> Any:
    if not content:
        raise ValueError("empty ERP JSON content")

    parse_error: Exception | None = None
    for encoding in JSON_TEXT_ENCODINGS:
        try:
            decoded = content.decode(encoding)
        except UnicodeDecodeError as exc:
            parse_error = exc
            continue

        try:
            return json.loads(decoded)
        except json.JSONDecodeError as exc:
            parse_error = exc

    raise ValueError(f"invalid ERP JSON content: {parse_error}")


def _load_json_file(path: Path) -> Any:
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise ValueError(f"unable to read ERP file: {exc}") from exc
    return _parse_json_bytes(content)


def _sanitize_json_filename(filename: str) -> str:
    base_name = Path(filename or "").name.strip()
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", base_name)
    if not safe_name:
        raise ValueError("filename is required")
    if not safe_name.lower().endswith(".json"):
        safe_name = f"{safe_name}.json"
    return safe_name


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


def _resolve_candidate_file_path(file_path: str) -> Path:
    raw_path = Path(file_path or "").expanduser()
    if not str(raw_path).strip():
        raise ValueError("file_path is required")

    search_roots = tuple(_resolve_erp_source_dirs())

    if raw_path.is_absolute():
        if raw_path.is_file() and any(_is_within(raw_path, root) for root in search_roots):
            return raw_path
        raise ValueError("ERP file not found inside allowed directories")

    if ".." in raw_path.parts:
        raise ValueError("file_path must not contain parent directory traversal")

    for root in search_roots:
        candidate = root / raw_path
        if candidate.is_file():
            return candidate

    raise ValueError("ERP file not found")


def import_erp_payload(payload: Any) -> Dict[str, Any]:
    index = _build_index(payload)
    if not index:
        raise ValueError("no valid product records with code found in ERP payload")

    imported_at = datetime.now(timezone.utc).isoformat()
    stored_payload = {
        "imported_at": imported_at,
        "products": list(index.values()),
    }

    target = _resolve_json_target_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(stored_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "path": str(target),
        "products_imported": len(index),
        "imported_at": imported_at,
    }


def import_erp_file(file_path: str) -> Dict[str, Any]:
    source = _resolve_candidate_file_path(file_path)
    payload = _load_json_file(source)
    result = import_erp_payload(payload)
    result["source_path"] = str(source)
    result["source_size_bytes"] = source.stat().st_size
    return result


def receive_erp_file(filename: str, content: bytes) -> Dict[str, Any]:
    if len(content) > get_max_upload_size_bytes():
        raise ValueError("ERP upload too large")
    payload = _parse_json_bytes(content)
    safe_filename = _sanitize_json_filename(filename)
    inbox_dir = resolve_erp_inbox_dir()
    inbox_dir.mkdir(parents=True, exist_ok=True)

    target = inbox_dir / safe_filename
    if target.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        target = inbox_dir / f"{target.stem}_{stamp}{target.suffix}"

    target.write_bytes(content)

    result = import_erp_payload(payload)
    result["uploaded_path"] = str(target)
    result["uploaded_size_bytes"] = target.stat().st_size
    return result


def list_erp_files() -> List[Dict[str, Any]]:
    active_path = _resolve_json_path()
    active = active_path.resolve(strict=False)
    seen: dict[Path, Path] = {}

    for root in _resolve_erp_source_dirs():
        if not root.is_dir():
            continue
        for pattern in DISCOVERY_PATTERNS:
            for item in root.glob(pattern):
                if not item.is_file():
                    continue
                seen[item.resolve(strict=False)] = item

    if active_path.is_file():
        seen[active] = active_path

    files: List[Dict[str, Any]] = []
    for resolved, item in seen.items():
        stat = item.stat()
        files.append(
            {
                "path": str(item),
                "name": item.name,
                "size_bytes": stat.st_size,
                "updated_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                "is_active": resolved == active,
            }
        )

    files.sort(key=lambda entry: entry["updated_at"], reverse=True)
    return files


def load_erp_index() -> Dict[str, Dict[str, Any]]:
    source = _resolve_json_path()
    if not source.is_file():
        return {}

    try:
        payload = _load_json_file(source)
    except Exception:
        return {}

    try:
        return _build_index(payload)
    except ValueError:
        return {}


def get_erp_status() -> Dict[str, Any]:
    source = _resolve_json_path()
    index = load_erp_index()
    return {
        "path": str(source),
        "exists": source.is_file(),
        "products_loaded": len(index),
        "updated_at": datetime.fromtimestamp(source.stat().st_mtime, tz=timezone.utc).isoformat()
        if source.is_file()
        else None,
    }


def _placeholder_urls(code: str) -> tuple[str, str]:
    safe_code = quote(str(code), safe="")
    return (
        f"https://placehold.co/900x700?text=Sem+Imagem+{safe_code}",
        f"https://placehold.co/240x240?text=Sem+foto+{safe_code}",
    )


def _merge_single_product(base: Dict[str, Any], erp: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)

    for field in ("Nome", "Descricao", "Especificacoes"):
        value = _stringify(erp.get(field))
        if value:
            merged[field] = value

    base_category = _stringify(merged.get("Categoria"))
    erp_category = _infer_category(
        name=_stringify(erp.get("Nome")),
        description=_stringify(erp.get("Descricao")),
        fallback_category=_stringify(erp.get("Categoria")),
        dept_code=_stringify(erp.get("CODEPTO")),
        sec_code=_stringify(erp.get("CODSEC")),
    )
    if base_category and base_category.lower() != "sem categoria":
        if erp_category and not erp_category.startswith("DEPTO "):
            merged["Categoria"] = _to_business_category(
                erp_category,
                _stringify(merged.get("Nome")),
                _stringify(merged.get("Descricao")),
            )
    else:
        merged["Categoria"] = _to_business_category(
            erp_category or "Sem categoria",
            _stringify(merged.get("Nome")),
            _stringify(merged.get("Descricao")),
        )

    for field in ("URLFoto", "FotoBranco", "FotoAmbient", "FotoMedidas"):
        value = _stringify(erp.get(field))
        if value:
            merged[field] = value

    for key, value in erp.items():
        if key in merged and _stringify(merged.get(key)):
            continue
        merged[key] = value

    merged["Codigo"] = str(erp.get("Codigo") or base.get("Codigo") or "").strip()
    return merged


def _create_product_from_erp(erp: Dict[str, Any]) -> Dict[str, Any]:
    code = str(erp.get("Codigo") or "").strip()
    if not code:
        return {}

    cover_url, thumb_url = _placeholder_urls(code)
    inferred_category = _infer_category(
        name=_stringify(erp.get("Nome")),
        description=_stringify(erp.get("Descricao")),
        fallback_category=_stringify(erp.get("Categoria")),
        dept_code=_stringify(erp.get("CODEPTO")),
        sec_code=_stringify(erp.get("CODSEC")),
    )
    created = {
        "Codigo": code,
        "Nome": _stringify(erp.get("Nome")) or f"Produto {code}",
        "Descricao": _stringify(erp.get("Descricao")),
        "Categoria": _to_business_category(
            inferred_category,
            _stringify(erp.get("Nome")),
            _stringify(erp.get("Descricao")),
        ),
        "Especificacoes": _stringify(erp.get("Especificacoes")),
        "URLFoto": _stringify(erp.get("URLFoto")) or cover_url,
        "FotoBranco": _stringify(erp.get("FotoBranco")) or _stringify(erp.get("URLFoto")) or thumb_url,
        "FotoAmbient": _stringify(erp.get("FotoAmbient")),
        "FotoMedidas": _stringify(erp.get("FotoMedidas")),
    }

    for key, value in erp.items():
        if key not in created:
            created[key] = value

    return created


def _code_sort_key(code: str) -> tuple[int, Any]:
    text = str(code or "").strip()
    return (0, int(text)) if text.isdigit() else (1, text)


def _product_sort_key(product: Dict[str, Any]) -> tuple[Any, ...]:
    category = _stringify(product.get("Categoria")) or "Sem categoria"
    sem_categoria = _normalize_text(category) == "sem categoria"
    name = _stringify(product.get("Nome"))
    code = _normalize_code(product.get("Codigo")) or _stringify(product.get("Codigo"))
    return (
        sem_categoria,
        _normalize_text(category),
        _code_sort_key(code),
        _normalize_text(name),
    )


def sort_products_by_category(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(products, key=_product_sort_key)


def merge_products_with_erp(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    erp_index = load_erp_index()
    if not erp_index:
        return products

    strict_mode = os.getenv("CATALOG_ERP_STRICT_MODE", "true").strip().lower() not in {"0", "false", "no"}
    merged_products: List[Dict[str, Any]] = []
    seen_codes: set[str] = set()

    for product in products:
        code = _normalize_code(product.get("Codigo"))
        if code and code in erp_index:
            merged_products.append(_merge_single_product(product, erp_index[code]))
            seen_codes.add(code)
        else:
            if not strict_mode:
                merged_products.append(product)
            if code:
                seen_codes.add(code)

    missing_codes = sorted((code for code in erp_index.keys() if code not in seen_codes), key=_code_sort_key)
    for code in missing_codes:
        created = _create_product_from_erp(erp_index[code])
        if created:
            merged_products.append(created)

    normalized_categories: List[Dict[str, Any]] = []
    for item in merged_products:
        normalized = dict(item)
        normalized["Categoria"] = _to_business_category(
            _stringify(normalized.get("Categoria")),
            _stringify(normalized.get("Nome")),
            _stringify(normalized.get("Descricao")),
        )
        normalized_categories.append(normalized)

    return sort_products_by_category(normalized_categories)
