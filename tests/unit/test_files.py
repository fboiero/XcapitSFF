"""Tests for file/document management system."""

import hashlib

from xcapitsff.core.files import EntityType, FileManager, TenantPlan


def _make_manager() -> FileManager:
    return FileManager()


def _sample_content(text: str = "hello world") -> bytes:
    return text.encode("utf-8")


# --- Upload ---


def test_upload_creates_metadata_with_correct_checksum():
    mgr = _make_manager()
    content = _sample_content("test data")
    meta = mgr.upload("t1", "report.pdf", content, "user1")

    expected = hashlib.sha256(content).hexdigest()
    assert meta.checksum == expected
    assert meta.size_bytes == len(content)
    assert meta.tenant_id == "t1"
    assert meta.filename == "report.pdf"
    assert meta.uploaded_by == "user1"


def test_upload_auto_detects_content_type():
    mgr = _make_manager()
    meta = mgr.upload("t1", "image.png", _sample_content(), "user1")
    assert meta.content_type == "image/png"

    meta2 = mgr.upload("t1", "data.csv", _sample_content(), "user1")
    assert meta2.content_type == "text/csv"


def test_upload_uses_provided_content_type():
    mgr = _make_manager()
    meta = mgr.upload(
        "t1", "file.txt", _sample_content(), "user1",
        content_type="text/plain",
    )
    assert meta.content_type == "text/plain"


def test_upload_default_entity_type_is_none():
    mgr = _make_manager()
    meta = mgr.upload("t1", "file.txt", _sample_content(), "user1")
    assert meta.entity_type == EntityType.NONE
    assert meta.entity_id is None


def test_upload_with_entity():
    mgr = _make_manager()
    meta = mgr.upload(
        "t1", "file.txt", _sample_content(), "user1",
        entity_type=EntityType.LEAD, entity_id="42",
    )
    assert meta.entity_type == EntityType.LEAD
    assert meta.entity_id == "42"


def test_upload_with_tags_and_description():
    mgr = _make_manager()
    meta = mgr.upload(
        "t1", "file.txt", _sample_content(), "user1",
        tags=["important", "q1"], description="Quarterly report",
    )
    assert meta.tags == ["important", "q1"]
    assert meta.description == "Quarterly report"


# --- Download ---


def test_download_returns_correct_content():
    mgr = _make_manager()
    content = _sample_content("binary data here")
    meta = mgr.upload("t1", "doc.pdf", content, "user1")

    result = mgr.download(meta.id)
    assert result is not None
    returned_meta, returned_content = result
    assert returned_content == content
    assert returned_meta.id == meta.id


def test_download_nonexistent_returns_none():
    mgr = _make_manager()
    assert mgr.download("nonexistent-id") is None


# --- Delete ---


def test_delete_removes_file():
    mgr = _make_manager()
    meta = mgr.upload("t1", "file.txt", _sample_content(), "user1")
    assert mgr.delete(meta.id) is True
    assert mgr.download(meta.id) is None


def test_delete_nonexistent_returns_false():
    mgr = _make_manager()
    assert mgr.delete("nonexistent-id") is False


# --- List ---


def test_list_by_tenant():
    mgr = _make_manager()
    mgr.upload("t1", "a.txt", _sample_content(), "user1")
    mgr.upload("t1", "b.txt", _sample_content(), "user1")
    mgr.upload("t2", "c.txt", _sample_content(), "user2")

    t1_files = mgr.list_files("t1")
    assert len(t1_files) == 2
    t2_files = mgr.list_files("t2")
    assert len(t2_files) == 1


