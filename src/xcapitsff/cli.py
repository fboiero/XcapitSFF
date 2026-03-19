"""XcapitSFF CLI — management commands for the platform."""

import argparse
import asyncio
import csv
import io
import sys
from pathlib import Path


def _project_root() -> Path:
    """Return the project root (two levels up from this file)."""
    return Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Subcommand implementations
# ---------------------------------------------------------------------------


def cmd_serve(args: argparse.Namespace) -> int:
    """Start the FastAPI server via uvicorn."""
    try:
        import uvicorn
    except ImportError:
        print("ERROR: uvicorn is not installed. Install it with: pip install uvicorn[standard]")
        return 1

    host = args.host
    port = args.port
    reload_flag = args.reload

    print(f"Starting XcapitSFF server on {host}:{port} (reload={reload_flag})")
    uvicorn.run(
        "xcapitsff.api.app:app",
        host=host,
        port=port,
        reload=reload_flag,
    )
    return 0


def cmd_seed(args: argparse.Namespace) -> int:
    """Seed the database from a TSV file."""

    async def _seed() -> int:
        from xcapitsff.core.database import async_session, init_db
        from xcapitsff.sales.importer import import_from_file

        seed_file = args.file
        if not Path(seed_file).exists():
            print(f"ERROR: Seed file not found: {seed_file}")
            return 1

        await init_db()
        async with async_session() as session:
            try:
                count = await import_from_file(session, seed_file)
                await session.commit()
                print(f"Successfully seeded {count} leads from {seed_file}")
                return 0
            except Exception as exc:
                await session.rollback()
                print(f"ERROR: Failed to seed database: {exc}")
                return 1

    return asyncio.run(_seed())


def cmd_stats(_args: argparse.Namespace) -> int:
    """Print pipeline stats in a formatted table."""

    async def _stats() -> int:
        from xcapitsff.core.database import async_session, init_db
        from xcapitsff.sales.pipeline import get_pipeline_stats

        await init_db()
        async with async_session() as session:
            try:
                stats = await get_pipeline_stats(session)
            except Exception as exc:
                print(f"ERROR: Failed to retrieve stats: {exc}")
                return 1

        # ---- Formatted output ----
        print()
        print("=" * 50)
        print("  XcapitSFF Sales Pipeline Stats")
        print("=" * 50)
        print()
        print(f"  Total leads:      {stats.total_leads}")
        print(f"  Avg ICP score:    {stats.avg_score_icp or 'N/A'}")
        print(f"  C-Level contacts: {stats.c_level_count}")
        print(f"  Conversion rate:  {stats.conversion_rate or 'N/A'}%")
        print()

        _print_table("Leads by Stage", stats.by_stage)
        _print_table("Leads by Region", stats.by_region)
        _print_table("Leads by Afinidad", stats.by_afinidad)

        return 0

    return asyncio.run(_stats())


def cmd_qualify(_args: argparse.Namespace) -> int:
    """Run ICP scoring on all unscored leads."""

    async def _qualify() -> int:
        from sqlalchemy import select

        from xcapitsff.core.database import async_session, init_db
        from xcapitsff.core.models import Lead
        from xcapitsff.sales.scoring import calculate_icp_score

        await init_db()
        async with async_session() as session:
            try:
                result = await session.execute(
                    select(Lead).where(Lead.score_icp.is_(None))
                )
                unscored = list(result.scalars().all())

                if not unscored:
                    print("No unscored leads found. Nothing to do.")
                    return 0

                scored_count = 0
                for lead in unscored:
                    score = calculate_icp_score(
                        region=lead.region.value if hasattr(lead.region, "value") else str(lead.region),
                        c_level=lead.c_level,
                        existing_score=None,
                        afinidad=lead.afinidad.value if hasattr(lead.afinidad, "value") else str(lead.afinidad),
                    )
                    lead.score_icp = score
                    scored_count += 1

                await session.commit()
                print(f"Successfully scored {scored_count} leads.")

                # Print summary
                print()
                print(f"  {'Lead ID':<10} {'Region':<10} {'C-Level':<10} {'Score':<10}")
                print(f"  {'-'*10} {'-'*10} {'-'*10} {'-'*10}")
                for lead in unscored:
                    region_val = lead.region.value if hasattr(lead.region, "value") else str(lead.region)
                    print(f"  {lead.id:<10} {region_val:<10} {'Yes' if lead.c_level else 'No':<10} {lead.score_icp:<10}")

                return 0
            except Exception as exc:
                await session.rollback()
                print(f"ERROR: Failed to qualify leads: {exc}")
                return 1

    return asyncio.run(_qualify())


