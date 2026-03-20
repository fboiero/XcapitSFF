"""Saved views & filters — persist user-defined views for entity lists.

Users can create, share, and reuse filtered/sorted/columned views
for leads, tickets, customers, etc.
"""

import copy
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from operator import itemgetter

logger = logging.getLogger(__name__)


class ViewEntity(str, Enum):
    LEADS = "leads"
    TICKETS = "tickets"
    CUSTOMERS = "customers"
    CONTACTS = "contacts"
    COMPANIES = "companies"
    DEALS = "deals"


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


class FilterOperator(str, Enum):
    EQ = "eq"
    NE = "ne"
    GT = "gt"
    LT = "lt"
    GTE = "gte"
    LTE = "lte"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    IS_EMPTY = "is_empty"
    IS_NOT_EMPTY = "is_not_empty"


@dataclass
class FilterCondition:
    field: str
    operator: FilterOperator | str
    value: object = None

    def __post_init__(self) -> None:
        if isinstance(self.operator, str):
            self.operator = FilterOperator(self.operator)

    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "operator": self.operator.value if isinstance(self.operator, FilterOperator) else self.operator,
            "value": self.value,
        }


@dataclass
class ViewConfig:
    columns: list[str] = field(default_factory=list)
    filters: list[FilterCondition] = field(default_factory=list)
    sort_by: str = ""
    sort_order: SortOrder = SortOrder.DESC
    group_by: str | None = None
    page_size: int = 25

    def to_dict(self) -> dict:
        return {
            "columns": self.columns,
            "filters": [f.to_dict() for f in self.filters],
            "sort_by": self.sort_by,
            "sort_order": self.sort_order.value,
            "group_by": self.group_by,
            "page_size": self.page_size,
        }


@dataclass
class SavedView:
    id: str
    tenant_id: str
    user_id: str | None
    entity: ViewEntity
    name: str
    description: str
    config: ViewConfig
    is_default: bool = False
    is_shared: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    usage_count: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "entity": self.entity.value,
            "name": self.name,
            "description": self.description,
            "config": self.config.to_dict(),
            "is_default": self.is_default,
            "is_shared": self.is_shared,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "usage_count": self.usage_count,
        }


def _match_filter(row: dict, condition: FilterCondition) -> bool:
    """Evaluate a single filter condition against a row dict."""
    val = row.get(condition.field)
    op = condition.operator

    if op == FilterOperator.IS_EMPTY:
        return val is None or val == "" or val == []
    if op == FilterOperator.IS_NOT_EMPTY:
        return val is not None and val != "" and val != []

    target = condition.value

    if op == FilterOperator.EQ:
        return val == target
    if op == FilterOperator.NE:
        return val != target
    if op == FilterOperator.GT:
        return val is not None and val > target
    if op == FilterOperator.LT:
        return val is not None and val < target
    if op == FilterOperator.GTE:
        return val is not None and val >= target
    if op == FilterOperator.LTE:
        return val is not None and val <= target
    if op == FilterOperator.IN:
        return val in (target or [])
    if op == FilterOperator.NOT_IN:
        return val not in (target or [])
    if op == FilterOperator.CONTAINS:
        if isinstance(val, str) and isinstance(target, str):
            return target.lower() in val.lower()
        return False

    return True


# Pre-built default views
DEFAULT_VIEWS: dict[ViewEntity, list[dict]] = {
    ViewEntity.LEADS: [
        {
            "name": "Hot Leads",
            "description": "High-score leads ready for outreach",
            "config": ViewConfig(
                columns=["company_name", "contact_name", "score_icp", "stage", "region"],
                filters=[FilterCondition("score_icp", FilterOperator.GTE, 80)],
                sort_by="score_icp",
                sort_order=SortOrder.DESC,
            ),
        },
        {
            "name": "New This Week",
            "description": "Leads created recently",
            "config": ViewConfig(
                columns=["company_name", "contact_name", "created_at", "stage"],
                sort_by="created_at",
                sort_order=SortOrder.DESC,
                page_size=50,
            ),
        },
    ],
    ViewEntity.TICKETS: [
        {
            "name": "Open Tickets",
            "description": "All unresolved tickets",
            "config": ViewConfig(
                columns=["subject", "status", "priority", "assigned_agent", "created_at"],
                filters=[FilterCondition("status", FilterOperator.IN, ["open", "in_progress"])],
                sort_by="created_at",
                sort_order=SortOrder.DESC,
            ),
        },
        {
            "name": "Urgent Priority",
            "description": "Tickets with urgent priority",
            "config": ViewConfig(
                columns=["subject", "status", "priority", "assigned_agent"],
                filters=[FilterCondition("priority", FilterOperator.EQ, "urgent")],
                sort_by="created_at",
                sort_order=SortOrder.DESC,
            ),
        },
    ],
    ViewEntity.CUSTOMERS: [
        {
            "name": "VIP Customers",
            "description": "Customers on premium plans",
            "config": ViewConfig(
                columns=["company_name", "contact_name", "plan", "region"],
                filters=[FilterCondition("plan", FilterOperator.EQ, "premium")],
                sort_by="company_name",
                sort_order=SortOrder.ASC,
            ),
        },
    ],
}


