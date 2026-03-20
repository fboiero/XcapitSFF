"""Keyboard Shortcuts — power user productivity.

Defines keyboard shortcuts that the web frontend implements.
This module provides the shortcut definitions and help text.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Shortcut:
    key: str  # e.g., "Ctrl+K", "G then L"
    action: str
    description: str
    category: str  # navigation, actions, views


SHORTCUTS: list[Shortcut] = [
    # Navigation
    Shortcut("G then D", "navigate('dashboard')", "Ir al Dashboard", "navigation"),
    Shortcut("G then L", "navigate('leads')", "Ir a Leads", "navigation"),
    Shortcut("G then T", "navigate('tickets')", "Ir a Tickets", "navigation"),
    Shortcut("G then O", "navigate('outreach')", "Ir a Outreach", "navigation"),
    Shortcut("G then A", "navigate('analytics')", "Ir a Analytics", "navigation"),
    Shortcut("G then S", "navigate('settings')", "Ir a Settings", "navigation"),

    # Actions
    Shortcut("C then L", "openForm('create_lead')", "Crear nuevo lead", "actions"),
    Shortcut("C then T", "openForm('create_ticket')", "Crear nuevo ticket", "actions"),
    Shortcut("C then O", "openForm('compose_outreach')", "Componer outreach", "actions"),
    Shortcut("C then M", "openForm('schedule_meeting')", "Agendar reunión", "actions"),

    # Search & Chat
    Shortcut("Ctrl+K", "openSearch()", "Búsqueda rápida", "search"),
    Shortcut("/", "openChat()", "Abrir chat con asistente", "search"),
    Shortcut("Escape", "closeModal()", "Cerrar modal/chat", "search"),

    # Views
    Shortcut("V then K", "navigate('kanban')", "Ver Kanban", "views"),
    Shortcut("V then F", "navigate('funnel')", "Ver Funnel", "views"),
    Shortcut("V then I", "navigate('inbox')", "Ver Inbox", "views"),
    Shortcut("V then H", "navigate('health')", "Ver Health Score", "views"),

    # Quick actions
    Shortcut("?", "showShortcuts()", "Mostrar atajos de teclado", "help"),
    Shortcut("R", "refreshData()", "Refrescar datos", "actions"),
]


def get_shortcuts(category: str | None = None) -> list[Shortcut]:
    if category:
        return [s for s in SHORTCUTS if s.category == category]
    return list(SHORTCUTS)


def get_shortcuts_help() -> dict:
    """Formatted help for the shortcuts modal."""
    categories = {}
    for s in SHORTCUTS:
        if s.category not in categories:
            categories[s.category] = []
        categories[s.category].append({
            "key": s.key,
            "description": s.description,
        })
    return {
        "title": "Atajos de Teclado",
        "categories": categories,
    }


def get_shortcuts_js() -> str:
    """Generate JavaScript for keyboard shortcut handling."""
    return """
// Keyboard shortcuts
let shortcutBuffer = '';
let shortcutTimeout = null;

document.addEventListener('keydown', (e) => {
    // Don't capture if typing in input/textarea
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return;

    const key = e.key.toLowerCase();

    // Special shortcuts
    if (e.ctrlKey && key === 'k') { e.preventDefault(); openSearch(); return; }
    if (key === '/' && !e.ctrlKey) { e.preventDefault(); openChat(); return; }
    if (key === 'escape') { closeModal(); return; }
    if (key === '?') { showShortcuts(); return; }
    if (key === 'r' && !e.ctrlKey) { refreshData(); return; }

    // Two-key sequences (G then D, C then L, V then K)
    clearTimeout(shortcutTimeout);
    shortcutBuffer += key;
    shortcutTimeout = setTimeout(() => { shortcutBuffer = ''; }, 500);

    const shortcuts = {
        'gd': () => navigate('dashboard'),
        'gl': () => navigate('leads'),
        'gt': () => navigate('tickets'),
        'go': () => navigate('outreach'),
        'ga': () => navigate('analytics'),
        'gs': () => navigate('settings'),
        'cl': () => openForm('create_lead'),
        'ct': () => openForm('create_ticket'),
        'co': () => openForm('compose_outreach'),
        'cm': () => openForm('schedule_meeting'),
        'vk': () => navigate('kanban'),
        'vf': () => navigate('funnel'),
        'vi': () => navigate('inbox'),
        'vh': () => navigate('health'),
    };

    if (shortcuts[shortcutBuffer]) {
        shortcuts[shortcutBuffer]();
        shortcutBuffer = '';
    }
});
"""
