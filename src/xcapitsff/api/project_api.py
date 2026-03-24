"""API endpoints for Project Management."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from xcapitsff.discovery.project import ProjectManager, ProjectStatus, TaskStatus, project_manager

router = APIRouter(prefix="/projects", tags=["Projects"])


class CreateProjectRequest(BaseModel):
    client_name: str
    plan: str = "pro"
    tenant_id: str | None = None
    discovery_session_id: str | None = None
    milestones: list[dict] | None = None
    name: str = ""
    description: str = ""
    budget: float = 0
    start_date: str = ""
    end_date: str = ""


class AddTaskRequest(BaseModel):
    title: str
    description: str = ""
    assignee: str = "unassigned"
    priority: str = "medium"
    estimated_hours: float = 0
    milestone_id: str | None = None


class UpdateTaskStatusRequest(BaseModel):
    status: str  # todo, in_progress, review, done, blocked


@router.post("/", status_code=201)
async def create_project(req: CreateProjectRequest):
    project = project_manager.create_project(
        client_name=req.client_name,
        plan=req.plan,
        tenant_id=req.tenant_id,
        discovery_session_id=req.discovery_session_id,
        milestones_data=req.milestones,
        name=req.name,
        description=req.description,
        budget=req.budget,
        start_date=req.start_date,
        end_date=req.end_date,
    )
    return {"project_id": project.project_id, "client": project.client_name, "status": project.status.value}


@router.get("/")
async def list_projects(status: str | None = None):
    s = ProjectStatus(status) if status else None
    projects = project_manager.list_projects(status=s)
    return {
        "count": len(projects),
        "projects": [
            {
                "project_id": p.project_id,
                "client": p.client_name,
                "plan": p.plan,
                "status": p.status.value,
                "progress": p.progress,
                "tasks": len(p.tasks),
                "created_at": p.created_at.isoformat(),
            }
            for p in projects
        ],
    }


@router.get("/stats")
async def project_stats():
    return project_manager.get_stats()


@router.get("/{project_id}")
async def get_project(project_id: str):
    project = project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project_manager.get_project_report(project_id)


@router.post("/{project_id}/tasks")
async def add_task(project_id: str, req: AddTaskRequest):
    task = project_manager.add_task(
        project_id=project_id,
        title=req.title,
        description=req.description,
        assignee=req.assignee,
        priority=req.priority,
        estimated_hours=req.estimated_hours,
        milestone_id=req.milestone_id,
    )
    if not task:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"task_id": task.task_id, "title": task.title, "status": task.status.value, "milestone_id": task.milestone_id}


@router.patch("/{project_id}/tasks/{task_id}")
async def update_task(project_id: str, task_id: str, req: UpdateTaskStatusRequest):
    try:
        status = TaskStatus(req.status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {req.status}")
    success = project_manager.update_task_status(project_id, task_id, status)
    if not success:
        raise HTTPException(status_code=404, detail="Project or task not found")
    return {"task_id": task_id, "status": status.value}
