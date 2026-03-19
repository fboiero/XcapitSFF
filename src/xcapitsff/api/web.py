"""Web routes — serves the HTML dashboard via FastAPI HTMLResponse.

No separate frontend build is required. All HTML, CSS, and JS are inline.
Users can open http://localhost:8000/app to see the working dashboard.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse

from .web_assets import get_base_html

router = APIRouter(tags=["Web Dashboard"])


@router.get("/", include_in_schema=False)
async def landing():
    """Landing page — redirect to the main dashboard."""
    return RedirectResponse(url="/app", status_code=302)


@router.get("/app", response_class=HTMLResponse, include_in_schema=False)
async def dashboard_app():
    """Main dashboard — single-page application with sidebar navigation."""
    body = """
    <div class="app-layout">
        <!-- Sidebar -->
        <aside class="sidebar">
            <div class="sidebar-logo">
                <div class="logo-icon">X</div>
                <span class="logo-text">XcapitSFF</span>
            </div>

            <nav class="sidebar-nav">
                <div class="nav-section-title">Principal</div>
                <div class="nav-item active" data-section="dashboard" onclick="navigate('dashboard')">
                    <span class="nav-icon">&#127968;</span>
                    <span>Panel</span>
                </div>
                <div class="nav-item" data-section="leads" onclick="navigate('leads')">
                    <span class="nav-icon">&#128100;</span>
                    <span>Leads</span>
                </div>
                <div class="nav-item" data-section="tickets" onclick="navigate('tickets')">
                    <span class="nav-icon">&#127915;</span>
                    <span>Tickets</span>
                </div>
                <div class="nav-item" data-section="outreach" onclick="navigate('outreach')">
                    <span class="nav-icon">&#9993;</span>
                    <span>Outreach</span>
                </div>

                <div class="nav-section-title">Inteligencia</div>
                <div class="nav-item" data-section="analytics" onclick="navigate('analytics')">
                    <span class="nav-icon">&#128200;</span>
                    <span>Analytics</span>
                </div>
                <div class="nav-item" data-section="chat" onclick="navigate('chat')">
                    <span class="nav-icon">&#129302;</span>
                    <span>Asistente</span>
                </div>

                <div class="nav-section-title">Sistema</div>
                <div class="nav-item" data-section="settings" onclick="navigate('settings')">
                    <span class="nav-icon">&#9881;</span>
                    <span>Configuracion</span>
                </div>
            </nav>

            <div class="sidebar-footer">
                XcapitSFF v0.1.0<br>
                AI-powered SFF
            </div>
        </aside>

        <!-- Main Area -->
        <div class="main-area">
            <!-- Top Bar -->
            <header class="topbar">
                <div class="topbar-title" id="page-title">Panel Principal</div>
                <span class="topbar-badge badge-green" id="health-badge">&#9679; Salud: --%</span>
                <button class="topbar-icon-btn" title="Notificaciones" onclick="navigate('dashboard')">
                    &#128276;
                    <span class="notif-dot" id="notif-dot" style="display:none;"></span>
                </button>
                <button class="topbar-icon-btn" title="Actualizar" onclick="loadDashboard()">
                    &#128260;
                </button>
                <div class="topbar-avatar" title="Usuario">U</div>
            </header>

            <!-- Content -->
            <main class="content-area" id="main-content">
                <div class="loading-spinner">
                    <div class="spinner"></div>
                    Cargando panel...
                </div>
            </main>
        </div>
    </div>

    <!-- Floating Chat Button -->
    <button class="chat-fab" id="chat-fab" onclick="navigate('chat')" title="Asistente IA">
        &#128172;
    </button>
    """
    return HTMLResponse(content=get_base_html("XcapitSFF — Dashboard", body))


@router.get("/app/chat", response_class=HTMLResponse, include_in_schema=False)
async def chat_page():
    """Full-screen chat interface with the AI assistant."""
    body = """
    <div class="app-layout">
        <!-- Sidebar -->
        <aside class="sidebar">
            <div class="sidebar-logo">
                <div class="logo-icon">X</div>
                <span class="logo-text">XcapitSFF</span>
            </div>

            <nav class="sidebar-nav">
                <div class="nav-section-title">Principal</div>
                <div class="nav-item" data-section="dashboard" onclick="navigate('dashboard')">
                    <span class="nav-icon">&#127968;</span>
                    <span>Panel</span>
                </div>
                <div class="nav-item" data-section="leads" onclick="navigate('leads')">
                    <span class="nav-icon">&#128100;</span>
                    <span>Leads</span>
                </div>
                <div class="nav-item" data-section="tickets" onclick="navigate('tickets')">
                    <span class="nav-icon">&#127915;</span>
                    <span>Tickets</span>
                </div>
                <div class="nav-item" data-section="outreach" onclick="navigate('outreach')">
                    <span class="nav-icon">&#9993;</span>
                    <span>Outreach</span>
                </div>

                <div class="nav-section-title">Inteligencia</div>
                <div class="nav-item" data-section="analytics" onclick="navigate('analytics')">
                    <span class="nav-icon">&#128200;</span>
                    <span>Analytics</span>
                </div>
                <div class="nav-item active" data-section="chat" onclick="navigate('chat')">
                    <span class="nav-icon">&#129302;</span>
                    <span>Asistente</span>
                </div>

                <div class="nav-section-title">Sistema</div>
                <div class="nav-item" data-section="settings" onclick="navigate('settings')">
                    <span class="nav-icon">&#9881;</span>
                    <span>Configuracion</span>
                </div>
            </nav>

            <div class="sidebar-footer">
                XcapitSFF v0.1.0<br>
                AI-powered SFF
            </div>
        </aside>

        <!-- Main Area -->
        <div class="main-area">
            <!-- Top Bar -->
            <header class="topbar">
                <div class="topbar-title" id="page-title">Asistente IA</div>
                <span class="topbar-badge badge-green" id="health-badge">&#9679; Salud: --%</span>
                <button class="topbar-icon-btn" title="Notificaciones" onclick="navigate('dashboard')">
                    &#128276;
                    <span class="notif-dot" id="notif-dot" style="display:none;"></span>
                </button>
                <button class="topbar-icon-btn" title="Actualizar" onclick="loadDashboard()">
                    &#128260;
                </button>
                <div class="topbar-avatar" title="Usuario">U</div>
            </header>

            <!-- Content -->
            <main class="content-area" id="main-content">
                <div class="loading-spinner">
                    <div class="spinner"></div>
                    Cargando asistente...
                </div>
            </main>
        </div>
    </div>
    """

    return HTMLResponse(
        content=get_base_html("XcapitSFF — Asistente IA", body, initial_section="chat")
    )
