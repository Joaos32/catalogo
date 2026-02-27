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
import base64
import requests
from msal import ConfidentialClientApplication


def _get_access_token() -> str:
    """Acquire a confidential client token from Azure AD."""
    client_id = os.environ.get("AZURE_CLIENT_ID")
    tenant_id = os.environ.get("AZURE_TENANT_ID")
    client_secret = os.environ.get("AZURE_CLIENT_SECRET")
    if not all([client_id, tenant_id, client_secret]):
        # missing configuration is an environment issue rather than a logic bug
        raise EnvironmentError("Azure credentials not set in environment variables")
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    app = ConfidentialClientApplication(
        client_id, authority=authority, client_credential=client_secret
    )
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" not in result:
        raise RuntimeError(f"Failed to obtain token: {result.get('error_description')}")
    return result["access_token"]


def _encode_share_url(url: str) -> str:
    """Convert a OneDrive share URL into Graph "shares/{id}" syntax.

    The url must be base64 URL-safe encoded and prefixed with "u!".
    """
    # remove trailing query params like ?e=...
    clean = url.split('?')[0]
    raw = base64.urlsafe_b64encode(clean.encode()).decode().rstrip("=")
    return f"u!{raw}"


def list_shared_items(share_url: str):
    """List children of a shared folder given its share link."""
    token = _get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    share_id = _encode_share_url(share_url)
    # get driveItem for shared link
    url = f"https://graph.microsoft.com/v1.0/shares/{share_id}/driveItem/children"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json().get("value", [])


def categorize_photos(items: list, code: str = None) -> dict:
    """Return representative URLs matching criteria.

    Criteria:
        - white_background: filename contains 'branco' or 'white'
        - ambient: filename contains 'ambient' or 'ambiente'
        - measures: filename contains 'medida' or 'measure'

    If a code is provided, only consider items whose names include the code.
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
