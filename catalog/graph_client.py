import os
from typing import Any, Dict, List
import requests
from .auth import get_access_token

BASE_URL = "https://graph.microsoft.com/v1.0"


def _get_headers(scopes: List[str] = None) -> Dict[str, str]:
    token = get_access_token(scopes=scopes or ["Files.Read"])
    return {"Authorization": f"Bearer {token}"}


def get_share_info(share_url: str) -> Dict[str, Any]:
    """Return share information for a shared link (driveItem metadata)."""
    # share_url expected full 1drv.ms link
    from .onedrive import _encode_share_url

    share_id = _encode_share_url(share_url)
    resp = requests.get(f"{BASE_URL}/shares/{share_id}/driveItem", headers=_get_headers())
    resp.raise_for_status()
    return resp.json()


def list_children(drive_id: str, item_id: str) -> List[Dict[str, Any]]:
    """List direct children of a drive item."""
    resp = requests.get(
        f"{BASE_URL}/drives/{drive_id}/items/{item_id}/children",
        headers=_get_headers(),
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("value", [])
