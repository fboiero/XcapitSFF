"""Tests for saved views & filters system."""

from xcapitsff.core.saved_views import (
    DEFAULT_VIEWS,
    FilterCondition,
    FilterOperator,
    SavedViewManager,
    SortOrder,
    ViewConfig,
    ViewEntity,
    _match_filter,
)


def _make_config(**kwargs) -> ViewConfig:
    defaults = {
        "columns": ["name", "score"],
        "sort_by": "score",
        "sort_order": SortOrder.DESC,
    }
    defaults.update(kwargs)
    return ViewConfig(**defaults)


def test_create_view():
    mgr = SavedViewManager()
    config = _make_config()
    view = mgr.create("t1", "user1", ViewEntity.LEADS, "Hot Leads", config)
    assert view.tenant_id == "t1"
    assert view.user_id == "user1"
    assert view.entity == ViewEntity.LEADS
    assert view.name == "Hot Leads"
    assert view.usage_count == 0
    assert view.is_shared is False
    assert view.is_default is False
    assert mgr.count == 1


def test_create_view_string_entity():
    mgr = SavedViewManager()
    config = _make_config()
    view = mgr.create("t1", "user1", "leads", "My View", config)
    assert view.entity == ViewEntity.LEADS


def test_create_shared_view():
    mgr = SavedViewManager()
    config = _make_config()
    view = mgr.create("t1", "user1", ViewEntity.LEADS, "Team View", config, is_shared=True)
    assert view.is_shared is True


def test_update_view():
    mgr = SavedViewManager()
    view = mgr.create("t1", "user1", ViewEntity.LEADS, "Original", _make_config())
    updated = mgr.update(view.id, name="Renamed", description="Updated desc")
    assert updated is not None
    assert updated.name == "Renamed"
    assert updated.description == "Updated desc"


def test_update_nonexistent_returns_none():
    mgr = SavedViewManager()
    assert mgr.update("nonexistent", name="X") is None


def test_delete_view():
    mgr = SavedViewManager()
    view = mgr.create("t1", "user1", ViewEntity.LEADS, "To Delete", _make_config())
    assert mgr.delete(view.id) is True
    assert mgr.count == 0


def test_delete_nonexistent_returns_false():
    mgr = SavedViewManager()
    assert mgr.delete("nonexistent") is False


def test_get_views_own_and_shared():
    mgr = SavedViewManager()
    mgr.create("t1", "user1", ViewEntity.LEADS, "My View", _make_config())
    mgr.create("t1", "user2", ViewEntity.LEADS, "User2 Private", _make_config())
    mgr.create("t1", "user2", ViewEntity.LEADS, "Shared View", _make_config(), is_shared=True)

    views = mgr.get_views("t1", "user1")
    names = [v.name for v in views]
    assert "My View" in names
    assert "Shared View" in names
    assert "User2 Private" not in names


def test_get_views_filtered_by_entity():
    mgr = SavedViewManager()
    mgr.create("t1", "user1", ViewEntity.LEADS, "Leads View", _make_config())
    mgr.create("t1", "user1", ViewEntity.TICKETS, "Tickets View", _make_config())

    views = mgr.get_views("t1", "user1", entity=ViewEntity.LEADS)
    assert len(views) == 1
    assert views[0].entity == ViewEntity.LEADS


def test_set_and_get_default():
    mgr = SavedViewManager()
    view = mgr.create("t1", "user1", ViewEntity.LEADS, "Default View", _make_config())
    result = mgr.set_default(view.id, "user1")
    assert result is not None
    assert result.is_default is True

    default = mgr.get_default("t1", "user1", ViewEntity.LEADS)
    assert default is not None
    assert default.id == view.id


def test_set_default_replaces_previous():
    mgr = SavedViewManager()
    v1 = mgr.create("t1", "user1", ViewEntity.LEADS, "View 1", _make_config())
    v2 = mgr.create("t1", "user1", ViewEntity.LEADS, "View 2", _make_config())

    mgr.set_default(v1.id, "user1")
    mgr.set_default(v2.id, "user1")

    assert v1.is_default is False
    assert v2.is_default is True

    default = mgr.get_default("t1", "user1", ViewEntity.LEADS)
    assert default.id == v2.id