def cmd_export(args: argparse.Namespace) -> int:
    """Export leads to CSV."""

    async def _export() -> int:
        from sqlalchemy import select

        from xcapitsff.core.database import async_session, init_db
        from xcapitsff.core.models import Lead

        await init_db()
        async with async_session() as session:
            try:
                result = await session.execute(
                    select(Lead).order_by(Lead.score_icp.desc().nullslast())
                )
                leads = list(result.scalars().all())

                if not leads:
                    print("No leads found to export.")
                    return 0

                output_path = args.output
                output = io.StringIO()
                writer = csv.writer(output)

                # Header
                writer.writerow([
                    "id", "company_name", "contact_name", "contact_email",
                    "region", "c_level", "score_icp", "afinidad", "stage",
                    "assigned_agent", "notes", "created_at", "updated_at",
                ])

                # Data
                for lead in leads:
                    writer.writerow([
                        lead.id,
                        lead.company_name or "",
                        lead.contact_name or "",
                        lead.contact_email or "",
                        lead.region.value if hasattr(lead.region, "value") else str(lead.region),
                        "Yes" if lead.c_level else "No",
                        lead.score_icp if lead.score_icp is not None else "",
                        lead.afinidad.value if hasattr(lead.afinidad, "value") else str(lead.afinidad),
                        lead.stage.value if hasattr(lead.stage, "value") else str(lead.stage),
                        lead.assigned_agent or "",
                        lead.notes or "",
                        lead.created_at.isoformat() if lead.created_at else "",
                        lead.updated_at.isoformat() if lead.updated_at else "",
                    ])

                csv_content = output.getvalue()
                output.close()

                if output_path == "-":
                    print(csv_content, end="")
                else:
                    Path(output_path).write_text(csv_content, encoding="utf-8")
                    print(f"Exported {len(leads)} leads to {output_path}")

                return 0
            except Exception as exc:
                print(f"ERROR: Failed to export leads: {exc}")
                return 1

    return asyncio.run(_export())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _print_table(title: str, data: dict[str, int]) -> None:
    """Print a simple two-column table."""
    if not data:
        print(f"  {title}: (no data)")
        print()
        return

    max_key_len = max(len(str(k)) for k in data)
    max_val_len = max(len(str(v)) for v in data.values())
    col_width = max(max_key_len, len(title)) + 2

    print(f"  {title}")
    print(f"  {'-' * (col_width + max_val_len + 5)}")
    for key, value in sorted(data.items()):
        print(f"  {str(key):<{col_width}} {value:>{max_val_len}}")
    print()


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="xcapitsff",
        description="XcapitSFF CLI — management commands for the AI-powered platform",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- serve ---
    serve_parser = subparsers.add_parser("serve", help="Start the FastAPI server")
    serve_parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    serve_parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    serve_parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")

    # --- seed ---
    seed_parser = subparsers.add_parser("seed", help="Seed the database from a TSV file")
    default_seed = str(_project_root() / "data" / "leads_seed.tsv")
    seed_parser.add_argument(
        "--file", "-f", default=default_seed,
        help=f"Path to TSV seed file (default: {default_seed})",
    )

    # --- stats ---
    subparsers.add_parser("stats", help="Print sales pipeline statistics")

    # --- qualify ---
    subparsers.add_parser("qualify", help="Run ICP scoring on all unscored leads")

    # --- export ---
    export_parser = subparsers.add_parser("export", help="Export leads to CSV")
    export_parser.add_argument(
        "--output", "-o", default="leads_export.csv",
        help="Output file path (default: leads_export.csv, use '-' for stdout)",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    commands = {
        "serve": cmd_serve,
        "seed": cmd_seed,
        "stats": cmd_stats,
        "qualify": cmd_qualify,
        "export": cmd_export,
    }

    handler = commands.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)

    exit_code = handler(args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
