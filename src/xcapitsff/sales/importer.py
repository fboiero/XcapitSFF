"""Lead data importer — CSV/TSV parsing, validation, dedup, and bulk import."""

import csv
import io
import logging
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.models import Lead
from xcapitsff.sales.scoring import calculate_icp_score

logger = logging.getLogger(__name__)

VALID_REGIONS = {"LATAM", "Iberia"}
VALID_AFINIDAD = {"HIGH", "MEDIUM", "LOW"}
REGION_ALIASES = {
    "latam": "LATAM",
    "lat": "LATAM",
    "latinoamerica": "LATAM",
    "iberia": "Iberia",
    "españa": "Iberia",
    "spain": "Iberia",
    "portugal": "Iberia",
    "europe": "Iberia",
}


@dataclass
class ImportError:
    row: int
    field: str
    value: str
    message: str


@dataclass
class ImportResult:
    total_rows: int = 0
    parsed: int = 0
    imported: int = 0
    skipped_empty: int = 0
    skipped_duplicate: int = 0
    errors: list[ImportError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        return (self.imported / self.total_rows * 100) if self.total_rows > 0 else 0.0

    def summary(self) -> str:
        lines = [
            f"Import Summary:",
            f"  Total rows:      {self.total_rows}",
            f"  Parsed:          {self.parsed}",
            f"  Imported:        {self.imported}",
            f"  Skipped (empty): {self.skipped_empty}",
            f"  Skipped (dupes): {self.skipped_duplicate}",
            f"  Errors:          {len(self.errors)}",
            f"  Success rate:    {self.success_rate:.1f}%",
        ]
        if self.warnings:
            lines.append(f"  Warnings:")
            for w in self.warnings[:10]:
                lines.append(f"    - {w}")
        if self.errors:
            lines.append(f"  First errors:")
            for e in self.errors[:5]:
                lines.append(f"    - Row {e.row}: {e.field}='{e.value}' — {e.message}")
        return "\n".join(lines)


def _normalize_region(raw: str) -> str | None:
    stripped = raw.strip()
    if stripped in VALID_REGIONS:
        return stripped
    alias = REGION_ALIASES.get(stripped.lower())
    if alias:
        return alias
    return None


def _normalize_afinidad(raw: str) -> str:
    upper = raw.strip().upper()
    if upper in VALID_AFINIDAD:
        return upper
    if upper in ("ALTA", "ALTO", "HI"):
        return "HIGH"
    if upper in ("MEDIA", "MED"):
        return "MEDIUM"
    if upper in ("BAJA", "BAJO", "LO"):
        return "LOW"
    return "MEDIUM"


def _parse_c_level(raw: str) -> bool:
    lower = raw.strip().lower()
    return lower in ("si", "sí", "yes", "true", "1", "s", "y")


def _parse_score(raw: str) -> float | None:
    stripped = raw.strip()
    if not stripped:
        return None
    try:
        score = float(stripped)
        if score < 0:
            return 0.0
        if score > 100:
            return 100.0
        return score
    except ValueError:
        return None


def _detect_delimiter(content: str) -> str:
    first_line = content.split("\n")[0] if content else ""
    if "\t" in first_line:
        return "\t"
    if ";" in first_line:
        return ";"
    return ","


def _detect_header(first_row: list[str]) -> bool:
    header_keywords = {"region", "c-level", "score", "afinidad", "icp", "level", "company"}
    row_text = " ".join(cell.lower() for cell in first_row)
    return any(kw in row_text for kw in header_keywords)


def parse_leads(content: str) -> tuple[list[dict], ImportResult]:
    """Parse CSV/TSV content with auto-detection of delimiter and header."""
    result = ImportResult()
    leads = []

    delimiter = _detect_delimiter(content)
    reader = csv.reader(io.StringIO(content), delimiter=delimiter)
    rows = list(reader)
    result.total_rows = len(rows)

    if not rows:
        return leads, result

    start = 1 if _detect_header(rows[0]) else 0

    for i, row in enumerate(rows[start:], start=start + 1):
        # Skip empty rows
        if not row or all(cell.strip() == "" for cell in row):
            result.skipped_empty += 1
            continue

        # Parse region
        region_raw = row[0].strip() if len(row) > 0 else ""
        if not region_raw:
            result.skipped_empty += 1
            continue

        region = _normalize_region(region_raw)
        if not region:
            result.errors.append(ImportError(i, "region", region_raw, "Unknown region"))
            continue

        # Parse C-Level
        c_level_raw = row[1].strip() if len(row) > 1 else ""
        c_level = _parse_c_level(c_level_raw)

        # Parse Score ICP
        score_raw = row[2].strip() if len(row) > 2 else ""
        score_icp = _parse_score(score_raw)
        if score_raw and score_icp is None:
            result.errors.append(ImportError(i, "score_icp", score_raw, "Invalid number"))
            continue

        # Parse Afinidad
        afinidad_raw = row[3].strip() if len(row) > 3 else ""
        afinidad = _normalize_afinidad(afinidad_raw) if afinidad_raw else "MEDIUM"

        # Optional: company name (column 4)
        company = row[4].strip() if len(row) > 4 else None

        # Optional: contact email (column 5)
        email = row[5].strip() if len(row) > 5 else None

        leads.append({
            "region": region,
            "c_level": c_level,
            "score_icp": score_icp,
            "afinidad": afinidad,
            "company_name": company,
            "contact_email": email,
        })
        result.parsed += 1

    return leads, result


# Backward-compatible wrapper
def parse_leads_tsv(content: str) -> list[dict]:
    leads, _ = parse_leads(content)
    return leads


async def _find_duplicates(db: AsyncSession, leads_data: list[dict]) -> set[str]:
    """Find leads that already exist based on email or region+c_level+score+afinidad combo."""
    existing_keys: set[str] = set()

    # Get existing leads' fingerprints
    existing = await db.execute(select(Lead))
    for lead in existing.scalars().all():
        if lead.contact_email:
            existing_keys.add(f"email:{lead.contact_email.lower()}")
        key = f"{lead.region}:{lead.c_level}:{lead.score_icp}:{lead.afinidad}"
        existing_keys.add(key)

    return existing_keys


def _lead_fingerprint(data: dict) -> tuple[str | None, str]:
    email_key = f"email:{data['contact_email'].lower()}" if data.get("contact_email") else None
    combo_key = f"{data['region']}:{data['c_level']}:{data.get('score_icp')}:{data['afinidad']}"
    return email_key, combo_key


async def import_leads_bulk(
    db: AsyncSession,
    leads_data: list[dict],
    skip_duplicates: bool = True,
    batch_size: int = 100,
) -> ImportResult:
    """Import leads in bulk with validation, dedup, and batching."""
    result = ImportResult(total_rows=len(leads_data), parsed=len(leads_data))

    existing_keys = await _find_duplicates(db, leads_data) if skip_duplicates else set()

    batch: list[Lead] = []
    for data in leads_data:
        # Dedup check
        if skip_duplicates:
            email_key, combo_key = _lead_fingerprint(data)
            if email_key and email_key in existing_keys:
                result.skipped_duplicate += 1
                continue
            if combo_key in existing_keys:
                result.skipped_duplicate += 1
                continue
            if email_key:
                existing_keys.add(email_key)
            existing_keys.add(combo_key)

        score = calculate_icp_score(
            region=data["region"],
            c_level=data["c_level"],
            existing_score=data.get("score_icp"),
            afinidad=data["afinidad"],
        )

        lead = Lead(
            company_name=data.get("company_name"),
            contact_email=data.get("contact_email"),
            region=data["region"],
            c_level=data["c_level"],
            score_icp=score,
            afinidad=data["afinidad"],
        )
        batch.append(lead)

        if len(batch) >= batch_size:
            db.add_all(batch)
            await db.flush()
            result.imported += len(batch)
            batch = []

    if batch:
        db.add_all(batch)
        await db.flush()
        result.imported += len(batch)

    logger.info(result.summary())
    return result


async def import_from_file(db: AsyncSession, file_path: str) -> int:
    """Import leads from a TSV/CSV file. Returns count imported."""
    path = Path(file_path)
    content = path.read_text(encoding="utf-8")
    leads_data, parse_result = parse_leads(content)
    import_result = await import_leads_bulk(db, leads_data)
    return import_result.imported
