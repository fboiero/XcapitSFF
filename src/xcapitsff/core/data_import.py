"""Data import engine — generic CSV/TSV import for leads, customers, tickets, contacts."""

import csv
import io
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from xcapitsff.logging_config import get_logger

logger = get_logger(__name__)


# --- Known fields per entity type ---

ENTITY_FIELDS: dict[str, list[str]] = {
    "leads": [
        "company_name", "contact_name", "contact_email", "region",
        "c_level", "score_icp", "afinidad", "stage", "notes", "assigned_agent",
    ],
    "customers": [
        "company_name", "contact_name", "contact_email", "region", "plan",
    ],
    "tickets": [
        "customer_id", "subject", "description", "priority", "category", "assigned_agent",
    ],
    "contacts": [
        "first_name", "last_name", "email", "phone", "company", "title",
    ],
}

# Heuristic mapping: common column header variations → canonical field names
COLUMN_ALIASES: dict[str, str] = {
    "company": "company_name",
    "empresa": "company_name",
    "nombre_empresa": "company_name",
    "name": "contact_name",
    "contact": "contact_name",
    "nombre": "contact_name",
    "email": "contact_email",
    "correo": "contact_email",
    "mail": "contact_email",
    "e-mail": "contact_email",
    "region": "region",
    "región": "region",
    "c_level": "c_level",
    "c-level": "c_level",
    "clevel": "c_level",
    "score": "score_icp",
    "score_icp": "score_icp",
    "icp": "score_icp",
    "afinidad": "afinidad",
    "affinity": "afinidad",
    "stage": "stage",
    "etapa": "stage",
    "notes": "notes",
    "notas": "notes",
    "agent": "assigned_agent",
    "agente": "assigned_agent",
    "assigned": "assigned_agent",
    "plan": "plan",
    "subject": "subject",
    "asunto": "subject",
    "description": "description",
    "descripción": "description",
    "priority": "priority",
    "prioridad": "priority",
    "category": "category",
    "categoría": "category",
    "customer_id": "customer_id",
    "first_name": "first_name",
    "last_name": "last_name",
    "phone": "phone",
    "teléfono": "phone",
    "telefono": "phone",
    "title": "title",
    "título": "title",
    "titulo": "title",
}


# --- Dataclasses ---


@dataclass
class ImportConfig:
    delimiter: str = ","
    has_header: bool = True
    field_mapping: dict[str, str] = field(default_factory=dict)  # column → field
    skip_duplicates: bool = True
    update_existing: bool = False
    dry_run: bool = False


