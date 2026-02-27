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
