"""Reporting engine — generate structured reports for all modules.

Reports can be rendered as JSON, plain text tables, or markdown.
This module provides the formatting layer that sits between
analytics data and the presentation.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ReportSection:
    title: str
    content: str
    data: dict | list | None = None


@dataclass
class Report:
    title: str
    generated_at: datetime = field(default_factory=datetime.now)
    sections: list[ReportSection] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def add_section(self, title: str, content: str, data=None) -> None:
        self.sections.append(ReportSection(title=title, content=content, data=data))

    def to_markdown(self) -> str:
        lines = [
            f"# {self.title}",
            f"*Generado: {self.generated_at.strftime('%Y-%m-%d %H:%M')}*",
            "",
        ]
        for section in self.sections:
            lines.append(f"## {section.title}")
            lines.append(section.content)
            lines.append("")
        return "\n".join(lines)

    def to_text(self) -> str:
        lines = [
            f"{'=' * 60}",
            f"  {self.title}",
            f"  Generado: {self.generated_at.strftime('%Y-%m-%d %H:%M')}",
            f"{'=' * 60}",
            "",
        ]
        for section in self.sections:
            lines.append(f"--- {section.title} ---")
            lines.append(section.content)
            lines.append("")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "generated_at": self.generated_at.isoformat(),
            "metadata": self.metadata,
            "sections": [
                {
                    "title": s.title,
                    "content": s.content,
                    "data": s.data,
                }
                for s in self.sections
            ],
        }


def format_table(headers: list[str], rows: list[list], align: str = "left") -> str:
    """Format data as a plain text table."""
    if not rows:
        return "(sin datos)"

    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))

    header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    separator = "-+-".join("-" * w for w in col_widths)

    lines = [header_line, separator]
    for row in rows:
        line = " | ".join(
            str(cell).ljust(col_widths[i]) if i < len(col_widths) else str(cell)
            for i, cell in enumerate(row)
        )
        lines.append(line)

    return "\n".join(lines)


def format_kpi_card(label: str, value, unit: str = "") -> str:
    return f"  {label}: {value}{unit}"


def format_bar_chart(data: dict[str, int], max_width: int = 30) -> str:
    """Format a simple horizontal bar chart."""
    if not data:
        return "(sin datos)"

    max_val = max(data.values()) if data.values() else 1
    lines = []
    for label, value in data.items():
        bar_len = int(value / max_val * max_width) if max_val > 0 else 0
        bar = "#" * bar_len
        lines.append(f"  {label:15s} |{bar} {value}")
    return "\n".join(lines)


async def generate_executive_report(db) -> Report:
    """Generate a comprehensive executive report."""
    from xcapitsff.sales.pipeline import get_hot_leads, get_pipeline_funnel, get_pipeline_stats
    from xcapitsff.support.tickets import get_overdue_tickets, get_support_stats

    report = Report(title="XcapitSFF — Reporte Ejecutivo")

    # Sales section
    sales_stats = await get_pipeline_stats(db)
    funnel = await get_pipeline_funnel(db)
    hot_leads = await get_hot_leads(db, limit=10)

    sales_content = "\n".join([
        format_kpi_card("Total leads", sales_stats.total_leads),
        format_kpi_card("Score ICP promedio", sales_stats.avg_score_icp or "N/A"),
        format_kpi_card("Leads C-Level", sales_stats.c_level_count),
        format_kpi_card("Tasa de conversión", sales_stats.conversion_rate, "%"),
        format_kpi_card("Hot leads pendientes", len(hot_leads)),
        "",
        "Funnel:",
        format_bar_chart({item["stage"]: item["count"] for item in funnel}),
        "",
        "Por región:",
        format_bar_chart(sales_stats.by_region),
    ])
    report.add_section("Ventas", sales_content, data={
        "stats": {
            "total": sales_stats.total_leads,
            "avg_score": sales_stats.avg_score_icp,
            "conversion_rate": sales_stats.conversion_rate,
        },
        "funnel": funnel,
    })

    # Support section
    support_stats = await get_support_stats(db)
    overdue = await get_overdue_tickets(db)

    support_content = "\n".join([
        format_kpi_card("Total tickets", support_stats.total_tickets),
        format_kpi_card("Tickets abiertos", support_stats.open_tickets),
        format_kpi_card("Tiempo resolución promedio", support_stats.avg_resolution_hours, "h"),
        format_kpi_card("Tickets vencidos (SLA)", len(overdue)),
        "",
        "Por categoría:",
        format_bar_chart(support_stats.by_category),
        "",
        "Por prioridad:",
        format_bar_chart(support_stats.by_priority),
    ])
    report.add_section("Soporte", support_content, data={
        "stats": {
            "total": support_stats.total_tickets,
            "open": support_stats.open_tickets,
            "overdue": len(overdue),
        },
    })

    return report
