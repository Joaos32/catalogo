# Catálogo Project

Este é um projeto Python para catalogar itens usando fotos do OneDrive e informações de uma planilha online.

## Setup

> O backend foi migrado para FastAPI; as instruções abaixo refletirão essa mudança.
> ⚠️ **Python must be installed and available in your PATH.**
1. Crie e ative um ambiente virtual (importante para evitar imports faltando):
   ```sh
   python -m venv venv
   .\venv\Scripts\activate     # PowerShell
   # ou: venv\Scripts\activate.bat  # CMD
   ```
2. Instale dependências:
   ```sh
   pip install -r requirements.txt
   ```

Se você não ativar o venv **e** usar um comando genérico como `py app.py`, o
Python do sistema será utilizado. Isso acarretará erro de módulo ausente, já que
as dependências estão instaladas apenas no ambiente virtual. Use um destes
comandos dentro do venv:

```powershell
cd d:\Catalogo
.\venv\Scripts\activate
python app.py      # executa via uvicorn internamente
```

ou, quando quiser rodar diretamente o ASGI server:

```powershell
uvicorn app:app --reload      # recarrega automaticamente ao editar código
```

Alternativamente você pode chamar explicitamente o interpretador do venv:

```powershell
& "d:\Catalogo\venv\Scripts\python.exe" app.py
```

## Estrutura

O frontend continua em `frontend/`, servido estaticamente pelo FastAPI.
A API agora utiliza `fastapi` e a organização do pacote `catalog` não mudou.

- `app.py`: aplicação FastAPI principal (substituiu o Flask). The file also mounts the `catalog` router and serves static frontend files.
- `catalog/`: módulos do projeto.
  - `spreadsheet.py`: utilitários para carregar Google Sheets
  - `onedrive.py`: stubs para integração com OneDrive

## Exemplos de uso

Após iniciar o servidor (`python app.py` ou `uvicorn app:app`), você pode
acessar endpoints (as rotas permanecem iguais às da versão Flask):

- `GET /` – verifica se a API está no ar. O front-end React também é
  servido aqui, mas a porta padrão agora é **8000** quando o servidor é
  iniciado com uvicorn (ex. `http://127.0.0.1:8000/`).
- `GET /catalog/sheet?url=<SHEET_URL>` – busca os dados de uma planilha pública do Google (observe que o blueprint está vinculado ao prefixo `/catalog`).
  - Exemplo:
    ```sh
    curl "http://127.0.0.1:5000/catalog/sheet?url=https://docs.google.com/spreadsheets/d/14C-BtunMb82fYNwjsulbyqLgBFwrXbrzFh2XCdevvoM/edit?usp=sharing"
    ```
    O resultado será um JSON com as linhas da planilha.
- `GET /catalog/photos` – retorna URLs categorizadas (fundo branco, ambientação, medidas) a partir de um link compartilhado e código de produto.


## Frontend React (sem Node.js necessário)

*A única diferença é a porta de operação do backend; CORS e comportamento da
SPA continuam iguais.*

### CORS e execução em portas distintas

O FastAPI inclui o middleware CORSMiddleware, e `app.py` já o adiciona com
`allow_origins=["*"]` se a dependência estiver instalada. As mesmas instruções
de ativar o venv e garantir que o pacote `fastapi` (e `uvicorn`) estejam
instalados continuam válidas.

Se você servir `frontend/` com `python -m http.server 3000` ou outro servidor
estático, o browser fará requisições para `http://127.0.0.1:8000` (backend). Isso
é considerado "cross‑origin" e só funciona se o FastAPI retornar o cabeçalho
`Access-Control-Allow-Origin`. O projeto adiciona automaticamente o
`CORSMiddleware` quando o pacote está disponível no ambiente. **Por isso é
crítico rodar o servidor usando o Python do venv onde `fastapi` e
`uvicorn` foram instalados**; caso contrário o backend responderá sem o
cabeçalho e o navegador bloqueará a requisição.

Você pode testar manualmente com `curl`:

```powershell
curl -i -H "Origin: http://localhost:3000" \
    "http://127.0.0.1:5000/catalog/sheet?url=<SHEET_URL>"
```

Se o `flask-cors` estiver ativo, a resposta conterá:
```
Access-Control-Allow-Origin: *
```
Caso contrário, a linha estará ausente e o navegador recusará a requisição.

