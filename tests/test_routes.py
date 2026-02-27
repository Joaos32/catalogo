import pytest
from fastapi.testclient import TestClient
from app import app

# monkeypatch helper
def fake_list_shared_items(url):
    # return items with predictable names
    return [
        {"name": "ABC_branco.jpg", "webUrl": "u1"},
        {"name": "ABC_ambient.jpg", "webUrl": "u2"},
        {"name": "ABC_medida.jpg", "webUrl": "u3"},
    ]


def test_photos_endpoint(monkeypatch):
    monkeypatch.setattr('catalog.onedrive.list_shared_items', fake_list_shared_items)
    client = TestClient(app)
    rv = client.get('/catalog/photos', params={
        'shareUrl': 'https://example.com/share',
        'code': 'ABC'
    })
    assert rv.status_code == 200
    data = rv.json()
    assert data['white_background'] == 'u1'
    assert data['ambient'] == 'u2'
    assert data['measures'] == 'u3'


def test_photos_missing_param():
    client = TestClient(app)
    rv = client.get('/catalog/photos')
    assert rv.status_code == 400
    assert 'error' in rv.json()


def test_photos_no_credentials(monkeypatch):
    # if environment variables for Azure are not defined, the route should
    # return empty photo lists instead of failing with HTTP 500.
    monkeypatch.delenv('AZURE_CLIENT_ID', raising=False)
    monkeypatch.delenv('AZURE_CLIENT_SECRET', raising=False)
    monkeypatch.delenv('AZURE_TENANT_ID', raising=False)
    client = TestClient(app)
    rv = client.get('/catalog/photos', params={'shareUrl': 'x', 'code': 'y'})
    assert rv.status_code == 200
    data = rv.json()
    # should return placeholder images containing the code
    assert 'white_background' in data and 'ambient' in data and 'measures' in data
    assert 'y' in data['white_background']
    assert data['white_background'].startswith('https://placehold.co/')


def test_product_images_route(monkeypatch):
    # simulate onedrive response
    monkeypatch.setattr('catalog.onedrive.find_images_for_code', lambda shareUrl, code: [
        {'name': f'{code}.jpg', 'variant': 0, 'url': 'u1'},
        {'name': f'{code}-1.png', 'variant': 1, 'url': 'u2'},
    ])
    client = TestClient(app)
    rv = client.get('/catalog/produtos/6649/imagens', params={'shareUrl': 'https://fake'})
    assert rv.status_code == 200
    data = rv.json()
    assert data['codigo'] == '6649'
    assert len(data['imagens']) == 2
    assert data['imagens'][1]['variant'] == 1
    # missing shareUrl parameter should return 400
    rv2 = client.get('/catalog/produtos/6649/imagens')
    assert rv2.status_code == 400
