from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import traceback

from .spreadsheet import fetch_sheet
from . import catalog_router as router


@router.get('/items')
async def list_items():
    # placeholder endpoint, same as before
    return []


@router.get('/sheet')
async def sheet_data(url: str | None = None):
    """Return JSON data from a Google Sheet specified by query parameter `url`."""
    if not url:
        # mimic previous Flask error shape so tests continue to pass
        return JSONResponse(status_code=400, content={"error": "missing url query parameter"})
    try:
        df = fetch_sheet(url)
        return df.to_dict(orient='records')
    except Exception as e:
        print(f"Error fetching sheet: {e}")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get('/photos')
async def photos(shareUrl: str | None = None, code: str | None = None):
    """Return categorized photo URLs from a shared OneDrive folder.

    Query parameters:
        shareUrl: public share link to the OneDrive folder (required)
        code: optional product code to filter filenames
    """
    if not shareUrl:
        return JSONResponse(status_code=400, content={"error": "missing shareUrl query parameter"})
    try:
        from .onedrive import list_shared_items, categorize_photos

        items = list_shared_items(shareUrl)
        cats = categorize_photos(items, code=code)
        return cats
    # the graph client/auth helpers may throw either EnvironmentError or
    # ValueError when configuration is missing or invalid; treat both as a
    # non-fatal "photos disabled" scenario so front-end can use placeholders.
    except (EnvironmentError, ValueError) as e:
        print(f"Photos disabled (environment issue): {e}")
        traceback.print_exc()
        demo = {
            "white_background": "https://placehold.co/150x150?text=Branco",
            "ambient": "https://placehold.co/150x150?text=Ambient",
            "measures": "https://placehold.co/150x150?text=Medidas",
        }
        # If a code is passed, embed it as text for clarity
        if code:
            demo = {k: v + f"+{code}" for k, v in demo.items()}
        return demo
    except Exception as e:
        print(f"Error fetching photos: {e}")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get('/produtos/{codigo}/imagens')
async def product_images(codigo: str, shareUrl: str | None = None):
    """Return all image variants for a given product code.

    Query parameters:
        shareUrl: public share link for the root OneDrive folder (required)
    """
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
