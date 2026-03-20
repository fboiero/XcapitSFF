"""Tests for the dashboard widgets system."""

from __future__ import annotations

import pytest

from xcapitsff.core.dashboard_widgets import (
    DEFAULT_WIDGETS,
    WIDGET_CATALOG,
    DashboardLayout,
    DashboardWidgetManager,
    Widget,
    WidgetData,
    WidgetSize,
    WidgetType,
)


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture()
def manager() -> DashboardWidgetManager:
    """Fresh manager per test — no shared state."""
    return DashboardWidgetManager()


TENANT = "tenant-1"
USER = "user-1"


# ===================================================================
# Layout creation
# ===================================================================


class TestCreateLayout:
    def test_create_layout_returns_layout(self, manager: DashboardWidgetManager):
        layout = manager.create_layout(TENANT, USER, "Test Dashboard")
        assert isinstance(layout, DashboardLayout)
        assert layout.tenant_id == TENANT
        assert layout.user_id == USER
        assert layout.name == "Test Dashboard"

    def test_create_layout_has_id(self, manager: DashboardWidgetManager):
        layout = manager.create_layout(TENANT, USER, "D")
        assert layout.id is not None
        assert len(layout.id) == 36  # UUID

    def test_create_layout_is_default(self, manager: DashboardWidgetManager):
        layout = manager.create_layout(TENANT, USER, "D")
        assert layout.is_default is True


# ===================================================================
# Default widgets
# ===================================================================


class TestDefaultWidgets:
    def test_default_layout_has_8_widgets(self, manager: DashboardWidgetManager):
        layout = manager.create_layout(TENANT, USER, "D")
        assert len(layout.widgets) == 8

    def test_default_widget_types(self, manager: DashboardWidgetManager):
        layout = manager.create_layout(TENANT, USER, "D")
        types = {w.type for w in layout.widgets}
        assert WidgetType.KPI in types
        assert WidgetType.FUNNEL in types
        assert WidgetType.TABLE in types

    def test_default_widgets_constant_matches(self):
        assert len(DEFAULT_WIDGETS) == 8

    def test_default_widgets_have_unique_positions(self, manager: DashboardWidgetManager):
        layout = manager.create_layout(TENANT, USER, "D")
        positions = [(w.position["row"], w.position["col"]) for w in layout.widgets]
        assert len(positions) == len(set(positions))


# ===================================================================
# Add widget
# ===================================================================


class TestAddWidget:
    def test_add_widget(self, manager: DashboardWidgetManager):
        layout = manager.create_layout(TENANT, USER, "D")
        widget = manager.add_widget(layout.id, WidgetType.BAR_CHART, "Barras")
        assert isinstance(widget, Widget)
        assert widget.type == WidgetType.BAR_CHART
        assert widget.title == "Barras"
        assert len(layout.widgets) == 9

    def test_add_widget_with_config(self, manager: DashboardWidgetManager):
        layout = manager.create_layout(TENANT, USER, "D")
        cfg = {"data_source": "custom", "filters": {"status": "open"}, "refresh_interval_seconds": 30}
        widget = manager.add_widget(layout.id, WidgetType.KPI, "Custom", config=cfg)
        assert widget.config == cfg

    def test_add_widget_custom_size_and_position(self, manager: DashboardWidgetManager):
        layout = manager.create_layout(TENANT, USER, "D")
        widget = manager.add_widget(
            layout.id, WidgetType.HEATMAP, "Heat",
            size=WidgetSize.FULL, position={"row": 10, "col": 0},
        )
        assert widget.size == WidgetSize.FULL
        assert widget.position == {"row": 10, "col": 0}

    def test_add_widget_invalid_layout_raises(self, manager: DashboardWidgetManager):
        with pytest.raises(ValueError, match="not found"):
            manager.add_widget("nonexistent", WidgetType.KPI, "X")


# ===================================================================
# Remove widget
# ===================================================================


class TestRemoveWidget:
    def test_remove_existing_widget(self, manager: DashboardWidgetManager):
        layout = manager.create_layout(TENANT, USER, "D")
        wid = layout.widgets[0].id
        assert manager.remove_widget(layout.id, wid) is True
        assert len(layout.widgets) == 7

    def test_remove_nonexistent_widget(self, manager: DashboardWidgetManager):
        layout = manager.create_layout(TENANT, USER, "D")
        assert manager.remove_widget(layout.id, "no-such-id") is False

    def test_remove_from_nonexistent_layout(self, manager: DashboardWidgetManager):
        assert manager.remove_widget("bad-layout", "bad-widget") is False


# ===================================================================
# Update widget
# ===================================================================


