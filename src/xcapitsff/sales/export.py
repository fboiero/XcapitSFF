"""Export engine — generate CSV/JSON exports of leads and pipeline data."""

import csv
import io
import json
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.models import Lead, OutreachMessage


@dataclass
class ExportResult:
    format: str
    row_count: int
    content: str
    filename: str


async def export_leads_csv(
    db: AsyncSession,
    include_outreach: bool = False,
) -> ExportResult:
    """Export all leads to CSV format."""
    result = await db.execute(select(Lead).order_by(Lead.score_icp.desc().nullslast()))
    leads = list(result.scalars().all())

    output = io.StringIO()
    writer = csv.writer(output)

    headers = [
        "id", "company_name", "contact_name", "contact_email",
        "region", "c_level", "score_icp", "afinidad", "stage",
        "assigned_agent", "created_at", "updated_at",
    ]
    if include_outreach:
        headers.extend(["outreach_count", "last_outreach_channel", "last_outreach_date"])

    writer.writerow(headers)

    for lead in leads:
        row = [
            lead.id,
            lead.company_name or "",
            lead.contact_name or "",
            lead.contact_email or "",
            _enum_val(lead.region),
            "Si" if lead.c_level else "No",
            lead.score_icp or "",
            _enum_val(lead.afinidad),
            _enum_val(lead.stage),
            lead.assigned_agent or "",
            lead.created_at.isoformat() if lead.created_at else "",
            lead.updated_at.isoformat() if lead.updated_at else "",
        ]

        if include_outreach:
            outreach = await db.execute(
                select(OutreachMessage)
                .where(OutreachMessage.lead_id == lead.id)
                .order_by(OutreachMessage.created_at.desc())
            )
            messages = list(outreach.scalars().all())
            row.extend([
                len(messages),
                messages[0].channel if messages else "",
                messages[0].created_at.isoformat() if messages else "",
            ])

        writer.writerow(row)

    content = output.getvalue()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return ExportResult(
        format="csv",
        row_count=len(leads),
        content=content,
        filename=f"leads_export_{timestamp}.csv",
    )


async def export_leads_json(db: AsyncSession) -> ExportResult:
    """Export all leads to JSON format."""
    result = await db.execute(select(Lead).order_by(Lead.score_icp.desc().nullslast()))
    leads = list(result.scalars().all())

    data = []
    for lead in leads:
        data.append({
            "id": lead.id,
            "company_name": lead.company_name,
            "contact_name": lead.contact_name,
            "contact_email": lead.contact_email,
            "region": _enum_val(lead.region),
            "c_level": lead.c_level,
            "score_icp": lead.score_icp,
            "afinidad": _enum_val(lead.afinidad),
            "stage": _enum_val(lead.stage),
            "assigned_agent": lead.assigned_agent,
            "created_at": lead.created_at.isoformat() if lead.created_at else None,
            "updated_at": lead.updated_at.isoformat() if lead.updated_at else None,
        })

    content = json.dumps(data, indent=2, ensure_ascii=False)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return ExportResult(
        format="json",
        row_count=len(leads),
        content=content,
        filename=f"leads_export_{timestamp}.json",
    )


async def export_pipeline_summary(db: AsyncSession) -> ExportResult:
    """Export pipeline summary as CSV."""
    from xcapitsff.sales.pipeline import get_pipeline_funnel, get_pipeline_stats

    stats = await get_pipeline_stats(db)
    funnel = await get_pipeline_funnel(db)

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Pipeline Summary", datetime.now().isoformat()])
    writer.writerow([])
    writer.writerow(["Metric", "Value"])
    writer.writerow(["Total Leads", stats.total_leads])
    writer.writerow(["Avg ICP Score", stats.avg_score_icp or "N/A"])
    writer.writerow(["C-Level Count", stats.c_level_count])
    writer.writerow(["Conversion Rate", f"{stats.conversion_rate}%" if stats.conversion_rate else "N/A"])
    writer.writerow([])
    writer.writerow(["Funnel"])
    writer.writerow(["Stage", "Count"])
    for item in funnel:
        writer.writerow([item["stage"], item["count"]])
    writer.writerow([])
    writer.writerow(["By Region"])
    for region, count in stats.by_region.items():
        writer.writerow([region, count])
    writer.writerow([])
    writer.writerow(["By Afinidad"])
    for af, count in stats.by_afinidad.items():
        writer.writerow([af, count])

    content = output.getvalue()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return ExportResult(
        format="csv",
        row_count=stats.total_leads,
        content=content,
        filename=f"pipeline_summary_{timestamp}.csv",
    )


def _enum_val(val) -> str:
    return val.value if hasattr(val, "value") else str(val)
