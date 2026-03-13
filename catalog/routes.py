from io import BytesIO
from pathlib import Path
import traceback

from fastapi import APIRouter, Body, Request
from fastapi.responses import FileResponse, JSONResponse, Response

from .spreadsheet import fetch_sheet


router = APIRouter()


def _tiff_to_jpeg_bytes(asset_path: str) -> bytes | None:
    """Converte formatos raster locais para bytes JPEG para compatibilidade no navegador."""
    ext = Path(asset_path).suffix.lower()
    if ext not in {".tif", ".tiff", ".psd", ".heic", ".heif"}:
        return None

    try:
        from PIL import Image
    except Exception:
        # Pillow e opcional; se indisponivel, mantem resposta original.
        return None

    try:
        with Image.open(asset_path) as image:
            # Achata transparencia sobre fundo branco para compatibilidade com JPEG.
            if image.mode in ("RGBA", "LA"):
                background = Image.new("RGB", image.size, (255, 255, 255))
                alpha = image.split()[-1]
                background.paste(image.convert("RGB"), mask=alpha)
                converted = background
            else:
                converted = image.convert("RGB") if image.mode != "RGB" else image

            output = BytesIO()
            converted.save(output, format="JPEG", quality=88, optimize=True)
            return output.getvalue()
    except Exception:
        return None


@router.get("/items")
async def list_items():
    return []


@router.get("/sheet")
async def sheet_data(url: str | None = None):
    """Retorna dados JSON de uma planilha Google via parametro de consulta `url`."""
    if not url:
        return JSONResponse(status_code=400, content={"error": "missing url query parameter"})
    try:
        df = fetch_sheet(url)
        return df.to_dict(orient="records")
    except ValueError as e:
        print(f"Sheet fetch failed, trying local fallback: {e}")
        traceback.print_exc()
        try:
            from .onedrive import list_local_products

            local_products = list_local_products()
            if local_products:
                return local_products
        except Exception as local_exc:
            print(f"Local products fallback failed: {local_exc}")
            traceback.print_exc()
        return []
    except Exception as e:
        print(f"Error fetching sheet: {e}")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/photos")
async def photos(shareUrl: str | None = None, code: str | None = None):
    """Retorna URLs de fotos categorizadas do OneDrive local ou Microsoft Graph."""
    if code:
        try:
            from .onedrive import categorize_local_photos, resolve_local_products_root

            local_photos = categorize_local_photos(code=code)
            if any(local_photos.values()):
                return local_photos
            # Se existir raiz local de produtos, permanece em modo local e evita
            # chamadas ao Graph quando as credenciais Azure nao estiverem configuradas.
            if resolve_local_products_root():
                return local_photos
        except Exception as local_exc:
            print(f"Local photo lookup failed, trying Graph: {local_exc}")
            traceback.print_exc()

    if not shareUrl:
        return JSONResponse(status_code=400, content={"error": "missing shareUrl query parameter"})
    try:
        from .onedrive import list_shared_items, categorize_photos

        items = list_shared_items(shareUrl)
        return categorize_photos(items, code=code)
    except (EnvironmentError, ValueError) as e:
        print(f"Photos disabled (environment issue): {e}")
        traceback.print_exc()
        demo = {
            "white_background": "https://placehold.co/150x150?text=Branco",
            "ambient": "https://placehold.co/150x150?text=Ambient",
            "measures": "https://placehold.co/150x150?text=Medidas",
        }
        if code:
            demo = {k: v + f"+{code}" for k, v in demo.items()}
        return demo
    except Exception as e:
        print(f"Error fetching photos: {e}")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/local/produtos")
async def local_products():
    """Retorna produtos encontrados na pasta local do OneDrive."""
    try:
        from .onedrive import list_local_products

        return list_local_products()
    except Exception as e:
        print(f"Error loading local products: {e}")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/erp/import")
