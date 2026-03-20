"""Tests for notes & comments system."""

from xcapitsff.core.notes import EntityType, NoteType, NotesManager, _extract_mentions


def test_create_note():
    mgr = NotesManager()
    note = mgr.create("t1", EntityType.LEAD, "10", "user1", "Hello world")
    assert note.tenant_id == "t1"
    assert note.entity_type == EntityType.LEAD
    assert note.entity_id == "10"
    assert note.author_id == "user1"
    assert note.content == "Hello world"
    assert note.type == NoteType.NOTE
    assert note.pinned is False
    assert note.edited is False
    assert mgr.count == 1


def test_create_note_with_type():
    mgr = NotesManager()
    note = mgr.create("t1", EntityType.TICKET, "5", "user1", "Call log entry", type=NoteType.CALL_LOG)
    assert note.type == NoteType.CALL_LOG


def test_create_note_string_entity_type():
    mgr = NotesManager()
    note = mgr.create("t1", "lead", "10", "user1", "Testing string type")
    assert note.entity_type == EntityType.LEAD


def test_extract_mentions():
    mentions = _extract_mentions("Hey @alice and @bob, please review")
    assert "alice" in mentions
    assert "bob" in mentions
    assert len(mentions) == 2


def test_extract_mentions_deduplicated():
    mentions = _extract_mentions("@alice @bob @alice again")
    assert mentions == ["alice", "bob"]


def test_auto_extract_mentions_on_create():
    mgr = NotesManager()
    note = mgr.create("t1", EntityType.LEAD, "10", "user1", "FYI @carlos and @diana")
    assert "carlos" in note.mentions
    assert "diana" in note.mentions


def test_create_merges_explicit_and_extracted_mentions():
    mgr = NotesManager()
    note = mgr.create(
        "t1", EntityType.LEAD, "10", "user1",
        "Check with @alice",
        mentions=["bob"],
    )
    assert "bob" in note.mentions
    assert "alice" in note.mentions


def test_update_note():
    mgr = NotesManager()
    note = mgr.create("t1", EntityType.LEAD, "10", "user1", "Original")
    updated = mgr.update(note.id, "Updated content with @newuser")
    assert updated is not None
    assert updated.content == "Updated content with @newuser"
    assert updated.edited is True
    assert "newuser" in updated.mentions


def test_update_nonexistent_returns_none():
    mgr = NotesManager()
    assert mgr.update("nonexistent", "text") is None


def test_delete_note():
    mgr = NotesManager()
    note = mgr.create("t1", EntityType.LEAD, "10", "user1", "To delete")
    assert mgr.delete(note.id) is True
    assert mgr.count == 0


def test_delete_nonexistent_returns_false():
    mgr = NotesManager()
    assert mgr.delete("nonexistent") is False


def test_get_notes_for_entity():
    mgr = NotesManager()
    mgr.create("t1", EntityType.LEAD, "10", "user1", "Note 1")
    mgr.create("t1", EntityType.LEAD, "10", "user1", "Note 2")
    mgr.create("t1", EntityType.LEAD, "20", "user1", "Note on different lead")

    notes = mgr.get_notes(EntityType.LEAD, "10")
    assert len(notes) == 2


def test_get_notes_filtered_by_type():
    mgr = NotesManager()
    mgr.create("t1", EntityType.LEAD, "10", "user1", "Regular note")
    mgr.create("t1", EntityType.LEAD, "10", "user1", "Internal note", type=NoteType.INTERNAL)

    notes = mgr.get_notes(EntityType.LEAD, "10", type=NoteType.INTERNAL)
    assert len(notes) == 1
    assert notes[0].type == NoteType.INTERNAL


def test_get_notes_pinned_first():
    mgr = NotesManager()
    n1 = mgr.create("t1", EntityType.LEAD, "10", "user1", "Not pinned")
    n2 = mgr.create("t1", EntityType.LEAD, "10", "user1", "Pinned")
    mgr.pin(n2.id)

    notes = mgr.get_notes(EntityType.LEAD, "10")
    assert notes[0].id == n2.id
    assert notes[0].pinned is True


def test_pin_and_unpin():
    mgr = NotesManager()
    note = mgr.create("t1", EntityType.LEAD, "10", "user1", "Test")
    assert note.pinned is False

    pinned = mgr.pin(note.id)
    assert pinned is not None
    assert pinned.pinned is True

    unpinned = mgr.unpin(note.id)
    assert unpinned is not None
    assert unpinned.pinned is False


def test_pin_nonexistent_returns_none():
    mgr = NotesManager()
    assert mgr.pin("nonexistent") is None
    assert mgr.unpin("nonexistent") is None


