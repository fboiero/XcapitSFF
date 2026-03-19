"""API endpoints for Quickstart and Notification Preferences."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from xcapitsff.selfservice.quickstart import quickstart_manager
from xcapitsff.selfservice.notifications_preferences import notif_prefs

router = APIRouter(tags=["Self-Service"])


# === Quickstart ===

@router.post("/quickstart/start")
async def start_quickstart(tenant_id: str = "default"):
    progress = quickstart_manager.start(tenant_id)
    return quickstart_manager.get_summary(tenant_id)


@router.get("/quickstart/actions")
async def get_quickstart_actions(category: str | None = None):
    actions = quickstart_manager.get_actions(category)
    return {
        "count": len(actions),
        "actions": [
            {
                "action_id": a.action_id,
                "title": a.title,
                "description": a.description,
                "category": a.category,
                "estimated_seconds": a.estimated_seconds,
                "endpoint": a.api_endpoint,
                "method": a.api_method,
                "result": a.result_description,
            }
            for a in actions
        ],
    }


@router.get("/quickstart/next")
async def get_next_action(tenant_id: str = "default"):
    action = quickstart_manager.get_next_action(tenant_id)
    if not action:
        return {"message": "¡Completaste todas las acciones! 🎉", "next": None}
    return {
        "action_id": action.action_id,
        "title": action.title,
        "description": action.description,
        "endpoint": action.api_endpoint,
        "method": action.api_method,
        "body": action.api_body,
    }


@router.post("/quickstart/complete/{action_id}")
async def complete_quickstart_action(action_id: str, tenant_id: str = "default"):
    progress = quickstart_manager.complete_action(tenant_id, action_id)
    return quickstart_manager.get_summary(tenant_id)


@router.get("/quickstart/progress")
async def get_quickstart_progress(tenant_id: str = "default"):
    return quickstart_manager.get_summary(tenant_id)


# === Notification Preferences ===

class UpdatePrefRequest(BaseModel):
    channel: str | None = None
    frequency: str | None = None
    enabled: bool | None = None


@router.get("/preferences/notifications")
async def get_notification_prefs(user_id: str = "default"):
    prefs = notif_prefs.get_preferences(user_id)
    return {
        "user_id": user_id,
        "preferences": [
            {
                "event_type": p.event_type,
                "label": p.label,
                "channel": p.channel.value,
                "frequency": p.frequency.value,
                "enabled": p.enabled,
            }
            for p in prefs
        ],
    }


@router.patch("/preferences/notifications/{event_type}")
async def update_notification_pref(
    event_type: str, req: UpdatePrefRequest, user_id: str = "default"
):
    pref = notif_prefs.update_preference(
        user_id, event_type, req.channel, req.frequency, req.enabled,
    )
    if not pref:
        raise HTTPException(status_code=404, detail="Preference not found")
    return {
        "event_type": pref.event_type,
        "channel": pref.channel.value,
        "frequency": pref.frequency.value,
        "enabled": pref.enabled,
    }


@router.post("/preferences/notifications/mute-all")
async def mute_all_notifications(user_id: str = "default"):
    notif_prefs.mute_all(user_id)
    return {"status": "all notifications muted"}


@router.post("/preferences/notifications/reset")
async def reset_notification_prefs(user_id: str = "default"):
    prefs = notif_prefs.reset_to_defaults(user_id)
    return {"status": "reset to defaults", "count": len(prefs)}
