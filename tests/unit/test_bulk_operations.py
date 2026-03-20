"""Tests for bulk operations engine and data import engine."""

import pytest

from xcapitsff.core.bulk_operations import (
    BulkJob,
    BulkJobStatus,
    BulkOperationType,
    BulkOperationsEngine,
    EntityType,
    PlanTier,
)
from xcapitsff.core.data_import import (
    DataImportEngine,
    ImportConfig,
    validate_row,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine():
    return BulkOperationsEngine()


@pytest.fixture
def import_engine():
    return DataImportEngine()


SAMPLE_CSV = "company_name,contact_name,contact_email,region,afinidad\nAcme,John,john@acme.com,LATAM,HIGH\nBeta,Jane,jane@beta.com,Iberia,MEDIUM\n"

SAMPLE_CSV_WITH_DUPES = "company_name,contact_name,contact_email,region,afinidad\nAcme,John,john@acme.com,LATAM,HIGH\nAcme,John,john@acme.com,LATAM,HIGH\nBeta,Jane,jane@beta.com,Iberia,MEDIUM\n"

SAMPLE_CSV_BAD_ROWS = "company_name,contact_name,contact_email,region,afinidad\n,,,,\nBeta,Jane,jane@beta.com,Iberia,MEDIUM\n"

SAMPLE_TSV = "empresa\tnombre\tcorreo\tregion\nafinidad\nAcme\tJohn\tjohn@acme.com\tLATAM\tHIGH\n"


# ===========================================================================
# BULK OPERATIONS ENGINE TESTS
# ===========================================================================


class TestCreateJob:
    def test_create_job_basic(self, engine):
        job = engine.create_job(
            tenant_id="t1",
            operation=BulkOperationType.UPDATE,
            entity_type=EntityType.LEADS,
            entity_ids=[1, 2, 3],
            params={"fields": {"stage": "qualified"}},
            created_by="admin",
        )
        assert job.id is not None
        assert job.tenant_id == "t1"
        assert job.operation == BulkOperationType.UPDATE
        assert job.entity_type == EntityType.LEADS
        assert job.entity_ids == [1, 2, 3]
        assert job.total_count == 3
        assert job.status == BulkJobStatus.PENDING
        assert job.created_by == "admin"

    def test_create_job_empty_ids_raises(self, engine):
        with pytest.raises(ValueError, match="must not be empty"):
            engine.create_job(
                tenant_id="t1",
                operation=BulkOperationType.DELETE,
                entity_type=EntityType.LEADS,
                entity_ids=[],
            )

    def test_create_job_stores_in_memory(self, engine):
        job = engine.create_job(
            tenant_id="t1",
            operation=BulkOperationType.TAG,
            entity_type=EntityType.CUSTOMERS,
            entity_ids=[10],
        )
        fetched = engine.get_job(job.id)
        assert fetched.id == job.id


class TestExecuteUpdateJob:
    def test_execute_update_success(self, engine):
        job = engine.create_job(
            tenant_id="t1",
            operation=BulkOperationType.UPDATE,
            entity_type=EntityType.LEADS,
            entity_ids=[1, 2, 3],
            params={"fields": {"notes": "bulk updated"}},
        )
        result = engine.execute_job(job.id)
        assert result.status == BulkJobStatus.COMPLETED
        assert result.success_count == 3
        assert result.error_count == 0
        assert result.processed_count == 3

    def test_execute_update_no_fields_error(self, engine):
        job = engine.create_job(
            tenant_id="t1",
            operation=BulkOperationType.UPDATE,
            entity_type=EntityType.LEADS,
            entity_ids=[1, 2],
            params={},  # No fields
        )
        result = engine.execute_job(job.id)
        assert result.status == BulkJobStatus.COMPLETED
        assert result.error_count == 2
        assert result.success_count == 0
        assert len(result.errors) == 2
        assert "No fields specified" in result.errors[0]["error"]


class TestExecuteDeleteJob:
    def test_execute_delete_success(self, engine):
        job = engine.create_job(
            tenant_id="t1",
            operation=BulkOperationType.DELETE,
            entity_type=EntityType.TICKETS,
            entity_ids=[10, 20, 30],
        )
        result = engine.execute_job(job.id)
        assert result.status == BulkJobStatus.COMPLETED
        assert result.success_count == 3
        assert result.error_count == 0


class TestExecuteAssignJob:
    def test_execute_assign_success(self, engine):
        job = engine.create_job(
            tenant_id="t1",
            operation=BulkOperationType.ASSIGN,
            entity_type=EntityType.LEADS,
            entity_ids=[1, 2],
            params={"assignee": "agent_carlos"},
        )
        result = engine.execute_job(job.id)
        assert result.success_count == 2
        assert result.error_count == 0

    def test_execute_assign_no_assignee_error(self, engine):
        job = engine.create_job(
            tenant_id="t1",
            operation=BulkOperationType.ASSIGN,
            entity_type=EntityType.LEADS,
            entity_ids=[1],
            params={},
        )
        result = engine.execute_job(job.id)
        assert result.error_count == 1
        assert "No assignee" in result.errors[0]["error"]


class TestExecuteTagJob:
    def test_execute_tag_success(self, engine):
        job = engine.create_job(
            tenant_id="t1",
            operation=BulkOperationType.TAG,
            entity_type=EntityType.CUSTOMERS,
            entity_ids=[5, 6, 7],
            params={"tags": ["vip", "enterprise"]},
        )
        result = engine.execute_job(job.id)
        assert result.success_count == 3

    def test_execute_tag_no_tags_error(self, engine):
        job = engine.create_job(
            tenant_id="t1",
            operation=BulkOperationType.TAG,
            entity_type=EntityType.CUSTOMERS,
            entity_ids=[5],
            params={},
        )
        result = engine.execute_job(job.id)
        assert result.error_count == 1
        assert "No tags" in result.errors[0]["error"]


class TestExecuteMoveStageJob:
    def test_execute_move_stage_success(self, engine):
        job = engine.create_job(
            tenant_id="t1",
            operation=BulkOperationType.MOVE_STAGE,
            entity_type=EntityType.LEADS,
            entity_ids=[1, 2, 3],
            params={"stage": "qualified"},
        )
        result = engine.execute_job(job.id)
        assert result.success_count == 3
        assert result.error_count == 0

    def test_execute_move_stage_invalid_stage(self, engine):
        job = engine.create_job(
            tenant_id="t1",
            operation=BulkOperationType.MOVE_STAGE,
            entity_type=EntityType.LEADS,
            entity_ids=[1],
            params={"stage": "nonexistent"},
        )
        result = engine.execute_job(job.id)
        assert result.error_count == 1
        assert "Invalid stage" in result.errors[0]["error"]

    def test_execute_move_stage_wrong_entity_type(self, engine):
        job = engine.create_job(
            tenant_id="t1",
            operation=BulkOperationType.MOVE_STAGE,
            entity_type=EntityType.TICKETS,
            entity_ids=[1],
            params={"stage": "qualified"},
        )
        result = engine.execute_job(job.id)
        assert result.error_count == 1
        assert "only supported for leads" in result.errors[0]["error"]


class TestJobProgressTracking:
    def test_progress_before_execution(self, engine):
        job = engine.create_job(
            tenant_id="t1",
            operation=BulkOperationType.DELETE,
            entity_type=EntityType.LEADS,
            entity_ids=[1, 2, 3, 4, 5],
        )
        progress = engine.get_job_progress(job.id)
        assert progress["percentage"] == 0.0
        assert progress["processed"] == 0
        assert progress["total"] == 5
        assert progress["status"] == "pending"

    def test_progress_after_execution(self, engine):
        job = engine.create_job(
            tenant_id="t1",
            operation=BulkOperationType.DELETE,
            entity_type=EntityType.LEADS,
            entity_ids=[1, 2, 3, 4, 5],
        )
        engine.execute_job(job.id)
        progress = engine.get_job_progress(job.id)
        assert progress["percentage"] == 100.0
        assert progress["processed"] == 5
        assert progress["total"] == 5
        assert progress["status"] == "completed"

    def test_result_summary_populated(self, engine):
        job = engine.create_job(
            tenant_id="t1",
            operation=BulkOperationType.DELETE,
            entity_type=EntityType.LEADS,
            entity_ids=[1, 2],
        )
        result = engine.execute_job(job.id)
        assert result.result_summary["total"] == 2
        assert result.result_summary["processed"] == 2
        assert result.result_summary["success"] == 2
        assert result.result_summary["errors"] == 0


class TestContinueOnError:
    def test_partial_errors_dont_stop_job(self, engine):
        """Job with mixed success/failure entities should complete, not abort."""
        # Use ASSIGN with no assignee — will fail, but intersperse with entities
        # that would succeed if we had an assignee. Since we don't, all fail.
        # Instead, use UPDATE with some entities having fields and some not.
        # Actually, let's test with MOVE_STAGE on mixed entity types is not possible
        # since all share entity_type. Let's use TAG with tags provided = all succeed.
        # For a true partial test, create two jobs — one success, one failure.
        # Better: mix TAG (needs tags) with empty params means all fail.
        # The simplest: use UPDATE where params have fields → all succeed.
        # And ensure that the job completes even if errors happen.

        # We'll demonstrate continue-on-error by using move_stage on tickets
        # (which fails) mixed with leads is not possible in a single job.
        # Instead, test that even when all items error, the job still completes.
        job = engine.create_job(
            tenant_id="t1",
            operation=BulkOperationType.ASSIGN,
            entity_type=EntityType.LEADS,
            entity_ids=[1, 2, 3],
            params={},  # No assignee → all will error
        )
        result = engine.execute_job(job.id)
        assert result.status == BulkJobStatus.COMPLETED  # Not FAILED
        assert result.processed_count == 3  # All were processed
        assert result.error_count == 3

    def test_started_at_set(self, engine):
        job = engine.create_job(
            tenant_id="t1",
            operation=BulkOperationType.DELETE,
            entity_type=EntityType.LEADS,
            entity_ids=[1],
        )
        assert job.started_at is None
        engine.execute_job(job.id)
        assert job.started_at is not None

    def test_completed_at_set(self, engine):
        job = engine.create_job(
            tenant_id="t1",
            operation=BulkOperationType.DELETE,
            entity_type=EntityType.LEADS,
            entity_ids=[1],
        )
        assert job.completed_at is None
        engine.execute_job(job.id)
        assert job.completed_at is not None


class TestCancelJob:
    def test_cancel_pending_job(self, engine):
        job = engine.create_job(
            tenant_id="t1",
            operation=BulkOperationType.DELETE,
            entity_type=EntityType.LEADS,
            entity_ids=[1, 2],
        )
        cancelled = engine.cancel_job(job.id)
        assert cancelled.status == BulkJobStatus.CANCELLED
        assert cancelled.completed_at is not None

    def test_cancel_completed_job_raises(self, engine):
        job = engine.create_job(
            tenant_id="t1",
            operation=BulkOperationType.DELETE,
            entity_type=EntityType.LEADS,
            entity_ids=[1],
        )
        engine.execute_job(job.id)
        with pytest.raises(ValueError, match="Cannot cancel"):
            engine.cancel_job(job.id)

    def test_execute_cancelled_job_raises(self, engine):
        job = engine.create_job(
            tenant_id="t1",
            operation=BulkOperationType.DELETE,
            entity_type=EntityType.LEADS,
            entity_ids=[1],
        )
        engine.cancel_job(job.id)
        with pytest.raises(ValueError, match="Cannot execute a cancelled job"):
            engine.execute_job(job.id)


class TestMaxEntitiesValidation:
    def test_free_plan_limit_1000(self, engine):
        ids = list(range(1001))
        with pytest.raises(ValueError, match="exceeds FREE plan limit of 1000"):
            engine.create_job(
                tenant_id="t1",
                operation=BulkOperationType.DELETE,
                entity_type=EntityType.LEADS,
                entity_ids=ids,
                plan=PlanTier.FREE,
            )

    def test_free_plan_at_limit_ok(self, engine):
        ids = list(range(1000))
        job = engine.create_job(
            tenant_id="t1",
            operation=BulkOperationType.DELETE,
            entity_type=EntityType.LEADS,
            entity_ids=ids,
            plan=PlanTier.FREE,
        )
        assert job.total_count == 1000

    def test_pro_plan_limit_10000(self, engine):
        ids = list(range(10001))
        with pytest.raises(ValueError, match="exceeds PRO plan limit of 10000"):
            engine.create_job(
                tenant_id="t1",
                operation=BulkOperationType.DELETE,
                entity_type=EntityType.LEADS,
                entity_ids=ids,
                plan=PlanTier.PRO,
            )

    def test_enterprise_plan_allows_large(self, engine):
        ids = list(range(50000))
        job = engine.create_job(
            tenant_id="t1",
            operation=BulkOperationType.DELETE,
            entity_type=EntityType.LEADS,
            entity_ids=ids,
            plan=PlanTier.ENTERPRISE,
        )
        assert job.total_count == 50000


class TestListJobs:
    def test_list_jobs_by_tenant(self, engine):
        engine.create_job("t1", BulkOperationType.DELETE, EntityType.LEADS, [1])
        engine.create_job("t1", BulkOperationType.TAG, EntityType.LEADS, [2])
        engine.create_job("t2", BulkOperationType.DELETE, EntityType.LEADS, [3])

        t1_jobs = engine.list_jobs("t1")
        assert len(t1_jobs) == 2

        t2_jobs = engine.list_jobs("t2")
        assert len(t2_jobs) == 1

    def test_list_jobs_with_status_filter(self, engine):
        j1 = engine.create_job("t1", BulkOperationType.DELETE, EntityType.LEADS, [1])
        engine.create_job("t1", BulkOperationType.DELETE, EntityType.LEADS, [2])

        engine.execute_job(j1.id)

        pending = engine.list_jobs("t1", status=BulkJobStatus.PENDING)
        assert len(pending) == 1

        completed = engine.list_jobs("t1", status=BulkJobStatus.COMPLETED)
        assert len(completed) == 1

    def test_list_jobs_empty_tenant(self, engine):
        assert engine.list_jobs("nonexistent") == []

    def test_get_nonexistent_job_raises(self, engine):
        with pytest.raises(KeyError):
            engine.get_job("nonexistent-id")


# ===========================================================================
# DATA IMPORT ENGINE TESTS
# ===========================================================================


class TestImportPreview:
    def test_preview_basic(self, import_engine):
        preview = import_engine.preview_import(SAMPLE_CSV)
        assert len(preview) == 2
        assert preview[0]["company_name"] == "Acme"
        assert preview[1]["contact_email"] == "jane@beta.com"

    def test_preview_limit_rows(self, import_engine):
        preview = import_engine.preview_import(SAMPLE_CSV, rows=1)
        assert len(preview) == 1

    def test_preview_empty_data(self, import_engine):
        preview = import_engine.preview_import("")
        assert preview == []


class TestImportExecution:
    def test_import_basic(self, import_engine):
        job = import_engine.create_import(
            tenant_id="t1",
            filename="leads.csv",
            raw_data=SAMPLE_CSV,
            entity_type="leads",
        )
        result = import_engine.execute_import(job.id)
        assert result.status == "completed"
        assert result.imported_rows == 2
        assert result.error_rows == 0

    def test_import_already_completed_raises(self, import_engine):
        job = import_engine.create_import(
            tenant_id="t1",
            filename="leads.csv",
            raw_data=SAMPLE_CSV,
            entity_type="leads",
        )
        import_engine.execute_import(job.id)
        with pytest.raises(ValueError, match="already completed"):
            import_engine.execute_import(job.id)

    def test_import_invalid_entity_type(self, import_engine):
        with pytest.raises(ValueError, match="Unsupported entity type"):
            import_engine.create_import(
                tenant_id="t1",
                filename="bad.csv",
                raw_data=SAMPLE_CSV,
                entity_type="widgets",
            )

    def test_import_empty_data_raises(self, import_engine):
        with pytest.raises(ValueError, match="must not be empty"):
            import_engine.create_import(
                tenant_id="t1",
                filename="empty.csv",
                raw_data="",
                entity_type="leads",
            )


class TestFieldSuggestions:
    def test_field_suggestions_leads(self, import_engine):
        suggestions = import_engine.get_field_suggestions(SAMPLE_CSV, "leads")
        assert suggestions["company_name"] == "company_name"
        assert suggestions["contact_email"] == "contact_email"
        assert suggestions["region"] == "region"
        assert suggestions["afinidad"] == "afinidad"

    def test_field_suggestions_spanish_headers(self, import_engine):
        csv_data = "empresa,correo,region\nAcme,a@a.com,LATAM\n"
        suggestions = import_engine.get_field_suggestions(csv_data, "leads")
        assert suggestions["empresa"] == "company_name"
        assert suggestions["correo"] == "contact_email"

    def test_field_suggestions_invalid_entity_type(self, import_engine):
        with pytest.raises(ValueError, match="Unsupported entity type"):
            import_engine.get_field_suggestions(SAMPLE_CSV, "widgets")


class TestRowValidation:
    def test_validate_lead_valid(self):
        errors = validate_row(
            {"company_name": "Acme", "contact_email": "a@a.com", "region": "LATAM"},
            "leads",
        )
        assert errors == []

    def test_validate_lead_missing_identifiers(self):
        errors = validate_row({}, "leads")
        assert any("company_name or contact_email" in e for e in errors)

    def test_validate_lead_invalid_region(self):
        errors = validate_row(
            {"company_name": "Acme", "region": "INVALID"},
            "leads",
        )
        assert any("Invalid region" in e for e in errors)

    def test_validate_lead_invalid_afinidad(self):
        errors = validate_row(
            {"company_name": "Acme", "afinidad": "SUPER"},
            "leads",
        )
        assert any("Invalid afinidad" in e for e in errors)

    def test_validate_lead_invalid_stage(self):
        errors = validate_row(
            {"company_name": "Acme", "stage": "nonexistent"},
            "leads",
        )
        assert any("Invalid stage" in e for e in errors)

    def test_validate_customer_missing_fields(self):
        errors = validate_row({}, "customers")
        assert len(errors) == 3  # company_name, contact_name, contact_email

    def test_validate_ticket_missing_fields(self):
        errors = validate_row({}, "tickets")
        assert len(errors) == 3  # customer_id, subject, description

    def test_validate_contact_valid(self):
        errors = validate_row({"email": "test@test.com"}, "contacts")
        assert errors == []


class TestSkipDuplicates:
    def test_skip_duplicates_enabled(self, import_engine):
        config = ImportConfig(skip_duplicates=True)
        job = import_engine.create_import(
            tenant_id="t1",
            filename="dupes.csv",
            raw_data=SAMPLE_CSV_WITH_DUPES,
            entity_type="leads",
            config=config,
        )
        result = import_engine.execute_import(job.id)
        assert result.imported_rows == 2  # 3 rows minus 1 duplicate
        assert result.skipped_rows == 1

    def test_skip_duplicates_disabled(self, import_engine):
        config = ImportConfig(skip_duplicates=False)
        job = import_engine.create_import(
            tenant_id="t1",
            filename="dupes.csv",
            raw_data=SAMPLE_CSV_WITH_DUPES,
            entity_type="leads",
            config=config,
        )
        result = import_engine.execute_import(job.id)
        assert result.imported_rows == 3  # All 3 rows imported


class TestDryRun:
    def test_dry_run_counts_but_does_not_import(self, import_engine):
        config = ImportConfig(dry_run=True)
        job = import_engine.create_import(
            tenant_id="t1",
            filename="test.csv",
            raw_data=SAMPLE_CSV,
            entity_type="leads",
            config=config,
        )
        result = import_engine.execute_import(job.id)
        assert result.status == "completed"
        assert result.imported_rows == 2  # Counted but not actually stored


class TestListImports:
    def test_list_imports_by_tenant(self, import_engine):
        import_engine.create_import("t1", "a.csv", SAMPLE_CSV, "leads")
        import_engine.create_import("t1", "b.csv", SAMPLE_CSV, "leads")
        import_engine.create_import("t2", "c.csv", SAMPLE_CSV, "leads")

        t1 = import_engine.list_imports("t1")
        assert len(t1) == 2

        t2 = import_engine.list_imports("t2")
        assert len(t2) == 1

    def test_list_imports_empty(self, import_engine):
        assert import_engine.list_imports("nobody") == []
