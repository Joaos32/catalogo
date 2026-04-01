"""Geracao de exportacoes do catalogo em multiplos formatos."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from io import BytesIO, StringIO
import ipaddress
import json
import mimetypes
import os
from pathlib import Path
import re
import socket
import textwrap
from typing import Any, Dict, Iterable, List, Sequence
import unicodedata
from urllib.parse import parse_qs, unquote, urlparse
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd
from PIL import Image, ImageDraw, ImageFont, ImageOps
import requests

from . import onedrive


SUPPORTED_EXPORT_FORMATS = {"csv", "json", "xlsx", "xls", "pdf", "zip"}
PREFERRED_COLUMNS = (
    "Codigo",
    "Nome",
    "Categoria",
    "Descricao",
    "Especificacoes",
    "URLFoto",
    "FotoBranco",
    "FotoAmbient",
    "FotoMedidas",
    "CODPROD",
    "CODAUXILIAR",
    "NBM",
    "PERCIPIVENDA",
)
PHOTO_FIELDS: tuple[tuple[str, str], ...] = (
    ("Capa", "URLFoto"),
    ("Fundo branco", "FotoBranco"),
    ("Ambientada", "FotoAmbient"),
    ("Medidas", "FotoMedidas"),
)
PAGE_SIZE = (1240, 1754)
PAGE_MARGIN = 80
BASE_DIR = Path(__file__).resolve().parents[1]
BRAND_BANNER_CANDIDATES = (
    BASE_DIR / "frontend" / "public" / "assets" / "azul-nitro.jpg",
    BASE_DIR / "frontend" / "assets" / "azul-nitro.jpg",
    BASE_DIR / "Azul nitro.jpg",
)
DISPLAY_LABEL_MAP = {
    "Codigo": "Codigo",
    "Nome": "Produto",
    "Categoria": "Categoria",
    "Descricao": "Descricao",
    "Especificacoes": "Especificacoes",
    "CODPROD": "Codigo",
    "CODAUXILIAR": "Codigo de barras",
    "NBM": "NCM",
    "PERCIPIVENDA": "IPI",
    "EMBALAGEM": "Embalagem",
    "UNIDADE": "Unidade",
    "PESOLIQ": "Peso liquido",
    "PESOBRUTO": "Peso bruto",
    "CODEPTO": "Departamento",
    "CODSEC": "Secao",
}
FEATURED_ATTRIBUTE_KEYS = (
    "CODPROD",
    "CODAUXILIAR",
    "NBM",
    "PERCIPIVENDA",
    "EMBALAGEM",
    "UNIDADE",
    "PESOLIQ",
    "PESOBRUTO",
    "CODEPTO",
    "CODSEC",
)


def _normalize_text(value: Any) -> str:
    normalized = unicodedata.normalize("NFD", str(value or ""))
    without_accents = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return without_accents.lower().strip()


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value).strip()


def _slugify(value: str, fallback: str = "catalogo") -> str:
    normalized = _normalize_text(value)
    slug = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return slug or fallback


def _load_products() -> List[Dict[str, Any]]:
    return onedrive.list_local_products()


def _max_remote_image_bytes() -> int:
    raw_value = os.getenv("CATALOG_EXPORT_MAX_REMOTE_IMAGE_BYTES", "").strip()
    if not raw_value:
        return 5 * 1024 * 1024
    try:
        parsed = int(raw_value)
    except ValueError:
        return 5 * 1024 * 1024
    return parsed if parsed > 0 else 5 * 1024 * 1024


def _is_public_ip_address(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )


def _is_permitted_remote_image_url(url: str) -> bool:
    parsed = urlparse(url or "")
    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.username or parsed.password:
        return False

    hostname = (parsed.hostname or "").strip().lower()
    if not hostname or hostname == "localhost" or hostname.endswith(".localhost"):
        return False

    if _is_public_ip_address(hostname):
        return True

    try:
        resolved = socket.getaddrinfo(
            hostname,
            parsed.port or (443 if parsed.scheme == "https" else 80),
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror:
        return False
    except OSError:
        return False

    addresses = {item[4][0] for item in resolved if item and len(item) >= 5 and item[4]}
    if not addresses:
        return False
    return all(_is_public_ip_address(address) for address in addresses)


def _download_remote_image_bytes(url: str) -> tuple[bytes | None, str]:
    if not _is_permitted_remote_image_url(url):
        return None, ""

    max_bytes = _max_remote_image_bytes()

    try:
        response = requests.get(
            url,
            timeout=8,
            stream=True,
            allow_redirects=False,
            headers={"Accept": "image/*"},
        )
        response.raise_for_status()
    except Exception:
        return None, ""

    content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type and not content_type.startswith("image/"):
        response.close()
        return None, ""

    declared_length = response.headers.get("content-length", "").strip()
    if declared_length:
        try:
            if int(declared_length) > max_bytes:
                response.close()
                return None, ""
        except ValueError:
            pass

    payload = bytearray()
    try:
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            payload.extend(chunk)
            if len(payload) > max_bytes:
                return None, ""
    finally:
        response.close()

    extension = Path(urlparse(url).path).suffix.lower()
    if not extension and content_type:
        extension = mimetypes.guess_extension(content_type) or ""
    return bytes(payload), extension


def _filter_products(
    products: Sequence[Dict[str, Any]],
    *,
    query: str = "",
    category: str = "",
    code: str = "",
) -> List[Dict[str, Any]]:
    normalized_query = _normalize_text(query)
    normalized_category = _normalize_text(category)
    normalized_code = str(code or "").strip()
    filtered: List[Dict[str, Any]] = []

    for product in products:
        product_code = _stringify(product.get("Codigo"))
        if normalized_code and product_code != normalized_code:
            continue

        if normalized_category and normalized_category != "todas":
            product_category = _normalize_text(product.get("Categoria"))
            if product_category != normalized_category:
                continue

        if normalized_query:
            blob = _normalize_text(
                " ".join(
                    (
                        _stringify(product.get("Codigo")),
                        _stringify(product.get("Nome")),
                        _stringify(product.get("Descricao")),
                        _stringify(product.get("Categoria")),
                    )
                )
            )
            if normalized_query not in blob:
                continue

        filtered.append(dict(product))

    return filtered


def _ordered_columns(products: Sequence[Dict[str, Any]]) -> List[str]:
    columns = {key for product in products for key in product.keys()}
    ordered = [column for column in PREFERRED_COLUMNS if column in columns]
    extra = sorted((column for column in columns if column not in ordered), key=_normalize_text)
    return ordered + extra


def _tabular_rows(products: Sequence[Dict[str, Any]]) -> tuple[List[str], List[Dict[str, str]]]:
    columns = _ordered_columns(products)
    rows: List[Dict[str, str]] = []
    for product in products:
        rows.append({column: _stringify(product.get(column)) for column in columns})
    return columns, rows


def _build_csv_bytes(products: Sequence[Dict[str, Any]]) -> bytes:
    columns, rows = _tabular_rows(products)
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")


def _build_json_bytes(
    products: Sequence[Dict[str, Any]],
    *,
    query: str,
    category: str,
    code: str,
) -> bytes:
    payload = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "filters": {
            "query": query,
            "category": category,
            "code": code,
        },
        "products": list(products),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def _build_xlsx_bytes(products: Sequence[Dict[str, Any]]) -> bytes:
    columns, rows = _tabular_rows(products)
    dataframe = pd.DataFrame(rows, columns=columns)
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(writer, sheet_name="Produtos", index=False)
        worksheet = writer.sheets["Produtos"]
        worksheet.freeze_panes = "A2"
        for index, column in enumerate(dataframe.columns, start=1):
            values = [column, *dataframe[column].astype(str).tolist()]
            width = min(max((len(value) for value in values), default=10) + 2, 60)
            worksheet.column_dimensions[worksheet.cell(row=1, column=index).column_letter].width = width

    return output.getvalue()


def _load_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_names = [
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "Arial Bold.ttf" if bold else "Arial.ttf",
        "arialbd.ttf" if bold else "arial.ttf",
    ]
    for font_name in font_names:
        try:
            return ImageFont.truetype(font_name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _measure_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    left, top, right, bottom = draw.textbbox((0, 0), text or " ", font=font)
    return right - left, bottom - top


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> List[str]:
    if not text:
        return [""]

    wrapped_lines: List[str] = []
    for paragraph in str(text).splitlines() or [""]:
        current = ""
        for word in paragraph.split():
            candidate = word if not current else f"{current} {word}"
            width, _ = _measure_text(draw, candidate, font)
            if width <= max_width:
                current = candidate
                continue
            if current:
                wrapped_lines.append(current)
            current = word
        wrapped_lines.append(current or "")
    return wrapped_lines or [""]


def _draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    font: ImageFont.ImageFont,
    x: int,
    y: int,
    max_width: int,
    fill: str = "#102845",
    line_spacing: int = 8,
) -> int:
    lines = _wrap_text(draw, text, font, max_width)
    _, line_height = _measure_text(draw, "Ag", font)
    for line in lines:
        draw.text((x, y), line, fill=fill, font=font)
        y += line_height + line_spacing
    return y


def _new_pdf_page() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    page = Image.new("RGB", PAGE_SIZE, "#f3f6fb")
    return page, ImageDraw.Draw(page)


def _display_label(key: str) -> str:
    if key in DISPLAY_LABEL_MAP:
        return DISPLAY_LABEL_MAP[key]
    cleaned = re.sub(r"[_\-]+", " ", key or "").strip()
    return cleaned.title() if cleaned else "Campo"


def _load_brand_banner() -> Image.Image | None:
    for path in BRAND_BANNER_CANDIDATES:
        if not path.is_file():
            continue
        try:
            with Image.open(path) as image:
                if image.mode != "RGB":
                    image = image.convert("RGB")
                return image.copy()
        except Exception:
            continue
    return None


def _rounded_box(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    *,
    fill: str,
    outline: str | None = None,
    radius: int = 28,
    width: int = 2,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def _paste_fitted_image(
    page: Image.Image,
    image: Image.Image,
    box: tuple[int, int, int, int],
    *,
    background: str = "white",
) -> None:
    left, top, right, bottom = box
    available = (max(1, right - left), max(1, bottom - top))
    fitted = ImageOps.contain(image, available)
    canvas = Image.new("RGB", available, background)
    offset = ((available[0] - fitted.width) // 2, (available[1] - fitted.height) // 2)
    canvas.paste(fitted, offset)
    page.paste(canvas, (left, top))


def _draw_metric_card(
    draw: ImageDraw.ImageDraw,
    *,
    box: tuple[int, int, int, int],
    label: str,
    value: str,
    label_font: ImageFont.ImageFont,
    value_font: ImageFont.ImageFont,
) -> None:
    _rounded_box(draw, box, fill="#ffffff", outline="#d7e7ff", radius=22)
    left, top, right, bottom = box
    draw.text((left + 18, top + 16), label.upper(), fill="#5b7caa", font=label_font)
    y = top + 50
    max_width = right - left - 36
    _draw_wrapped_text(draw, text=value or "-", font=value_font, x=left + 18, y=y, max_width=max_width, fill="#123874", line_spacing=6)


def _draw_attribute_grid(
    draw: ImageDraw.ImageDraw,
    *,
    attributes: Sequence[tuple[str, str]],
    box: tuple[int, int, int, int],
    columns: int,
    section_font: ImageFont.ImageFont,
    label_font: ImageFont.ImageFont,
    value_font: ImageFont.ImageFont,
    title: str,
) -> int:
    _rounded_box(draw, box, fill="#ffffff", outline="#d7e7ff", radius=30)
    left, top, right, bottom = box
    draw.text((left + 24, top + 20), title, fill="#123874", font=section_font)
    header_y = top + 60
    cell_gap = 16
    usable_width = right - left - 48
    cell_width = (usable_width - (columns - 1) * cell_gap) // columns
    cell_height = 92
    row_y = header_y
    used = 0

    for index, (label, value) in enumerate(attributes):
        row = index // columns
        col = index % columns
        cell_left = left + 24 + col * (cell_width + cell_gap)
        cell_top = header_y + row * (cell_height + 12)
        cell_bottom = cell_top + cell_height
        if cell_bottom > bottom - 20:
            break

        draw.rounded_rectangle(
            (cell_left, cell_top, cell_left + cell_width, cell_bottom),
            radius=18,
            fill="#f7fbff",
            outline="#e4eefc",
            width=2,
        )
        draw.text((cell_left + 16, cell_top + 14), _display_label(label).upper(), fill="#5b7caa", font=label_font)
        _draw_wrapped_text(
            draw,
            text=value or "-",
            font=value_font,
            x=cell_left + 16,
            y=cell_top + 42,
            max_width=cell_width - 32,
            fill="#153662",
            line_spacing=6,
        )
        row_y = cell_bottom
        used = index + 1

    return used


def _product_attributes(product: Dict[str, Any]) -> List[tuple[str, str]]:
    base_keys = {"Codigo", "Nome", "Categoria", "Descricao", "Especificacoes"}
    attributes: List[tuple[str, str]] = []

    for key in FEATURED_ATTRIBUTE_KEYS:
        value = _stringify(product.get(key))
        if value:
            attributes.append((key, value))

    extra_keys = sorted((key for key in product.keys() if key not in base_keys and key not in FEATURED_ATTRIBUTE_KEYS), key=_normalize_text)
    for key in extra_keys:
        value = _stringify(product.get(key))
        if value:
            attributes.append((key, value))

    return attributes


def _photo_references(product: Dict[str, Any]) -> List[Dict[str, str]]:
    code = _stringify(product.get("Codigo"))
    references: List[Dict[str, str]] = []
    seen: set[str] = set()

    for label, key in PHOTO_FIELDS:
        url = _stringify(product.get(key))
        if url and url not in seen:
            references.append({"label": label, "url": url})
            seen.add(url)

    if code:
        try:
            for index, image in enumerate(onedrive.find_local_images_for_code(code), start=1):
                url = _stringify(image.get("url"))
                if not url or url in seen:
                    continue
                label = _stringify(image.get("name")) or f"Imagem {index}"
                references.append({"label": label, "url": url})
                seen.add(url)
        except Exception:
            pass

    return references


def _resolve_photo_bytes(url: str) -> tuple[bytes | None, str]:
    parsed = urlparse(url or "")
    path_value = parse_qs(parsed.query).get("path", [""])[0]

    if parsed.path.endswith("/catalog/local/asset") and path_value:
        asset_path = onedrive.resolve_local_asset_path(unquote(path_value))
        if not asset_path:
            return None, ""
        local_path = Path(asset_path)
        try:
            return local_path.read_bytes(), local_path.suffix.lower()
        except OSError:
            return None, local_path.suffix.lower()

    if parsed.scheme not in {"http", "https"}:
        return None, ""

    return _download_remote_image_bytes(url)


def _open_image_for_export(url: str) -> Image.Image | None:
    payload, _ = _resolve_photo_bytes(url)
    if not payload:
        return None

    try:
        with Image.open(BytesIO(payload)) as image:
            if image.mode not in {"RGB", "RGBA"}:
                image = image.convert("RGB")
            if image.mode == "RGBA":
                background = Image.new("RGB", image.size, "white")
                background.paste(image, mask=image.split()[-1])
                image = background
            return image.copy()
    except Exception:
        return None


def _build_product_pdf_pages(product: Dict[str, Any]) -> List[Image.Image]:
    brand_font = _load_font(68, bold=True)
    title_font = _load_font(28, bold=True)
    product_font = _load_font(36, bold=True)
    section_font = _load_font(24, bold=True)
    body_font = _load_font(20)
    small_font = _load_font(16)
    tiny_font = _load_font(13, bold=True)
    code = _stringify(product.get("Codigo"))
    name = _stringify(product.get("Nome")) or f"Produto {code}"
    category = _stringify(product.get("Categoria")) or "Sem categoria"
    description = _stringify(product.get("Descricao")) or "Sem descricao cadastrada."
    specs = _stringify(product.get("Especificacoes")) or "Sem especificacoes cadastradas."
    attributes = _product_attributes(product)
    banner = _load_brand_banner()
    images = [image for image in (_open_image_for_export(item["url"]) for item in _photo_references(product)[:4]) if image is not None]

    featured_metrics = [
        ("Codigo", code),
        ("Codigo de barras", _stringify(product.get("CODAUXILIAR"))),
        ("NCM", _stringify(product.get("NBM"))),
        ("IPI", _stringify(product.get("PERCIPIVENDA"))),
    ]
    highlighted_attributes = [
        (label, value)
        for label, value in attributes
        if label not in {"CODPROD", "CODAUXILIAR", "NBM", "PERCIPIVENDA"}
    ]

    pages: List[Image.Image] = []
    page, draw = _new_pdf_page()
    hero_box = (60, 56, 1180, 288)
    _rounded_box(draw, hero_box, fill="#123f87", radius=36)
    if banner is not None:
        _paste_fitted_image(page, banner, (60, 56, 420, 288), background="#123f87")
        draw.rounded_rectangle((60, 56, 420, 288), radius=36, outline=None, fill=None)
        draw.rectangle((280, 56, 420, 288), fill="#123f87")

    draw.text((444, 90), "NITROLUX", fill="white", font=brand_font)
    draw.text((448, 170), "FICHA TECNICA DO PRODUTO", fill="#dbe8ff", font=title_font)
    draw.text((448, 210), f"Categoria: {category}", fill="#f3f7ff", font=body_font)

    code_box = (942, 96, 1138, 204)
    _rounded_box(draw, code_box, fill="#ffffff", radius=28)
    draw.text((970, 118), "CODIGO", fill="#5b7caa", font=tiny_font)
    draw.text((970, 144), code or "-", fill="#123874", font=_load_font(42, bold=True))

    info_box = (60, 330, 570, 980)
    photo_box = (598, 330, 1180, 980)
    _rounded_box(draw, info_box, fill="#ffffff", outline="#d7e7ff", radius=32)
    _rounded_box(draw, photo_box, fill="#ffffff", outline="#d7e7ff", radius=32)

    desc_y = _draw_wrapped_text(
        draw,
        text=name,
        font=product_font,
        x=88,
        y=360,
        max_width=430,
        fill="#123874",
        line_spacing=8,
    )
    desc_y = _draw_wrapped_text(
        draw,
        text=description,
        font=body_font,
        x=88,
        y=desc_y + 18,
        max_width=430,
        fill="#31557f",
        line_spacing=8,
    )
    draw.text((88, desc_y + 18), "ESPECIFICACOES", fill="#5b7caa", font=tiny_font)
    _draw_wrapped_text(
        draw,
        text=specs,
        font=body_font,
        x=88,
        y=desc_y + 48,
        max_width=430,
        fill="#153662",
        line_spacing=8,
    )

    if images:
        _paste_fitted_image(page, images[0], (632, 364, 1146, 804))
    else:
        placeholder_font = _load_font(24, bold=True)
        draw.rounded_rectangle((632, 364, 1146, 804), radius=26, fill="#f5f9ff", outline="#e4eefc", width=2)
        draw.text((744, 560), "SEM FOTO", fill="#7d96ba", font=placeholder_font)

    draw.text((632, 830), "IMAGENS DO PRODUTO", fill="#5b7caa", font=tiny_font)
    thumb_y = 860
    thumb_width = 150
    thumb_gap = 18
    for index, image in enumerate(images[1:4], start=0):
        left = 632 + index * (thumb_width + thumb_gap)
        box = (left, thumb_y, left + thumb_width, thumb_y + 100)
        _rounded_box(draw, box, fill="#f7fbff", outline="#e4eefc", radius=18)
        _paste_fitted_image(page, image, (left + 6, thumb_y + 6, left + thumb_width - 6, thumb_y + 94), background="#f7fbff")

    metric_width = 244
    metric_gap = 16
    metric_top = 1008
    for index, (label, value) in enumerate(featured_metrics):
        left = 60 + index * (metric_width + metric_gap)
        _draw_metric_card(
            draw,
            box=(left, metric_top, left + metric_width, metric_top + 130),
            label=label,
            value=value or "-",
            label_font=tiny_font,
            value_font=_load_font(22, bold=True),
        )

    metadata_box = (60, 1168, 1180, 1662)
    used = _draw_attribute_grid(
        draw,
        attributes=highlighted_attributes,
        box=metadata_box,
        columns=2,
        section_font=section_font,
        label_font=tiny_font,
        value_font=small_font,
        title="DETALHES TECNICOS",
    )

    footer_font = _load_font(14)
    footer_text = f"Gerado em {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}"
    draw.text((60, 1688), footer_text, fill="#6d82a6", font=footer_font)
    pages.append(page)

    remaining_attributes = highlighted_attributes[used:]
    while remaining_attributes:
        extra_page, extra_draw = _new_pdf_page()
        header_box = (60, 56, 1180, 196)
        _rounded_box(extra_draw, header_box, fill="#123f87", radius=30)
        extra_draw.text((88, 96), f"DETALHES COMPLEMENTARES - PRODUTO {code or '-'}", fill="white", font=title_font)
        extra_draw.text((88, 136), name, fill="#dbe8ff", font=body_font)
        consumed = _draw_attribute_grid(
            extra_draw,
            attributes=remaining_attributes,
            box=(60, 236, 1180, 1648),
            columns=2,
            section_font=section_font,
            label_font=tiny_font,
            value_font=small_font,
            title="ATRIBUTOS ADICIONAIS",
        )
        extra_draw.text((60, 1688), footer_text, fill="#6d82a6", font=footer_font)
        pages.append(extra_page)
        remaining_attributes = remaining_attributes[consumed:]

    return pages


def _build_catalog_pdf_pages(
    products: Sequence[Dict[str, Any]],
    *,
    query: str,
    category: str,
    code: str,
) -> List[Image.Image]:
    title_font = _load_font(34, bold=True)
    subtitle_font = _load_font(20, bold=True)
    body_font = _load_font(18)
    small_font = _load_font(16)
    line_height = _measure_text(ImageDraw.Draw(Image.new("RGB", (10, 10), "white")), "Ag", body_font)[1] + 14

    pages: List[Image.Image] = []
    rows_per_page = 34
    exported_at = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    summary = [
        f"Itens: {len(products)}",
        f"Categoria: {category or 'Todas'}",
        f"Busca: {query or '-'}",
        f"Codigo: {code or '-'}",
        f"Exportado em: {exported_at}",
    ]

    for page_index, start in enumerate(range(0, len(products), rows_per_page), start=1):
        page, draw = _new_pdf_page()
        y = PAGE_MARGIN
        draw.text((PAGE_MARGIN, y), "Catalogo de Produtos", fill="#123874", font=title_font)
        y += 52
        for item in summary:
            draw.text((PAGE_MARGIN, y), item, fill="#37506e", font=small_font)
            y += 24
        y += 12
        draw.rectangle((PAGE_MARGIN, y, PAGE_SIZE[0] - PAGE_MARGIN, y + 42), fill="#ebf2ff")
        draw.text((PAGE_MARGIN + 14, y + 10), "Codigo", fill="#123874", font=subtitle_font)
        draw.text((PAGE_MARGIN + 170, y + 10), "Nome", fill="#123874", font=subtitle_font)
        draw.text((PAGE_MARGIN + 780, y + 10), "Categoria", fill="#123874", font=subtitle_font)
        y += 58

        for row_index, product in enumerate(products[start : start + rows_per_page], start=1):
            code_text = _stringify(product.get("Codigo"))
            name_text = textwrap.shorten(_stringify(product.get("Nome")), width=52, placeholder="...")
            category_text = textwrap.shorten(_stringify(product.get("Categoria")), width=28, placeholder="...")
            draw.text((PAGE_MARGIN + 14, y), code_text, fill="#102845", font=body_font)
            draw.text((PAGE_MARGIN + 170, y), name_text, fill="#102845", font=body_font)
            draw.text((PAGE_MARGIN + 780, y), category_text, fill="#37506e", font=body_font)
            draw.line((PAGE_MARGIN, y + line_height - 8, PAGE_SIZE[0] - PAGE_MARGIN, y + line_height - 8), fill="#ebf2ff")
            y += line_height

        draw.text(
            (PAGE_MARGIN, PAGE_SIZE[1] - PAGE_MARGIN),
            f"Pagina {page_index}",
            fill="#617892",
            font=small_font,
        )
        pages.append(page)

    return pages or [_new_pdf_page()[0]]


def _build_pdf_bytes(
    products: Sequence[Dict[str, Any]],
    *,
    query: str,
    category: str,
    code: str,
) -> bytes:
    pages = (
        _build_product_pdf_pages(products[0])
        if len(products) == 1
        else _build_catalog_pdf_pages(products, query=query, category=category, code=code)
    )
    output = BytesIO()
    first_page, *other_pages = pages
    first_page.save(output, format="PDF", save_all=True, append_images=other_pages)
    return output.getvalue()


def _build_photo_manifest_rows(products: Sequence[Dict[str, Any]]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for product in products:
        code = _stringify(product.get("Codigo"))
        name = _stringify(product.get("Nome"))
        for reference in _photo_references(product):
            rows.append(
                {
                    "Codigo": code,
                    "Nome": name,
                    "Foto": reference["label"],
                    "URL": reference["url"],
                }
            )
    return rows


def _csv_from_rows(rows: Sequence[Dict[str, str]], columns: Sequence[str]) -> bytes:
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(columns), extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")


def _build_zip_bytes(
    products: Sequence[Dict[str, Any]],
    *,
    query: str,
    category: str,
    code: str,
    base_name: str,
) -> bytes:
    output = BytesIO()
    photo_manifest: List[Dict[str, str]] = []

    with ZipFile(output, mode="w", compression=ZIP_DEFLATED) as zip_file:
        zip_file.writestr(f"{base_name}.csv", _build_csv_bytes(products))
        zip_file.writestr(f"{base_name}.json", _build_json_bytes(products, query=query, category=category, code=code))
        zip_file.writestr(
            "README.txt",
            (
                "Pacote de exportacao do catalogo.\n"
                "- Arquivos CSV/JSON contem os dados exportados.\n"
                "- A pasta fotos/ contem imagens locais ou remotas que puderam ser baixadas.\n"
                "- O manifesto_fotos.csv lista todas as referencias encontradas, mesmo quando a imagem nao foi baixada.\n"
            ).encode("utf-8"),
        )

        for product in products:
            product_code = _stringify(product.get("Codigo")) or "sem-codigo"
            for index, reference in enumerate(_photo_references(product), start=1):
                photo_label = reference["label"]
                photo_url = reference["url"]
                file_in_zip = ""
                payload, extension = _resolve_photo_bytes(photo_url)
                if payload:
                    safe_label = _slugify(photo_label, fallback=f"imagem-{index}")
                    resolved_extension = extension or ".bin"
                    file_in_zip = f"fotos/{product_code}/{index:02d}_{safe_label}{resolved_extension}"
                    zip_file.writestr(file_in_zip, payload)

                photo_manifest.append(
                    {
                        "Codigo": product_code,
                        "Nome": _stringify(product.get("Nome")),
                        "Foto": photo_label,
                        "URL": photo_url,
                        "ArquivoZip": file_in_zip,
                    }
                )

        zip_file.writestr(
            "manifesto_fotos.csv",
            _csv_from_rows(photo_manifest, ("Codigo", "Nome", "Foto", "URL", "ArquivoZip")),
        )

    return output.getvalue()


def _response_metadata(format_name: str, *, base_name: str) -> tuple[str, str]:
    normalized = format_name.lower()
    if normalized == "csv":
        return "text/csv; charset=utf-8", f"{base_name}.csv"
    if normalized in {"xlsx", "xls"}:
        return (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            f"{base_name}.xlsx",
        )
    if normalized == "json":
        return "application/json; charset=utf-8", f"{base_name}.json"
    if normalized == "pdf":
        return "application/pdf", f"{base_name}.pdf"
    if normalized == "zip":
        return "application/zip", f"{base_name}.zip"
    raise ValueError("unsupported export format")


def build_catalog_export(
    *,
    format_name: str,
    query: str = "",
    category: str = "",
    code: str = "",
) -> tuple[bytes, str, str]:
    normalized_format = format_name.lower().strip()
    if normalized_format not in SUPPORTED_EXPORT_FORMATS:
        raise ValueError("unsupported export format")

    products = _filter_products(_load_products(), query=query, category=category, code=code)
    if not products:
        raise ValueError("no products available for the selected export")

    if code:
        base_name = f"produto-{_slugify(code, fallback='item')}"
    elif category and _normalize_text(category) != "todas":
        base_name = f"catalogo-{_slugify(category)}"
    else:
        base_name = "catalogo-produtos"

    if normalized_format == "csv":
        payload = _build_csv_bytes(products)
    elif normalized_format in {"xlsx", "xls"}:
        payload = _build_xlsx_bytes(products)
    elif normalized_format == "json":
        payload = _build_json_bytes(products, query=query, category=category, code=code)
    elif normalized_format == "pdf":
        payload = _build_pdf_bytes(products, query=query, category=category, code=code)
    else:
        payload = _build_zip_bytes(products, query=query, category=category, code=code, base_name=base_name)

    media_type, filename = _response_metadata(normalized_format, base_name=base_name)
    return payload, media_type, filename
