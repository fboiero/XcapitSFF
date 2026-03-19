"""Tests for the reporting engine."""

from xcapitsff.core.reporting import Report, format_bar_chart, format_kpi_card, format_table


def test_report_creation():
    r = Report(title="Test Report")
    assert r.title == "Test Report"
    assert len(r.sections) == 0


def test_add_section():
    r = Report(title="Test")
    r.add_section("Section 1", "Content here")
    assert len(r.sections) == 1
    assert r.sections[0].title == "Section 1"


def test_to_markdown():
    r = Report(title="Test Report")
    r.add_section("KPIs", "Total: 100")
    md = r.to_markdown()
    assert "# Test Report" in md
    assert "## KPIs" in md
    assert "Total: 100" in md


def test_to_text():
    r = Report(title="Test Report")
    r.add_section("KPIs", "Total: 100")
    text = r.to_text()
    assert "Test Report" in text
    assert "KPIs" in text


def test_to_dict():
    r = Report(title="Test")
    r.add_section("S1", "C1", data={"key": "val"})
    d = r.to_dict()
    assert d["title"] == "Test"
    assert len(d["sections"]) == 1
    assert d["sections"][0]["data"]["key"] == "val"


def test_format_table():
    t = format_table(["Name", "Score"], [["Alice", 90], ["Bob", 75]])
    assert "Alice" in t
    assert "Score" in t


def test_format_table_empty():
    t = format_table(["Name"], [])
    assert "sin datos" in t


def test_format_kpi_card():
    card = format_kpi_card("Total Leads", 150)
    assert "Total Leads: 150" in card


def test_format_kpi_card_with_unit():
    card = format_kpi_card("Rate", 25.5, "%")
    assert "25.5%" in card


def test_format_bar_chart():
    chart = format_bar_chart({"LATAM": 80, "Iberia": 20})
    assert "LATAM" in chart
    assert "#" in chart


def test_format_bar_chart_empty():
    chart = format_bar_chart({})
    assert "sin datos" in chart