---

Os arquivos estáticos do front-end estão em `frontend/`. A aplicação React usa CDN
para não precisar instalar Node/webpack. Para testar:

```powershell
python app.py    # inicia o servidor FastAPI via uvicorn (porta 8000 por padrão)
# abra http://127.0.0.1:8000/ no navegador
```

Se preferir servir diretamente os arquivos sem o backend, inicie um servidor HTTP simples:

```powershell
cd frontend
py -m http.server 3000
# acesse http://localhost:3000/ (o backend precisa estar em execução à parte em 8000)
```

> ⚠️ **Importante**: nesse modo estático o front-end **não executa o servidor
> Flask automaticamente**. Você precisa abrir outro terminal e iniciar o
> backend (`python app.py` dentro do venv) para que as chamadas a
> `/catalog/...` funcionem. Se o Flask não estiver em execução, o servidor
> estático responderá com 404 (como mostrado no log que você enviou).
>
> A aplicação tenta automaticamente usar `http://127.0.0.1:5000` quando detecta
> que está em `localhost:3000`, mas isso só é útil se o Flask estiver ativo.
>
> > 🤫 As versões mais recentes da interface não disparam mensagens vermelhas no
> > console quando a planilha ou as fotos falham de carregar. Se o back-end não
> > responder ou devolver um 500, ele é convertido em dados de demonstração ou em
> > imagens de placeholder; assim você pode testar o layout sem ``noise`` do
> > DevTools.
>
> ➤ **Nota adicional**: sempre reinicie o servidor Flask após alterar o
> código (por exemplo, ao modificar `routes.py` ou `onedrive.py`). Caso contrário
> você continuará a ver erros antigos no console que já foram corrigidos (por
> exemplo, o 500 Internal Server Error para fotos, que agora retorna placeholders).
> Use `CTRL+C` no terminal onde o Flask roda e execute novamente `python app.py`.


A interface é responsiva e adequada para web, tablets e celulares.

### Fotos de Produto

Para que cada cartão faça download das imagens correspondentes, o front-end
automaticamente consulta o endpoint `/catalog/photos` usando um link compartilhado
da pasta do OneDrive (configurado no código em `app.js`). Ele passa o campo
`Codigo` de cada produto, que deve existir na planilha ou ser gerado localmente
como o `id`. As três categorias retornadas são exibidas como miniaturas abaixo do
card (fundo branco, ambientação e medidas).
## OneDrive (Microsoft Graph)

A funcionalidade de fotos depende da API do Microsoft Graph. Para habilitá-la:

1. Registre um app no [Azure Portal](https://portal.azure.com) e anote `client_id`,
   `tenant_id` e gere um `client_secret`.
2. Defina variáveis de ambiente no host:
   ```powershell
   $env:AZURE_CLIENT_ID = "..."
   $env:AZURE_TENANT_ID = "..."
   $env:AZURE_CLIENT_SECRET = "..."
   ```
   **Observação**: caso esses valores não estejam definidos o serviço ainda
   iniciará e o endpoint `/catalog/photos` responderá com URLs de imagem de
   placeholder em vez de lançar um erro de servidor. Isso permite testar o
   layout e verificar os cartões mesmo sem acesso ao OneDrive; as fotos reais
   aparecerão assim que as credenciais do Azure forem fornecidas.

3. Para um link de pasta compartilhada do OneDrive fornecido pela empresa, você
   pode chamar o endpoint `/catalog/photos` passando `shareUrl` e (opcionalmente)
   um `code` de produto. O servidor fará a seleção automática de até três fotos:
   
   - `white_background`: imagem com fundo branco (nome contém "branco"/"white")
   - `ambient`: imagem em ambiente (nome contém "ambient"/"ambiente")
   - `measures`: fundo branco com medidas (nome contém "medida"/"measure")

   Exemplo de uso:
   ```sh
   curl "http://127.0.0.1:5000/catalog/photos?shareUrl=https://1drv.ms/f/c/..." \
        -G --data-urlencode "code=XYZ123"
   ```
   Retornará um JSON com as URLs das imagens correspondentes.

## Próximos passos

- Manuseio de erros e caching.
- Adicionar autenticação/endpoints para uso no front‑end.
