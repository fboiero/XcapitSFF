"""Web routes -- serves the HTML dashboard via FastAPI HTMLResponse.

No separate frontend build is required. All HTML, CSS, and JS are inline.
Users can open http://localhost:8000/app to see the working dashboard.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse

from .web_assets import get_base_html

router = APIRouter(tags=["Web Dashboard"])


@router.get("/", include_in_schema=False)
async def landing():
    """Landing page -- redirect to the main dashboard."""
    return RedirectResponse(url="/app", status_code=302)


@router.get("/app", response_class=HTMLResponse, include_in_schema=False)
async def dashboard_app():
    """Main dashboard -- single-page application with sidebar navigation."""
    return HTMLResponse(content=get_base_html("XcapitSFF", initial_section="dashboard"))


@router.get("/app/chat", response_class=HTMLResponse, include_in_schema=False)
async def chat_page():
    """Full-screen chat interface with the AI assistant."""
    return HTMLResponse(content=get_base_html("XcapitSFF", initial_section="chat"))


@router.get("/app/{section}", response_class=HTMLResponse, include_in_schema=False)
async def app_section(section: str):
    """Deep-link to a specific section of the SPA."""
    return HTMLResponse(content=get_base_html("XcapitSFF", initial_section=section))
