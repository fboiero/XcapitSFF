"""Project Management — track client projects post-sale.

Each client project has phases, milestones, tasks, and status tracking.
This enables the PM agent to monitor progress and report to clients.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class ProjectStatus(str, Enum):
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    BLOCKED = "blocked"


@dataclass
class ProjectTask:
    task_id: str
    title: str
    description: str
    assignee: str  # agent or human
    status: TaskStatus = TaskStatus.TODO
    priority: str = "medium"  # high, medium, low
    estimated_hours: float = 0
    actual_hours: float = 0
    due_date: datetime | None = None
    completed_at: datetime | None = None
    dependencies: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    milestone_id: str | None = None  # link to milestone


@dataclass
class Milestone:
    milestone_id: str
    name: str
    description: str
    due_date: datetime
    tasks: list[str] = field(default_factory=list)  # task_ids
    completed: bool = False
    completed_at: datetime | None = None


@dataclass
class ProjectPhase:
    phase_id: str
    name: str
    description: str
    start_date: datetime
    end_date: datetime
    milestones: list[Milestone] = field(default_factory=list)
    deliverables: list[str] = field(default_factory=list)


@dataclass
class Project:
    project_id: str
    client_name: str
    tenant_id: str | None = None
    discovery_session_id: str | None = None
    plan: str = "pro"
    status: ProjectStatus = ProjectStatus.PLANNING
    phases: list[ProjectPhase] = field(default_factory=list)
    tasks: list[ProjectTask] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    notes: str = ""

    @property
    def progress(self) -> float:
        if not self.tasks:
            return 0.0
        done = sum(1 for t in self.tasks if t.status == TaskStatus.DONE)
        return round(done / len(self.tasks) * 100, 1)

    @property
    def total_estimated_hours(self) -> float:
        return sum(t.estimated_hours for t in self.tasks)

    @property
    def total_actual_hours(self) -> float:
        return sum(t.actual_hours for t in self.tasks)


class ProjectManager:
    """Manages client projects lifecycle."""

    def __init__(self):
        self._projects: dict[str, Project] = {}
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"PROJ-{self._counter:04d}"

    def _next_task_id(self, project_id: str) -> str:
        project = self._projects.get(project_id)
        task_count = len(project.tasks) + 1 if project else 1
        return f"{project_id}-T{task_count:03d}"

    def create_project(
        self,
        client_name: str,
        plan: str = "pro",
        tenant_id: str | None = None,
        discovery_session_id: str | None = None,
        milestones_data: list[dict] | None = None,
        name: str = "",
        description: str = "",
        budget: float = 0,
        start_date: str = "",
        end_date: str = "",
    ) -> Project:
        project = Project(
            project_id=self._next_id(),
            client_name=client_name,
            plan=plan,
            tenant_id=tenant_id,
            discovery_session_id=discovery_session_id,
        )
        project.notes = description

        # Process milestones into phases
        if milestones_data:
            for i, ms_data in enumerate(milestones_data):
                due = ms_data.get("due_date", "")
                if isinstance(due, str) and due:
                    try:
                        due_dt = datetime.fromisoformat(due)
                    except ValueError:
                        due_dt = datetime.now() + timedelta(weeks=(i+1)*4)
                else:
                    due_dt = datetime.now() + timedelta(weeks=(i+1)*4)

                milestone = Milestone(
                    milestone_id=f"{project.project_id}-M{i+1:03d}",
                    name=ms_data.get("name", f"Milestone {i+1}"),
                    description=ms_data.get("description", ""),
                    due_date=due_dt,
                )
                # Create a phase for each milestone
                start_dt = datetime.now() + timedelta(weeks=i*4) if i == 0 else project.phases[-1].end_date if project.phases else datetime.now()
                phase = ProjectPhase(
                    phase_id=f"{project.project_id}-P{i+1}",
                    name=ms_data.get("name", f"Fase {i+1}"),
                    description=ms_data.get("description", ""),
                    start_date=start_dt,
                    end_date=due_dt,
                    milestones=[milestone],
                )
                project.phases.append(phase)

        self._projects[project.project_id] = project
        logger.info(f"Project created: {project.project_id} for {client_name} with {len(project.phases)} phases")
        return project

    def create_from_proposal(self, client_name: str, plan: str, phases_data: list[dict]) -> Project:
        """Create a project from a proposal's phases."""
        project = self.create_project(client_name, plan)
        now = datetime.now()
        offset = 0

        for i, phase_data in enumerate(phases_data):
            weeks = phase_data.get("duration_weeks", 4)
            phase = ProjectPhase(
                phase_id=f"{project.project_id}-P{i + 1}",
                name=phase_data.get("name", f"Fase {i + 1}"),
                description=phase_data.get("description", ""),
                start_date=now + timedelta(weeks=offset),
                end_date=now + timedelta(weeks=offset + weeks),
                deliverables=phase_data.get("deliverables", []),
            )
            project.phases.append(phase)
            offset += weeks

        return project

    def add_task(
        self,
        project_id: str,
        title: str,
        description: str = "",
        assignee: str = "unassigned",
        priority: str = "medium",
        estimated_hours: float = 0,
        milestone_id: str | None = None,
    ) -> ProjectTask | None:
        project = self._projects.get(project_id)
        if not project:
            return None

        task = ProjectTask(
            task_id=self._next_task_id(project_id),
            title=title,
            description=description,
            assignee=assignee,
            priority=priority,
            estimated_hours=estimated_hours,
            milestone_id=milestone_id,
        )
        project.tasks.append(task)

        # Link task to milestone if specified
        if milestone_id:
            for phase in project.phases:
                for ms in phase.milestones:
                    if ms.milestone_id == milestone_id:
                        ms.tasks.append(task.task_id)
                        break

        return task

    def update_task_status(self, project_id: str, task_id: str, status: TaskStatus) -> bool:
        project = self._projects.get(project_id)
        if not project:
            return False
        for task in project.tasks:
            if task.task_id == task_id:
                task.status = status
                if status == TaskStatus.DONE:
                    task.completed_at = datetime.now()
                return True
        return False

    def get_tasks_by_milestone(self, project_id: str, milestone_id: str) -> list[ProjectTask]:
        """Get all tasks linked to a specific milestone."""
        project = self._projects.get(project_id)
        if not project:
            return []
        return [t for t in project.tasks if t.milestone_id == milestone_id]

    def get_project(self, project_id: str) -> Project | None:
        return self._projects.get(project_id)

    def list_projects(self, status: ProjectStatus | None = None) -> list[Project]:
        projects = list(self._projects.values())
        if status:
            projects = [p for p in projects if p.status == status]
        return sorted(projects, key=lambda p: p.created_at, reverse=True)

    def get_project_report(self, project_id: str) -> dict | None:
        project = self.get_project(project_id)
        if not project:
            return None

        tasks_by_status = {}
        for task in project.tasks:
            s = task.status.value
            tasks_by_status[s] = tasks_by_status.get(s, 0) + 1

        blocked = [t for t in project.tasks if t.status == TaskStatus.BLOCKED]
        overdue = [
            t for t in project.tasks
            if t.due_date and t.due_date < datetime.now() and t.status != TaskStatus.DONE
        ]

        milestones_data = [
            {
                "milestone_id": ms.milestone_id,
                "name": ms.name,
                "due_date": ms.due_date.isoformat(),
                "completed": ms.completed,
                "task_count": len(ms.tasks),
                "tasks_done": len([t for t in project.tasks if t.task_id in ms.tasks and t.status == TaskStatus.DONE]),
            }
            for phase in project.phases
            for ms in phase.milestones
        ]

        return {
            "project_id": project.project_id,
            "client": project.client_name,
            "status": project.status.value,
            "progress": project.progress,
            "total_tasks": len(project.tasks),
            "tasks_by_status": tasks_by_status,
            "estimated_hours": project.total_estimated_hours,
            "actual_hours": project.total_actual_hours,
            "blocked_tasks": len(blocked),
            "overdue_tasks": len(overdue),
            "phases": len(project.phases),
            "milestones": milestones_data,
        }

    def get_stats(self) -> dict:
        by_status = {}
        for p in self._projects.values():
            s = p.status.value
            by_status[s] = by_status.get(s, 0) + 1

        return {
            "total_projects": len(self._projects),
            "by_status": by_status,
            "total_tasks": sum(len(p.tasks) for p in self._projects.values()),
        }


# Singleton
project_manager = ProjectManager()
