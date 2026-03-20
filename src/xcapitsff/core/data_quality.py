"""Data-quality checks for the XcapitSFF database.

Each ``check_*`` function inspects a particular entity set and returns a
:class:`DataQualityReport` that summarises the issues found.
``run_full_quality_check`` orchestrates all individual checks and returns a
consolidated dictionary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.models import (
    Customer,
    Lead,
    LeadStage,
    Ticket,
    TicketMessage,
    TicketStatus,
)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class QualityIssue:
    """A single quality issue found during a check."""

    severity: str  # "critical", "warning", "info"
    entity_type: str  # "lead", "ticket", "customer"
    entity_id: int | None
    field: str | None
    description: str


@dataclass
class DataQualityReport:
    """Aggregated report from a quality-check run."""

    total_records: int = 0
    issues_found: int = 0
    issues_by_severity: dict[str, int] = field(default_factory=lambda: {
        "critical": 0,
        "warning": 0,
        "info": 0,
    })
    details: list[QualityIssue] = field(default_factory=list)

    def add_issue(self, issue: QualityIssue) -> None:
        self.details.append(issue)
        self.issues_found += 1
        self.issues_by_severity[issue.severity] = (
            self.issues_by_severity.get(issue.severity, 0) + 1
        )


# ---------------------------------------------------------------------------
# Lead quality
# ---------------------------------------------------------------------------


async def check_lead_quality(db: AsyncSession) -> DataQualityReport:
    """Run quality checks on the leads table.

    Checks performed:
    1. Orphan leads — no email **and** no company name.
    2. Duplicate leads — multiple leads sharing the same email address.
    3. Score outliers — ICP score at extreme ends (0 or 100).
    4. Stale raw leads — leads in the RAW stage for more than 90 days.
    """
    report = DataQualityReport()

    # Total count
    total_q = await db.execute(select(func.count(Lead.id)))
    report.total_records = total_q.scalar() or 0

    # 1. Orphan leads (no email AND no company name)
    orphan_q = await db.execute(
        select(Lead.id).where(
            (Lead.contact_email.is_(None) | (Lead.contact_email == ""))
            & (Lead.company_name.is_(None) | (Lead.company_name == ""))
        )
    )
    for (lead_id,) in orphan_q.all():
        report.add_issue(QualityIssue(
            severity="critical",
            entity_type="lead",
            entity_id=lead_id,
            field=None,
            description="Lead has no email and no company name (orphan record)",
        ))

    # 2. Duplicate leads (same non-null email)
    dup_q = await db.execute(
        select(Lead.contact_email, func.count(Lead.id).label("cnt"))
        .where(Lead.contact_email.isnot(None))
        .where(Lead.contact_email != "")
        .group_by(Lead.contact_email)
        .having(func.count(Lead.id) > 1)
    )
    for email, count in dup_q.all():
        report.add_issue(QualityIssue(
            severity="warning",
            entity_type="lead",
            entity_id=None,
            field="contact_email",
            description=f"Duplicate email '{email}' appears on {count} leads",
        ))

    # 3. Score outliers (ICP score exactly 0 or 100)
    outlier_q = await db.execute(
        select(Lead.id, Lead.score_icp).where(
            Lead.score_icp.isnot(None)
            & ((Lead.score_icp == 0) | (Lead.score_icp == 100))
        )
    )
    for lead_id, score in outlier_q.all():
        report.add_issue(QualityIssue(
            severity="info",
            entity_type="lead",
            entity_id=lead_id,
            field="score_icp",
            description=f"ICP score is at extreme value ({score}); may need review",
        ))

    # 4. Stale RAW leads (> 90 days)
    cutoff = datetime.now(tz=None) - timedelta(days=90)
    stale_q = await db.execute(
        select(Lead.id, Lead.created_at).where(
            (Lead.stage == LeadStage.RAW) & (Lead.created_at < cutoff)
        )
    )
    for lead_id, created_at in stale_q.all():
        days_old = (datetime.now(tz=None) - created_at).days
        report.add_issue(QualityIssue(
            severity="warning",
            entity_type="lead",
            entity_id=lead_id,
            field="stage",
            description=f"Lead has been in RAW stage for {days_old} days (> 90 day threshold)",
        ))

    return report


# ---------------------------------------------------------------------------
# Ticket quality
# ---------------------------------------------------------------------------


async def check_ticket_quality(db: AsyncSession) -> DataQualityReport:
    """Run quality checks on the tickets table.

    Checks performed:
    1. Tickets with no category.
    2. Resolved/closed tickets with no resolution text.
    3. Open tickets older than 30 days with no messages.
    """
    report = DataQualityReport()

    # Total count
    total_q = await db.execute(select(func.count(Ticket.id)))
    report.total_records = total_q.scalar() or 0

    # 1. Tickets with no category
    no_cat_q = await db.execute(
        select(Ticket.id).where(
            Ticket.category.is_(None) | (Ticket.category == "")
        )
    )
    for (ticket_id,) in no_cat_q.all():
        report.add_issue(QualityIssue(
            severity="warning",
            entity_type="ticket",
            entity_id=ticket_id,
            field="category",
            description="Ticket has no category assigned",
        ))

    # 2. Resolved / closed tickets with no resolution text
    no_res_q = await db.execute(
        select(Ticket.id, Ticket.status).where(
            Ticket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED])
            & (Ticket.resolution.is_(None) | (Ticket.resolution == ""))
        )
    )
    for ticket_id, status in no_res_q.all():
        report.add_issue(QualityIssue(
            severity="warning",
            entity_type="ticket",
            entity_id=ticket_id,
            field="resolution",
            description=f"Ticket is {status.value} but has no resolution text",
        ))

    # 3. Open tickets older than 30 days with no messages
    cutoff_30 = datetime.now(tz=None) - timedelta(days=30)

    # Sub-query: ticket IDs that have at least one message
    tickets_with_messages = (
        select(TicketMessage.ticket_id).distinct().subquery()
    )

    stale_open_q = await db.execute(
        select(Ticket.id, Ticket.created_at).where(
            (Ticket.status == TicketStatus.OPEN)
            & (Ticket.created_at < cutoff_30)
            & (Ticket.id.notin_(select(tickets_with_messages.c.ticket_id)))
        )
    )
    for ticket_id, created_at in stale_open_q.all():
        days_old = (datetime.now(tz=None) - created_at).days
        report.add_issue(QualityIssue(
            severity="critical",
            entity_type="ticket",
            entity_id=ticket_id,
            field=None,
            description=(
                f"Open ticket has been without any messages for {days_old} days "
                f"(> 30 day threshold)"
            ),
        ))

    return report


# ---------------------------------------------------------------------------
# Customer quality
# ---------------------------------------------------------------------------


async def check_customer_quality(db: AsyncSession) -> DataQualityReport:
    """Run quality checks on the customers table.

    Checks performed:
    1. Customers with no plan set.
    2. Duplicate customer emails.
    3. Customers with no associated tickets (may indicate inactive accounts).
    """
    report = DataQualityReport()

    # Total count
    total_q = await db.execute(select(func.count(Customer.id)))
    report.total_records = total_q.scalar() or 0

    # 1. Customers without a plan
    no_plan_q = await db.execute(
        select(Customer.id).where(
            Customer.plan.is_(None) | (Customer.plan == "")
        )
    )
    for (customer_id,) in no_plan_q.all():
        report.add_issue(QualityIssue(
            severity="warning",
            entity_type="customer",
            entity_id=customer_id,
            field="plan",
            description="Customer has no plan assigned",
        ))

    # 2. Duplicate customer emails
    dup_email_q = await db.execute(
        select(Customer.contact_email, func.count(Customer.id).label("cnt"))
        .where(Customer.contact_email.isnot(None))
        .where(Customer.contact_email != "")
        .group_by(Customer.contact_email)
        .having(func.count(Customer.id) > 1)
    )
    for email, count in dup_email_q.all():
        report.add_issue(QualityIssue(
            severity="critical",
            entity_type="customer",
            entity_id=None,
            field="contact_email",
            description=f"Duplicate customer email '{email}' appears on {count} records",
        ))

    # 3. Customers with zero tickets
    customers_with_tickets = (
        select(Ticket.customer_id).distinct().subquery()
    )
    no_tickets_q = await db.execute(
        select(Customer.id).where(
            Customer.id.notin_(select(customers_with_tickets.c.customer_id))
        )
    )
    for (customer_id,) in no_tickets_q.all():
        report.add_issue(QualityIssue(
            severity="info",
            entity_type="customer",
            entity_id=customer_id,
            field=None,
            description="Customer has no tickets; may be an inactive account",
        ))

    return report


# ---------------------------------------------------------------------------
# Full quality check
# ---------------------------------------------------------------------------


async def run_full_quality_check(db: AsyncSession) -> dict:
    """Run all quality checks and return a consolidated report dictionary.

    Returns a dict with keys: ``leads``, ``tickets``, ``customers``, and
    ``summary``.
    """
    lead_report = await check_lead_quality(db)
    ticket_report = await check_ticket_quality(db)
    customer_report = await check_customer_quality(db)

    total_issues = (
        lead_report.issues_found
        + ticket_report.issues_found
        + customer_report.issues_found
    )

    # Merge severity counts
    merged_severity: dict[str, int] = {"critical": 0, "warning": 0, "info": 0}
    for rpt in (lead_report, ticket_report, customer_report):
        for sev, cnt in rpt.issues_by_severity.items():
            merged_severity[sev] = merged_severity.get(sev, 0) + cnt

    def _serialize_report(report: DataQualityReport) -> dict:
        return {
            "total_records": report.total_records,
            "issues_found": report.issues_found,
            "issues_by_severity": dict(report.issues_by_severity),
            "details": [
                {
                    "severity": d.severity,
                    "entity_type": d.entity_type,
                    "entity_id": d.entity_id,
                    "field": d.field,
                    "description": d.description,
                }
                for d in report.details
            ],
        }

    return {
        "summary": {
            "total_issues": total_issues,
            "issues_by_severity": merged_severity,
        },
        "leads": _serialize_report(lead_report),
        "tickets": _serialize_report(ticket_report),
        "customers": _serialize_report(customer_report),
    }
