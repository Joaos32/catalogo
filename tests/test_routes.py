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
    monkeypatch.setattr('catalog.onedrive.resolve_local_products_root', lambda: None)
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


def test_spa_blocks_path_traversal():
    client = TestClient(app)
    for path in ('/..%2Fapp.py', '/%2e%2e%2fapp.py'):
        rv = client.get(path)
        assert rv.status_code == 200
        assert rv.headers.get('content-type', '').startswith('text/html')
        assert 'from fastapi import FastAPI' not in rv.text


def test_photos_no_credentials(monkeypatch):
    # if environment variables for Azure are not defined, the route should
    # return empty photo lists instead of failing with HTTP 500.
    monkeypatch.delenv('AZURE_CLIENT_ID', raising=False)
    monkeypatch.delenv('AZURE_CLIENT_SECRET', raising=False)
    monkeypatch.delenv('AZURE_TENANT_ID', raising=False)
    monkeypatch.setattr('catalog.onedrive.resolve_local_products_root', lambda: None)
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
    monkeypatch.setattr('catalog.onedrive.find_local_images_for_code', lambda code: [])
    monkeypatch.setattr('catalog.onedrive.resolve_local_products_root', lambda: None)
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


def test_product_images_route_prefers_local(monkeypatch):
    monkeypatch.setattr(
        'catalog.onedrive.find_local_images_for_code',
        lambda code: [{'name': f'{code}.jpg', 'variant': 0, 'url': 'local-u1'}]
    )
    monkeypatch.setattr(
        'catalog.onedrive.find_images_for_code',
        lambda shareUrl, code: (_ for _ in ()).throw(RuntimeError('should not call graph'))
    )
    client = TestClient(app)
    rv = client.get('/catalog/produtos/6649/imagens')
    assert rv.status_code == 200
    data = rv.json()
    assert data['codigo'] == '6649'
    assert data['imagens'][0]['url'] == 'local-u1'


def test_product_images_local_mode_without_photos(monkeypatch):
    monkeypatch.setattr('catalog.onedrive.find_local_images_for_code', lambda code: [])
    monkeypatch.setattr('catalog.onedrive.resolve_local_products_root', lambda: r'C:\Users\joao.silva\OneDrive\MARKETING\Catalogo')
    monkeypatch.setattr(
        'catalog.onedrive.find_images_for_code',
        lambda shareUrl, code: (_ for _ in ()).throw(RuntimeError('should not call graph'))
    )
    client = TestClient(app)
    rv = client.get('/catalog/produtos/6379/imagens')
    assert rv.status_code == 200
    assert rv.json() == {'codigo': '6379', 'imagens': []}


def test_local_products_route(monkeypatch):
    monkeypatch.setattr(
        'catalog.onedrive.list_local_products',
        lambda: [{'Codigo': '5989', 'Nome': 'Produto', 'Categoria': 'ABAJUR'}]
    )
    client = TestClient(app)
    rv = client.get('/catalog/local/produtos')
    assert rv.status_code == 200
    data = rv.json()
    assert isinstance(data, list)
    assert data[0]['Codigo'] == '5989'


def test_local_asset_route(monkeypatch):
    monkeypatch.setattr('catalog.onedrive.resolve_local_asset_path', lambda path: __file__)
    client = TestClient(app)
    rv = client.get('/catalog/local/asset', params={'path': 'x'})
    assert rv.status_code == 200
    assert rv.content


def test_local_asset_route_converts_tiff(monkeypatch):
    monkeypatch.setattr('catalog.onedrive.resolve_local_asset_path', lambda path: r'C:\fake\img.tif')
    monkeypatch.setattr('catalog.routes._tiff_to_jpeg_bytes', lambda asset_path: b'jpeg-bytes')
    client = TestClient(app)
    rv = client.get('/catalog/local/asset', params={'path': 'x'})
    assert rv.status_code == 200
    assert rv.headers.get('content-type', '').startswith('image/jpeg')
    assert rv.content == b'jpeg-bytes'


def test_photos_prefers_local(monkeypatch):
    monkeypatch.setattr(
        'catalog.onedrive.categorize_local_photos',
        lambda code: {'white_background': 'local1', 'ambient': None, 'measures': None}
    )
    monkeypatch.setattr('catalog.onedrive.list_shared_items', lambda shareUrl: (_ for _ in ()).throw(RuntimeError('should not call')))
    client = TestClient(app)
    rv = client.get('/catalog/photos', params={'shareUrl': 'x', 'code': 'ABC'})
    assert rv.status_code == 200
    assert rv.json()['white_background'] == 'local1'


def test_photos_local_mode_without_share_url(monkeypatch):
    monkeypatch.setattr(
        'catalog.onedrive.categorize_local_photos',
        lambda code: {'white_background': None, 'ambient': None, 'measures': None}
    )
    monkeypatch.setattr('catalog.onedrive.resolve_local_products_root', lambda: r'C:\Users\joao.silva\OneDrive\MARKETING\Catalogo')
    monkeypatch.setattr(
        'catalog.onedrive.list_shared_items',
        lambda shareUrl: (_ for _ in ()).throw(RuntimeError('should not call'))
    )
    client = TestClient(app)
    rv = client.get('/catalog/photos', params={'code': 'ABC'})
    assert rv.status_code == 200
    assert rv.json() == {'white_background': None, 'ambient': None, 'measures': None}
