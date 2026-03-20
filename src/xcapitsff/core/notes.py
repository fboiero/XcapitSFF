"""Notes & comments system — attach notes to any entity (lead, ticket, customer, etc.).

Supports multiple note types (note, comment, internal, call log, email log, meeting note),
@mention extraction, pinning, and search.
"""

import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class NoteType(str, Enum):
    NOTE = "note"
    COMMENT = "comment"
    INTERNAL = "internal"
    CALL_LOG = "call_log"
    EMAIL_LOG = "email_log"
    MEETING_NOTE = "meeting_note"


class EntityType(str, Enum):
    LEAD = "lead"
    TICKET = "ticket"
    CUSTOMER = "customer"
    CONTACT = "contact"
    COMPANY = "company"
    DEAL = "deal"


_MENTION_RE = re.compile(r"@([\w.-]+)")


@dataclass
class Note:
    id: str
    tenant_id: str
    entity_type: EntityType
    entity_id: str
    author_id: str
    type: NoteType
    content: str
    mentions: list[str] = field(default_factory=list)
    pinned: bool = False
    edited: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "entity_type": self.entity_type.value,
            "entity_id": self.entity_id,
            "author_id": self.author_id,
            "type": self.type.value,
            "content": self.content,
            "mentions": self.mentions,
            "pinned": self.pinned,
            "edited": self.edited,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


def _extract_mentions(content: str) -> list[str]:
    """Extract @user_id mentions from content."""
    return list(dict.fromkeys(_MENTION_RE.findall(content)))


class NotesManager:
    """In-memory notes storage with query capabilities."""

    def __init__(self) -> None:
        self._notes: dict[str, Note] = {}

    def create(
        self,
        tenant_id: str,
        entity_type: EntityType | str,
        entity_id: str,
        author_id: str,
        content: str,
        type: NoteType = NoteType.NOTE,
        mentions: list[str] | None = None,
    ) -> Note:
        """Create a new note attached to an entity."""
        if isinstance(entity_type, str):
            entity_type = EntityType(entity_type)

        auto_mentions = _extract_mentions(content)
        all_mentions = list(dict.fromkeys((mentions or []) + auto_mentions))

        note = Note(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            entity_type=entity_type,
            entity_id=str(entity_id),
            author_id=author_id,
            type=type,
            content=content,
            mentions=all_mentions,
        )
        self._notes[note.id] = note
        logger.info("Note %s created on %s#%s by %s", note.id, entity_type, entity_id, author_id)
        return note

    def update(self, note_id: str, content: str) -> Note | None:
        """Update note content and re-extract mentions."""
        note = self._notes.get(note_id)
        if not note:
            return None
        note.content = content
        note.mentions = _extract_mentions(content)
        note.edited = True
        note.updated_at = datetime.now()
        logger.info("Note %s updated", note_id)
        return note

    def delete(self, note_id: str) -> bool:
        """Delete a note by id."""
        if note_id in self._notes:
            del self._notes[note_id]
            logger.info("Note %s deleted", note_id)
            return True
        return False

    def get(self, note_id: str) -> Note | None:
        """Get a single note by id."""
        return self._notes.get(note_id)

    def get_notes(
        self,
        entity_type: EntityType | str,
        entity_id: str,
        type: NoteType | None = None,
        limit: int = 50,
    ) -> list[Note]:
        """Get notes for a specific entity, optionally filtered by type."""
        if isinstance(entity_type, str):
            entity_type = EntityType(entity_type)

        results = [
            n for n in self._notes.values()
            if n.entity_type == entity_type and n.entity_id == str(entity_id)
        ]
        if type is not None:
            results = [n for n in results if n.type == type]

        # Pinned first, then by creation date descending
        results.sort(key=lambda n: (not n.pinned, -n.created_at.timestamp()))
        return results[:limit]

    def pin(self, note_id: str) -> Note | None:
        """Pin a note."""
        note = self._notes.get(note_id)
        if not note:
            return None
        note.pinned = True
        note.updated_at = datetime.now()
        return note

    def unpin(self, note_id: str) -> Note | None:
        """Unpin a note."""
        note = self._notes.get(note_id)
        if not note:
            return None
        note.pinned = False
        note.updated_at = datetime.now()
        return note

    def search_notes(self, tenant_id: str, query: str) -> list[Note]:
        """Search notes by content within a tenant."""
        query_lower = query.lower()
        return [
            n for n in self._notes.values()
            if n.tenant_id == tenant_id and query_lower in n.content.lower()
        ]

    def get_recent_notes(
        self,
        tenant_id: str,
        user_id: str | None = None,
        limit: int = 20,
    ) -> list[Note]:
        """Get most recent notes for a tenant, optionally by author."""
        results = [n for n in self._notes.values() if n.tenant_id == tenant_id]
        if user_id:
            results = [n for n in results if n.author_id == user_id]
        results.sort(key=lambda n: n.created_at, reverse=True)
        return results[:limit]

    def get_mentions(self, tenant_id: str, user_id: str) -> list[Note]:
        """Get notes where a specific user is mentioned."""
        return [
            n for n in self._notes.values()
            if n.tenant_id == tenant_id and user_id in n.mentions
        ]

    def count_by_entity(self, entity_type: EntityType | str, entity_id: str) -> int:
        """Count notes attached to an entity."""
        if isinstance(entity_type, str):
            entity_type = EntityType(entity_type)
        return sum(
            1 for n in self._notes.values()
            if n.entity_type == entity_type and n.entity_id == str(entity_id)
        )

    @property
    def count(self) -> int:
        return len(self._notes)


# Singleton
notes_manager = NotesManager()
