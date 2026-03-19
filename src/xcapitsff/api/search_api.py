"""API endpoint for unified search."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.database import get_db
from xcapitsff.core.search import SearchEntityType, search_all

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/")
async def api_search(
    q: str = Query(min_length=2, max_length=200),
    types: str | None = Query(default=None, description="Comma-separated: lead,ticket,customer,article"),
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Search across all entities — leads, tickets, customers, KB articles."""
    entity_types = None
    if types:
        type_map = {
            "lead": SearchEntityType.LEAD,
            "ticket": SearchEntityType.TICKET,
            "customer": SearchEntityType.CUSTOMER,
            "article": SearchEntityType.ARTICLE,
        }
        entity_types = [type_map[t.strip()] for t in types.split(",") if t.strip() in type_map]

    response = await search_all(db, q, entity_types, limit)

    return {
        "query": response.query,
        "total": response.total,
        "by_type": response.by_type,
        "results": [
            {
                "type": r.entity_type.value,
                "id": r.entity_id,
                "title": r.title,
                "subtitle": r.subtitle,
                "score": round(r.score, 2),
                "snippet": r.snippet,
                "metadata": r.metadata,
            }
            for r in response.results
        ],
    }
