"""Tests for artifact store."""

from xcapitsff.core.artifact_store import (
    ArtifactFormat,
    ArtifactStore,
    ArtifactType,
)


def test_store_and_retrieve():
    store = ArtifactStore()
    art = store.store("ws-1", "task-1", ArtifactType.SPEC, "spec.md", "# Spec\nContent")
    assert art.id.startswith("ART-")
    assert art.workspace_id == "ws-1"
    assert art.task_id == "task-1"
    assert art.type == ArtifactType.SPEC
    assert art.name == "spec.md"
    assert art.content == "# Spec\nContent"
    assert art.version == 1
    assert art.parent_id is None

    retrieved = store.get(art.id)
    assert retrieved is not None
    assert retrieved.id == art.id


def test_get_nonexistent():
    store = ArtifactStore()
    assert store.get("ART-9999") is None


def test_size_bytes_auto_computed():
    store = ArtifactStore()
    content = "Hello world"
    art = store.store("ws-1", "task-1", ArtifactType.CODE, "main.py", content)
    assert art.size_bytes == len(content.encode())


def test_size_bytes_unicode():
    store = ArtifactStore()
    content = "Hola mundo con acentos: cafe\u0301"
    art = store.store("ws-1", "task-1", ArtifactType.DOCUMENT, "doc.md", content)
    assert art.size_bytes == len(content.encode())


def test_format_default_markdown():
    store = ArtifactStore()
    art = store.store("ws-1", "task-1", ArtifactType.SPEC, "spec.md", "content")
    assert art.format == ArtifactFormat.MARKDOWN


def test_format_explicit():
    store = ArtifactStore()
    art = store.store(
        "ws-1", "task-1", ArtifactType.CODE, "main.py", "print('hi')",
        format=ArtifactFormat.PYTHON,
    )
    assert art.format == ArtifactFormat.PYTHON


def test_auto_increment_version_on_parent():
    store = ArtifactStore()
    v1 = store.store("ws-1", "task-1", ArtifactType.SPEC, "spec.md", "v1 content")
    assert v1.version == 1

    v2 = store.store(
        "ws-1", "task-1", ArtifactType.SPEC, "spec.md", "v2 content",
        parent_id=v1.id,
    )
    assert v2.version == 2
    assert v2.parent_id == v1.id

    v3 = store.store(
        "ws-1", "task-1", ArtifactType.SPEC, "spec.md", "v3 content",
        parent_id=v2.id,
    )
    assert v3.version == 3


def test_parent_id_nonexistent_stays_v1():
    store = ArtifactStore()
    art = store.store(
        "ws-1", "task-1", ArtifactType.SPEC, "spec.md", "content",
        parent_id="ART-0000",
    )
    assert art.version == 1


def test_list_by_workspace():
    store = ArtifactStore()
    store.store("ws-1", "task-1", ArtifactType.SPEC, "spec.md", "a")
    store.store("ws-1", "task-2", ArtifactType.CODE, "code.py", "b")
    store.store("ws-2", "task-3", ArtifactType.SPEC, "spec2.md", "c")

    ws1 = store.list_by_workspace("ws-1")
    assert len(ws1) == 2

    ws2 = store.list_by_workspace("ws-2")
    assert len(ws2) == 1


def test_list_by_workspace_with_type_filter():
    store = ArtifactStore()
    store.store("ws-1", "task-1", ArtifactType.SPEC, "spec.md", "a")
    store.store("ws-1", "task-2", ArtifactType.CODE, "code.py", "b")
    store.store("ws-1", "task-3", ArtifactType.SPEC, "spec2.md", "c")

    specs = store.list_by_workspace("ws-1", artifact_type=ArtifactType.SPEC)
    assert len(specs) == 2
    assert all(a.type == ArtifactType.SPEC for a in specs)


def test_list_by_task():
    store = ArtifactStore()
    store.store("ws-1", "task-1", ArtifactType.SPEC, "spec.md", "a")
    store.store("ws-1", "task-1", ArtifactType.CODE, "code.py", "b")
    store.store("ws-1", "task-2", ArtifactType.SPEC, "spec2.md", "c")

    task1 = store.list_by_task("task-1")
    assert len(task1) == 2

    task2 = store.list_by_task("task-2")
    assert len(task2) == 1