@dataclass
class ImportJob:
    id: str
    tenant_id: str
    filename: str
    entity_type: str
    config: ImportConfig
    raw_data: str = ""
    status: str = "pending"  # pending, processing, completed, failed
    total_rows: int = 0
    imported_rows: int = 0
    skipped_rows: int = 0
    error_rows: int = 0
    errors: list[dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None


# --- Validation ---


def validate_row(row: dict, entity_type: str) -> list[str]:
    """Validate a single parsed row against entity-type rules. Returns list of error messages."""
    errors: list[str] = []

    if entity_type == "leads":
        # At least one identifier required
        if not row.get("company_name") and not row.get("contact_email"):
            errors.append("Either company_name or contact_email is required")
        # Validate region if present
        if row.get("region") and row["region"] not in ("LATAM", "Iberia"):
            errors.append(f"Invalid region: {row['region']}")
        # Validate afinidad if present
        if row.get("afinidad") and row["afinidad"] not in ("HIGH", "MEDIUM", "LOW"):
            errors.append(f"Invalid afinidad: {row['afinidad']}")
        # Validate stage if present
        valid_stages = {"raw", "qualified", "contacted", "meeting", "proposal", "negotiation", "won", "lost"}
        if row.get("stage") and row["stage"] not in valid_stages:
            errors.append(f"Invalid stage: {row['stage']}")

    elif entity_type == "customers":
        if not row.get("company_name"):
            errors.append("company_name is required")
        if not row.get("contact_name"):
            errors.append("contact_name is required")
        if not row.get("contact_email"):
            errors.append("contact_email is required")

    elif entity_type == "tickets":
        if not row.get("customer_id"):
            errors.append("customer_id is required")
        if not row.get("subject"):
            errors.append("subject is required")
        if not row.get("description"):
            errors.append("description is required")

    elif entity_type == "contacts":
        if not row.get("email") and not row.get("first_name"):
            errors.append("Either email or first_name is required")

    return errors


# --- Engine ---


class DataImportEngine:
    """Engine for importing CSV/TSV data into the system."""

    def __init__(self) -> None:
        self._jobs: dict[str, ImportJob] = {}

    def create_import(
        self,
        tenant_id: str,
        filename: str,
        raw_data: str,
        entity_type: str,
        config: ImportConfig | None = None,
    ) -> ImportJob:
        """Create a new import job."""
        if entity_type not in ENTITY_FIELDS:
            raise ValueError(f"Unsupported entity type: {entity_type}. Valid: {list(ENTITY_FIELDS.keys())}")

        if not raw_data.strip():
            raise ValueError("raw_data must not be empty")

        job = ImportJob(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            filename=filename,
            entity_type=entity_type,
            config=config or ImportConfig(),
            raw_data=raw_data,
        )
        self._jobs[job.id] = job
        logger.info("Import job created: id=%s entity_type=%s filename=%s", job.id, entity_type, filename)
        return job

    def preview_import(
        self, raw_data: str, config: ImportConfig | None = None, rows: int = 5
    ) -> list[dict]:
        """Preview parsed rows without importing. Returns up to `rows` parsed dicts."""
        cfg = config or ImportConfig()
        parsed = self._parse_raw(raw_data, cfg)
        return parsed[:rows]

    def execute_import(self, job_id: str) -> ImportJob:
        """Execute an import job, processing all rows."""
        job = self._get_job_or_raise(job_id)

        if job.status in ("completed", "failed"):
            raise ValueError(f"Job already {job.status}")

        job.status = "processing"
        parsed_rows = self._parse_raw(job.raw_data, job.config)
        job.total_rows = len(parsed_rows)

        seen_keys: set[str] = set()

        for i, row in enumerate(parsed_rows):
            # Validate
            validation_errors = validate_row(row, job.entity_type)
            if validation_errors:
                job.error_rows += 1
                job.errors.append({"row": i + 1, "data": row, "errors": validation_errors})
                continue

            # Skip duplicates
            if job.config.skip_duplicates:
                dup_key = self._dedup_key(row, job.entity_type)
                if dup_key in seen_keys:
                    job.skipped_rows += 1
                    continue
                seen_keys.add(dup_key)

            if job.config.dry_run:
                job.imported_rows += 1
                continue

            # In a real implementation this would write to the DB;
            # here we simulate success
            job.imported_rows += 1

        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        logger.info(
            "Import job completed: id=%s imported=%d skipped=%d errors=%d",
            job.id,
            job.imported_rows,
            job.skipped_rows,
            job.error_rows,
        )
        return job

    def get_field_suggestions(self, raw_data: str, entity_type: str) -> dict[str, str]:
        """Auto-map CSV column headers to entity fields using heuristics."""
        if entity_type not in ENTITY_FIELDS:
            raise ValueError(f"Unsupported entity type: {entity_type}")

        # Read the first line to get headers
        first_line = raw_data.strip().split("\n")[0] if raw_data.strip() else ""
        if not first_line:
            return {}

        delimiter = self._detect_delimiter(raw_data)
        reader = csv.reader(io.StringIO(first_line), delimiter=delimiter)
        headers = next(reader, [])

        valid_fields = set(ENTITY_FIELDS[entity_type])
        mapping: dict[str, str] = {}

        for header in headers:
            clean = header.strip().lower().replace(" ", "_")
            # Direct match
            if clean in valid_fields:
                mapping[header] = clean
            # Alias match
            elif clean in COLUMN_ALIASES and COLUMN_ALIASES[clean] in valid_fields:
                mapping[header] = COLUMN_ALIASES[clean]

        return mapping

    def list_imports(self, tenant_id: str) -> list[ImportJob]:
        """List import jobs for a tenant."""
        jobs = [j for j in self._jobs.values() if j.tenant_id == tenant_id]
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)

    # --- Private helpers ---

    def _get_job_or_raise(self, job_id: str) -> ImportJob:
        job = self._jobs.get(job_id)
        if not job:
            raise KeyError(f"Import job not found: {job_id}")
        return job

    def _detect_delimiter(self, content: str) -> str:
        first_line = content.split("\n")[0] if content else ""
        if "\t" in first_line:
            return "\t"
        if ";" in first_line:
            return ";"
        return ","

    def _parse_raw(self, raw_data: str, config: ImportConfig) -> list[dict]:
        """Parse raw CSV/TSV data into list of dicts using config mapping."""
        delimiter = config.delimiter or self._detect_delimiter(raw_data)
        reader = csv.reader(io.StringIO(raw_data), delimiter=delimiter)
        rows = list(reader)

        if not rows:
            return []

        headers: list[str] = []
        data_start = 0

        if config.has_header and rows:
            headers = [h.strip() for h in rows[0]]
            data_start = 1
        else:
            # Generate generic column names
            if rows:
                headers = [f"col_{i}" for i in range(len(rows[0]))]

        # Apply field mapping
        mapping = config.field_mapping or {}
        mapped_headers = []
        for h in headers:
            if h in mapping:
                mapped_headers.append(mapping[h])
            else:
                # Try auto-mapping
                clean = h.lower().replace(" ", "_")
                if clean in COLUMN_ALIASES:
                    mapped_headers.append(COLUMN_ALIASES[clean])
                else:
                    mapped_headers.append(h)

        result: list[dict] = []
        for row in rows[data_start:]:
            if not row or all(cell.strip() == "" for cell in row):
                continue
            record = {}
            for j, cell in enumerate(row):
                if j < len(mapped_headers):
                    record[mapped_headers[j]] = cell.strip()
            result.append(record)

        return result

    def _dedup_key(self, row: dict, entity_type: str) -> str:
        """Generate a dedup key for a row based on entity type."""
        if entity_type == "leads":
            email = row.get("contact_email", "").lower()
            if email:
                return f"email:{email}"
            return f"company:{row.get('company_name', '')}:{row.get('contact_name', '')}"
        elif entity_type == "customers":
            return f"email:{row.get('contact_email', '').lower()}"
        elif entity_type == "tickets":
            return f"ticket:{row.get('customer_id', '')}:{row.get('subject', '')}"
        elif entity_type == "contacts":
            return f"contact:{row.get('email', '').lower()}"
        return str(uuid.uuid4())  # No dedup possible


# Module-level singleton
import_engine = DataImportEngine()
