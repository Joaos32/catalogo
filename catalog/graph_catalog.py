"""Utilitarios para descoberta de itens e imagens via Microsoft Graph."""

from __future__ import annotations

import base64
from typing import Any, Callable, Dict, Iterable, List


def encode_share_url(url: str) -> str:
    clean = url.split("?")[0]
    raw = base64.urlsafe_b64encode(clean.encode()).decode().rstrip("=")
    return f"u!{raw}"


def list_shared_items(
    share_url: str,
    *,
    get_share_info_fn: Callable[[str], Dict[str, Any]],
    list_children_fn: Callable[[str, str], List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    try:
        info = get_share_info_fn(share_url)
        drive_id = info.get("parentReference", {}).get("driveId")
        item_id = info.get("id")
        if not drive_id or not item_id:
            raise ValueError("unable to resolve shared folder")
        return list_children_fn(drive_id, item_id)
    except Exception as exc:
        raise EnvironmentError(str(exc))


def categorize_photos(items: Iterable[Dict[str, Any]], code: str | None = None) -> Dict[str, str | None]:
    result = {"white_background": None, "ambient": None, "measures": None}
    for item in items:
        name = str(item.get("name", "")).lower()
        web_url = item.get("webUrl")
        if code and code.lower() not in name:
            continue
        if result["white_background"] is None and ("branco" in name or "white" in name):
            result["white_background"] = web_url
        if result["ambient"] is None and ("ambient" in name or "ambiente" in name):
            result["ambient"] = web_url
        if result["measures"] is None and ("medida" in name or "measure" in name):
            result["measures"] = web_url
    return result


def find_images_for_code(
    share_url: str,
    code: str,
    *,
    max_depth: int,
    get_share_info_fn: Callable[[str], Dict[str, Any]],
    list_children_fn: Callable[[str, str], List[Dict[str, Any]]],
    match_filename_fn: Callable[[str, str], int | None],
    img_extensions: Iterable[str],
) -> List[Dict[str, Any]]:
    info = get_share_info_fn(share_url)
    drive_id = info.get("parentReference", {}).get("driveId")
    item_id = info.get("id")
    if not drive_id or not item_id:
        raise ValueError("unable to resolve shared folder")

    matches: List[Dict[str, Any]] = []
    normalized_extensions = tuple(img_extensions)

    def _recurse(current_drive_id: str, current_item_id: str, depth: int) -> None:
        if depth > max_depth:
            return

        children = list_children_fn(current_drive_id, current_item_id)
        for item in children:
            if "folder" in item:
                _recurse(current_drive_id, item.get("id"), depth + 1)
                continue

            name = str(item.get("name", ""))
            if not any(name.lower().endswith(ext) for ext in normalized_extensions):
                continue

            variant = match_filename_fn(name, code)
            if variant is None:
                continue

            url = item.get("@microsoft.graph.downloadUrl") or (
                f"https://graph.microsoft.com/v1.0/drives/{current_drive_id}/items/{item.get('id')}/content"
            )
            matches.append({"name": name, "variant": variant, "url": url})

    _recurse(drive_id, item_id, 0)
    matches.sort(key=lambda item: item["variant"])
    return matches