async def import_erp_products(payload: dict | list = Body(...)):
    """Importa um payload JSON do ERP e atualiza o espelho de produtos por codigo."""
    try:
        from .erp_catalog import import_erp_payload

        return import_erp_payload(payload)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    except Exception as e:
        print(f"Error importing ERP payload: {e}")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/erp/upload")
async def upload_erp_file(request: Request, filename: str | None = None):
    """Recebe um arquivo JSON bruto no corpo da requisicao e importa para o catalogo."""
    try:
        body = await request.body()
        if not body:
            return JSONResponse(status_code=400, content={"error": "empty request body"})

        selected_name = (
            filename
            or request.headers.get("x-file-name")
            or request.headers.get("x-filename")
            or "erp_upload.json"
        )

        from .erp_catalog import receive_erp_file

        return receive_erp_file(filename=selected_name, content=body)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    except Exception as e:
        print(f"Error uploading ERP file: {e}")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/erp/import-file")
async def import_erp_file_from_backend(payload: dict = Body(...)):
    """Importa um arquivo JSON ja depositado no backend."""
    try:
        file_path = str(payload.get("file_path") or payload.get("path") or "").strip()
        if not file_path:
            return JSONResponse(status_code=400, content={"error": "missing file_path"})

        from .erp_catalog import import_erp_file

        return import_erp_file(file_path)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    except Exception as e:
        print(f"Error importing ERP file from backend: {e}")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/erp/files")
async def list_backend_erp_files():
    """Lista os arquivos JSON do ERP encontrados na infraestrutura local do backend."""
    try:
        from .erp_catalog import list_erp_files

        return {"files": list_erp_files()}
    except Exception as e:
        print(f"Error listing ERP files: {e}")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/erp/status")
async def erp_status():
    """Retorna status da carga JSON do ERP utilizada para enriquecer o catalogo."""
    try:
        from .erp_catalog import get_erp_status

        return get_erp_status()
    except Exception as e:
        print(f"Error reading ERP status: {e}")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/export")
async def export_catalog(
    format: str = "csv",
    query: str | None = None,
    category: str | None = None,
    code: str | None = None,
):
    """Gera uma exportacao do catalogo em CSV, Excel, JSON, PDF ou ZIP."""
    try:
        from .exporter import build_catalog_export

        payload, media_type, filename = build_catalog_export(
            format_name=format,
            query=str(query or "").strip(),
            category=str(category or "").strip(),
            code=str(code or "").strip(),
        )
        return Response(
            content=payload,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-store",
            },
        )
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    except Exception as e:
        print(f"Error exporting catalog: {e}")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/local/asset")
async def local_asset(path: str | None = None):
    """Serve um arquivo de imagem local da pasta de produtos configurada no OneDrive."""
    if not path:
        return JSONResponse(status_code=400, content={"error": "missing path query parameter"})
    try:
        from .onedrive import resolve_local_asset_path

        asset_path = resolve_local_asset_path(path)
        if not asset_path:
            return JSONResponse(status_code=404, content={"error": "asset not found"})

        converted = _tiff_to_jpeg_bytes(asset_path)
        if converted is not None:
            return Response(content=converted, media_type="image/jpeg")

        return FileResponse(asset_path)
    except Exception as e:
        print(f"Error serving local asset: {e}")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/produtos/{codigo}/imagens")
async def product_images(codigo: str, shareUrl: str | None = None):
    """Retorna todas as variacoes de imagem para um codigo de produto."""
    try:
        from .onedrive import find_local_images_for_code, resolve_local_products_root

        local_images = find_local_images_for_code(codigo)
        if local_images or resolve_local_products_root():
            return {"codigo": codigo, "imagens": local_images}
    except Exception as local_exc:
        print(f"Local image lookup failed, trying Graph: {local_exc}")
        traceback.print_exc()

    if not shareUrl:
        return JSONResponse(status_code=400, content={"error": "missing shareUrl query parameter"})
    try:
        from .onedrive import find_images_for_code

        images = find_images_for_code(shareUrl, codigo)
        return {"codigo": codigo, "imagens": images}
    except Exception as e:
        print(f"Error searching images: {e}")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})