def test_list_by_entity():
    mgr = _make_manager()
    mgr.upload("t1", "a.txt", _sample_content(), "u1",
               entity_type=EntityType.LEAD, entity_id="10")
    mgr.upload("t1", "b.txt", _sample_content(), "u1",
               entity_type=EntityType.TICKET, entity_id="20")
    mgr.upload("t1", "c.txt", _sample_content(), "u1",
               entity_type=EntityType.LEAD, entity_id="10")

    leads = mgr.list_files("t1", entity_type=EntityType.LEAD)
    assert len(leads) == 2
    tickets = mgr.list_files("t1", entity_type=EntityType.TICKET)
    assert len(tickets) == 1

    lead10 = mgr.list_files("t1", entity_type=EntityType.LEAD, entity_id="10")
    assert len(lead10) == 2


# --- Attach / Detach ---


def test_attach_to_entity():
    mgr = _make_manager()
    meta = mgr.upload("t1", "file.txt", _sample_content(), "u1")
    assert meta.entity_type == EntityType.NONE

    updated = mgr.attach_to_entity(meta.id, EntityType.CUSTOMER, "55")
    assert updated is not None
    assert updated.entity_type == EntityType.CUSTOMER
    assert updated.entity_id == "55"


def test_detach_from_entity():
    mgr = _make_manager()
    meta = mgr.upload("t1", "file.txt", _sample_content(), "u1",
                       entity_type=EntityType.LEAD, entity_id="10")
    updated = mgr.detach_from_entity(meta.id)
    assert updated is not None
    assert updated.entity_type == EntityType.NONE
    assert updated.entity_id is None


def test_attach_nonexistent_returns_none():
    mgr = _make_manager()
    assert mgr.attach_to_entity("nope", EntityType.LEAD, "1") is None


def test_detach_nonexistent_returns_none():
    mgr = _make_manager()
    assert mgr.detach_from_entity("nope") is None


# --- Storage usage ---


def test_storage_usage_calculation():
    mgr = _make_manager()
    mgr.upload("t1", "a.pdf", b"x" * 100, "u1")
    mgr.upload("t1", "b.pdf", b"y" * 200, "u1")
    mgr.upload("t1", "c.png", b"z" * 50, "u1")
    mgr.upload("t2", "d.txt", b"w" * 300, "u2")

    usage = mgr.get_storage_usage("t1")
    assert usage["total_files"] == 3
    assert usage["total_bytes"] == 350
    assert usage["by_type"]["application/pdf"] == 2
    assert usage["by_type"]["image/png"] == 1

    usage2 = mgr.get_storage_usage("t2")
    assert usage2["total_files"] == 1
    assert usage2["total_bytes"] == 300


# --- Search ---


def test_search_by_filename():
    mgr = _make_manager()
    mgr.upload("t1", "invoice_2024.pdf", _sample_content(), "u1")
    mgr.upload("t1", "report.pdf", _sample_content(), "u1")

    results = mgr.search_files("t1", "invoice")
    assert len(results) == 1
    assert results[0].filename == "invoice_2024.pdf"


def test_search_by_description():
    mgr = _make_manager()
    mgr.upload("t1", "doc.pdf", _sample_content(), "u1",
               description="Annual financial review")
    mgr.upload("t1", "other.pdf", _sample_content(), "u1",
               description="Marketing plan")

    results = mgr.search_files("t1", "financial")
    assert len(results) == 1


def test_search_by_tags():
    mgr = _make_manager()
    mgr.upload("t1", "a.pdf", _sample_content(), "u1", tags=["urgent", "q1"])
    mgr.upload("t1", "b.pdf", _sample_content(), "u1", tags=["q2"])

    results = mgr.search_files("t1", "urgent")
    assert len(results) == 1


def test_search_empty_query_returns_empty():
    mgr = _make_manager()
    mgr.upload("t1", "a.pdf", _sample_content(), "u1")
    assert mgr.search_files("t1", "") == []
    assert mgr.search_files("t1", "   ") == []


# --- Validation ---


def test_validate_disallowed_extension():
    valid, error = FileManager.validate_upload("malware.exe", 100)
    assert valid is False
    assert "not allowed" in error


def test_validate_allowed_extension():
    valid, error = FileManager.validate_upload("report.pdf", 100)
    assert valid is True
    assert error is None


