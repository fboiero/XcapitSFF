"""Script para poblar la base de conocimiento con artículos iniciales."""

import asyncio
import json
import sys
from collections import Counter
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from xcapitsff.core.database import async_session, init_db
from xcapitsff.core.models import KnowledgeArticle


async def main():
    data_file = Path(__file__).parent.parent / "data" / "knowledge_base_seed.json"
    if not data_file.exists():
        print(f"Error: no se encontró {data_file}")
        sys.exit(1)

    with open(data_file, encoding="utf-8") as f:
        data = json.load(f)

    articles = data.get("articles", [])
    if not articles:
        print("Error: el archivo no contiene artículos.")
        sys.exit(1)

    print(f"Encontrados {len(articles)} artículos en {data_file.name}")
    print()

    # Inicializar la base de datos
    print("Inicializando base de datos...")
    await init_db()

    category_count: Counter[str] = Counter()
    tag_count: Counter[str] = Counter()

    async with async_session() as db:
        for article_data in articles:
            article = KnowledgeArticle(
                title=article_data["title"],
                content=article_data["content"],
                category=article_data["category"],
                tags=article_data.get("tags"),
                is_published=True,
            )
            db.add(article)
            category_count[article_data["category"]] += 1

            if article_data.get("tags"):
                for tag in article_data["tags"].split(","):
                    tag_count[tag.strip()] += 1

        await db.commit()

    # Resumen
    print("=" * 60)
    print("  RESUMEN DE ARTÍCULOS CREADOS")
    print("=" * 60)
    print()
    print(f"  Total de artículos: {len(articles)}")
    print()
    print("  Por categoría:")
    for category, count in sorted(category_count.items()):
        print(f"    - {category}: {count} artículos")
    print()
    print(f"  Tags únicos: {len(tag_count)}")
    print(f"  Top 10 tags más usados:")
    for tag, count in tag_count.most_common(10):
        print(f"    - {tag}: {count}")
    print()
    print("=" * 60)
    print("¡Base de conocimiento poblada exitosamente!")
    print()
    print("Para iniciar la API:")
    print("  PYTHONPATH=src uvicorn xcapitsff.api.app:app --reload")


if __name__ == "__main__":
    asyncio.run(main())
