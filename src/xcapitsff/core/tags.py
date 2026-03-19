"""Tagging system — create, assign, and search tags across tenant entities."""

from __future__ import annotations

import re
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_ENTITY_TYPES = {"lead", "ticket", "customer", "all"}
_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


@dataclass
class Tag:
    tag_id: str
    name: str
    color: str  # hex, e.g. "#FF5733"
    tenant_id: str
    entity_type: str  # lead / ticket / customer / all
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# TagManager
# ---------------------------------------------------------------------------


class TagManager:
    """In-memory tag store — manages tags and entity-tag associations."""

    def __init__(self) -> None:
        self._tags: dict[str, Tag] = {}
        # associations: set of (tag_id, entity_type, entity_id)
        self._associations: set[tuple[str, str, int]] = set()

    # -- Tag CRUD ------------------------------------------------------------

    def create_tag(
        self,
        tenant_id: str,
        name: str,
        color: str = "#3B82F6",
        entity_type: str = "all",
    ) -> Tag:
        """Create a new tag for a tenant."""
        if entity_type not in VALID_ENTITY_TYPES:
            raise ValueError(
                f"Invalid entity_type '{entity_type}'. "
                f"Must be one of: {VALID_ENTITY_TYPES}"
            )

        if not _HEX_COLOR_RE.match(color):
            raise ValueError(
                f"Invalid color '{color}'. Must be a hex color like '#FF5733'"
            )

        name = name.strip()
        if not name:
            raise ValueError("Tag name cannot be empty")

        # Check for duplicate name within same tenant + entity_type
        for tag in self._tags.values():
            if (
                tag.tenant_id == tenant_id
                and tag.name.lower() == name.lower()
                and tag.entity_type == entity_type
            ):
                raise ValueError(
                    f"Tag '{name}' already exists for tenant '{tenant_id}' "
                    f"on entity type '{entity_type}'"
                )

        tag_id = str(uuid.uuid4())
        tag = Tag(
            tag_id=tag_id,
            name=name,
            color=color,
            tenant_id=tenant_id,
            entity_type=entity_type,
        )
        self._tags[tag_id] = tag
        return tag

    def get_tag(self, tag_id: str) -> Tag | None:
        """Return a tag by id."""
        return self._tags.get(tag_id)

    def get_tags(
        self, tenant_id: str, entity_type: str | None = None
    ) -> list[Tag]:
        """List tags for a tenant, optionally filtered by entity type."""
        results: list[Tag] = []
        for tag in self._tags.values():
            if tag.tenant_id != tenant_id:
                continue
            if entity_type is not None:
                # Include tags matching the specific entity_type OR "all"
                if tag.entity_type != entity_type and tag.entity_type != "all":
                    continue
            results.append(tag)
        results.sort(key=lambda t: t.name.lower())
        return results

    def delete_tag(self, tag_id: str) -> bool:
        """Delete a tag and all its associations."""
        if tag_id not in self._tags:
            return False
        del self._tags[tag_id]
        self._associations = {
            assoc for assoc in self._associations if assoc[0] != tag_id
        }
        return True

    # -- Entity tagging ------------------------------------------------------

    def tag_entity(self, tag_id: str, entity_type: str, entity_id: int) -> bool:
        """Add a tag to an entity. Returns True if newly added, False if already tagged."""
        tag = self._tags.get(tag_id)
        if tag is None:
            raise ValueError(f"Tag '{tag_id}' not found")

        if tag.entity_type != "all" and tag.entity_type != entity_type:
            raise ValueError(
                f"Tag '{tag.name}' is restricted to entity type '{tag.entity_type}', "
                f"cannot apply to '{entity_type}'"
            )

        key = (tag_id, entity_type, entity_id)
        if key in self._associations:
            return False
        self._associations.add(key)
        return True

    def untag_entity(self, tag_id: str, entity_type: str, entity_id: int) -> bool:
        """Remove a tag from an entity. Returns True if removed, False if not found."""
        key = (tag_id, entity_type, entity_id)
        if key not in self._associations:
            return False
        self._associations.discard(key)
        return True

    def get_entity_tags(self, entity_type: str, entity_id: int) -> list[Tag]:
        """Return all tags on a specific entity."""
        tag_ids = [
            tid
            for tid, etype, eid in self._associations
            if etype == entity_type and eid == entity_id
        ]
        tags = [self._tags[tid] for tid in tag_ids if tid in self._tags]
        tags.sort(key=lambda t: t.name.lower())
        return tags

    def find_by_tag(self, tag_id: str) -> list[tuple[str, int]]:
        """Return all (entity_type, entity_id) pairs associated with a tag."""
        results: list[tuple[str, int]] = []
        for tid, etype, eid in self._associations:
            if tid == tag_id:
                results.append((etype, eid))
        return results

    # -- Analytics -----------------------------------------------------------

    def get_popular_tags(
        self, tenant_id: str, limit: int = 20
    ) -> list[tuple[Tag, int]]:
        """Return the most used tags for a tenant, with usage count."""
        # Count usages per tag_id
        counter: Counter[str] = Counter()
        for tid, _etype, _eid in self._associations:
            tag = self._tags.get(tid)
            if tag and tag.tenant_id == tenant_id:
                counter[tid] += 1

        # Also include tags with zero usage
        for tag in self._tags.values():
            if tag.tenant_id == tenant_id and tag.tag_id not in counter:
                counter[tag.tag_id] = 0

        popular = counter.most_common(limit)
        return [
            (self._tags[tid], count)
            for tid, count in popular
            if tid in self._tags
        ]

    # -- Merge ---------------------------------------------------------------

    def merge_tags(self, source_id: str, target_id: str) -> int:
        """Merge source tag into target tag.

        All entity associations from source are moved to target, then source
        is deleted. Returns the number of associations migrated.
        """
        source = self._tags.get(source_id)
        target = self._tags.get(target_id)
        if source is None:
            raise ValueError(f"Source tag '{source_id}' not found")
        if target is None:
            raise ValueError(f"Target tag '{target_id}' not found")
        if source.tenant_id != target.tenant_id:
            raise ValueError("Cannot merge tags from different tenants")

        migrated = 0
        to_remove: list[tuple[str, str, int]] = []
        to_add: list[tuple[str, str, int]] = []

        for assoc in self._associations:
            tid, etype, eid = assoc
            if tid == source_id:
                new_assoc = (target_id, etype, eid)
                if new_assoc not in self._associations:
                    to_add.append(new_assoc)
                    migrated += 1
                to_remove.append(assoc)

        for assoc in to_remove:
            self._associations.discard(assoc)
        for assoc in to_add:
            self._associations.add(assoc)

        # Delete the source tag
        del self._tags[source_id]
        return migrated

    # -- Suggestion ----------------------------------------------------------

    def suggest_tags(self, text: str, tenant_id: str) -> list[Tag]:
        """Suggest tags based on text content (simple keyword matching)."""
        if not text:
            return []

        text_lower = text.lower()
        scored: list[tuple[Tag, int]] = []

        for tag in self._tags.values():
            if tag.tenant_id != tenant_id:
                continue
            tag_name_lower = tag.name.lower()
            # Check if the tag name appears in the text
            if tag_name_lower in text_lower:
                # Score by position (earlier = better) and length (longer match = better)
                pos = text_lower.index(tag_name_lower)
                score = len(tag_name_lower) * 100 - pos
                scored.append((tag, score))
            else:
                # Check individual words of the tag name
                tag_words = tag_name_lower.split()
                matches = sum(1 for w in tag_words if w in text_lower)
                if matches > 0:
                    score = matches * 50
                    scored.append((tag, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [tag for tag, _score in scored]


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

tag_manager = TagManager()
