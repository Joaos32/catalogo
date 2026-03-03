"""Utilities to interact with OneDrive using Microsoft Graph and local folders."""

import os
import re
import base64
import unicodedata
import json
import subprocess
from typing import List, Dict
from urllib.parse import quote
from pathlib import Path

from .graph_client import get_share_info, list_children
from .cache import cached


IMG_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff")
INDEX_EXTENSIONS = IMG_EXTENSIONS + (".lnk",)
SEGMENT_PREFIX_CODE_PATTERN = re.compile(r"^\s*(?P<code>\d{3,8})(?=\D|$)")
GENERIC_CODE_PATTERN = re.compile(r"\b(?P<code>\d{4,8})\b")
PARENTHESIZED_VARIANT_SUFFIX_PATTERN = re.compile(r"\((?P<variant>\d{1,3})\)\s*$")
LEGACY_NUMERIC_VARIANT_PATTERN = re.compile(r"^[-_]\s*(?P<variant>\d{1,3})\s*$")
CATEGORY_STOP_TOKENS = {"C", "COM"}
CATEGORY_TRIM_TAIL_TOKENS = {"C", "COM", "DE", "DA", "DO", "DOS", "DAS", "E"}


def _encode_share_url(url: str) -> str:
    """Convert a OneDrive share URL into Graph "shares/{id}" syntax."""
    clean = url.split("?")[0]
    raw = base64.urlsafe_b64encode(clean.encode()).decode().rstrip("=")
    return f"u!{raw}"


def list_shared_items(share_url: str):
    """List *immediate* children of a shared folder."""
    try:
        info = get_share_info(share_url)
        drive_id = info.get("parentReference", {}).get("driveId")
        item_id = info.get("id")
        if not drive_id or not item_id:
            raise ValueError("unable to resolve shared folder")
        return list_children(drive_id, item_id)
    except Exception as exc:
        raise EnvironmentError(str(exc))


def categorize_photos(items: list, code: str = None) -> dict:
    """Return representative URLs matching criteria."""
    result = {"white_background": None, "ambient": None, "measures": None}
    for it in items:
        name = it.get("name", "").lower()
        weburl = it.get("webUrl")
        if code and code.lower() not in name:
            continue
        if result["white_background"] is None and ("branco" in name or "white" in name):
            result["white_background"] = weburl
        if result["ambient"] is None and ("ambient" in name or "ambiente" in name):
            result["ambient"] = weburl
        if result["measures"] is None and ("medida" in name or "measure" in name):
            result["measures"] = weburl
    return result


def _match_filename(name: str, code: str):
    stem = Path(name or "").stem.strip()
    pref = SEGMENT_PREFIX_CODE_PATTERN.match(stem)
    if not pref:
        return None
    if pref.group("code") != str(code):
        return None
    remainder = stem[pref.end() :].strip()
    if not remainder:
        return 0

    legacy_variant = LEGACY_NUMERIC_VARIANT_PATTERN.match(remainder)
    if legacy_variant:
        return int(legacy_variant.group("variant"))

    parenthesized_variant = PARENTHESIZED_VARIANT_SUFFIX_PATTERN.search(remainder)
    if parenthesized_variant:
        return int(parenthesized_variant.group("variant"))

    return 0


def _local_products_paths(base_dir: str) -> List[str]:
    return [
        os.path.join(base_dir, "FOTOS_PRODUTOS"),
        os.path.join(base_dir, "MARKETING", "01_PRODUTOS", "BACKUP PRODUTOS"),
        os.path.join(base_dir, "MARKETING", "Catalogo"),
        os.path.join(base_dir, "MARKETING", "01_PRODUTOS"),
    ]


