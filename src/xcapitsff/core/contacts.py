"""Contact management — CRUD, search, merge, tagging, timeline."""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Contact:
    id: str
    tenant_id: str
    first_name: str
    last_name: str
    email: str | None = None
    phone: str | None = None
    title: str | None = None
    company_id: str | None = None
    source: str = "manual"  # manual, import, web, referral
    tags: list[str] = field(default_factory=list)
    custom_fields: dict[str, Any] = field(default_factory=dict)
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_contacted_at: datetime | None = None
    owner_id: str | None = None


VALID_SOURCES = {"manual", "import", "web", "referral"}


class ContactManager:
    """In-memory contact management with multi-tenant isolation."""

    def __init__(self) -> None:
        self._contacts: dict[str, Contact] = {}
        self._timeline: dict[str, list[dict[str, Any]]] = {}

    # --- helpers ---

    def _record_event(self, contact_id: str, event_type: str, details: dict | None = None) -> None:
        if contact_id not in self._timeline:
            self._timeline[contact_id] = []
        self._timeline[contact_id].append(
            {
                "event_type": event_type,
                "timestamp": datetime.now(tz=None).isoformat(),
                "details": details or {},
            }
        )

    # --- CRUD ---

    def create(
        self,
        tenant_id: str,
        first_name: str,
        last_name: str,
        email: str | None = None,
        **kwargs: Any,
    ) -> Contact:
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id is required")
        if not first_name or not first_name.strip():
            raise ValueError("first_name is required")
        if not last_name or not last_name.strip():
            raise ValueError("last_name is required")

        source = kwargs.get("source", "manual")
        if source not in VALID_SOURCES:
            raise ValueError(f"Invalid source: {source}. Must be one of {VALID_SOURCES}")

        contact_id = str(uuid.uuid4())
        now = datetime.now(tz=None)
        contact = Contact(
            id=contact_id,
            tenant_id=tenant_id,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            email=email.strip() if email else None,
            phone=kwargs.get("phone"),
            title=kwargs.get("title"),
            company_id=kwargs.get("company_id"),
            source=source,
            tags=list(kwargs.get("tags", [])),
            custom_fields=dict(kwargs.get("custom_fields", {})),
            notes=kwargs.get("notes", ""),
            created_at=now,
            updated_at=now,
            last_contacted_at=kwargs.get("last_contacted_at"),
            owner_id=kwargs.get("owner_id"),
        )
        self._contacts[contact_id] = contact
        self._record_event(contact_id, "created", {"first_name": first_name, "last_name": last_name})
        logger.info("Contact created: id=%s tenant=%s name=%s %s", contact_id, tenant_id, first_name, last_name)
        return contact

    def update(self, contact_id: str, **kwargs: Any) -> Contact:
        contact = self._contacts.get(contact_id)
        if not contact:
            raise KeyError(f"Contact not found: {contact_id}")

        if "source" in kwargs and kwargs["source"] not in VALID_SOURCES:
            raise ValueError(f"Invalid source: {kwargs['source']}. Must be one of {VALID_SOURCES}")

        changed: dict[str, Any] = {}
        for key, value in kwargs.items():
            if hasattr(contact, key) and key not in ("id", "tenant_id", "created_at"):
                old = getattr(contact, key)
                setattr(contact, key, value)
                changed[key] = {"old": old, "new": value}

        contact.updated_at = datetime.now(tz=None)
        self._record_event(contact_id, "updated", changed)
        logger.info("Contact updated: id=%s fields=%s", contact_id, list(changed.keys()))
        return contact

    def delete(self, contact_id: str) -> bool:
        contact = self._contacts.pop(contact_id, None)
        if contact is None:
            return False
        self._timeline.pop(contact_id, None)
        logger.info("Contact deleted: id=%s", contact_id)
        return True

    def get(self, contact_id: str) -> Contact:
        contact = self._contacts.get(contact_id)
        if not contact:
            raise KeyError(f"Contact not found: {contact_id}")
        return contact

    def list_contacts(
        self,
        tenant_id: str,
        company_id: str | None = None,
        owner_id: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Contact]:
        results = [c for c in self._contacts.values() if c.tenant_id == tenant_id]

        if company_id is not None:
            results = [c for c in results if c.company_id == company_id]
        if owner_id is not None:
            results = [c for c in results if c.owner_id == owner_id]
        if search:
            q = search.lower()
            results = [
                c
                for c in results
                if q in c.first_name.lower()
                or q in c.last_name.lower()
                or (c.email and q in c.email.lower())
            ]

        results.sort(key=lambda c: c.created_at, reverse=True)
        return results[offset : offset + limit]

    def search(self, tenant_id: str, query: str) -> list[Contact]:
        if not query or not query.strip():
            return []
        q = query.lower().strip()
        results: list[Contact] = []
        for c in self._contacts.values():
            if c.tenant_id != tenant_id:
                continue
            searchable = " ".join(
                filter(
                    None,
                    [
                        c.first_name,
                        c.last_name,
                        c.email or "",
                        c.title or "",
                        c.notes,
                        " ".join(c.tags),
                    ],
                )
            ).lower()
            if q in searchable:
                results.append(c)
        results.sort(key=lambda c: c.created_at, reverse=True)
        return results

    def merge_contacts(self, primary_id: str, secondary_id: str) -> Contact:
        primary = self._contacts.get(primary_id)
        secondary = self._contacts.get(secondary_id)
        if not primary:
            raise KeyError(f"Primary contact not found: {primary_id}")
        if not secondary:
            raise KeyError(f"Secondary contact not found: {secondary_id}")
        if primary.tenant_id != secondary.tenant_id:
            raise ValueError("Cannot merge contacts from different tenants")

        # Fill empty fields from secondary
        if not primary.email and secondary.email:
            primary.email = secondary.email
        if not primary.phone and secondary.phone:
            primary.phone = secondary.phone
        if not primary.title and secondary.title:
            primary.title = secondary.title
        if not primary.company_id and secondary.company_id:
            primary.company_id = secondary.company_id
        if not primary.notes and secondary.notes:
            primary.notes = secondary.notes
        elif primary.notes and secondary.notes:
            primary.notes = f"{primary.notes}\n---\n{secondary.notes}"

        # Merge tags (union)
        merged_tags = list(set(primary.tags + secondary.tags))
        primary.tags = merged_tags

        # Merge custom fields (primary takes precedence)
        for key, value in secondary.custom_fields.items():
            if key not in primary.custom_fields:
                primary.custom_fields[key] = value

        primary.updated_at = datetime.now(tz=None)

        # Merge timelines
        secondary_events = self._timeline.get(secondary_id, [])
        if secondary_events:
            if primary_id not in self._timeline:
                self._timeline[primary_id] = []
            self._timeline[primary_id].extend(secondary_events)
            self._timeline[primary_id].sort(key=lambda e: e["timestamp"])

        self._record_event(primary_id, "merged", {"merged_from": secondary_id})

        # Remove secondary
        self._contacts.pop(secondary_id, None)
        self._timeline.pop(secondary_id, None)

        logger.info("Contacts merged: primary=%s secondary=%s", primary_id, secondary_id)
        return primary

    def get_contact_timeline(self, contact_id: str) -> list[dict[str, Any]]:
        if contact_id not in self._contacts:
            raise KeyError(f"Contact not found: {contact_id}")
        return list(self._timeline.get(contact_id, []))

    def assign(self, contact_id: str, owner_id: str) -> Contact:
        contact = self._contacts.get(contact_id)
        if not contact:
            raise KeyError(f"Contact not found: {contact_id}")
        old_owner = contact.owner_id
        contact.owner_id = owner_id
        contact.updated_at = datetime.now(tz=None)
        self._record_event(contact_id, "assigned", {"old_owner": old_owner, "new_owner": owner_id})
        logger.info("Contact assigned: id=%s owner=%s", contact_id, owner_id)
        return contact

    def bulk_import(self, tenant_id: str, contacts: list[dict[str, Any]]) -> dict[str, Any]:
        imported = 0
        skipped = 0
        errors: list[str] = []

        for i, data in enumerate(contacts):
            try:
                first_name = data.get("first_name", "").strip()
                last_name = data.get("last_name", "").strip()
                if not first_name or not last_name:
                    skipped += 1
                    errors.append(f"Row {i}: missing first_name or last_name")
                    continue

                kwargs = {
                    k: v
                    for k, v in data.items()
                    if k not in ("first_name", "last_name", "email", "tenant_id")
                }
                self.create(
                    tenant_id=tenant_id,
                    first_name=first_name,
                    last_name=last_name,
                    email=data.get("email"),
                    **kwargs,
                )
                imported += 1
            except Exception as exc:
                skipped += 1
                errors.append(f"Row {i}: {exc}")

        logger.info(
            "Bulk import: tenant=%s imported=%d skipped=%d errors=%d",
            tenant_id,
            imported,
            skipped,
            len(errors),
        )
        return {"imported": imported, "skipped": skipped, "errors": errors}

    def get_contacts_by_company(self, company_id: str) -> list[Contact]:
        results = [c for c in self._contacts.values() if c.company_id == company_id]
        results.sort(key=lambda c: c.created_at, reverse=True)
        return results

    def add_tag(self, contact_id: str, tag: str) -> Contact:
        contact = self._contacts.get(contact_id)
        if not contact:
            raise KeyError(f"Contact not found: {contact_id}")
        tag = tag.strip().lower()
        if not tag:
            raise ValueError("Tag cannot be empty")
        if tag not in contact.tags:
            contact.tags.append(tag)
            contact.updated_at = datetime.now(tz=None)
            self._record_event(contact_id, "tag_added", {"tag": tag})
        return contact

    def remove_tag(self, contact_id: str, tag: str) -> Contact:
        contact = self._contacts.get(contact_id)
        if not contact:
            raise KeyError(f"Contact not found: {contact_id}")
        tag = tag.strip().lower()
        if tag in contact.tags:
            contact.tags.remove(tag)
            contact.updated_at = datetime.now(tz=None)
            self._record_event(contact_id, "tag_removed", {"tag": tag})
        return contact
