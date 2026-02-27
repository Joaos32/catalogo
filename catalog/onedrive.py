"""Utilities to interact with OneDrive using Microsoft Graph.

This module uses MSAL for authentication. To use it you'll need to register an
app in Azure AD and set the following environment variables:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_CLIENT_SECRET` (or use a certificate)

Then acquire a token for the `https://graph.microsoft.com/.default` scope and
call the drive API.
"""

import os
import re
import base64
from typing import List, Dict

from .graph_client import get_share_info, list_children
from .cache import cached

# keep earlier categorization util for backwards compatibility


def _encode_share_url(url: str) -> str:
    """Convert a OneDrive share URL into Graph "shares/{id}" syntax.

    The url must be base64 URL-safe encoded and prefixed with "u!.".
    """
    clean = url.split('?')[0]
    raw = base64.urlsafe_b64encode(clean.encode()).decode().rstrip("=")
    return f"u!{raw}"


# legacy helper used by `/catalog/photos` endpoint
# kept for compatibility; authentication now uses delegated tokens via graph_client

def list_shared_items(share_url: str):
    """List *immediate* children of a shared folder.

    This function uses the Graph `driveItem/children` endpoint directly and
    predates the new search-by-code logic. It remains available for existing
    frontend code such as `/catalog/photos`.
    """
    try:
        info = get_share_info(share_url)
        drive_id = info.get("parentReference", {}).get("driveId")
        item_id = info.get("id")
        if not drive_id or not item_id:
            raise ValueError("unable to resolve shared folder")
        return list_children(drive_id, item_id)
    except Exception as exc:
        # wrap any Graph/auth error in EnvironmentError so callers can fall
        # back to placeholder behavior like before
        raise EnvironmentError(str(exc))

def categorize_photos(items: list, code: str = None) -> dict:
    """Return representative URLs matching criteria.

    (unchanged legacy helper)
    """
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


# ------------------ new utilities for product image lookup ------------------

IMG_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
FILENAME_PATTERN = re.compile(r"^(?P<code>\d+)(?:[-_](?P<variant>\d+))?\.(?:jpg|jpeg|png|webp)$", re.IGNORECASE)


def _match_filename(name: str, code: str):
    m = FILENAME_PATTERN.match(name)
    if not m:
        return None
    if m.group("code") != code:
        return None
    variant = m.group("variant")
    return int(variant) if variant is not None else 0


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
            # Graph returns a 'folder' key for directories; it may be an empty
            # dict, so check for the presence of the key rather than truthiness.
            if "folder" in it:
                _recurse(d_id, it.get("id"), depth + 1)
                continue
            name = it.get("name", "")
            if not any(name.lower().endswith(ext) for ext in IMG_EXTENSIONS):
                continue
            variant = _match_filename(name, code)
            if variant is None:
                continue
            url = it.get("@microsoft.graph.downloadUrl") or f"https://graph.microsoft.com/v1.0/drives/{d_id}/items/{it.get('id')}/content"
            matches.append({"name": name, "variant": variant, "url": url})

    _recurse(drive_id, item_id, 0)
    matches.sort(key=lambda x: x["variant"])
    return matches