def test_validate_file_too_large_free():
    size = 6 * 1024 * 1024  # 6 MB
    valid, error = FileManager.validate_upload("file.pdf", size, TenantPlan.FREE)
    assert valid is False
    assert "5 MB" in error


def test_validate_max_file_size_per_plan():
    # FREE: 5 MB limit
    valid, _ = FileManager.validate_upload("f.pdf", 5 * 1024 * 1024, TenantPlan.FREE)
    assert valid is True
    valid, _ = FileManager.validate_upload("f.pdf", 5 * 1024 * 1024 + 1, TenantPlan.FREE)
    assert valid is False

    # PRO: 25 MB limit
    valid, _ = FileManager.validate_upload("f.pdf", 25 * 1024 * 1024, TenantPlan.PRO)
    assert valid is True
    valid, _ = FileManager.validate_upload("f.pdf", 25 * 1024 * 1024 + 1, TenantPlan.PRO)
    assert valid is False

    # ENTERPRISE: 100 MB limit
    valid, _ = FileManager.validate_upload("f.pdf", 100 * 1024 * 1024, TenantPlan.ENTERPRISE)
    assert valid is True
    valid, _ = FileManager.validate_upload("f.pdf", 100 * 1024 * 1024 + 1, TenantPlan.ENTERPRISE)
    assert valid is False


def test_validate_accepts_string_plan():
    valid, error = FileManager.validate_upload("f.pdf", 6 * 1024 * 1024, "PRO")
    assert valid is True
    assert error is None


# --- Storage path format ---


def test_storage_path_format():
    mgr = _make_manager()
    meta = mgr.upload("tenant-abc", "report.pdf", _sample_content(), "u1")

    parts = meta.storage_path.split("/")
    assert parts[0] == "tenant-abc"
    # year and month parts
    assert parts[1].isdigit() and len(parts[1]) == 4  # year
    assert parts[2].isdigit() and len(parts[2]) == 2  # month
    # last part contains uuid and filename
    assert "report.pdf" in parts[3]
    assert meta.id in parts[3]


# --- Multi-tenant isolation ---


def test_multi_tenant_isolation():
    mgr = _make_manager()
    mgr.upload("t1", "secret.pdf", _sample_content("t1 data"), "u1")
    mgr.upload("t2", "public.pdf", _sample_content("t2 data"), "u2")

    t1_files = mgr.list_files("t1")
    t2_files = mgr.list_files("t2")

    assert len(t1_files) == 1
    assert len(t2_files) == 1
    assert t1_files[0].filename == "secret.pdf"
    assert t2_files[0].filename == "public.pdf"

    # Search is also isolated
    assert len(mgr.search_files("t1", "public")) == 0
    assert len(mgr.search_files("t2", "secret")) == 0

    # Usage is isolated
    u1 = mgr.get_storage_usage("t1")
    u2 = mgr.get_storage_usage("t2")
    assert u1["total_files"] == 1
    assert u2["total_files"] == 1


def test_get_metadata_returns_none_for_missing():
    mgr = _make_manager()
    assert mgr.get_metadata("no-such-id") is None


def test_upload_entity_type_as_string():
    mgr = _make_manager()
    meta = mgr.upload("t1", "f.txt", _sample_content(), "u1", entity_type="ticket")
    assert meta.entity_type == EntityType.TICKET


def test_list_files_entity_type_as_string():
    mgr = _make_manager()
    mgr.upload("t1", "f.txt", _sample_content(), "u1", entity_type=EntityType.LEAD)
    results = mgr.list_files("t1", entity_type="lead")
    assert len(results) == 1


def test_attach_entity_type_as_string():
    mgr = _make_manager()
    meta = mgr.upload("t1", "f.txt", _sample_content(), "u1")
    updated = mgr.attach_to_entity(meta.id, "customer", "99")
    assert updated is not None
    assert updated.entity_type == EntityType.CUSTOMER
