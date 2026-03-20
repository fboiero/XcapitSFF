"""Bulk operations engine — mass operations on leads, tickets, and customers."""

import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from xcapitsff.logging_config import get_logger

logger = get_logger(__name__)


# --- Enums ---


class BulkOperationType(str, enum.Enum):
    UPDATE = "update"
    DELETE = "delete"
    ASSIGN = "assign"
    TAG = "tag"
    UNTAG = "untag"
    MOVE_STAGE = "move_stage"
    EXPORT = "export"
    SCORE = "score"
    ENROLL_SEQUENCE = "enroll_sequence"
    MERGE = "merge"


class BulkJobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EntityType(str, enum.Enum):
    LEADS = "leads"
    TICKETS = "tickets"
    CUSTOMERS = "customers"


class PlanTier(str, enum.Enum):
    FREE = "FREE"
    PRO = "PRO"
    ENTERPRISE = "ENTERPRISE"


# Plan limits for max entities per bulk job
PLAN_ENTITY_LIMITS: dict[PlanTier, int] = {
    PlanTier.FREE: 1_000,
    PlanTier.PRO: 10_000,
    PlanTier.ENTERPRISE: 100_000,
}


# --- Dataclass ---


@dataclass
class BulkJob:
    id: str
    tenant_id: str
    operation: BulkOperationType
    entity_type: EntityType
    entity_ids: list[int]
    params: dict
    status: BulkJobStatus = BulkJobStatus.PENDING
    created_by: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    total_count: int = 0
    processed_count: int = 0
    success_count: int = 0
    error_count: int = 0
    errors: list[dict] = field(default_factory=list)
    result_summary: dict = field(default_factory=dict)


# --- Engine ---


