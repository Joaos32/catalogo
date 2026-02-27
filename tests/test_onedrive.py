import pytest
from catalog.onedrive import _encode_share_url, categorize_photos


def test_encode_share_url():
    url = "https://1drv.ms/f/c/abc123?e=xyz"
    encoded = _encode_share_url(url)
    assert encoded.startswith("u!")
    # should not contain '='
    assert "=" not in encoded


def test_categorize_photos():
    items = [
        {"name": "PROD1_branco.jpg", "webUrl": "http://example.com/w1"},
        {"name": "PROD1_ambient.jpg", "webUrl": "http://example.com/a1"},
        {"name": "PROD1_medida.jpg", "webUrl": "http://example.com/m1"},
        {"name": "OTHER.jpg", "webUrl": "http://example.com/o"},
    ]
    cats = categorize_photos(items, code="PROD1")
    assert cats["white_background"] == "http://example.com/w1"
    assert cats["ambient"] == "http://example.com/a1"
    assert cats["measures"] == "http://example.com/m1"

    # code filter
    cats2 = categorize_photos(items, code="OTHER")
    assert cats2["white_background"] is None
    assert cats2["ambient"] is None
    assert cats2["measures"] is None


def test_match_and_find_images(monkeypatch):
    # prepare fake graph client responses to simulate nested folders
    calls = {"share": 0, "children": 0}

    def fake_share_info(url):
        calls["share"] += 1
        return {"parentReference": {"driveId": "drive123"}, "id": "root"}

    def fake_list_children(drive_id, item_id):
        calls["children"] += 1
        if item_id == "root":
            return [
                {"name": "cat", "folder": {}, "id": "f1"},
                {"name": "6649.jpg", "id": "i1", "@microsoft.graph.downloadUrl": "u1"},
                {"name": "6649-1.jpg", "id": "i2", "@microsoft.graph.downloadUrl": "u2"},
                {"name": "other.png", "id": "i3", "@microsoft.graph.downloadUrl": "u3"},
            ]
        elif item_id == "f1":
            return [
                {"name": "6649_2.webp", "id": "i4", "@microsoft.graph.downloadUrl": "u4"},
                {"name": "junk.txt", "id": "i5"},
            ]
        else:
            return []

    # apply patch directly to functions imported in onedrive module
    monkeypatch.setattr('catalog.onedrive.get_share_info', fake_share_info)
    monkeypatch.setattr('catalog.onedrive.list_children', fake_list_children)

    from catalog.onedrive import find_images_for_code

    imgs = find_images_for_code('https://1drv.ms/fake', '6649')
    assert len(imgs) == 3
    assert imgs[0]['name'] == '6649.jpg' and imgs[0]['variant'] == 0
    assert imgs[1]['name'] == '6649-1.jpg' and imgs[1]['variant'] == 1
    assert imgs[2]['name'] == '6649_2.webp' and imgs[2]['variant'] == 2

    # second call should hit cache; counts should not increase
    before = calls.copy()
    imgs2 = find_images_for_code('https://1drv.ms/fake', '6649')
    assert imgs2 == imgs
    assert calls == before


def test_auth_endpoints(monkeypatch):
    import os
    from fastapi.testclient import TestClient

    # provide dummy env first so module-level constants may be set if needed
    os.environ['AZURE_CLIENT_ID'] = 'id'
    os.environ['AZURE_CLIENT_SECRET'] = 'secret'
    os.environ['AZURE_TENANT_ID'] = 'tenant'
    os.environ['AZURE_REDIRECT_URI'] = 'http://localhost'

    class DummyApp:
        def get_authorization_request_url(self, *args, **kwargs):
            return "https://login.microsoftonline.com/fake"
    monkeypatch.setattr('catalog.auth._build_msal_app', lambda: DummyApp())

    # import app after patching so router is registered normally
    from app import app

    # rather than rely solely on routing, also verify handler logic
    from catalog.auth import login, callback
    from fastapi.responses import RedirectResponse

    resp = login()
    assert isinstance(resp, RedirectResponse)
    assert resp.headers.get('location', '').startswith('https://login.microsoftonline.com')

    # callback raises if called directly without a code; we verify
    # behaviour via HTTP client below instead.
    # still ensure routes are present and callable via client
    client = TestClient(app)
    resp3 = client.get('/auth/login', follow_redirects=False)
    assert resp3.status_code in (302, 307)
    resp4 = client.get('/auth/callback')
    assert resp4.status_code == 400

