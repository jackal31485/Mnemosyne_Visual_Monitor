from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

_BROWSER_HTML = (
    Path(__file__).resolve().parent.parent.parent / "ui" / "browser.html"
)


@router.get("/browser/")
@router.get("/browser.html")
def browser() -> HTMLResponse:
    return HTMLResponse(
        content=_BROWSER_HTML.read_text(encoding="utf-8")
    )