def test_search_notes():
    mgr = NotesManager()
    mgr.create("t1", EntityType.LEAD, "10", "user1", "Meeting about Q4 budget")
    mgr.create("t1", EntityType.TICKET, "5", "user2", "Budget issue resolved")
    mgr.create("t2", EntityType.LEAD, "1", "user3", "Budget in another tenant")

    results = mgr.search_notes("t1", "budget")
    assert len(results) == 2


def test_search_notes_case_insensitive():
    mgr = NotesManager()
    mgr.create("t1", EntityType.LEAD, "10", "user1", "IMPORTANT meeting")

    results = mgr.search_notes("t1", "important")
    assert len(results) == 1


def test_get_recent_notes():
    mgr = NotesManager()
    mgr.create("t1", EntityType.LEAD, "10", "user1", "First")
    mgr.create("t1", EntityType.LEAD, "20", "user2", "Second")
    mgr.create("t2", EntityType.LEAD, "30", "user3", "Other tenant")

    recent = mgr.get_recent_notes("t1", limit=10)
    assert len(recent) == 2
    # Most recent first
    assert recent[0].content == "Second"


def test_get_recent_notes_by_user():
    mgr = NotesManager()
    mgr.create("t1", EntityType.LEAD, "10", "user1", "User1 note")
    mgr.create("t1", EntityType.LEAD, "20", "user2", "User2 note")

    recent = mgr.get_recent_notes("t1", user_id="user1")
    assert len(recent) == 1
    assert recent[0].author_id == "user1"


def test_get_mentions():
    mgr = NotesManager()
    mgr.create("t1", EntityType.LEAD, "10", "user1", "Hey @bob check this")
    mgr.create("t1", EntityType.TICKET, "5", "user2", "Ping @bob @alice")
    mgr.create("t1", EntityType.LEAD, "20", "user3", "No mentions here")

    bob_mentions = mgr.get_mentions("t1", "bob")
    assert len(bob_mentions) == 2

    alice_mentions = mgr.get_mentions("t1", "alice")
    assert len(alice_mentions) == 1


def test_count_by_entity():
    mgr = NotesManager()
    mgr.create("t1", EntityType.LEAD, "10", "user1", "Note 1")
    mgr.create("t1", EntityType.LEAD, "10", "user1", "Note 2")
    mgr.create("t1", EntityType.LEAD, "20", "user1", "Note 3")

    assert mgr.count_by_entity(EntityType.LEAD, "10") == 2
    assert mgr.count_by_entity(EntityType.LEAD, "20") == 1
    assert mgr.count_by_entity(EntityType.LEAD, "99") == 0


def test_get_single_note():
    mgr = NotesManager()
    note = mgr.create("t1", EntityType.LEAD, "10", "user1", "Test")
    fetched = mgr.get(note.id)
    assert fetched is not None
    assert fetched.id == note.id


def test_get_nonexistent_note():
    mgr = NotesManager()
    assert mgr.get("nonexistent") is None


def test_to_dict():
    mgr = NotesManager()
    note = mgr.create("t1", EntityType.LEAD, "10", "user1", "Test @alice")
    d = note.to_dict()
    assert d["id"] == note.id
    assert d["tenant_id"] == "t1"
    assert d["entity_type"] == "lead"
    assert d["entity_id"] == "10"
    assert d["author_id"] == "user1"
    assert d["type"] == "note"
    assert d["content"] == "Test @alice"
    assert "alice" in d["mentions"]
    assert d["pinned"] is False
    assert d["edited"] is False
    assert "created_at" in d
    assert "updated_at" in d


def test_note_type_enum_values():
    assert NoteType.NOTE.value == "note"
    assert NoteType.COMMENT.value == "comment"
    assert NoteType.INTERNAL.value == "internal"
    assert NoteType.CALL_LOG.value == "call_log"
    assert NoteType.EMAIL_LOG.value == "email_log"
    assert NoteType.MEETING_NOTE.value == "meeting_note"


def test_entity_type_enum_values():
    assert EntityType.LEAD.value == "lead"
    assert EntityType.TICKET.value == "ticket"
    assert EntityType.CUSTOMER.value == "customer"
    assert EntityType.CONTACT.value == "contact"
    assert EntityType.COMPANY.value == "company"
    assert EntityType.DEAL.value == "deal"


def test_get_notes_limit():
    mgr = NotesManager()
    for i in range(10):
        mgr.create("t1", EntityType.LEAD, "10", "user1", f"Note {i}")

    notes = mgr.get_notes(EntityType.LEAD, "10", limit=3)
    assert len(notes) == 3
