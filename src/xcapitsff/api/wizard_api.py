"""API endpoints for the self-service Setup Wizard, templates, and tutorials."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from xcapitsff.selfservice.templates_catalog import TemplateCatalog
from xcapitsff.selfservice.tutorials import TutorialManager
from xcapitsff.selfservice.wizard import SetupWizard

router = APIRouter(tags=["Wizard"])

# ---------------------------------------------------------------------------
# Shared instances (in production these would be injected via DI)
# ---------------------------------------------------------------------------

_wizard = SetupWizard()
_catalog = TemplateCatalog()
_tutorials = TutorialManager()


def get_wizard() -> SetupWizard:
    return _wizard


def get_catalog() -> TemplateCatalog:
    return _catalog


def get_tutorial_manager() -> TutorialManager:
    return _tutorials


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class StartWizardRequest(BaseModel):
    tenant_id: str


class SubmitStepRequest(BaseModel):
    tenant_id: str
    step_id: str
    data: dict


class SkipStepRequest(BaseModel):
    tenant_id: str
    step_id: str


class GoBackRequest(BaseModel):
    tenant_id: str


class CompleteWizardRequest(BaseModel):
    tenant_id: str


class ApplyTemplateRequest(BaseModel):
    tenant_id: str


class StartTutorialRequest(BaseModel):
    tenant_id: str


# ---------------------------------------------------------------------------
# Wizard endpoints
# ---------------------------------------------------------------------------


@router.post("/wizard/start")
async def api_start_wizard(req: StartWizardRequest):
    """Start the setup wizard for a tenant."""
    progress = _wizard.start_wizard(req.tenant_id)
    return {
        "tenant_id": progress.tenant_id,
        "current_step": progress.current_step,
        "started_at": progress.started_at,
    }


@router.get("/wizard/current")
async def api_get_current_step(tenant_id: str):
    """Get the current wizard step for a tenant."""
    try:
        step = _wizard.get_current_step(tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {
        "step_id": step.step_id,
        "title": step.title,
        "description": step.description,
        "type": step.type,
        "is_completed": step.is_completed,
        "is_skippable": step.is_skippable,
        "fields": [
            {
                "name": f.name,
                "label": f.label,
                "type": f.type,
                "required": f.required,
                "options": f.options,
                "default": f.default,
                "help_text": f.help_text,
            }
            for f in step.fields
        ],
    }


@router.post("/wizard/submit")
async def api_submit_step(req: SubmitStepRequest):
    """Submit data for the current wizard step."""
    try:
        progress = _wizard.submit_step(req.tenant_id, req.step_id, req.data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "tenant_id": progress.tenant_id,
        "current_step": progress.current_step,
        "completed_steps": progress.completed_steps,
        "skipped_steps": progress.skipped_steps,
    }


@router.post("/wizard/skip")
async def api_skip_step(req: SkipStepRequest):
    """Skip the current wizard step."""
    try:
        progress = _wizard.skip_step(req.tenant_id, req.step_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "tenant_id": progress.tenant_id,
        "current_step": progress.current_step,
        "completed_steps": progress.completed_steps,
        "skipped_steps": progress.skipped_steps,
    }


@router.post("/wizard/back")
async def api_go_back(req: GoBackRequest):
    """Go back to the previous wizard step."""
    try:
        progress = _wizard.go_back(req.tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "tenant_id": progress.tenant_id,
        "current_step": progress.current_step,
        "completed_steps": progress.completed_steps,
    }


@router.get("/wizard/progress")
async def api_get_progress(tenant_id: str):
    """Get the overall wizard progress for a tenant."""
    try:
        progress = _wizard.get_progress(tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {
        "tenant_id": progress.tenant_id,
        "current_step": progress.current_step,
        "completed_steps": progress.completed_steps,
        "skipped_steps": progress.skipped_steps,
        "started_at": progress.started_at,
        "completed_at": progress.completed_at,
        "configuration": progress.configuration,
    }


@router.post("/wizard/complete")
async def api_complete_wizard(req: CompleteWizardRequest):
    """Finalize the wizard and apply all configuration."""
    try:
        result = _wizard.complete_wizard(req.tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


# ---------------------------------------------------------------------------
# Template endpoints
# ---------------------------------------------------------------------------


@router.get("/wizard/templates")
async def api_list_templates():
    """List all available industry templates."""
    templates = _catalog.list_templates()
    return [
        {
            "template_id": t.template_id,
            "name": t.name,
            "description": t.description,
            "industry": t.industry,
            "recommended_plan": t.recommended_plan,
            "features_enabled": t.features_enabled,
        }
        for t in templates
    ]


@router.post("/wizard/templates/{template_id}/apply")
async def api_apply_template(template_id: str, req: ApplyTemplateRequest):
    """Apply an industry template to a tenant."""
    try:
        result = _catalog.apply_template(req.tenant_id, template_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result


# ---------------------------------------------------------------------------
# Tutorial endpoints
# ---------------------------------------------------------------------------


@router.get("/tutorials")
async def api_list_tutorials(audience: str | None = None):
    """List available tutorials, optionally filtered by audience."""
    tutorials = _tutorials.list_tutorials(audience=audience)
    return [
        {
            "tutorial_id": t.tutorial_id,
            "name": t.name,
            "description": t.description,
            "target_audience": t.target_audience,
            "estimated_minutes": t.estimated_minutes,
            "steps_count": len(t.steps),
        }
        for t in tutorials
    ]


@router.post("/tutorials/{tutorial_id}/start")
async def api_start_tutorial(tutorial_id: str, req: StartTutorialRequest):
    """Start a tutorial for a tenant."""
    try:
        tutorial = _tutorials.start_tutorial(req.tenant_id, tutorial_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {
        "tutorial_id": tutorial.tutorial_id,
        "name": tutorial.name,
        "steps": [
            {
                "step_number": s.step_number,
                "title": s.title,
                "description": s.description,
                "action": s.action,
                "highlight_element": s.highlight_element,
                "completed": s.completed,
            }
            for s in tutorial.steps
        ],
    }


@router.post("/tutorials/{tutorial_id}/step/{step_number}/complete")
async def api_complete_tutorial_step(
    tutorial_id: str, step_number: int, req: StartTutorialRequest
):
    """Mark a tutorial step as completed."""
    try:
        tutorial = _tutorials.complete_step(req.tenant_id, tutorial_id, step_number)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "tutorial_id": tutorial.tutorial_id,
        "steps": [
            {
                "step_number": s.step_number,
                "title": s.title,
                "completed": s.completed,
            }
            for s in tutorial.steps
        ],
    }


@router.get("/tutorials/progress")
async def api_tutorial_progress(tenant_id: str):
    """Get tutorial completion progress for a tenant."""
    return _tutorials.get_progress(tenant_id)
