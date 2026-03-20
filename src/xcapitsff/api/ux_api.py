"""API endpoints for UX features — shortcuts, command palette, role dashboards."""

from fastapi import APIRouter, Query

from xcapitsff.selfservice.command_palette import command_palette
from xcapitsff.selfservice.keyboard_shortcuts import get_shortcuts_help, get_shortcuts_js
from xcapitsff.selfservice.role_dashboards import get_available_roles, get_dashboard_for_role, get_quick_actions_for_role

router = APIRouter(tags=["UX"])


# === Command Palette ===

@router.get("/command-palette/search")
async def search_commands(q: str = Query(default="", max_length=100)):
    """Search commands for the Ctrl+K palette."""
    results = command_palette.search(q)
    return {
        "query": q,
        "count": len(results),
        "results": [
            {
                "id": r.item_id,
                "title": r.title,
                "subtitle": r.subtitle,
                "category": r.category,
                "icon": r.icon,
                "action": r.action,
            }
            for r in results
        ],
    }


@router.post("/command-palette/execute/{command_id}")
async def execute_command(command_id: str):
    """Record command execution (for recent commands tracking)."""
    cmd = command_palette.execute(command_id)
    if not cmd:
        return {"status": "not_found"}
    return {"status": "executed", "action": cmd.action}


# === Keyboard Shortcuts ===

@router.get("/shortcuts")
async def get_shortcuts():
    """Get all keyboard shortcuts."""
    return get_shortcuts_help()


@router.get("/shortcuts/js")
async def get_shortcuts_javascript():
    """Get the JavaScript code for keyboard shortcut handling."""
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(get_shortcuts_js(), media_type="application/javascript")


# === Role Dashboards ===

@router.get("/dashboard-config/{role}")
async def get_role_dashboard(role: str):
    """Get dashboard configuration for a user role."""
    config = get_dashboard_for_role(role)
    return {
        "role": config.role,
        "title": config.title,
        "kpis": config.kpis,
        "sections": config.sections,
        "quick_actions": config.quick_actions,
        "refresh_interval": config.refresh_interval_seconds,
    }


@router.get("/dashboard-config")
async def list_dashboard_roles():
    """List available dashboard role configurations."""
    return {"roles": get_available_roles()}


@router.get("/quick-actions/{role}")
async def get_role_quick_actions(role: str):
    """Get quick actions for a specific role."""
    return {"role": role, "actions": get_quick_actions_for_role(role)}
