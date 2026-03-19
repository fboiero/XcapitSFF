"""Unified search engine — search across leads, tickets, customers, and KB articles.

Provides a single search endpoint that queries all entities and returns
relevance-ranked results.
"""

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.models import Customer, KnowledgeArticle, Lead, Ticket

logger = logging.getLogger(__name__)


class SearchEntityType(str, Enum):
    LEAD = "lead"
    TICKET = "ticket"
    CUSTOMER = "customer"
    ARTICLE = "article"


@dataclass
class SearchResult:
    entity_type: SearchEntityType
    entity_id: int
    title: str
    subtitle: str
    score: float
    snippet: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class SearchResponse:
    query: str
    total: int
    results: list[SearchResult]
    by_type: dict[str, int] = field(default_factory=dict)


def _normalize(text: str) -> str:
    text = text.lower().strip()
    nfkd = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text).strip()


def _match_score(text: str, query_tokens: list[str], weight: float = 1.0) -> float:
    if not text or not query_tokens:
        return 0.0
    norm = _normalize(text)
    score = 0.0
    for token in query_tokens:
        if token in norm:
            score += weight
    return score


async def search_all(
    db: AsyncSession,
    query: str,
    entity_types: list[SearchEntityType] | None = None,
    limit: int = 20,
) -> SearchResponse:
    """Search across all entities and return ranked results."""
    if not query or len(query.strip()) < 2:
        return SearchResponse(query=query, total=0, results=[])

    query_norm = _normalize(query)
    tokens = [t for t in query_norm.split() if len(t) > 1]
    if not tokens:
        return SearchResponse(query=query, total=0, results=[])

    types = entity_types or list(SearchEntityType)
    all_results: list[SearchResult] = []
    pattern = f"%{query}%"

    if SearchEntityType.LEAD in types:
        leads = await db.execute(
            select(Lead).where(
                or_(
                    Lead.company_name.ilike(pattern),
                    Lead.contact_name.ilike(pattern),
                    Lead.contact_email.ilike(pattern),
                    Lead.notes.ilike(pattern),
                )
            ).limit(limit)
        )
        for lead in leads.scalars().all():
            score = (
                _match_score(lead.company_name or "", tokens, 3.0) +
                _match_score(lead.contact_name or "", tokens, 2.0) +
                _match_score(lead.contact_email or "", tokens, 2.0) +
                _match_score(lead.notes or "", tokens, 0.5)
            )
            region = lead.region if isinstance(lead.region, str) else lead.region.value
            stage = lead.stage if isinstance(lead.stage, str) else lead.stage.value
            all_results.append(SearchResult(
                entity_type=SearchEntityType.LEAD,
                entity_id=lead.id,
                title=lead.company_name or f"Lead #{lead.id}",
                subtitle=f"{lead.contact_name or 'Sin contacto'} · {region} · Score: {lead.score_icp}",
                score=score,
                snippet=f"Stage: {stage} · C-Level: {'Sí' if lead.c_level else 'No'}",
                metadata={"score_icp": lead.score_icp, "region": region, "stage": stage},
            ))

    if SearchEntityType.TICKET in types:
        tickets = await db.execute(
            select(Ticket).where(
                or_(
                    Ticket.subject.ilike(pattern),
                    Ticket.description.ilike(pattern),
                )
            ).limit(limit)
        )
        for ticket in tickets.scalars().all():
            score = (
                _match_score(ticket.subject, tokens, 3.0) +
                _match_score(ticket.description, tokens, 1.0)
            )
            status = ticket.status if isinstance(ticket.status, str) else ticket.status.value
            all_results.append(SearchResult(
                entity_type=SearchEntityType.TICKET,
                entity_id=ticket.id,
                title=ticket.subject,
                subtitle=f"Status: {status} · Priority: {ticket.priority}",
                score=score,
                snippet=ticket.description[:150],
                metadata={"status": status, "priority": ticket.priority},
            ))

    if SearchEntityType.CUSTOMER in types:
        customers = await db.execute(
            select(Customer).where(
                or_(
                    Customer.company_name.ilike(pattern),
                    Customer.contact_name.ilike(pattern),
                    Customer.contact_email.ilike(pattern),
                )
            ).limit(limit)
        )
        for customer in customers.scalars().all():
            score = (
                _match_score(customer.company_name, tokens, 3.0) +
                _match_score(customer.contact_name, tokens, 2.0) +
                _match_score(customer.contact_email, tokens, 2.0)
            )
            all_results.append(SearchResult(
                entity_type=SearchEntityType.CUSTOMER,
                entity_id=customer.id,
                title=customer.company_name,
                subtitle=f"{customer.contact_name} · {customer.contact_email}",
                score=score,
                metadata={"plan": customer.plan},
            ))

    if SearchEntityType.ARTICLE in types:
        articles = await db.execute(
            select(KnowledgeArticle).where(
                KnowledgeArticle.is_published.is_(True),
                or_(
                    KnowledgeArticle.title.ilike(pattern),
                    KnowledgeArticle.content.ilike(pattern),
                    KnowledgeArticle.tags.ilike(pattern),
                )
            ).limit(limit)
        )
        for article in articles.scalars().all():
            score = (
                _match_score(article.title, tokens, 4.0) +
                _match_score(article.content, tokens, 0.5) +
                _match_score(article.tags or "", tokens, 2.0)
            )
            all_results.append(SearchResult(
                entity_type=SearchEntityType.ARTICLE,
                entity_id=article.id,
                title=article.title,
                subtitle=f"Categoría: {article.category}",
                score=score,
                snippet=article.content[:150],
                metadata={"category": article.category, "tags": article.tags},
            ))

    # Sort by score descending
    all_results.sort(key=lambda r: r.score, reverse=True)
    all_results = all_results[:limit]

    # Count by type
    by_type: dict[str, int] = {}
    for r in all_results:
        by_type[r.entity_type.value] = by_type.get(r.entity_type.value, 0) + 1

    return SearchResponse(
        query=query,
        total=len(all_results),
        results=all_results,
        by_type=by_type,
    )
