# Catalogo de Produtos

API em FastAPI + frontend React (Vite + TypeScript) para:
- listar produtos locais (OneDrive/pasta local)
- buscar dados de Google Sheets
- servir imagens de produto
- consultar imagens via Microsoft Graph (opcional)

## Requisitos
- Python 3.10+
- Node.js 20+
- `pip`
- (Opcional) credenciais Azure para rotas Graph

## Instalacao Rapida

Backend:
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

Frontend:
```powershell
cd frontend
npm.cmd install
```

## Executar em Desenvolvimento

Terminal 1 (API):
```powershell
python app.py
```

Terminal 2 (frontend Vite):
```powershell
cd frontend
npm.cmd run dev
```

Aplicacao disponivel em:
- API: `http://127.0.0.1:8000`
- Frontend dev: `http://127.0.0.1:5173`

## Build do Frontend para Servir no FastAPI

```powershell
cd frontend
npm.cmd run build
```

Quando `frontend/dist/index.html` existe, o FastAPI serve automaticamente o build.
Se o build nao existir, a aplicacao usa fallback em `frontend/legacy`.

## Variaveis de Ambiente

Config geral:
- `CATALOG_HOST` (padrao: `127.0.0.1`)
- `CATALOG_PORT` (padrao: `8000`)
- `CATALOG_CORS_ALLOW_ORIGINS` (csv, padrao: `*`)
- `CATALOG_CORS_ALLOW_CREDENTIALS` (padrao: `true`)

Frontend (Vite):
- `VITE_API_BASES` (csv; padrao: `,http://127.0.0.1:8000,http://127.0.0.1:5000`)
- `VITE_REQUEST_TIMEOUT_MS` (padrao: `12000`)
- `VITE_DEV_PROXY_TARGET` (padrao: `http://127.0.0.1:8000`)

Dados locais:
- `CATALOG_LOCAL_PRODUCTS_PATH` (opcional, caminho explicito da pasta de produtos)
- `CATALOG_CADASTRO_HTML` (opcional, caminho explicito do `CADASTRO.html`)
- `CATALOG_ERP_JSON_PATH` (opcional, caminho do arquivo JSON espelho do ERP)
- `CATALOG_ERP_INBOX_DIR` (opcional, pasta para armazenar arquivos recebidos em `/catalog/erp/upload`)
- `CATALOG_ERP_SOURCE_DIRS` (opcional, lista CSV de pastas adicionais para descoberta automatica de JSON)
- `CATALOG_ERP_STRICT_MODE` (opcional, padrao: `true`; quando ativo, o catalogo exibe somente codigos presentes no JSON ERP atual)
  - Se nao informar, o backend tenta detectar automaticamente arquivos como `erp*.json` ou `pcprodut*.json` na raiz do projeto, em `reports/`, em `reports/erp_inbox` e em `catalog/json/`.
  - Se `CATALOG_ERP_JSON_PATH` estiver configurado mas o arquivo nao existir, o backend faz fallback automatico para essa descoberta.

Azure / Graph (opcional):
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`
- `AZURE_TENANT_ID`
- `AZURE_REDIRECT_URI`

## Endpoints Principais

API e frontend:
- `GET /` (SPA/frontend)
- `GET /catalog/sheet?url=<GOOGLE_SHEET_URL>`
- `GET /catalog/photos?code=<CODIGO>&shareUrl=<ONEDRIVE_SHARE_URL>`
- `GET /catalog/produtos/{codigo}/imagens?shareUrl=<ONEDRIVE_SHARE_URL>`
- `GET /catalog/local/produtos`
- `GET /catalog/local/asset?path=<CAMINHO_RELATIVO>`
- `POST /catalog/erp/import` (importa JSON do ERP e atualiza os dados por codigo)
- `POST /catalog/erp/upload?filename=<NOME_ARQUIVO>` (recebe JSON bruto no corpo da requisicao)
- `POST /catalog/erp/import-file` (importa arquivo JSON ja depositado no backend)
- `GET /catalog/erp/files` (lista arquivos JSON ERP encontrados)
- `GET /catalog/erp/status` (status da carga ERP atual)

Autenticacao:
- `GET /auth/login`
- `GET /auth/callback`

## Importacao JSON do ERP

O catalogo le o JSON do ERP diretamente no backend (sem upload na pagina web).
Com `CATALOG_ERP_JSON_PATH` configurado para `D:/catalogo/pcprodut_20260309_115420.json`,
os produtos sao enriquecidos automaticamente por `Codigo`, incluindo itens sem foto
(com placeholder) e organizacao por categoria.
Categorias tecnicas (`CODEPTO/CODSEC`) sao convertidas para nomes comerciais
quando houver mapeamento configurado no backend.
Atualmente o catalogo padroniza em grupos de negocio como:
`ILUMINACAO DECORATIVA`, `ILUMINACAO TECNICA`, `ILUMINACAO EXTERNA E PUBLICA`,
`LAMPADAS E FITAS`, `COMPONENTES E ACESSORIOS`, `UTILIDADES E OPERACAO`
e `OUTROS ITENS ERP`.

Se precisar importar manualmente um novo payload pela API:

```powershell
curl -X POST http://127.0.0.1:8000/catalog/erp/import `
  -H "Content-Type: application/json" `
  -d "{\"products\":[{\"codigo\":\"1234\",\"nome\":\"Produto ERP\",\"categoria\":\"PENDENTE\"}]}"
```

Para receber um arquivo JSON bruto no backend (sem upload em formulario web):

```powershell
curl -X POST "http://127.0.0.1:8000/catalog/erp/upload?filename=pcprodut_20260309_115420.json" `
  -H "Content-Type: application/json" `
  --data-binary "@D:/Catalogo/pcprodut_20260309_115420.json"
```

Para processar um arquivo ja depositado no servidor:

```powershell
curl -X POST "http://127.0.0.1:8000/catalog/erp/import-file" `
  -H "Content-Type: application/json" `
  -d "{\"file_path\":\"reports/pcprodut_20260309_115420.json\"}"
```

## Estrutura do Projeto
```text
.
|-- app.py
|-- frontend/
|   |-- src/
|   |-- public/
|   |-- legacy/
|   `-- dist/ (gerado no build)
|-- catalog/
|   |-- bootstrap.py
|   |-- auth.py
|   |-- routes.py
|   |-- onedrive.py
|   |-- spreadsheet.py
|   |-- cadastro.py
|   |-- cache.py
|   |-- graph_client.py
|   |-- api/
|   |   |-- __init__.py
|   |   |-- router.py
|   |   `-- frontend.py
|   `-- core/
|       |-- __init__.py
|       `-- settings.py
`-- tests/
```

## Testes
```powershell
pytest -q
```

## Observacoes
- O frontend principal usa React Router + TanStack Query.
- O frontend legado permanece em `frontend/legacy` como fallback.
- Se credenciais Azure nao estiverem configuradas, rotas de fotos podem operar em modo local/alternativo.