def test_get_latest_version():
    store = ArtifactStore()
    v1 = store.store("ws-1", "task-1", ArtifactType.SPEC, "spec.md", "v1")
    v2 = store.store("ws-1", "task-1", ArtifactType.SPEC, "spec.md", "v2", parent_id=v1.id)
    v3 = store.store("ws-1", "task-1", ArtifactType.SPEC, "spec.md", "v3", parent_id=v2.id)

    latest = store.get_latest_version(v1.id)
    assert latest.id == v3.id
    assert latest.version == 3


def test_get_latest_version_single():
    store = ArtifactStore()
    v1 = store.store("ws-1", "task-1", ArtifactType.SPEC, "spec.md", "v1")

    latest = store.get_latest_version(v1.id)
    assert latest.id == v1.id


def test_get_latest_version_nonexistent():
    store = ArtifactStore()
    assert store.get_latest_version("ART-0000") is None


def test_get_version_history():
    store = ArtifactStore()
    v1 = store.store("ws-1", "task-1", ArtifactType.SPEC, "spec.md", "v1")
    v2 = store.store("ws-1", "task-1", ArtifactType.SPEC, "spec.md", "v2", parent_id=v1.id)
    v3 = store.store("ws-1", "task-1", ArtifactType.SPEC, "spec.md", "v3", parent_id=v2.id)

    history = store.get_version_history(v1.id)
    assert len(history) == 3
    assert history[0].version == 1
    assert history[1].version == 2
    assert history[2].version == 3


def test_get_version_history_from_middle():
    store = ArtifactStore()
    v1 = store.store("ws-1", "task-1", ArtifactType.SPEC, "spec.md", "v1")
    v2 = store.store("ws-1", "task-1", ArtifactType.SPEC, "spec.md", "v2", parent_id=v1.id)
    v3 = store.store("ws-1", "task-1", ArtifactType.SPEC, "spec.md", "v3", parent_id=v2.id)

    history = store.get_version_history(v2.id)
    assert len(history) == 3
    assert history[0].id == v1.id
    assert history[2].id == v3.id


def test_get_version_history_nonexistent():
    store = ArtifactStore()
    assert store.get_version_history("ART-0000") == []


def test_diff_versions_added_lines():
    store = ArtifactStore()
    a = store.store("ws-1", "task-1", ArtifactType.SPEC, "spec.md", "line1\nline2")
    b = store.store("ws-1", "task-1", ArtifactType.SPEC, "spec.md", "line1\nline2\nline3\nline4")

    diff = store.diff_versions(a.id, b.id)
    assert diff["lines_added"] == 2
    assert diff["lines_removed"] == 0


def test_diff_versions_removed_lines():
    store = ArtifactStore()
    a = store.store("ws-1", "task-1", ArtifactType.SPEC, "spec.md", "line1\nline2\nline3")
    b = store.store("ws-1", "task-1", ArtifactType.SPEC, "spec.md", "line1")

    diff = store.diff_versions(a.id, b.id)
    assert diff["lines_removed"] == 2
    assert diff["lines_added"] == 0


def test_diff_versions_changed_lines():
    store = ArtifactStore()
    a = store.store("ws-1", "task-1", ArtifactType.SPEC, "spec.md", "line1\nold line")
    b = store.store("ws-1", "task-1", ArtifactType.SPEC, "spec.md", "line1\nnew line")

    diff = store.diff_versions(a.id, b.id)
    assert diff["lines_changed"] == 1


def test_diff_versions_nonexistent():
    store = ArtifactStore()
    diff = store.diff_versions("ART-0000", "ART-0001")
    assert diff == {"lines_added": 0, "lines_removed": 0, "lines_changed": 0}


def test_search_by_name():
    store = ArtifactStore()
    store.store("ws-1", "task-1", ArtifactType.SPEC, "user-stories.md", "content a")
    store.store("ws-1", "task-2", ArtifactType.CODE, "main.py", "content b")

    results = store.search("ws-1", "user-stories")
    assert len(results) == 1
    assert results[0].name == "user-stories.md"