@cached
def find_images_for_code(share_url: str, code: str, max_depth: int = 5) -> List[Dict]:
    info = get_share_info(share_url)
    drive_id = info.get("parentReference", {}).get("driveId")
    item_id = info.get("id")
    if not drive_id or not item_id:
        raise ValueError("unable to resolve shared folder")
    matches: List[Dict] = []

    def _recurse(d_id: str, i_id: str, depth: int):
        if depth > max_depth:
            return
        children = list_children(d_id, i_id)
        for it in children:
            if "folder" in it:
                _recurse(d_id, it.get("id"), depth + 1)
                continue
            name = it.get("name", "")
            if not any(name.lower().endswith(ext) for ext in IMG_EXTENSIONS):
                continue
            variant = _match_filename(name, code)
            if variant is None:
                continue
            url = it.get("@microsoft.graph.downloadUrl") or (
                f"https://graph.microsoft.com/v1.0/drives/{d_id}/items/{it.get('id')}/content"
            )
            matches.append({"name": name, "variant": variant, "url": url})

    _recurse(drive_id, item_id, 0)
    matches.sort(key=lambda x: x["variant"])
    return matches


def _candidate_local_roots() -> List[str]:
    candidates: List[str] = []
    explicit = os.getenv("CATALOG_LOCAL_PRODUCTS_PATH")
    if explicit:
        candidates.append(explicit)
    for base_env in ("OneDrive", "OneDriveCommercial", "OneDriveConsumer", "USERPROFILE"):
        base = os.getenv(base_env)
        if not base:
            continue
        base = base.rstrip("\\/")
        if base_env == "USERPROFILE":
            one_drive_base = os.path.join(base, "OneDrive")
            candidates.extend(_local_products_paths(one_drive_base))
        else:
            candidates.extend(_local_products_paths(base))
    # last fallback when env vars are missing in the server process
    home = str(Path.home())
    if home:
        candidates.extend(_local_products_paths(os.path.join(home, "OneDrive")))
    return candidates


def _existing_local_roots(path_override: str | None = None) -> List[str]:
    roots: List[str] = []
    seen = set()
    candidates = [path_override] if path_override else _candidate_local_roots()
    for candidate in candidates:
        if not candidate:
            continue
        abs_candidate = os.path.abspath(candidate)
        norm_key = abs_candidate.lower()
        if norm_key in seen:
            continue
        if os.path.isdir(abs_candidate):
            roots.append(abs_candidate)
            seen.add(norm_key)
    return roots


def resolve_local_products_root(path_override: str | None = None) -> str | None:
    roots = _existing_local_roots(path_override)
    return roots[0] if roots else None


