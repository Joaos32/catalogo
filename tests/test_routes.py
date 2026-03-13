import pytest
import os
from io import BytesIO
from zipfile import ZipFile
from fastapi.testclient import TestClient
from app import app

# Bloco auxiliar de monkeypatch.
def fake_list_shared_items(url):
    # Retorna itens com nomes previsiveis.
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
    # Se variaveis de ambiente do Azure nao estiverem definidas, a rota deve
    # retornar lista de fotos sem falhar com HTTP 500.
    monkeypatch.delenv('AZURE_CLIENT_ID', raising=False)
    monkeypatch.delenv('AZURE_CLIENT_SECRET', raising=False)
    monkeypatch.delenv('AZURE_TENANT_ID', raising=False)
    monkeypatch.setattr('catalog.onedrive.resolve_local_products_root', lambda: None)
    client = TestClient(app)
    rv = client.get('/catalog/photos', params={'shareUrl': 'x', 'code': 'y'})
    assert rv.status_code == 200
    data = rv.json()
    # Deve retornar placeholders contendo o codigo.
    assert 'white_background' in data and 'ambient' in data and 'measures' in data
    assert 'y' in data['white_background']
    assert data['white_background'].startswith('https://placehold.co/')


def test_product_images_route(monkeypatch):
    # Simula resposta do OneDrive.
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
    # Parametro shareUrl ausente deve retornar 400.
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


def test_erp_import_and_status(monkeypatch):
    target_path = os.path.join(os.getcwd(), 'reports', '_test_erp_products.json')
    if os.path.exists(target_path):
        os.remove(target_path)

    monkeypatch.setenv('CATALOG_ERP_JSON_PATH', target_path)

    client = TestClient(app)
    rv = client.post('/catalog/erp/import', json={
        'products': [
            {
                'codigo': '9911',
                'nome': 'Produto ERP',
                'categoria': 'LUMINARIA',
                'descricao': 'Descricao vinda do ERP',
                'voltagem': '220V',
            }
        ]
    })
    assert rv.status_code == 200
    payload = rv.json()
    assert payload['products_imported'] == 1

    status = client.get('/catalog/erp/status')
    assert status.status_code == 200
    data = status.json()
    assert data['exists'] is True
    assert data['products_loaded'] == 1

    if os.path.exists(target_path):
        os.remove(target_path)


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


def test_erp_upload_raw_json(monkeypatch):
    target_path = os.path.join(os.getcwd(), 'reports', '_test_erp_upload_target.json')
    inbox_dir = os.path.join(os.getcwd(), 'reports', '_test_erp_inbox')

    if os.path.exists(target_path):
        os.remove(target_path)
    if os.path.isdir(inbox_dir):
        for entry in os.listdir(inbox_dir):
            os.remove(os.path.join(inbox_dir, entry))
        os.rmdir(inbox_dir)

    monkeypatch.setenv('CATALOG_ERP_JSON_PATH', target_path)
    monkeypatch.setenv('CATALOG_ERP_INBOX_DIR', inbox_dir)

    client = TestClient(app)
    body = (
        '{"products":[{"codigo":"8877","nome":"Produto Upload",'
        '"categoria":"PENDENTE","descricao":"Arquivo recebido"}]}'
    )
    rv = client.post(
        '/catalog/erp/upload',
        params={'filename': 'pcprodut_upload.json'},
        content=body.encode('utf-8'),
        headers={'Content-Type': 'application/json'},
    )
    assert rv.status_code == 200
    data = rv.json()
    assert data['products_imported'] == 1
    assert os.path.exists(data['uploaded_path'])

    status = client.get('/catalog/erp/status')
    assert status.status_code == 200
    assert status.json()['products_loaded'] == 1

    if os.path.exists(target_path):
        os.remove(target_path)
    if os.path.isdir(inbox_dir):
        for entry in os.listdir(inbox_dir):
            os.remove(os.path.join(inbox_dir, entry))
        os.rmdir(inbox_dir)


def test_erp_import_file_endpoint(monkeypatch):
    source_path = os.path.join(os.getcwd(), 'reports', '_test_erp_source.json')
    target_path = os.path.join(os.getcwd(), 'reports', '_test_erp_target_from_file.json')

    for path in (source_path, target_path):
        if os.path.exists(path):
            os.remove(path)

    with open(source_path, 'w', encoding='utf-8') as handle:
        handle.write(
            '{"products":[{"codigo":"7788","nome":"Produto Arquivo","categoria":"LUMINARIA"}]}'
        )

    monkeypatch.setenv('CATALOG_ERP_JSON_PATH', target_path)

    client = TestClient(app)
    rv = client.post('/catalog/erp/import-file', json={'file_path': 'reports/_test_erp_source.json'})
    assert rv.status_code == 200
    data = rv.json()
    assert data['products_imported'] == 1
    assert data['source_path'].endswith('_test_erp_source.json')
    assert os.path.exists(target_path)

    files = client.get('/catalog/erp/files')
    assert files.status_code == 200
    payload = files.json()
    assert 'files' in payload
    assert any(item['is_active'] for item in payload['files'])

    for path in (source_path, target_path):
        if os.path.exists(path):
            os.remove(path)


