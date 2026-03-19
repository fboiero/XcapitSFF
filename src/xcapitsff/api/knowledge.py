"""API endpoints for Knowledge Base."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.database import get_db
from xcapitsff.core.schemas import ArticleCreate, ArticleResponse
from xcapitsff.support.knowledge import (
    create_article,
    get_article,
    get_article_for_ticket,
    get_articles_by_category,
    get_related_articles,
    search_articles,
)

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])


@router.post("/", response_model=ArticleResponse, status_code=201)
async def api_create_article(data: ArticleCreate, db: AsyncSession = Depends(get_db)):
    return await create_article(db, data)


@router.get("/search")
async def api_search_articles(
    q: str = Query(min_length=2),
    category: str | None = None,
    limit: int = Query(default=10, le=50),
    db: AsyncSession = Depends(get_db),
):
    results = await search_articles(db, q, category, limit)
    return [
        {
            "id": r.article.id,
            "title": r.article.title,
            "category": r.article.category,
            "tags": r.article.tags,
            "relevance_score": r.relevance_score,
            "match_type": r.match_type.value,
            "matched_terms": r.matched_terms,
            "content_preview": r.article.content[:200] + "..." if len(r.article.content) > 200 else r.article.content,
        }
        for r in results
    ]


@router.get("/category/{category}", response_model=list[ArticleResponse])
async def api_articles_by_category(category: str, db: AsyncSession = Depends(get_db)):
    return await get_articles_by_category(db, category)


@router.get("/for-ticket")
async def api_articles_for_ticket(
    subject: str = Query(min_length=2),
    description: str = Query(default=""),
    limit: int = Query(default=3, le=10),
    db: AsyncSession = Depends(get_db),
):
    """Find KB articles relevant to a support ticket."""
    results = await get_article_for_ticket(db, subject, description, limit)
    return [
        {
            "id": r.article.id,
            "title": r.article.title,
            "category": r.article.category,
            "relevance_score": r.relevance_score,
            "match_type": r.match_type.value,
            "content_preview": r.article.content[:200],
        }
        for r in results
    ]


@router.get("/{article_id}", response_model=ArticleResponse)
async def api_get_article(article_id: int, db: AsyncSession = Depends(get_db)):
    article = await get_article(db, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@router.get("/{article_id}/related")
async def api_related_articles(
    article_id: int,
    limit: int = Query(default=5, le=20),
    db: AsyncSession = Depends(get_db),
):
    results = await get_related_articles(db, article_id, limit)
    return [
        {
            "id": r.article.id,
            "title": r.article.title,
            "category": r.article.category,
            "relevance_score": r.relevance_score,
            "match_type": r.match_type.value,
        }
        for r in results
    ]