def test_get_default_returns_none_when_unset():
    mgr = SavedViewManager()
    assert mgr.get_default("t1", "user1", ViewEntity.LEADS) is None


def test_set_default_nonexistent_returns_none():
    mgr = SavedViewManager()
    assert mgr.set_default("nonexistent", "user1") is None


def test_duplicate_view():
    mgr = SavedViewManager()
    original = mgr.create("t1", "user1", ViewEntity.LEADS, "Original", _make_config(
        filters=[FilterCondition("score", FilterOperator.GTE, 80)],
    ))

    dup = mgr.duplicate(original.id, "Copy of Original")
    assert dup is not None
    assert dup.name == "Copy of Original"
    assert dup.id != original.id
    assert dup.entity == original.entity
    assert len(dup.config.filters) == 1
    assert dup.config.filters[0].value == 80
    assert dup.is_default is False
    assert dup.is_shared is False
    assert mgr.count == 2


def test_duplicate_nonexistent_returns_none():
    mgr = SavedViewManager()
    assert mgr.duplicate("nonexistent", "Copy") is None


def test_increment_usage():
    mgr = SavedViewManager()
    view = mgr.create("t1", "user1", ViewEntity.LEADS, "View", _make_config())
    assert view.usage_count == 0
    mgr.increment_usage(view.id)
    mgr.increment_usage(view.id)
    assert view.usage_count == 2


def test_get_popular_views():
    mgr = SavedViewManager()
    v1 = mgr.create("t1", "user1", ViewEntity.LEADS, "View 1", _make_config())
    v2 = mgr.create("t1", "user1", ViewEntity.LEADS, "View 2", _make_config())
    v3 = mgr.create("t1", "user1", ViewEntity.LEADS, "View 3", _make_config())

    for _ in range(5):
        mgr.increment_usage(v2.id)
    for _ in range(3):
        mgr.increment_usage(v3.id)

    popular = mgr.get_popular_views("t1", ViewEntity.LEADS, limit=2)
    assert len(popular) == 2
    assert popular[0].id == v2.id
    assert popular[1].id == v3.id


def test_apply_filters_eq():
    mgr = SavedViewManager()
    data = [
        {"name": "Alice", "status": "active"},
        {"name": "Bob", "status": "inactive"},
    ]
    config = ViewConfig(
        filters=[FilterCondition("status", FilterOperator.EQ, "active")],
    )
    result = mgr.apply_filters(data, config)
    assert len(result) == 1
    assert result[0]["name"] == "Alice"


def test_apply_filters_gt_lt():
    mgr = SavedViewManager()
    data = [
        {"name": "A", "score": 90},
        {"name": "B", "score": 50},
        {"name": "C", "score": 70},
    ]
    config = ViewConfig(
        filters=[FilterCondition("score", FilterOperator.GT, 60)],
    )
    result = mgr.apply_filters(data, config)
    assert len(result) == 2


def test_apply_filters_contains():
    mgr = SavedViewManager()
    data = [
        {"name": "Alice Smith"},
        {"name": "Bob Johnson"},
    ]
    config = ViewConfig(
        filters=[FilterCondition("name", FilterOperator.CONTAINS, "alice")],
    )
    result = mgr.apply_filters(data, config)
    assert len(result) == 1
    assert result[0]["name"] == "Alice Smith"


def test_apply_filters_in_operator():
    mgr = SavedViewManager()
    data = [
        {"name": "A", "status": "open"},
        {"name": "B", "status": "closed"},
        {"name": "C", "status": "in_progress"},
    ]
    config = ViewConfig(
        filters=[FilterCondition("status", FilterOperator.IN, ["open", "in_progress"])],
    )
    result = mgr.apply_filters(data, config)
    assert len(result) == 2


def test_apply_filters_is_empty():
    mgr = SavedViewManager()
    data = [
        {"name": "A", "email": ""},
        {"name": "B", "email": "b@x.com"},
        {"name": "C", "email": None},
    ]
    config = ViewConfig(
        filters=[FilterCondition("email", FilterOperator.IS_EMPTY)],
    )
    result = mgr.apply_filters(data, config)
    assert len(result) == 2


