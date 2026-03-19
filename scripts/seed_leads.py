"""Script to seed the database with initial lead data."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from xcapitsff.core.database import async_session, init_db
from xcapitsff.sales.importer import import_from_file, parse_leads


async def main():
    print("Initializing database...")
    await init_db()

    data_file = Path(__file__).parent.parent / "data" / "leads_seed.tsv"
    if not data_file.exists():
        print(f"Error: {data_file} not found")
        sys.exit(1)

    # Preview
    content = data_file.read_text(encoding="utf-8")
    leads, parse_result = parse_leads(content)
    print(f"Parsed {parse_result.parsed} leads from {data_file.name}")
    print(f"  Regions: ", end="")
    regions = {}
    afinidades = {}
    c_level_count = 0
    for l in leads:
        regions[l["region"]] = regions.get(l["region"], 0) + 1
        afinidades[l["afinidad"]] = afinidades.get(l["afinidad"], 0) + 1
        if l["c_level"]:
            c_level_count += 1
    print(", ".join(f"{k}={v}" for k, v in regions.items()))
    print(f"  Afinidad: ", ", ".join(f"{k}={v}" for k, v in afinidades.items()))
    print(f"  C-Level: {c_level_count}/{len(leads)}")

    print(f"\nImporting...")
    async with async_session() as db:
        count = await import_from_file(db, str(data_file))
        await db.commit()

    print(f"Done! Imported {count} leads.")
    print(f"\nTo start the API: PYTHONPATH=src uvicorn xcapitsff.api.app:app --reload")


if __name__ == "__main__":
    asyncio.run(main())