class BulkOperationsEngine:
    """Engine for executing bulk operations on leads, tickets, and customers."""

    def __init__(self) -> None:
        self._jobs: dict[str, BulkJob] = {}

    def create_job(
        self,
        tenant_id: str,
        operation: BulkOperationType,
        entity_type: EntityType,
        entity_ids: list[int],
        params: dict | None = None,
        created_by: str = "",
        plan: PlanTier = PlanTier.FREE,
    ) -> BulkJob:
        """Create a new bulk job. Validates entity count against plan limits."""
        limit = PLAN_ENTITY_LIMITS[plan]
        if len(entity_ids) > limit:
            raise ValueError(
                f"Entity count {len(entity_ids)} exceeds {plan.value} plan limit of {limit}"
            )

        if not entity_ids:
            raise ValueError("entity_ids must not be empty")

        job = BulkJob(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            operation=operation,
            entity_type=entity_type,
            entity_ids=list(entity_ids),
            params=params or {},
            created_by=created_by,
            total_count=len(entity_ids),
        )
        self._jobs[job.id] = job
        logger.info(
            "Bulk job created: id=%s op=%s entity_type=%s count=%d",
            job.id,
            operation.value,
            entity_type.value,
            len(entity_ids),
        )
        return job

    def execute_job(self, job_id: str) -> BulkJob:
        """Execute a bulk job, processing all entities. Continues on individual errors."""
        job = self._get_job_or_raise(job_id)

        if job.status == BulkJobStatus.CANCELLED:
            raise ValueError("Cannot execute a cancelled job")
        if job.status == BulkJobStatus.COMPLETED:
            raise ValueError("Job already completed")
        if job.status == BulkJobStatus.PROCESSING:
            raise ValueError("Job is already processing")

        job.status = BulkJobStatus.PROCESSING
        job.started_at = datetime.now(timezone.utc)

        operation_map = {
            BulkOperationType.UPDATE: self._execute_update,
            BulkOperationType.DELETE: self._execute_delete,
            BulkOperationType.ASSIGN: self._execute_assign,
            BulkOperationType.TAG: self._execute_tag,
            BulkOperationType.UNTAG: self._execute_untag,
            BulkOperationType.MOVE_STAGE: self._execute_move_stage,
            BulkOperationType.EXPORT: self._execute_export,
            BulkOperationType.SCORE: self._execute_score,
            BulkOperationType.ENROLL_SEQUENCE: self._execute_enroll_sequence,
            BulkOperationType.MERGE: self._execute_merge,
        }

        handler = operation_map.get(job.operation)
        if not handler:
            job.status = BulkJobStatus.FAILED
            job.completed_at = datetime.now(timezone.utc)
            raise ValueError(f"Unsupported operation: {job.operation}")

        for entity_id in job.entity_ids:
            if job.status == BulkJobStatus.CANCELLED:
                break

            try:
                success, error_msg = handler(job.entity_type, entity_id, job.params)
                job.processed_count += 1
                if success:
                    job.success_count += 1
                else:
                    job.error_count += 1
                    job.errors.append({"entity_id": entity_id, "error": error_msg or "Unknown error"})
            except Exception as exc:
                job.processed_count += 1
                job.error_count += 1
                job.errors.append({"entity_id": entity_id, "error": str(exc)})

        if job.status != BulkJobStatus.CANCELLED:
            job.status = BulkJobStatus.COMPLETED if job.error_count == 0 else BulkJobStatus.COMPLETED

        job.completed_at = datetime.now(timezone.utc)
        job.result_summary = {
            "total": job.total_count,
            "processed": job.processed_count,
            "success": job.success_count,
            "errors": job.error_count,
        }

        logger.info(
            "Bulk job completed: id=%s success=%d errors=%d",
            job.id,
            job.success_count,
            job.error_count,
        )
        return job

    def cancel_job(self, job_id: str) -> BulkJob:
        """Cancel a pending or processing job."""
        job = self._get_job_or_raise(job_id)

        if job.status in (BulkJobStatus.COMPLETED, BulkJobStatus.FAILED):
            raise ValueError(f"Cannot cancel a {job.status.value} job")

        job.status = BulkJobStatus.CANCELLED
        job.completed_at = datetime.now(timezone.utc)
        logger.info("Bulk job cancelled: id=%s", job.id)
        return job

    def get_job(self, job_id: str) -> BulkJob:
        """Get a job by ID."""
        return self._get_job_or_raise(job_id)

    def list_jobs(self, tenant_id: str, status: BulkJobStatus | None = None) -> list[BulkJob]:
        """List jobs for a tenant, optionally filtered by status."""
        jobs = [j for j in self._jobs.values() if j.tenant_id == tenant_id]
        if status is not None:
            jobs = [j for j in jobs if j.status == status]
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)

    def get_job_progress(self, job_id: str) -> dict:
        """Get progress info for a job."""
        job = self._get_job_or_raise(job_id)
        percentage = (job.processed_count / job.total_count * 100) if job.total_count > 0 else 0.0
        return {
            "job_id": job.id,
            "status": job.status.value,
            "percentage": round(percentage, 1),
            "processed": job.processed_count,
            "total": job.total_count,
            "success": job.success_count,
            "errors": job.error_count,
            "error_details": job.errors[:10],  # Limit to first 10
        }

    # --- Private helpers ---

    def _get_job_or_raise(self, job_id: str) -> BulkJob:
        job = self._jobs.get(job_id)
        if not job:
            raise KeyError(f"Job not found: {job_id}")
        return job

    def _execute_update(
        self, entity_type: EntityType, entity_id: int, params: dict
    ) -> tuple[bool, str | None]:
        """Simulate updating an entity's fields."""
        fields = params.get("fields", {})
        if not fields:
            return False, "No fields specified for update"
        logger.debug("Update %s #%d: %s", entity_type.value, entity_id, fields)
        return True, None

    def _execute_delete(
        self, entity_type: EntityType, entity_id: int, params: dict
    ) -> tuple[bool, str | None]:
        """Simulate deleting an entity."""
        logger.debug("Delete %s #%d", entity_type.value, entity_id)
        return True, None

    def _execute_assign(
        self, entity_type: EntityType, entity_id: int, params: dict
    ) -> tuple[bool, str | None]:
        """Simulate assigning an entity to an agent/owner."""
        assignee = params.get("assignee")
        if not assignee:
            return False, "No assignee specified"
        logger.debug("Assign %s #%d to %s", entity_type.value, entity_id, assignee)
        return True, None

    def _execute_tag(
        self, entity_type: EntityType, entity_id: int, params: dict
    ) -> tuple[bool, str | None]:
        """Simulate adding tags to an entity."""
        tags = params.get("tags", [])
        if not tags:
            return False, "No tags specified"
        logger.debug("Tag %s #%d: %s", entity_type.value, entity_id, tags)
        return True, None

    def _execute_untag(
        self, entity_type: EntityType, entity_id: int, params: dict
    ) -> tuple[bool, str | None]:
        """Simulate removing tags from an entity."""
        tags = params.get("tags", [])
        if not tags:
            return False, "No tags specified"
        logger.debug("Untag %s #%d: %s", entity_type.value, entity_id, tags)
        return True, None

    def _execute_move_stage(
        self, entity_type: EntityType, entity_id: int, params: dict
    ) -> tuple[bool, str | None]:
        """Simulate moving an entity to a new stage."""
        if entity_type != EntityType.LEADS:
            return False, f"move_stage is only supported for leads, got {entity_type.value}"
        stage = params.get("stage")
        if not stage:
            return False, "No target stage specified"
        valid_stages = {"raw", "qualified", "contacted", "meeting", "proposal", "negotiation", "won", "lost"}
        if stage not in valid_stages:
            return False, f"Invalid stage: {stage}"
        logger.debug("Move %s #%d to stage %s", entity_type.value, entity_id, stage)
        return True, None

    def _execute_export(
        self, entity_type: EntityType, entity_id: int, params: dict
    ) -> tuple[bool, str | None]:
        """Simulate exporting an entity."""
        logger.debug("Export %s #%d", entity_type.value, entity_id)
        return True, None

    def _execute_score(
        self, entity_type: EntityType, entity_id: int, params: dict
    ) -> tuple[bool, str | None]:
        """Simulate re-scoring an entity."""
        if entity_type != EntityType.LEADS:
            return False, f"score is only supported for leads, got {entity_type.value}"
        logger.debug("Score %s #%d", entity_type.value, entity_id)
        return True, None

    def _execute_enroll_sequence(
        self, entity_type: EntityType, entity_id: int, params: dict
    ) -> tuple[bool, str | None]:
        """Simulate enrolling an entity in a sequence."""
        sequence_id = params.get("sequence_id")
        if not sequence_id:
            return False, "No sequence_id specified"
        logger.debug("Enroll %s #%d in sequence %s", entity_type.value, entity_id, sequence_id)
        return True, None

    def _execute_merge(
        self, entity_type: EntityType, entity_id: int, params: dict
    ) -> tuple[bool, str | None]:
        """Simulate merging entities."""
        target_id = params.get("target_id")
        if not target_id:
            return False, "No target_id specified for merge"
        logger.debug("Merge %s #%d into %d", entity_type.value, entity_id, target_id)
        return True, None


# Module-level singleton
bulk_engine = BulkOperationsEngine()
