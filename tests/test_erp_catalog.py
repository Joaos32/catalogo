import os

from catalog.erp_catalog import import_erp_payload, merge_products_with_erp


def test_merge_products_with_erp_data(monkeypatch):
    target_path = os.path.join(os.getcwd(), 'reports', '_test_erp_merge.json')
    if os.path.exists(target_path):
        os.remove(target_path)


def test_merge_products_maps_to_business_categories(monkeypatch):
    target_path = os.path.join(os.getcwd(), 'reports', '_test_erp_business_map.json')
    if os.path.exists(target_path):
        os.remove(target_path)

    monkeypatch.setenv('CATALOG_ERP_JSON_PATH', target_path)

    import_erp_payload(
        {
            'products': [
                {'codigo': '3003', 'nome': 'Produto Painel', 'categoria': 'PAINEL'},
                {'codigo': '4004', 'nome': 'Produto Balizador', 'categoria': 'BALIZADOR'},
                {'codigo': '5005', 'nome': 'Produto Rele', 'descricao': 'RELE FOTOCELULA'},
                {'codigo': '6006', 'nome': 'Produto Sem Grupo', 'categoria': 'GRUPO X'},
            ]
        }
    )

    merged = merge_products_with_erp([])

    allowed = {
        'ILUMINACAO DECORATIVA',
        'ILUMINACAO TECNICA',
        'ILUMINACAO EXTERNA E PUBLICA',
        'LAMPADAS E FITAS',
        'COMPONENTES E ACESSORIOS',
        'UTILIDADES E OPERACAO',
        'OUTROS ITENS ERP',
    }

    categories = {item['Categoria'] for item in merged}
    assert categories.issubset(allowed)

    product_3003 = next(item for item in merged if item['Codigo'] == '3003')
    assert product_3003['Categoria'] == 'ILUMINACAO TECNICA'

    product_4004 = next(item for item in merged if item['Codigo'] == '4004')
    assert product_4004['Categoria'] == 'ILUMINACAO EXTERNA E PUBLICA'

    product_5005 = next(item for item in merged if item['Codigo'] == '5005')
    assert product_5005['Categoria'] == 'COMPONENTES E ACESSORIOS'

    product_6006 = next(item for item in merged if item['Codigo'] == '6006')
    assert product_6006['Categoria'] == 'OUTROS ITENS ERP'

    if os.path.exists(target_path):
        os.remove(target_path)

    monkeypatch.setenv('CATALOG_ERP_JSON_PATH', target_path)

    import_erp_payload(
        {
            'products': [
                {
                    'codigo': '1001',
                    'nome': 'Produto ERP 1001',
                    'categoria': 'PENDENTE',
                    'descricao': 'Descricao ERP 1001',
                    'voltagem': '220V',
                },
                {
                    'codigo': '2002',
                    'nome': 'Produto ERP 2002',
                    'categoria': 'LUMINARIA',
                },
            ]
        }
    )

    base_products = [
        {
            'Codigo': '1001',
            'Nome': 'Produto Local 1001',
            'Descricao': '',
            'Categoria': 'Sem categoria',
            'URLFoto': '/catalog/local/asset?path=1001.jpg',
            'Especificacoes': '',
            'FotoBranco': '/catalog/local/asset?path=1001.jpg',
            'FotoAmbient': '',
            'FotoMedidas': '',
        }
    ]

    merged = merge_products_with_erp(base_products)
    assert len(merged) == 2

    product_1001 = next(item for item in merged if item['Codigo'] == '1001')
    assert product_1001['Nome'] == 'Produto ERP 1001'
    assert product_1001['Categoria'] == 'ILUMINACAO DECORATIVA'
    assert product_1001['Descricao'] == 'Descricao ERP 1001'
    # Mantem foto local quando o ERP nao envia URL.
    assert product_1001['URLFoto'].startswith('/catalog/local/asset')
    assert product_1001['voltagem'] == '220V'

    product_2002 = next(item for item in merged if item['Codigo'] == '2002')
    assert product_2002['Nome'] == 'Produto ERP 2002'
    assert product_2002['Categoria'] == 'ILUMINACAO TECNICA'
    assert product_2002['URLFoto'].startswith('https://placehold.co/')

    if os.path.exists(target_path):
        os.remove(target_path)