def test_search_by_content():
    store = ArtifactStore()
    store.store("ws-1", "task-1", ArtifactType.SPEC, "spec.md", "implement the scoring engine")
    store.store("ws-1", "task-2", ArtifactType.CODE, "code.py", "hello world")

    results = store.search("ws-1", "scoring engine")
    assert len(results) == 1


def test_search_case_insensitive():
    store = ArtifactStore()
    store.store("ws-1", "task-1", ArtifactType.SPEC, "README.md", "Important Spec")

    results = store.search("ws-1", "important")
    assert len(results) == 1


def test_search_workspace_isolation():
    store = ArtifactStore()
    store.store("ws-1", "task-1", ArtifactType.SPEC, "spec.md", "shared keyword")
    store.store("ws-2", "task-2", ArtifactType.SPEC, "spec.md", "shared keyword")

    results = store.search("ws-1", "shared")
    assert len(results) == 1
    assert results[0].workspace_id == "ws-1"


def test_stats_global():
    store = ArtifactStore()
    store.store("ws-1", "task-1", ArtifactType.SPEC, "spec.md", "abc")
    store.store("ws-1", "task-2", ArtifactType.CODE, "main.py", "defgh", format=ArtifactFormat.PYTHON)
    store.store("ws-2", "task-3", ArtifactType.SPEC, "spec2.md", "ij")

    stats = store.get_stats()
    assert stats["total"] == 3
    assert stats["by_type"]["spec"] == 2
    assert stats["by_type"]["code"] == 1
    assert stats["by_format"]["markdown"] == 2
    assert stats["by_format"]["python"] == 1
    assert stats["total_bytes"] > 0


def test_stats_by_workspace():
    store = ArtifactStore()
    store.store("ws-1", "task-1", ArtifactType.SPEC, "spec.md", "abc")
    store.store("ws-2", "task-2", ArtifactType.CODE, "code.py", "defgh")

    stats = store.get_stats(workspace_id="ws-1")
    assert stats["total"] == 1
    assert "spec" in stats["by_type"]


def test_tags_stored():
    store = ArtifactStore()
    art = store.store(
        "ws-1", "task-1", ArtifactType.SPEC, "spec.md", "content",
        tags=["mvp", "v1"],
    )
    assert art.tags == ["mvp", "v1"]


def test_tags_default_empty():
    store = ArtifactStore()
    art = store.store("ws-1", "task-1", ArtifactType.SPEC, "spec.md", "content")
    assert art.tags == []


def test_created_by_agent():
    store = ArtifactStore()
    art = store.store(
        "ws-1", "task-1", ArtifactType.CODE, "code.py", "content",
        created_by_agent="sales_qualifier",
    )
    assert art.created_by_agent == "sales_qualifier"


def test_created_at_set():
    store = ArtifactStore()
    art = store.store("ws-1", "task-1", ArtifactType.SPEC, "spec.md", "content")
    assert art.created_at is not None


def test_multi_workspace_isolation():
    store = ArtifactStore()
    store.store("ws-1", "task-1", ArtifactType.SPEC, "spec.md", "a")
    store.store("ws-1", "task-2", ArtifactType.CODE, "code.py", "b")
    store.store("ws-2", "task-3", ArtifactType.SPEC, "spec.md", "c")
    store.store("ws-2", "task-4", ArtifactType.TEST, "test.py", "d")
    store.store("ws-3", "task-5", ArtifactType.REVIEW, "review.md", "e")

    assert len(store.list_by_workspace("ws-1")) == 2
    assert len(store.list_by_workspace("ws-2")) == 2
    assert len(store.list_by_workspace("ws-3")) == 1
    assert len(store.list_by_workspace("ws-4")) == 0


def test_all_artifact_types():
    store = ArtifactStore()
    for art_type in ArtifactType:
        store.store("ws-1", "task-1", art_type, f"{art_type.value}.md", "content")

    stats = store.get_stats("ws-1")
    assert stats["total"] == len(ArtifactType)


def test_all_artifact_formats():
    store = ArtifactStore()
    for fmt in ArtifactFormat:
        store.store("ws-1", "task-1", ArtifactType.DOCUMENT, f"doc.{fmt.value}", "content", format=fmt)

    stats = store.get_stats("ws-1")
    assert stats["total"] == len(ArtifactFormat)
