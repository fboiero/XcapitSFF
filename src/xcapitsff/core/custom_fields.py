"""Custom fields per tenant — allow each tenant to extend entities with their own data."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class FieldType(str, Enum):
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    BOOLEAN = "boolean"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    URL = "url"
    EMAIL = "email"
    PHONE = "phone"


VALID_ENTITY_TYPES = {"lead", "ticket", "customer"}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class CustomFieldDefinition:
    field_id: str
    tenant_id: str
    entity_type: str  # lead / ticket / customer
    name: str
    label: str
    field_type: FieldType
    required: bool = False
    default_value: Any = None
    options: list[str] = field(default_factory=list)
    display_order: int = 0


@dataclass
class CustomFieldValue:
    field_id: str
    entity_id: int
    value: Any
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_URL_RE = re.compile(r"^https?://\S+$")
_PHONE_RE = re.compile(r"^\+?[\d\s\-().]{5,20}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ---------------------------------------------------------------------------
# CustomFieldManager
# ---------------------------------------------------------------------------


class CustomFieldManager:
    """In-memory manager for custom field definitions and values."""

    def __init__(self) -> None:
        self._definitions: dict[str, CustomFieldDefinition] = {}
        # values keyed by (field_id, entity_id)
        self._values: dict[tuple[str, int], CustomFieldValue] = {}

    # -- Field definitions ---------------------------------------------------

    def define_field(
        self,
        tenant_id: str,
        entity_type: str,
        name: str,
        label: str,
        field_type: str | FieldType,
        required: bool = False,
        default_value: Any = None,
        options: list[str] | None = None,
        display_order: int = 0,
    ) -> CustomFieldDefinition:
        """Create a new custom field definition for a tenant + entity type."""
        if entity_type not in VALID_ENTITY_TYPES:
            raise ValueError(
                f"Invalid entity_type '{entity_type}'. Must be one of: {VALID_ENTITY_TYPES}"
            )

        if isinstance(field_type, str):
            field_type = FieldType(field_type)

        if field_type in (FieldType.SELECT, FieldType.MULTI_SELECT):
            if not options:
                raise ValueError(
                    f"Field type '{field_type.value}' requires a non-empty options list"
                )

        # Check for duplicate name within same tenant + entity_type
        for defn in self._definitions.values():
            if (
                defn.tenant_id == tenant_id
                and defn.entity_type == entity_type
                and defn.name == name
            ):
                raise ValueError(
                    f"Field '{name}' already exists for tenant '{tenant_id}' "
                    f"on entity type '{entity_type}'"
                )

        field_id = str(uuid.uuid4())
        definition = CustomFieldDefinition(
            field_id=field_id,
            tenant_id=tenant_id,
            entity_type=entity_type,
            name=name,
            label=label,
            field_type=field_type,
            required=required,
            default_value=default_value,
            options=options or [],
            display_order=display_order,
        )
        self._definitions[field_id] = definition
        return definition

    def get_fields(self, tenant_id: str, entity_type: str) -> list[CustomFieldDefinition]:
        """Return all custom field definitions for a tenant + entity type, sorted by display_order."""
        results = [
            d
            for d in self._definitions.values()
            if d.tenant_id == tenant_id and d.entity_type == entity_type
        ]
        results.sort(key=lambda d: d.display_order)
        return results

    def get_field(self, field_id: str) -> CustomFieldDefinition | None:
        """Return a single field definition by id."""
        return self._definitions.get(field_id)

    # -- Values --------------------------------------------------------------

    def validate_value(
        self, field_def: CustomFieldDefinition, value: Any
    ) -> tuple[bool, str | None]:
        """Validate *value* against *field_def*. Returns (ok, error_message | None)."""
        ft = field_def.field_type

        # None / missing handling
        if value is None:
            if field_def.required:
                return False, f"Field '{field_def.name}' is required"
            return True, None

        if ft == FieldType.TEXT:
            if not isinstance(value, str):
                return False, f"Expected text, got {type(value).__name__}"

        elif ft == FieldType.NUMBER:
            if not isinstance(value, (int, float)):
                return False, f"Expected number, got {type(value).__name__}"

        elif ft == FieldType.DATE:
            if isinstance(value, str):
                if not _DATE_RE.match(value):
                    return False, "Date must be in YYYY-MM-DD format"
            elif not isinstance(value, datetime):
                return False, f"Expected date string or datetime, got {type(value).__name__}"

        elif ft == FieldType.BOOLEAN:
            if not isinstance(value, bool):
                return False, f"Expected boolean, got {type(value).__name__}"

        elif ft == FieldType.SELECT:
            if value not in field_def.options:
                return False, (
                    f"Value '{value}' not in allowed options: {field_def.options}"
                )

        elif ft == FieldType.MULTI_SELECT:
            if not isinstance(value, list):
                return False, "Multi-select value must be a list"
            invalid = [v for v in value if v not in field_def.options]
            if invalid:
                return False, (
                    f"Invalid option(s): {invalid}. Allowed: {field_def.options}"
                )

        elif ft == FieldType.URL:
            if not isinstance(value, str) or not _URL_RE.match(value):
                return False, "Value must be a valid URL (http:// or https://)"

        elif ft == FieldType.EMAIL:
            if not isinstance(value, str) or not _EMAIL_RE.match(value):
                return False, "Value must be a valid email address"

        elif ft == FieldType.PHONE:
            if not isinstance(value, str) or not _PHONE_RE.match(value):
                return False, "Value must be a valid phone number"

        return True, None

    def set_value(self, field_id: str, entity_id: int, value: Any) -> CustomFieldValue:
        """Set a custom field value for a specific entity, with type validation."""
        field_def = self._definitions.get(field_id)
        if field_def is None:
            raise ValueError(f"Custom field '{field_id}' not found")

        ok, error = self.validate_value(field_def, value)
        if not ok:
            raise ValueError(error)

        cfv = CustomFieldValue(
            field_id=field_id,
            entity_id=entity_id,
            value=value,
            updated_at=datetime.now(timezone.utc),
        )
        self._values[(field_id, entity_id)] = cfv
        return cfv

    def get_value(self, field_id: str, entity_id: int) -> Any:
        """Return the value for a specific field + entity, or the field's default."""
        cfv = self._values.get((field_id, entity_id))
        if cfv is not None:
            return cfv.value

        field_def = self._definitions.get(field_id)
        if field_def is not None:
            return field_def.default_value
        return None

    def get_values(self, entity_id: int) -> dict[str, Any]:
        """Return all custom field values for a given entity as {field_name: value}."""
        result: dict[str, Any] = {}
        for (fid, eid), cfv in self._values.items():
            if eid == entity_id:
                field_def = self._definitions.get(fid)
                key = field_def.name if field_def else fid
                result[key] = cfv.value
        return result

    # -- Delete --------------------------------------------------------------

    def delete_field(self, field_id: str) -> bool:
        """Delete a field definition and all its stored values."""
        if field_id not in self._definitions:
            return False

        del self._definitions[field_id]

        keys_to_remove = [
            key for key in self._values if key[0] == field_id
        ]
        for key in keys_to_remove:
            del self._values[key]

        return True

    # -- Search --------------------------------------------------------------

    def search_by_field(
        self, tenant_id: str, field_id: str, value: Any
    ) -> list[int]:
        """Find entity ids whose custom field matches the given value."""
        field_def = self._definitions.get(field_id)
        if field_def is None:
            return []
        if field_def.tenant_id != tenant_id:
            return []

        matching: list[int] = []
        for (fid, eid), cfv in self._values.items():
            if fid == field_id and cfv.value == value:
                matching.append(eid)
        return matching


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

custom_field_manager = CustomFieldManager()
