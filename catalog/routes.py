from io import BytesIO
from pathlib import Path

from fastapi.responses import JSONResponse, FileResponse, Response
import traceback

from .spreadsheet import fetch_sheet
from . import catalog_router as router


def _tiff_to_jpeg_bytes(asset_path: str) -> bytes | None:
    """Convert TIFF files to JPEG bytes so browsers can render them reliably."""
    ext = Path(asset_path).suffix.lower()
    if ext not in {".tif", ".tiff"}:
        return None

    try:
        from PIL import Image
    except Exception:
        # Pillow is optional; if unavailable, keep original response path.
        return None

    try:
        with Image.open(asset_path) as image:
            # Flatten transparency onto white for JPEG compatibility.
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
    """Return JSON data from a Google Sheet specified by query parameter `url`."""
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
    """Return categorized photo URLs from local OneDrive or Microsoft Graph."""
    if code:
        try:
            from .onedrive import categorize_local_photos, resolve_local_products_root

            local_photos = categorize_local_photos(code=code)
            if any(local_photos.values()):
                return local_photos
            # If a local products root exists, stay in local mode and avoid Graph
            # calls when Azure credentials are not configured.
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
    """Return products discovered from the local OneDrive folder."""
    try:
        from .onedrive import list_local_products

        return list_local_products()
    except Exception as e:
        print(f"Error loading local products: {e}")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/local/asset")
async def local_asset(path: str | None = None):
    """Serve a local image file from the configured OneDrive products folder."""
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
    """Return all image variants for a given product code."""
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