def test_apply_filters_sorting_asc():
    mgr = SavedViewManager()
    data = [
        {"name": "C", "score": 30},
        {"name": "A", "score": 10},
        {"name": "B", "score": 20},
    ]
    config = ViewConfig(sort_by="score", sort_order=SortOrder.ASC)
    result = mgr.apply_filters(data, config)
    assert [r["name"] for r in result] == ["A", "B", "C"]


def test_apply_filters_sorting_desc():
    mgr = SavedViewManager()
    data = [
        {"name": "A", "score": 10},
        {"name": "C", "score": 30},
        {"name": "B", "score": 20},
    ]
    config = ViewConfig(sort_by="score", sort_order=SortOrder.DESC)
    result = mgr.apply_filters(data, config)
    assert [r["name"] for r in result] == ["C", "B", "A"]


def test_apply_filters_pagination():
    mgr = SavedViewManager()
    data = [{"id": i} for i in range(10)]
    config = ViewConfig(page_size=3)
    page1 = mgr.apply_filters(data, config, page=1)
    page2 = mgr.apply_filters(data, config, page=2)
    assert len(page1) == 3
    assert len(page2) == 3
    assert page1[0]["id"] != page2[0]["id"]


def test_delete_default_view_clears_default():
    mgr = SavedViewManager()
    view = mgr.create("t1", "user1", ViewEntity.LEADS, "Default", _make_config())
    mgr.set_default(view.id, "user1")
    mgr.delete(view.id)
    assert mgr.get_default("t1", "user1", ViewEntity.LEADS) is None


def test_to_dict():
    mgr = SavedViewManager()
    config = _make_config(
        filters=[FilterCondition("score", FilterOperator.GTE, 50)],
    )
    view = mgr.create("t1", "user1", ViewEntity.LEADS, "Test View", config, description="Desc")
    d = view.to_dict()
    assert d["name"] == "Test View"
    assert d["entity"] == "leads"
    assert d["description"] == "Desc"
    assert d["is_shared"] is False
    assert d["usage_count"] == 0
    assert len(d["config"]["filters"]) == 1
    assert d["config"]["filters"][0]["operator"] == "gte"


def test_view_entity_enum_values():
    assert ViewEntity.LEADS.value == "leads"
    assert ViewEntity.TICKETS.value == "tickets"
    assert ViewEntity.CUSTOMERS.value == "customers"
    assert ViewEntity.CONTACTS.value == "contacts"
    assert ViewEntity.COMPANIES.value == "companies"
    assert ViewEntity.DEALS.value == "deals"


def test_default_views_exist():
    assert ViewEntity.LEADS in DEFAULT_VIEWS
    assert ViewEntity.TICKETS in DEFAULT_VIEWS
    assert ViewEntity.CUSTOMERS in DEFAULT_VIEWS
    assert len(DEFAULT_VIEWS[ViewEntity.LEADS]) >= 1
    assert DEFAULT_VIEWS[ViewEntity.LEADS][0]["name"] == "Hot Leads"


def test_filter_condition_string_operator():
    fc = FilterCondition("score", "gte", 50)
    assert fc.operator == FilterOperator.GTE


def test_match_filter_ne():
    assert _match_filter({"status": "open"}, FilterCondition("status", FilterOperator.NE, "closed")) is True
    assert _match_filter({"status": "closed"}, FilterCondition("status", FilterOperator.NE, "closed")) is False


def test_match_filter_not_in():
    assert _match_filter(
        {"status": "open"},
        FilterCondition("status", FilterOperator.NOT_IN, ["closed", "resolved"]),
    ) is True
    assert _match_filter(
        {"status": "closed"},
        FilterCondition("status", FilterOperator.NOT_IN, ["closed", "resolved"]),
    ) is False


def test_match_filter_is_not_empty():
    assert _match_filter({"email": "a@b.com"}, FilterCondition("email", FilterOperator.IS_NOT_EMPTY)) is True
    assert _match_filter({"email": ""}, FilterCondition("email", FilterOperator.IS_NOT_EMPTY)) is False
    assert _match_filter({"email": None}, FilterCondition("email", FilterOperator.IS_NOT_EMPTY)) is False