def test_erp_import_file_rejects_path_traversal():
    client = TestClient(app)
    rv = client.post('/catalog/erp/import-file', json={'file_path': '..\\app.py'})
    assert rv.status_code == 400
    assert 'error' in rv.json()


def test_catalog_export_csv(monkeypatch):
    monkeypatch.setattr(
        'catalog.onedrive.list_local_products',
        lambda: [
            {
                'Codigo': '9911',
                'Nome': 'Produto Exportavel',
                'Categoria': 'LUMINARIA',
                'Descricao': 'Descricao para exportacao',
                'CODAUXILIAR': '7890000000001',
            }
        ]
    )
    client = TestClient(app)
    rv = client.get('/catalog/export', params={'format': 'csv'})
    assert rv.status_code == 200
    assert rv.headers.get('content-type', '').startswith('text/csv')
    assert 'attachment; filename="catalogo-produtos.csv"' == rv.headers.get('content-disposition')
    payload = rv.content.decode('utf-8-sig')
    assert 'Codigo,Nome,Categoria' in payload
    assert '9911' in payload
    assert 'Produto Exportavel' in payload


def test_catalog_export_xlsx_single_product(monkeypatch):
    monkeypatch.setattr(
        'catalog.onedrive.list_local_products',
        lambda: [{'Codigo': '9911', 'Nome': 'Produto Exportavel', 'Categoria': 'LUMINARIA'}]
    )
    client = TestClient(app)
    rv = client.get('/catalog/export', params={'format': 'xls', 'code': '9911'})
    assert rv.status_code == 200
    assert rv.headers.get('content-type', '').startswith(
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    assert rv.content[:4] == b'PK\x03\x04'


def test_catalog_export_pdf_single_product(monkeypatch):
    monkeypatch.setattr(
        'catalog.onedrive.list_local_products',
        lambda: [
            {
                'Codigo': '9911',
                'Nome': 'Produto Exportavel',
                'Categoria': 'LUMINARIA',
                'Descricao': 'Descricao para exportacao',
                'Especificacoes': 'Potencia: 12W',
            }
        ]
    )
    monkeypatch.setattr('catalog.onedrive.find_local_images_for_code', lambda code: [])
    client = TestClient(app)
    rv = client.get('/catalog/export', params={'format': 'pdf', 'code': '9911'})
    assert rv.status_code == 200
    assert rv.headers.get('content-type', '').startswith('application/pdf')
    assert rv.content[:5] == b'%PDF-'


def test_catalog_export_zip_includes_photos(monkeypatch):
    photo_path = os.path.join(os.getcwd(), 'reports', '_test_export_photo.jpg')
    if os.path.exists(photo_path):
        os.remove(photo_path)
    with open(photo_path, 'wb') as handle:
        handle.write(b'fake-image-bytes')

    monkeypatch.setattr(
        'catalog.onedrive.list_local_products',
        lambda: [
            {
                'Codigo': '9911',
                'Nome': 'Produto Exportavel',
                'Categoria': 'LUMINARIA',
                'FotoBranco': '/catalog/local/asset?path=9911_1.jpg',
            }
        ]
    )
    monkeypatch.setattr('catalog.onedrive.find_local_images_for_code', lambda code: [])
    monkeypatch.setattr('catalog.onedrive.resolve_local_asset_path', lambda rel_path: photo_path)

    client = TestClient(app)
    rv = client.get('/catalog/export', params={'format': 'zip', 'code': '9911'})
    assert rv.status_code == 200
    assert rv.headers.get('content-type', '').startswith('application/zip')

    with ZipFile(BytesIO(rv.content)) as archive:
        names = archive.namelist()
        assert 'produto-9911.csv' in names
        assert 'produto-9911.json' in names
        assert 'manifesto_fotos.csv' in names
        assert any(name.startswith('fotos/9911/') and name.endswith('.jpg') for name in names)

    if os.path.exists(photo_path):
        os.remove(photo_path)


def test_catalog_export_rejects_invalid_format(monkeypatch):
    monkeypatch.setattr('catalog.onedrive.list_local_products', lambda: [{'Codigo': '9911'}])
    client = TestClient(app)
    rv = client.get('/catalog/export', params={'format': 'xml'})
    assert rv.status_code == 400
    assert 'error' in rv.json()
