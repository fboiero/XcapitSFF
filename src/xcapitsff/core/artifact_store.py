"""Artifact Store — versioned storage for agent-produced artifacts.

Stores specs, PRDs, code, tests, reviews, and other artifacts produced by
agents during the orchestration pipeline. Supports versioning, search,
and diff operations.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ArtifactType(str, Enum):
    SPEC = "spec"
    PRD = "prd"
    CODE = "code"
    TEST = "test"
    REVIEW = "review"
    DOCUMENT = "document"
    PROPOSAL = "proposal"
    REPORT = "report"
    CONFIG = "config"


class ArtifactFormat(str, Enum):
    MARKDOWN = "markdown"
    JSON = "json"
    PYTHON = "python"
    YAML = "yaml"
    PLAIN = "plain"


def _generate_artifact_id() -> str:
    """Generate a sequential artifact ID like ART-0001."""
    _generate_artifact_id._counter = getattr(_generate_artifact_id, "_counter", 0) + 1
    return f"ART-{_generate_artifact_id._counter:04d}"


@dataclass
class Artifact:
    id: str
    workspace_id: str
    task_id: str
    type: ArtifactType
    name: str
    content: str
    format: ArtifactFormat = ArtifactFormat.MARKDOWN
    created_by_agent: str = ""
    version: int = 1
    parent_id: str | None = None
    tags: list[str] = field(default_factory=list)
    size_bytes: int = 0
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if self.size_bytes == 0:
            self.size_bytes = len(self.content.encode())


class ArtifactStore:
    """In-memory artifact store with versioning and search.

    In production, this would persist to a database or object store.
    For now, it's in-memory with full query support.
    """

    def __init__(self):
        self._artifacts: dict[str, Artifact] = {}

    def store(
        self,
        workspace_id: str,
        task_id: str,
        artifact_type: ArtifactType,
        name: str,
        content: str,
        format: ArtifactFormat = ArtifactFormat.MARKDOWN,
        created_by_agent: str = "",
        tags: list[str] | None = None,
        parent_id: str | None = None,
    ) -> Artifact:
        """Store an artifact. If parent_id is provided, auto-increment version."""
        version = 1
        if parent_id and parent_id in self._artifacts:
            parent = self._artifacts[parent_id]
            version = parent.version + 1

        artifact_id = _generate_artifact_id()
        artifact = Artifact(
            id=artifact_id,
            workspace_id=workspace_id,
            task_id=task_id,
            type=artifact_type,
            name=name,
            content=content,
            format=format,
            created_by_agent=created_by_agent,
            version=version,
            parent_id=parent_id,
            tags=tags or [],
        )
        self._artifacts[artifact_id] = artifact
        logger.info(
            "Stored artifact %s (%s) v%d in workspace %s",
            artifact_id, name, version, workspace_id,
        )
        return artifact

    def get(self, artifact_id: str) -> Artifact | None:
        """Get an artifact by ID."""
        return self._artifacts.get(artifact_id)

    def list_by_workspace(
        self,
        workspace_id: str,
        artifact_type: ArtifactType | None = None,
    ) -> list[Artifact]:
        """List all artifacts in a workspace, optionally filtered by type."""
        results = [
            a for a in self._artifacts.values()
            if a.workspace_id == workspace_id
        ]
        if artifact_type:
            results = [a for a in results if a.type == artifact_type]
        return results

    def list_by_task(self, task_id: str) -> list[Artifact]:
        """List all artifacts for a specific task."""
        return [
            a for a in self._artifacts.values()
            if a.task_id == task_id
        ]

    def get_latest_version(self, artifact_id: str) -> Artifact:
        """Follow the version chain forward to find the latest version."""
        artifact = self._artifacts.get(artifact_id)
        if not artifact:
            return None

        # Find the latest artifact that has this one in its parent chain
        latest = artifact
        changed = True
        while changed:
            changed = False
            for a in self._artifacts.values():
                if a.parent_id == latest.id and a.version > latest.version:
                    latest = a
                    changed = True
        return latest

    def get_version_history(self, artifact_id: str) -> list[Artifact]:
        """Get all versions in the chain, ordered by version number."""
        artifact = self._artifacts.get(artifact_id)
        if not artifact:
            return []

        # Walk back to the root
        root = artifact
        while root.parent_id and root.parent_id in self._artifacts:
            root = self._artifacts[root.parent_id]

        # Walk forward collecting all versions
        chain = [root]
        current = root
        changed = True
        while changed:
            changed = False
            for a in self._artifacts.values():
                if a.parent_id == current.id:
                    chain.append(a)
                    current = a
                    changed = True
                    break

        return sorted(chain, key=lambda a: a.version)

    def diff_versions(self, id_a: str, id_b: str) -> dict:
        """Compare two artifact versions line by line."""
        art_a = self._artifacts.get(id_a)
        art_b = self._artifacts.get(id_b)

        if not art_a or not art_b:
            return {"lines_added": 0, "lines_removed": 0, "lines_changed": 0}

        lines_a = art_a.content.splitlines()
        lines_b = art_b.content.splitlines()

        set_a = set(lines_a)
        set_b = set(lines_b)

        lines_added = len(set_b - set_a)
        lines_removed = len(set_a - set_b)

        # Lines changed = min of added/removed (paired changes)
        lines_changed = min(lines_added, lines_removed)
        lines_added -= lines_changed
        lines_removed -= lines_changed

        return {
            "lines_added": lines_added,
            "lines_removed": lines_removed,
            "lines_changed": lines_changed,
        }

    def search(self, workspace_id: str, query: str) -> list[Artifact]:
        """Search artifacts by substring match in name and content."""
        query_lower = query.lower()
        return [
            a for a in self._artifacts.values()
            if a.workspace_id == workspace_id
            and (query_lower in a.name.lower() or query_lower in a.content.lower())
        ]

    def get_stats(self, workspace_id: str | None = None) -> dict:
        """Get artifact statistics, optionally scoped to a workspace."""
        artifacts = list(self._artifacts.values())
        if workspace_id:
            artifacts = [a for a in artifacts if a.workspace_id == workspace_id]

        by_type: dict[str, int] = {}
        by_format: dict[str, int] = {}
        total_bytes = 0

        for a in artifacts:
            by_type[a.type.value] = by_type.get(a.type.value, 0) + 1
            by_format[a.format.value] = by_format.get(a.format.value, 0) + 1
            total_bytes += a.size_bytes

        return {
            "total": len(artifacts),
            "by_type": by_type,
            "by_format": by_format,
            "total_bytes": total_bytes,
        }


# Singleton
artifact_store = ArtifactStore()
