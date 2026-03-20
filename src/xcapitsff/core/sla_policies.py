"""SLA Policy Management — configurable SLA policies per tenant.

Provides multi-tenant SLA policy definitions with configurable targets
for first response, resolution, and update frequency. Tracks breaches
and calculates compliance metrics.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class SLAPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class SLATarget:
    first_response_minutes: int
    resolution_minutes: int
    update_frequency_minutes: int


@dataclass
class SLAPolicy:
    id: str
    tenant_id: str
    name: str
    description: str
    priority: SLAPriority
    targets: SLATarget
    business_hours_only: bool = False
    business_hours: dict = field(default_factory=dict)
    active: bool = True
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class SLABreach:
    id: str
    tenant_id: str
    ticket_id: str
    policy_id: str
    breach_type: str  # first_response, resolution, update
    breached_at: datetime
    target_minutes: float
    actual_minutes: float
    escalated: bool = False


@dataclass
class SLAStatus:
    ticket_id: str
    policy_id: str
    first_response_due: datetime
    first_response_met: bool | None
    resolution_due: datetime
    resolution_met: bool | None
    next_update_due: datetime | None
    breaches: list[SLABreach]
    is_within_sla: bool
    time_remaining_minutes: float


# Default policy definitions (target minutes)
DEFAULT_POLICIES: list[dict] = [
    {
        "name": "Critical SLA",
        "description": "Critical priority — 1h response, 4h resolution",
        "priority": SLAPriority.CRITICAL,
        "targets": SLATarget(
            first_response_minutes=60,
            resolution_minutes=240,
            update_frequency_minutes=30,
        ),
    },
    {
        "name": "High SLA",
        "description": "High priority — 4h response, 8h resolution",
        "priority": SLAPriority.HIGH,
        "targets": SLATarget(
            first_response_minutes=240,
            resolution_minutes=480,
            update_frequency_minutes=60,
        ),
    },
    {
        "name": "Medium SLA",
        "description": "Medium priority — 8h response, 24h resolution",
        "priority": SLAPriority.MEDIUM,
        "targets": SLATarget(
            first_response_minutes=480,
            resolution_minutes=1440,
            update_frequency_minutes=240,
        ),
    },
    {
        "name": "Low SLA",
        "description": "Low priority — 24h response, 72h resolution",
        "priority": SLAPriority.LOW,
        "targets": SLATarget(
            first_response_minutes=1440,
            resolution_minutes=4320,
            update_frequency_minutes=480,
        ),
    },
]


def _calculate_deadline(
    start: datetime,
    minutes: int,
    business_hours_only: bool,
    business_hours: dict,
) -> datetime:
    """Calculate the deadline, optionally respecting business hours.

    When *business_hours_only* is ``True``, only minutes within the
    configured working window count towards the target. Otherwise
    the deadline is simply ``start + timedelta(minutes=minutes)``.
    """
    if not business_hours_only or not business_hours:
        return start + timedelta(minutes=minutes)

    start_hour = business_hours.get("start_hour", 9)
    end_hour = business_hours.get("end_hour", 17)
    working_days = business_hours.get("working_days", [0, 1, 2, 3, 4])
    hours_per_day = end_hour - start_hour
    if hours_per_day <= 0:
        return start + timedelta(minutes=minutes)

    remaining = minutes
    current = start

    # If starting outside business hours, fast-forward to next window.
    if current.weekday() not in working_days or current.hour >= end_hour:
        current = current.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        current += timedelta(days=1)
        while current.weekday() not in working_days:
            current += timedelta(days=1)
    elif current.hour < start_hour:
        current = current.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        while current.weekday() not in working_days:
            current += timedelta(days=1)

    while remaining > 0:
        if current.weekday() not in working_days:
            current = current.replace(hour=start_hour, minute=0, second=0, microsecond=0)
            current += timedelta(days=1)
            continue

        available_today = (end_hour - current.hour) * 60 - current.minute
        if available_today <= 0:
            current = current.replace(hour=start_hour, minute=0, second=0, microsecond=0)
            current += timedelta(days=1)
            continue

        if remaining <= available_today:
            current += timedelta(minutes=remaining)
            remaining = 0
        else:
            remaining -= available_today
            current = current.replace(hour=start_hour, minute=0, second=0, microsecond=0)
            current += timedelta(days=1)
            while current.weekday() not in working_days:
                current += timedelta(days=1)

    return current


class SLAPolicyManager:
    """In-memory SLA policy manager with multi-tenant support."""

    def __init__(self) -> None:
        self._policies: dict[str, SLAPolicy] = {}
        self._breaches: list[SLABreach] = []

    # ---- CRUD ----

    def create_policy(
        self,
        tenant_id: str,
        name: str,
        priority: SLAPriority,
        targets: SLATarget,
        description: str = "",
        business_hours_only: bool = False,
        business_hours: dict | None = None,
    ) -> SLAPolicy:
        policy = SLAPolicy(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            name=name,
            description=description,
            priority=priority,
            targets=targets,
            business_hours_only=business_hours_only,
            business_hours=business_hours or {},
        )
        self._policies[policy.id] = policy
        logger.info("Created SLA policy %s for tenant %s", policy.id, tenant_id)
        return policy

    def update_policy(self, policy_id: str, **kwargs) -> SLAPolicy:
        policy = self._policies.get(policy_id)
        if policy is None:
            raise ValueError(f"Policy {policy_id} not found")
        for key, value in kwargs.items():
            if hasattr(policy, key) and key not in ("id", "created_at"):
                setattr(policy, key, value)
        logger.info("Updated SLA policy %s", policy_id)
        return policy

    def delete_policy(self, policy_id: str) -> bool:
        if policy_id in self._policies:
            del self._policies[policy_id]
            logger.info("Deleted SLA policy %s", policy_id)
            return True
        return False

    def list_policies(self, tenant_id: str) -> list[SLAPolicy]:
        return [p for p in self._policies.values() if p.tenant_id == tenant_id]

    def get_policy(self, policy_id: str) -> SLAPolicy | None:
        return self._policies.get(policy_id)

    def get_policy_for_ticket(
        self, tenant_id: str, priority: SLAPriority
    ) -> SLAPolicy | None:
        """Return the first active policy that matches tenant + priority."""
        for policy in self._policies.values():
            if (
                policy.tenant_id == tenant_id
                and policy.priority == priority
                and policy.active
            ):
                return policy
        return None

    # ---- SLA calculation ----

    def calculate_sla_status(
        self,
        ticket_id: str,
        policy_id: str,
        created_at: datetime,
        first_response_at: datetime | None = None,
        resolved_at: datetime | None = None,
        last_update_at: datetime | None = None,
    ) -> SLAStatus:
        policy = self._policies.get(policy_id)
        if policy is None:
            raise ValueError(f"Policy {policy_id} not found")

        targets = policy.targets
        bh_only = policy.business_hours_only
        bh = policy.business_hours

        first_response_due = _calculate_deadline(
            created_at, targets.first_response_minutes, bh_only, bh
        )
        resolution_due = _calculate_deadline(
            created_at, targets.resolution_minutes, bh_only, bh
        )

        if last_update_at:
            next_update_due: datetime | None = _calculate_deadline(
                last_update_at, targets.update_frequency_minutes, bh_only, bh
            )
        else:
            next_update_due = _calculate_deadline(
                created_at, targets.update_frequency_minutes, bh_only, bh
            )

        # Determine met/breached
        now = datetime.now()

        if first_response_at is not None:
            first_response_met = first_response_at <= first_response_due
        elif now > first_response_due:
            first_response_met = False
        else:
            first_response_met = None

        if resolved_at is not None:
            resolution_met = resolved_at <= resolution_due
        elif now > resolution_due:
            resolution_met = False
        else:
            resolution_met = None

        breaches: list[SLABreach] = []
        if first_response_met is False:
            actual = (
                (first_response_at - created_at).total_seconds() / 60
                if first_response_at
                else (now - created_at).total_seconds() / 60
            )
            breaches.append(
                SLABreach(
                    id=str(uuid.uuid4()),
                    tenant_id=policy.tenant_id,
                    ticket_id=ticket_id,
                    policy_id=policy_id,
                    breach_type="first_response",
                    breached_at=first_response_due,
                    target_minutes=targets.first_response_minutes,
                    actual_minutes=round(actual, 1),
                )
            )

        if resolution_met is False:
            actual = (
                (resolved_at - created_at).total_seconds() / 60
                if resolved_at
                else (now - created_at).total_seconds() / 60
            )
            breaches.append(
                SLABreach(
                    id=str(uuid.uuid4()),
                    tenant_id=policy.tenant_id,
                    ticket_id=ticket_id,
                    policy_id=policy_id,
                    breach_type="resolution",
                    breached_at=resolution_due,
                    target_minutes=targets.resolution_minutes,
                    actual_minutes=round(actual, 1),
                )
            )

        is_within_sla = first_response_met is not False and resolution_met is not False

        # Time remaining: smallest positive deadline gap
        if resolved_at is not None:
            time_remaining = 0.0
        else:
            remaining_first = (
                (first_response_due - now).total_seconds() / 60
                if first_response_met is None
                else float("inf")
            )
            remaining_resolution = (resolution_due - now).total_seconds() / 60
            time_remaining = round(min(remaining_first, remaining_resolution), 1)

        return SLAStatus(
            ticket_id=ticket_id,
            policy_id=policy_id,
            first_response_due=first_response_due,
            first_response_met=first_response_met,
            resolution_due=resolution_due,
            resolution_met=resolution_met,
            next_update_due=next_update_due,
            breaches=breaches,
            is_within_sla=is_within_sla,
            time_remaining_minutes=time_remaining,
        )

    # ---- Breach tracking ----

    def record_breach(
        self,
        tenant_id: str,
        ticket_id: str,
        policy_id: str,
        breach_type: str,
        target_minutes: float,
        actual_minutes: float,
    ) -> SLABreach:
        breach = SLABreach(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            ticket_id=ticket_id,
            policy_id=policy_id,
            breach_type=breach_type,
            breached_at=datetime.now(),
            target_minutes=target_minutes,
            actual_minutes=actual_minutes,
        )
        self._breaches.append(breach)
        logger.info(
            "Recorded SLA breach %s for ticket %s (type=%s)",
            breach.id,
            ticket_id,
            breach_type,
        )
        return breach

    def get_breaches(self, tenant_id: str, days: int = 30) -> list[SLABreach]:
        cutoff = datetime.now() - timedelta(days=days)
        return [
            b
            for b in self._breaches
            if b.tenant_id == tenant_id and b.breached_at >= cutoff
        ]

    # ---- Compliance ----

    def get_sla_compliance(self, tenant_id: str, days: int = 30) -> dict:
        breaches = self.get_breaches(tenant_id, days)
        total_tickets = len({b.ticket_id for b in breaches})

        first_response_breaches = [
            b for b in breaches if b.breach_type == "first_response"
        ]
        resolution_breaches = [b for b in breaches if b.breach_type == "resolution"]

        # Group breaches by priority via policy lookup
        by_priority: dict[str, dict] = {}
        for priority in SLAPriority:
            priority_breaches = [
                b
                for b in breaches
                if self._policies.get(b.policy_id)
                and self._policies[b.policy_id].priority == priority
            ]
            by_priority[priority.value] = {
                "breaches": len(priority_breaches),
                "tickets_affected": len({b.ticket_id for b in priority_breaches}),
            }

        avg_response = (
            round(
                sum(b.actual_minutes for b in first_response_breaches)
                / len(first_response_breaches),
                1,
            )
            if first_response_breaches
            else 0.0
        )
        avg_resolution = (
            round(
                sum(b.actual_minutes for b in resolution_breaches)
                / len(resolution_breaches),
                1,
            )
            if resolution_breaches
            else 0.0
        )

        breached_ticket_count = total_tickets
        # We don't track total tickets that were within SLA through breaches
        # alone, so compliance is based only on breach records.
        compliance_rate = 0.0 if total_tickets > 0 else 100.0

        return {
            "total_tickets": total_tickets,
            "within_sla": 0,
            "breached": breached_ticket_count,
            "compliance_rate": compliance_rate,
            "by_priority": by_priority,
            "avg_response_minutes": avg_response,
            "avg_resolution_minutes": avg_resolution,
        }

    # ---- Defaults ----

    def setup_defaults(self, tenant_id: str) -> list[SLAPolicy]:
        """Create the four default SLA policies for a new tenant."""
        created: list[SLAPolicy] = []
        for defn in DEFAULT_POLICIES:
            policy = self.create_policy(
                tenant_id=tenant_id,
                name=defn["name"],
                priority=defn["priority"],
                targets=defn["targets"],
                description=defn["description"],
            )
            created.append(policy)
        logger.info("Set up %d default SLA policies for tenant %s", len(created), tenant_id)
        return created


# Singleton
sla_policy_manager = SLAPolicyManager()