class TestUpdateWidget:
    def test_update_title(self, manager: DashboardWidgetManager):
        layout = manager.create_layout(TENANT, USER, "D")
        wid = layout.widgets[0].id
        updated = manager.update_widget(layout.id, wid, title="Nuevo Título")
        assert updated.title == "Nuevo Título"

    def test_update_multiple_fields(self, manager: DashboardWidgetManager):
        layout = manager.create_layout(TENANT, USER, "D")
        wid = layout.widgets[0].id
        updated = manager.update_widget(
            layout.id, wid,
            title="Changed",
            visible=False,
            size=WidgetSize.LARGE,
        )
        assert updated.title == "Changed"
        assert updated.visible is False
        assert updated.size == WidgetSize.LARGE

    def test_update_nonexistent_widget_raises(self, manager: DashboardWidgetManager):
        layout = manager.create_layout(TENANT, USER, "D")
        with pytest.raises(ValueError, match="not found"):
            manager.update_widget(layout.id, "no-id", title="X")

    def test_update_nonexistent_layout_raises(self, manager: DashboardWidgetManager):
        with pytest.raises(ValueError, match="not found"):
            manager.update_widget("bad", "bad", title="X")


# ===================================================================
# Reorder
# ===================================================================


class TestReorder:
    def test_reorder_changes_order(self, manager: DashboardWidgetManager):
        layout = manager.create_layout(TENANT, USER, "D")
        ids = [w.id for w in layout.widgets]
        reversed_ids = list(reversed(ids))
        result = manager.reorder_widgets(layout.id, reversed_ids)
        assert [w.id for w in result.widgets] == reversed_ids

    def test_reorder_updates_positions(self, manager: DashboardWidgetManager):
        layout = manager.create_layout(TENANT, USER, "D")
        ids = [w.id for w in layout.widgets]
        manager.reorder_widgets(layout.id, ids)
        for idx, w in enumerate(layout.widgets):
            assert w.position == {"row": idx // 3, "col": idx % 3}


# ===================================================================
# Widget data generation
# ===================================================================


class TestWidgetData:
    @pytest.mark.parametrize("wtype", list(WidgetType))
    def test_get_widget_data_for_each_type(self, manager: DashboardWidgetManager, wtype: WidgetType):
        widget = Widget(id="w1", type=wtype, title="Test", config={"filters": {"limit": 5}, "refresh_interval_seconds": 60})
        result = manager.get_widget_data(widget, TENANT)
        assert isinstance(result, WidgetData)
        assert result.widget_id == "w1"
        assert isinstance(result.data, dict)
        assert result.generated_at is not None

    def test_cached_until_uses_refresh_interval(self, manager: DashboardWidgetManager):
        widget = Widget(id="w1", type=WidgetType.KPI, title="T", config={"refresh_interval_seconds": 120})
        result = manager.get_widget_data(widget, TENANT)
        assert result.cached_until is not None
        diff = (result.cached_until - result.generated_at).total_seconds()
        assert diff == pytest.approx(120, abs=1)

    def test_zero_refresh_means_no_cache(self, manager: DashboardWidgetManager):
        widget = Widget(id="w1", type=WidgetType.QUICK_ACTIONS, title="T", config={"refresh_interval_seconds": 0})
        result = manager.get_widget_data(widget, TENANT)
        assert result.cached_until is None


# ===================================================================
# Full dashboard
# ===================================================================


class TestFullDashboard:
    def test_full_dashboard_structure(self, manager: DashboardWidgetManager):
        result = manager.get_full_dashboard(TENANT, USER)
        assert "layout" in result
        assert "widget_data" in result
        assert result["layout"]["tenant_id"] == TENANT
        assert result["layout"]["user_id"] == USER

    def test_full_dashboard_widget_data_count(self, manager: DashboardWidgetManager):
        result = manager.get_full_dashboard(TENANT, USER)
        # All 8 default widgets are visible
        assert len(result["widget_data"]) == 8

    def test_full_dashboard_hidden_widgets_excluded(self, manager: DashboardWidgetManager):
        layout = manager.create_layout(TENANT, USER, "D")
        layout.widgets[0].visible = False
        layout.widgets[1].visible = False
        result = manager.get_full_dashboard(TENANT, USER)
        assert len(result["widget_data"]) == 6

    def test_full_dashboard_auto_creates_layout(self, manager: DashboardWidgetManager):
        """get_full_dashboard on a new user auto-creates a default layout."""
        result = manager.get_full_dashboard("new-tenant", "new-user")
        assert result["layout"]["name"] == "Mi Dashboard"
        assert len(result["layout"]["widgets"]) == 8


# ===================================================================
# Reset to default
# ===================================================================


class TestResetToDefault:
    def test_reset_restores_8_widgets(self, manager: DashboardWidgetManager):
        layout = manager.create_layout(TENANT, USER, "D")
        manager.add_widget(layout.id, WidgetType.CALENDAR, "Cal")
        manager.add_widget(layout.id, WidgetType.HEATMAP, "Heat")
        assert len(layout.widgets) == 10
        manager.reset_to_default(layout.id)
        assert len(layout.widgets) == 8
        assert layout.is_default is True

    def test_reset_invalid_layout_raises(self, manager: DashboardWidgetManager):
        with pytest.raises(ValueError, match="not found"):
            manager.reset_to_default("bad-id")


# ===================================================================
# Clone layout
# ===================================================================


class TestCloneLayout:
    def test_clone_creates_new_layout(self, manager: DashboardWidgetManager):
        original = manager.create_layout(TENANT, USER, "Original")
        cloned = manager.clone_layout(original.id, "Cloned")
        assert cloned.id != original.id
        assert cloned.name == "Cloned"

    def test_clone_has_same_widget_count(self, manager: DashboardWidgetManager):
        original = manager.create_layout(TENANT, USER, "O")
        cloned = manager.clone_layout(original.id, "C")
        assert len(cloned.widgets) == len(original.widgets)

    def test_clone_widgets_have_new_ids(self, manager: DashboardWidgetManager):
        original = manager.create_layout(TENANT, USER, "O")
        cloned = manager.clone_layout(original.id, "C")
        orig_ids = {w.id for w in original.widgets}
        clone_ids = {w.id for w in cloned.widgets}
        assert orig_ids.isdisjoint(clone_ids)

    def test_clone_is_not_default(self, manager: DashboardWidgetManager):
        original = manager.create_layout(TENANT, USER, "O")
        cloned = manager.clone_layout(original.id, "C")
        assert cloned.is_default is False

    def test_clone_invalid_layout_raises(self, manager: DashboardWidgetManager):
        with pytest.raises(ValueError, match="not found"):
            manager.clone_layout("bad-id", "X")


# ===================================================================
# Widget catalog
# ===================================================================


class TestWidgetCatalog:
    def test_catalog_has_all_types(self, manager: DashboardWidgetManager):
        catalog = manager.get_widget_catalog()
        types = {c["type"] for c in catalog}
        for wt in WidgetType:
            assert wt.value in types

    def test_catalog_entries_have_required_fields(self, manager: DashboardWidgetManager):
        catalog = manager.get_widget_catalog()
        for entry in catalog:
            assert "type" in entry
            assert "name" in entry
            assert "description" in entry
            assert "default_config" in entry
            assert "available_sizes" in entry

    def test_catalog_count(self):
        assert len(WIDGET_CATALOG) == 12


# ===================================================================
# Position management
# ===================================================================


class TestPositionManagement:
    def test_auto_position_fills_row(self, manager: DashboardWidgetManager):
        layout = manager.create_layout(TENANT, USER, "D")
        # Clear widgets and add manually
        layout.widgets.clear()
        w1 = manager.add_widget(layout.id, WidgetType.KPI, "A")
        assert w1.position == {"row": 0, "col": 0}
        w2 = manager.add_widget(layout.id, WidgetType.KPI, "B")
        assert w2.position == {"row": 0, "col": 1}
        w3 = manager.add_widget(layout.id, WidgetType.KPI, "C")
        assert w3.position == {"row": 0, "col": 2}
        # Next should wrap to row 1
        w4 = manager.add_widget(layout.id, WidgetType.KPI, "D")
        assert w4.position == {"row": 1, "col": 0}

    def test_explicit_position_overrides_auto(self, manager: DashboardWidgetManager):
        layout = manager.create_layout(TENANT, USER, "D")
        w = manager.add_widget(layout.id, WidgetType.KPI, "X", position={"row": 99, "col": 2})
        assert w.position == {"row": 99, "col": 2}


# ===================================================================
# Multi-tenant isolation
# ===================================================================


class TestMultiTenantIsolation:
    def test_different_tenants_get_separate_layouts(self, manager: DashboardWidgetManager):
        l1 = manager.get_layout("tenant-a", "user-1")
        l2 = manager.get_layout("tenant-b", "user-1")
        assert l1.id != l2.id
        assert l1.tenant_id == "tenant-a"
        assert l2.tenant_id == "tenant-b"

    def test_different_users_same_tenant(self, manager: DashboardWidgetManager):
        l1 = manager.get_layout(TENANT, "user-a")
        l2 = manager.get_layout(TENANT, "user-b")
        assert l1.id != l2.id

    def test_modifying_one_tenant_does_not_affect_other(self, manager: DashboardWidgetManager):
        l1 = manager.get_layout("t1", "u1")
        l2 = manager.get_layout("t2", "u2")
        manager.add_widget(l1.id, WidgetType.CALENDAR, "Cal")
        assert len(l1.widgets) == 9
        assert len(l2.widgets) == 8


# ===================================================================
# Get layout (auto-create)
# ===================================================================


class TestGetLayout:
    def test_get_layout_auto_creates(self, manager: DashboardWidgetManager):
        layout = manager.get_layout("new-t", "new-u")
        assert layout.name == "Mi Dashboard"
        assert len(layout.widgets) == 8

    def test_get_layout_returns_same_on_second_call(self, manager: DashboardWidgetManager):
        l1 = manager.get_layout(TENANT, USER)
        l2 = manager.get_layout(TENANT, USER)
        assert l1.id == l2.id