class SavedViewManager:
    """In-memory saved views storage with query and apply capabilities."""

    def __init__(self) -> None:
        self._views: dict[str, SavedView] = {}
        # Track per-user defaults: (user_id, entity) -> view_id
        self._defaults: dict[tuple[str, ViewEntity], str] = {}

    def create(
        self,
        tenant_id: str,
        user_id: str | None,
        entity: ViewEntity | str,
        name: str,
        config: ViewConfig,
        description: str = "",
        is_shared: bool = False,
    ) -> SavedView:
        """Create a new saved view."""
        if isinstance(entity, str):
            entity = ViewEntity(entity)

        view = SavedView(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id=user_id,
            entity=entity,
            name=name,
            description=description,
            config=config,
            is_shared=is_shared,
        )
        self._views[view.id] = view
        logger.info("View '%s' created for %s by user %s", name, entity.value, user_id)
        return view

    def update(self, view_id: str, **kwargs) -> SavedView | None:
        """Update view attributes."""
        view = self._views.get(view_id)
        if not view:
            return None

        for key, value in kwargs.items():
            if hasattr(view, key):
                setattr(view, key, value)
        view.updated_at = datetime.now()
        logger.info("View %s updated", view_id)
        return view

    def delete(self, view_id: str) -> bool:
        """Delete a saved view."""
        if view_id in self._views:
            # Remove from defaults if it was set as default
            keys_to_remove = [k for k, v in self._defaults.items() if v == view_id]
            for k in keys_to_remove:
                del self._defaults[k]
            del self._views[view_id]
            logger.info("View %s deleted", view_id)
            return True
        return False

    def get(self, view_id: str) -> SavedView | None:
        """Get a single view by id."""
        return self._views.get(view_id)

    def get_views(
        self,
        tenant_id: str,
        user_id: str,
        entity: ViewEntity | str | None = None,
    ) -> list[SavedView]:
        """Get views for a user: their own views + shared views in the tenant."""
        if isinstance(entity, str):
            entity = ViewEntity(entity)

        results = [
            v for v in self._views.values()
            if v.tenant_id == tenant_id and (v.user_id == user_id or v.is_shared)
        ]
        if entity:
            results = [v for v in results if v.entity == entity]

        results.sort(key=lambda v: (-v.usage_count, v.name))
        return results

    def get_default(
        self,
        tenant_id: str,
        user_id: str,
        entity: ViewEntity | str,
    ) -> SavedView | None:
        """Get the default view for a user + entity combo."""
        if isinstance(entity, str):
            entity = ViewEntity(entity)

        view_id = self._defaults.get((user_id, entity))
        if view_id:
            view = self._views.get(view_id)
            if view and view.tenant_id == tenant_id:
                return view
        return None

    def set_default(self, view_id: str, user_id: str) -> SavedView | None:
        """Set a view as the default for a user + entity combo."""
        view = self._views.get(view_id)
        if not view:
            return None

        # Unset previous default for this user + entity
        old_key = (user_id, view.entity)
        old_view_id = self._defaults.get(old_key)
        if old_view_id and old_view_id in self._views:
            self._views[old_view_id].is_default = False

        view.is_default = True
        view.updated_at = datetime.now()
        self._defaults[old_key] = view_id
        logger.info("View %s set as default for user %s/%s", view_id, user_id, view.entity.value)
        return view

    def duplicate(self, view_id: str, new_name: str) -> SavedView | None:
        """Duplicate an existing view with a new name."""
        original = self._views.get(view_id)
        if not original:
            return None

        # Deep-copy the config
        new_config = ViewConfig(
            columns=list(original.config.columns),
            filters=[
                FilterCondition(f.field, f.operator, f.value)
                for f in original.config.filters
            ],
            sort_by=original.config.sort_by,
            sort_order=original.config.sort_order,
            group_by=original.config.group_by,
            page_size=original.config.page_size,
        )

        new_view = SavedView(
            id=str(uuid.uuid4()),
            tenant_id=original.tenant_id,
            user_id=original.user_id,
            entity=original.entity,
            name=new_name,
            description=f"Copy of {original.name}",
            config=new_config,
            is_shared=False,
            is_default=False,
        )
        self._views[new_view.id] = new_view
        logger.info("View %s duplicated as '%s' (%s)", view_id, new_name, new_view.id)
        return new_view

    def apply_filters(
        self,
        data: list[dict],
        config: ViewConfig,
        page: int = 1,
    ) -> list[dict]:
        """Apply a ViewConfig's filters, sorting, and pagination to a list of dicts."""
        # Filter
        filtered = data
        for condition in config.filters:
            filtered = [row for row in filtered if _match_filter(row, condition)]

        # Sort
        if config.sort_by:
            reverse = config.sort_order == SortOrder.DESC
            filtered.sort(
                key=lambda row: (row.get(config.sort_by) is None, row.get(config.sort_by, "")),
                reverse=reverse,
            )

        # Paginate
        page_size = config.page_size or 25
        start = (page - 1) * page_size
        end = start + page_size
        return filtered[start:end]

    def increment_usage(self, view_id: str) -> None:
        """Increment the usage counter of a view."""
        view = self._views.get(view_id)
        if view:
            view.usage_count += 1

    def get_popular_views(
        self,
        tenant_id: str,
        entity: ViewEntity | str,
        limit: int = 5,
    ) -> list[SavedView]:
        """Get the most-used views for an entity."""
        if isinstance(entity, str):
            entity = ViewEntity(entity)

        results = [
            v for v in self._views.values()
            if v.tenant_id == tenant_id and v.entity == entity
        ]
        results.sort(key=lambda v: v.usage_count, reverse=True)
        return results[:limit]

    @property
    def count(self) -> int:
        return len(self._views)


# Singleton
saved_view_manager = SavedViewManager()