def _clean_product_name(candidate: str) -> str:
    cleaned = re.sub(r"\s+", " ", (candidate or "").strip(" -_"))
    cleaned = re.sub(r"\s*\(\d{1,3}\)\s*$", "", cleaned)
    cleaned = re.sub(r"\s*-\s*(atalho|shortcut)\s*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip(" -_")
    if not cleaned:
        return ""
    # Keep only descriptive names; plain numeric suffixes are variants.
    if re.fullmatch(r"[1-4]", cleaned):
        return ""
    if re.fullmatch(r"\d+", cleaned):
        return ""
    return cleaned


def _derive_category_from_product_name(product_name: str) -> str:
    cleaned = _clean_product_name(product_name)
    if not cleaned:
        return "Sem categoria"

    tokens = cleaned.split()
    category_tokens: List[str] = []
    for token in tokens:
        token_upper = token.upper()
        if any(char.isdigit() for char in token):
            break
        if token_upper in CATEGORY_STOP_TOKENS and len(category_tokens) >= 2:
            break
        category_tokens.append(token)
        if len(category_tokens) >= 4:
            break

    while category_tokens and category_tokens[-1].upper() in CATEGORY_TRIM_TAIL_TOKENS:
        category_tokens.pop()

    if not category_tokens:
        category_tokens = tokens[:2]

    category = " ".join(category_tokens).strip(" -_")
    return category or "Sem categoria"


def _token_to_category(token: str, next_token: str = "") -> str | None:
    token = (token or "").upper()
    next_token = (next_token or "").upper()
    if not token:
        return None

    if token in {"ARANDELA", "ARANDELAS", "ARANDEDA"} or token.startswith("ARANDEL"):
        return "ARANDELA"
    if token.startswith("ABAJUR"):
        return "ABAJUR"
    if token.startswith("PENDENTE"):
        return "PENDENTE"
    if token.startswith("LUSTRE"):
        return "LUSTRE"
    if token.startswith("PAINEL"):
        return "PAINEL"
    if token.startswith("PLAFON"):
        return "PLAFON"
    if token in {"MINI"} and next_token.startswith("TRILHO"):
        return "TRILHO"
    if token.startswith("TRILHO"):
        return "TRILHO"
    if token.startswith("PERFIL"):
        return "PERFIL"
    if token.startswith("SENSOR"):
        return "SENSOR"
    if token.startswith("BOCAL"):
        return "BOCAL"
    if token.startswith("ESPETO"):
        return "ESPETO"
    if token.startswith("BALIZADOR"):
        return "BALIZADOR"
    if token.startswith("ESPELHO"):
        return "ESPELHO"
    if token.startswith("RELE"):
        return "RELE"
    if token.startswith("REFLET") or token.startswith("HOLOFOTE"):
        return "REFLETOR"
    if token.startswith("LAMP"):
        return "LAMPADA"
    if token.startswith("DRIVER") or token == "DRIVE" or token.startswith("FONTE"):
        return "DRIVER/FONTE"
    if token == "FITA":
        return "FITA LED"
    if token.startswith("LUMINARIA") or token in {"LUMI", "LUM", "LUMIN"}:
        return "LUMINARIA"
    return None


def _normalized_tokens(text: str) -> List[str]:
    normalized = _normalize_name_for_match(text).upper()
    normalized = re.sub(r"[^A-Z0-9\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized.split() if normalized else []


def _canonical_category(category: str, product_name: str = "") -> str:
    candidates = [category, product_name]
    for candidate in candidates:
        tokens = _normalized_tokens(candidate)
        if not tokens:
            continue

        if "ILUMINACAO" in tokens and "PUBLICA" in tokens:
            return "ILUMINACAO PUBLICA"
        if "PUBLICA" in tokens and ("LUM" in tokens or "LUMIN" in tokens):
            return "ILUMINACAO PUBLICA"

        first = _token_to_category(tokens[0], tokens[1] if len(tokens) > 1 else "")
        if first:
            return first

        for idx, token in enumerate(tokens[1:], start=1):
            mapped = _token_to_category(token, tokens[idx + 1] if idx + 1 < len(tokens) else "")
            if mapped and mapped != "LUMINARIA":
                return mapped

        if any(
            _token_to_category(token, tokens[idx + 1] if idx + 1 < len(tokens) else "")
            == "LUMINARIA"
            for idx, token in enumerate(tokens)
        ):
            return "LUMINARIA"

        if "FITA" in tokens and "LED" in tokens:
            return "FITA LED"

    return "Sem categoria"


def _extract_code_and_name_from_segment(segment: str) -> tuple[str | None, str]:
    pref = SEGMENT_PREFIX_CODE_PATTERN.search(segment or "")
    if not pref:
        return None, ""

    code = pref.group("code")
    remainder = (segment[pref.end() :] if segment else "").strip()
    remainder = re.sub(r"^[\s\-_]+", "", remainder)
    return code, _clean_product_name(remainder)


def _extract_code_from_parts(parts: List[str]) -> tuple[str | None, str, str]:
    raw_category = parts[0].strip() if len(parts) > 1 else ""
    if raw_category and not SEGMENT_PREFIX_CODE_PATTERN.search(raw_category):
        category = raw_category
    else:
        category = "Sem categoria"

    # Priority: filename first (description usually there), then parent folders.
    filename_stem = Path(parts[-1]).stem if parts else ""
    ordered_segments = [filename_stem]
    ordered_segments.extend(reversed(parts[:-1]))

    for segment in ordered_segments:
        code, product_name = _extract_code_and_name_from_segment(segment)
        if code:
            resolved_category = category
            if resolved_category == "Sem categoria" and product_name:
                resolved_category = _derive_category_from_product_name(product_name)
            resolved_category = _canonical_category(resolved_category, product_name)
            return code, product_name or f"Produto {code}", resolved_category

    for segment in ordered_segments:
        generic = GENERIC_CODE_PATTERN.search(segment)
        if generic:
            code = generic.group("code")
            return code, f"Produto {code}", _canonical_category(category, segment)

    return None, "", _canonical_category(category, "")


def _classify_variant(name: str) -> str:
    lowered = name.lower()
    if "branco" in lowered or "white" in lowered:
        return "white_background"
    if "ambient" in lowered or "ambiente" in lowered or "cena" in lowered:
        return "ambient"
    if "medida" in lowered or "measure" in lowered or "dimens" in lowered:
        return "measures"
    return "other"


def _normalize_name_for_match(name: str) -> str:
    normalized = unicodedata.normalize("NFD", name or "")
    without_accents = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return without_accents.lower()


def _is_description_title(name: str, code: str) -> bool:
    normalized = _normalize_name_for_match(name)
    for marker in ("descricao", "description", "descri"):
        if marker in normalized:
            return True

    code_prefix = str(code).strip()
    if not code_prefix:
        return False
    if not normalized.startswith(code_prefix):
        return False

    remainder = normalized[len(code_prefix) :].lstrip()
    if not remainder.startswith("-"):
        return False
    detail = remainder[1:].strip()
    if not detail:
        return False
    # Consider "5989-2.jpg" and similar numeric-only suffixes as non-descriptive.
    return not re.match(r"^\d+([._-]|$)", detail)


def _local_file_sort_key(file_info: Dict, code: str) -> tuple:
    name = file_info.get("name", "")
    normalized = _normalize_name_for_match(name)
    if _is_description_title(name, code):
        variant = _match_filename(name, str(code))
        if variant is not None and variant > 0:
            base_without_variant = re.sub(
                r"\s*\(\d{1,3}\)(?=\.[^.]+$)", "", name or "", flags=re.IGNORECASE
            )
            return (0, _normalize_name_for_match(base_without_variant), variant, normalized)
        return (0, normalized)

    variant = _match_filename(name, str(code))
    if variant is not None:
        return (1, variant, normalized)

    return (2, normalized)


def _asset_url(rel_path: str) -> str:
    normalized = rel_path.replace("\\", "/")
    return f"/catalog/local/asset?path={quote(normalized, safe='')}"


def _normalize_category_label(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", (value or "").strip())
    if cleaned in {"***", "-", "â€”"}:
        return ""
    return cleaned


def _rel_path_in_allowed_roots(abs_path: str, roots: List[str]) -> str | None:
    if not abs_path:
        return None
    candidate = os.path.abspath(abs_path)
    if not os.path.isfile(candidate):
        return None
    for root in roots:
        root_abs = os.path.abspath(root)
        try:
            within_root = os.path.commonpath([root_abs, candidate]) == root_abs
        except ValueError:
            continue
        if within_root:
            return os.path.relpath(candidate, root_abs)
    return None


def _resolve_shortcut_targets(scan_root: str) -> Dict[str, str]:
    """Resolve .lnk files under scan_root to absolute target paths."""
    if os.name != "nt":
        return {}
    if not scan_root or not os.path.isdir(scan_root):
        return {}

    safe_root = scan_root.replace("'", "''")
    script = (
        f"$root = '{safe_root}'; "
        "$shell = New-Object -ComObject WScript.Shell; "
        "Get-ChildItem -Path $root -Recurse -File -Filter *.lnk | ForEach-Object { "
        "  $target = ''; "
        "  try { $target = $shell.CreateShortcut($_.FullName).TargetPath } catch {} "
        "  [PSCustomObject]@{ link = $_.FullName; target = $target } "
        "} | ConvertTo-Json -Compress"
    )

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except Exception:
        return {}

    if result.returncode != 0:
        return {}

    payload = (result.stdout or "").strip()
    if not payload:
        return {}

    try:
        decoded = json.loads(payload)
    except Exception:
        return {}

    rows = decoded if isinstance(decoded, list) else [decoded]
    mapping: Dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        link = str(row.get("link") or "")
        target = str(row.get("target") or "")
        if link and target:
            mapping[os.path.abspath(link)] = os.path.abspath(target)
    return mapping


def _pick_distinct_fallback(files: List[Dict], taken: set[str]) -> Dict | None:
    for item in files:
        rel_path = item.get("rel_path")
        if rel_path and rel_path not in taken:
            return item
    return None


def _scan_local_photo_index(root: str) -> Dict[str, Dict]:
    index: Dict[str, Dict] = {}
    allowed_roots = _existing_local_roots()
    root_abs = os.path.abspath(root)
    if root_abs not in [os.path.abspath(item) for item in allowed_roots]:
        allowed_roots = [root_abs, *allowed_roots]
    shortcut_targets = _resolve_shortcut_targets(root_abs)

    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            lowered_name = filename.lower()
            if not lowered_name.endswith(INDEX_EXTENSIONS):
                continue
            full_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(full_path, root)
            parts = rel_path.split(os.sep)
            code, product_name, category = _extract_code_from_parts(parts)
            if not code:
                continue
            record = index.setdefault(
                code,
                {
                    "code": code,
                    "name": product_name or f"Produto {code}",
                    "category": category or "Sem categoria",
                    "files": [],
                    "variants": {"white_background": None, "ambient": None, "measures": None},
                },
            )
            if product_name and record["name"].startswith("Produto "):
                record["name"] = product_name
            if category and record["category"] == "Sem categoria":
                record["category"] = category

            if lowered_name.endswith(IMG_EXTENSIONS):
                file_info = {"name": filename, "full_path": full_path, "rel_path": rel_path}
                record["files"].append(file_info)
                variant = _classify_variant(filename)
                if variant in record["variants"] and record["variants"][variant] is None:
                    record["variants"][variant] = file_info
            elif lowered_name.endswith(".lnk"):
                target_path = shortcut_targets.get(os.path.abspath(full_path))
                target_ext = os.path.splitext(target_path or "")[1].lower()
                if target_ext not in IMG_EXTENSIONS:
                    continue
                target_rel_path = _rel_path_in_allowed_roots(target_path, allowed_roots)
                if not target_rel_path:
                    continue
                link_name = filename[:-4] if filename.lower().endswith(".lnk") else filename
                file_info = {
                    "name": link_name,
                    "full_path": target_path,
                    "rel_path": target_rel_path,
                }
                record["files"].append(file_info)
                variant = _classify_variant(link_name)
                if variant in record["variants"] and record["variants"][variant] is None:
                    record["variants"][variant] = file_info

    for record in index.values():
        record["files"].sort(key=lambda item: _local_file_sort_key(item, record.get("code", "")))
        chosen = set()

        white = record["variants"]["white_background"]
        if white is None and record["files"]:
            white = record["files"][0]
            record["variants"]["white_background"] = white
        if white:
            chosen.add(white["rel_path"])

        ambient = record["variants"]["ambient"]
        if ambient:
            chosen.add(ambient["rel_path"])
        else:
            fallback = _pick_distinct_fallback(record["files"], chosen)
            if fallback:
                record["variants"]["ambient"] = fallback
                chosen.add(fallback["rel_path"])

        measures = record["variants"]["measures"]
        if not measures:
            fallback = _pick_distinct_fallback(record["files"], chosen)
            if fallback:
                record["variants"]["measures"] = fallback

    return index


@cached
def build_local_photo_index(root_path: str | None = None) -> Dict[str, Dict]:
    root = resolve_local_products_root(root_path)
    if not root:
        return {}
    return _scan_local_photo_index(root)


def _get_local_index(path_override: str | None = None) -> Dict[str, Dict]:
    """Load local index from disk so folder edits are reflected immediately."""
    roots = _existing_local_roots(path_override)
    if not roots:
        return {}

    for root in roots:
        rebuilt = _scan_local_photo_index(root)
        if rebuilt:
            return rebuilt
    return {}


def _load_cadastro_records(path_override: str | None = None) -> Dict[str, Dict[str, str]]:
    # Runtime catalog uses default roots (path_override=None). For tests and
    # ad-hoc calls with overrides, keep source data predictable unless an
    # explicit cadastro path is configured.
    cadastro_path = os.getenv("CATALOG_CADASTRO_HTML")
    if path_override is not None and not cadastro_path:
        return {}

    try:
        from .cadastro import load_cadastro_index

        return load_cadastro_index(cadastro_path)
    except Exception as exc:
        print(f"Failed to load cadastro index: {exc}")
        return {}


def list_local_products(path_override: str | None = None) -> List[Dict]:
    index = _get_local_index(path_override)
    cadastro_records = _load_cadastro_records(path_override)
    products: List[Dict] = []
    for code, record in sorted(
        index.items(), key=lambda item: (item[1].get("category", ""), item[0])
    ):
        variants = record.get("variants", {})
        white = variants.get("white_background")
        ambient = variants.get("ambient")
        measures = variants.get("measures")

        white_url = _asset_url(white["rel_path"]) if white else ""
        ambient_url = _asset_url(ambient["rel_path"]) if ambient else ""
        measures_url = _asset_url(measures["rel_path"]) if measures else ""

        cadastro = cadastro_records.get(str(code), {})
        merged_name = str(cadastro.get("name") or record.get("name") or f"Produto {code}").strip()
        merged_description = str(cadastro.get("description") or "").strip()
        merged_specs = str(cadastro.get("specs") or "").strip()
        cadastro_category = _normalize_category_label(str(cadastro.get("category") or ""))
        if cadastro_category:
            # Keep categoria exactly as defined in CADASTRO.html (coluna A).
            merged_category = cadastro_category
        else:
            merged_category_source = _normalize_category_label(
                str(record.get("category") or "Sem categoria")
            )
            merged_category = _canonical_category(merged_category_source, merged_name)

        products.append(
            {
                "Codigo": code,
                "Nome": merged_name,
                "Descricao": merged_description,
                "Categoria": merged_category,
                "URLFoto": white_url,
                "Especificacoes": merged_specs,
                "FotoBranco": white_url,
                "FotoAmbient": ambient_url,
                "FotoMedidas": measures_url,
            }
        )
    return products


def categorize_local_photos(code: str, path_override: str | None = None) -> Dict[str, str | None]:
    record = _get_local_index(path_override).get(str(code))
    if not record:
        return {"white_background": None, "ambient": None, "measures": None}
    variants = record.get("variants", {})
    return {
        "white_background": _asset_url(variants["white_background"]["rel_path"])
        if variants.get("white_background")
        else None,
        "ambient": _asset_url(variants["ambient"]["rel_path"]) if variants.get("ambient") else None,
        "measures": _asset_url(variants["measures"]["rel_path"]) if variants.get("measures") else None,
    }


def find_local_images_for_code(code: str, path_override: str | None = None) -> List[Dict]:
    record = _get_local_index(path_override).get(str(code))
    if not record:
        return []
    ordered_files = sorted(
        record.get("files", []),
        key=lambda item: _local_file_sort_key(item, str(code)),
    )
    images: List[Dict] = []
    for idx, file_info in enumerate(ordered_files):
        images.append(
            {
                "name": file_info.get("name", ""),
                "variant": idx,
                "url": _asset_url(file_info.get("rel_path", "")),
            }
        )
    return images


def resolve_local_asset_path(rel_path: str, path_override: str | None = None) -> str | None:
    roots = _existing_local_roots(path_override)
    if not roots or not rel_path:
        return None

    normalized = rel_path.replace("/", os.sep).replace("\\", os.sep)
    for root in roots:
        candidate = os.path.abspath(os.path.join(root, normalized))
        try:
            within_root = os.path.commonpath([root, candidate]) == root
        except ValueError:
            continue
        if within_root and os.path.isfile(candidate):
            return candidate
    return None
