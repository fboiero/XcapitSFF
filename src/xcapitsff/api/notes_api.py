"""API endpoints for notes & comments."""

from fastapi import APIRouter, HTTPException, Query

from xcapitsff.core.notes import EntityType, NoteType, notes_manager

router = APIRouter(prefix="/notes", tags=["Notes"])


@router.post("/")
async def create_note(
    tenant_id: str,
    entity_type: str,
    entity_id: str,
    author_id: str,
    content: str,
    type: str = "note",
    mentions: list[str] | None = None,
):
    """Create a note attached to an entity."""
    try:
        note_type = NoteType(type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid note type: {type}")
    try:
        etype = EntityType(entity_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid entity type: {entity_type}")

    note = notes_manager.create(
        tenant_id=tenant_id,
        entity_type=etype,
        entity_id=entity_id,
        author_id=author_id,
        content=content,
        type=note_type,
        mentions=mentions,
    )
    return note.to_dict()


@router.get("/")
async def get_notes(
    entity_type: str,
    entity_id: str,
    type: str | None = None,
    limit: int = Query(default=50, le=200),
):
    """Get notes for an entity."""
    try:
        etype = EntityType(entity_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid entity type: {entity_type}")

    note_type = None
    if type:
        try:
            note_type = NoteType(type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid note type: {type}")

    notes = notes_manager.get_notes(etype, entity_id, type=note_type, limit=limit)
    return {"count": len(notes), "notes": [n.to_dict() for n in notes]}


@router.put("/{note_id}")
async def update_note(note_id: str, content: str):
    """Update a note's content."""
    note = notes_manager.update(note_id, content)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note.to_dict()


@router.delete("/{note_id}")
async def delete_note(note_id: str):
    """Delete a note."""
    deleted = notes_manager.delete(note_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"deleted": True}


@router.post("/{note_id}/pin")
async def pin_note(note_id: str, pinned: bool = True):
    """Pin or unpin a note."""
    if pinned:
        note = notes_manager.pin(note_id)
    else:
        note = notes_manager.unpin(note_id)

    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note.to_dict()


@router.get("/search")
async def search_notes(tenant_id: str, q: str):
    """Search notes by content."""
    notes = notes_manager.search_notes(tenant_id, q)
    return {"count": len(notes), "notes": [n.to_dict() for n in notes]}


@router.get("/recent")
async def recent_notes(
    tenant_id: str,
    user_id: str | None = None,
    limit: int = Query(default=20, le=100),
):
    """Get recent notes."""
    notes = notes_manager.get_recent_notes(tenant_id, user_id=user_id, limit=limit)
    return {"count": len(notes), "notes": [n.to_dict() for n in notes]}


@router.get("/mentions")
async def get_mentions(tenant_id: str, user_id: str):
    """Get notes where a user is mentioned."""
    notes = notes_manager.get_mentions(tenant_id, user_id)
    return {"count": len(notes), "notes": [n.to_dict() for n in notes]}
