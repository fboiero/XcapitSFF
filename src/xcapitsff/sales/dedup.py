"""Lead Deduplication Engine — find and merge duplicate leads.

Duplicates are identified by email match, company name similarity,
or a combination of signals. Merging preserves the highest-quality
data from each duplicate.
"""

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.models import Lead

logger = logging.getLogger(__name__)


@dataclass
class DuplicateGroup:
    primary_id: int
    duplicate_ids: list[int]
    match_type: str  # "email", "company", "combined"
    confidence: float
    details: str = ""


@dataclass
class DedupReport:
    total_leads: int
    groups_found: int
    total_duplicates: int
    by_match_type: dict[str, int] = field(default_factory=dict)
    groups: list[DuplicateGroup] = field(default_factory=list)
    scanned_at: datetime = field(default_factory=datetime.now)


def _normalize_company(name: str | None) -> str:
    """Normalize company name for comparison."""
    if not name:
        return ""
    text = name.lower().strip()
    # Remove accents
    nfkd = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Remove common suffixes
    for suffix in [" sa", " s.a.", " srl", " s.r.l.", " sas", " s.a.s.",
                   " ltda", " ltd", " inc", " corp", " llc", " gmbh",
                   " spa", " s.p.a."]:
        if text.endswith(suffix):
            text = text[:-len(suffix)]
    # Remove punctuation
    text = re.sub(r"[^\w\s]", "", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _normalize_email(email: str | None) -> str:
    """Normalize email for comparison."""
    if not email:
        return ""
    return email.lower().strip()


def _company_similarity(a: str, b: str) -> float:
    """Simple similarity score between two normalized company names."""
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    # Check if one contains the other
    if a in b or b in a:
        shorter = min(len(a), len(b))
        longer = max(len(a), len(b))
        return shorter / longer
    # Token overlap
    tokens_a = set(a.split())
    tokens_b = set(b.split())
    if not tokens_a or not tokens_b:
        return 0.0
    overlap = tokens_a & tokens_b
    return len(overlap) / max(len(tokens_a), len(tokens_b))


async def find_duplicates(
    db: AsyncSession,
    email_threshold: float = 1.0,
    company_threshold: float = 0.8,
) -> DedupReport:
    """Scan all leads and find duplicate groups."""
    result = await db.execute(select(Lead).order_by(Lead.id))
    all_leads = list(result.scalars().all())

    report = DedupReport(total_leads=len(all_leads))
    seen_in_group: set[int] = set()

    # Phase 1: Exact email matches
    email_map: dict[str, list[Lead]] = {}
    for lead in all_leads:
        norm = _normalize_email(lead.contact_email)
        if norm:
            email_map.setdefault(norm, []).append(lead)

    for email, leads in email_map.items():
        if len(leads) > 1:
            primary = max(leads, key=lambda l: l.score_icp or 0)
            dups = [l.id for l in leads if l.id != primary.id]
            if dups:
                group = DuplicateGroup(
                    primary_id=primary.id,
                    duplicate_ids=dups,
                    match_type="email",
                    confidence=1.0,
                    details=f"Shared email: {email}",
                )
                report.groups.append(group)
                seen_in_group.add(primary.id)
                seen_in_group.update(dups)

    # Phase 2: Company name similarity
    company_leads = [
        (lead, _normalize_company(lead.company_name))
        for lead in all_leads
        if lead.id not in seen_in_group and lead.company_name
    ]

    for i, (lead_a, name_a) in enumerate(company_leads):
        if lead_a.id in seen_in_group or not name_a:
            continue
        group_members = []
        for j, (lead_b, name_b) in enumerate(company_leads[i + 1:], start=i + 1):
            if lead_b.id in seen_in_group or not name_b:
                continue
            sim = _company_similarity(name_a, name_b)
            if sim >= company_threshold:
                group_members.append(lead_b)
                seen_in_group.add(lead_b.id)

        if group_members:
            all_in_group = [lead_a] + group_members
            primary = max(all_in_group, key=lambda l: l.score_icp or 0)
            dups = [l.id for l in all_in_group if l.id != primary.id]
            group = DuplicateGroup(
                primary_id=primary.id,
                duplicate_ids=dups,
                match_type="company",
                confidence=company_threshold,
                details=f"Similar company: {lead_a.company_name}",
            )
            report.groups.append(group)
            seen_in_group.add(lead_a.id)

    report.groups_found = len(report.groups)
    report.total_duplicates = sum(len(g.duplicate_ids) for g in report.groups)
    report.by_match_type = {}
    for g in report.groups:
        report.by_match_type[g.match_type] = report.by_match_type.get(g.match_type, 0) + 1

    return report


async def merge_duplicates(
    db: AsyncSession, primary_id: int, duplicate_ids: list[int]
) -> Lead | None:
    """Merge duplicate leads into the primary, keeping best data."""
    primary_result = await db.execute(select(Lead).where(Lead.id == primary_id))
    primary = primary_result.scalar_one_or_none()
    if not primary:
        return None

    dups_result = await db.execute(select(Lead).where(Lead.id.in_(duplicate_ids)))
    duplicates = list(dups_result.scalars().all())

    for dup in duplicates:
        # Fill in missing fields from duplicates
        if not primary.company_name and dup.company_name:
            primary.company_name = dup.company_name
        if not primary.contact_name and dup.contact_name:
            primary.contact_name = dup.contact_name
        if not primary.contact_email and dup.contact_email:
            primary.contact_email = dup.contact_email
        if not primary.notes:
            primary.notes = dup.notes
        elif dup.notes:
            primary.notes = f"{primary.notes}\n[Merged from #{dup.id}]: {dup.notes}"

        # Keep highest score
        if dup.score_icp and (not primary.score_icp or dup.score_icp > primary.score_icp):
            primary.score_icp = dup.score_icp

        # Delete duplicate
        await db.delete(dup)

    await db.flush()
    await db.refresh(primary)
    logger.info(f"Merged {len(duplicates)} leads into #{primary.id}")
    return primary
