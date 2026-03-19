"""Knowledge Base — artículos para soporte y autoservicio.

Incluye búsqueda con relevancia, artículos relacionados y
auto-matching de artículos para tickets de soporte.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.models import KnowledgeArticle
from xcapitsff.core.schemas import ArticleCreate


# ---------------------------------------------------------------------------
# Tipos auxiliares
# ---------------------------------------------------------------------------


class MatchType(str, Enum):
    """Tipo de coincidencia encontrada en la búsqueda."""

    TITLE = "title"
    CONTENT = "content"
    TAG = "tag"


@dataclass
class ArticleSearchResult:
    """Resultado de búsqueda con puntuación de relevancia."""

    article: KnowledgeArticle
    relevance_score: float
    match_type: MatchType
    matched_terms: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Utilidades de texto
# ---------------------------------------------------------------------------


def _normalize(text: str) -> str:
    """Normaliza texto: minúsculas, sin acentos, sin puntuación extra."""
    text = text.lower().strip()
    # Eliminar acentos
    nfkd = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Eliminar puntuación excepto espacios
    text = re.sub(r"[^\w\s]", " ", text)
    # Colapsar espacios
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _tokenize(text: str) -> list[str]:
    """Tokeniza el texto normalizado, descartando stopwords comunes en español."""
    stopwords = {
        "de", "la", "el", "en", "y", "a", "los", "las", "del", "un", "una",
        "por", "con", "para", "es", "al", "lo", "como", "se", "su", "que",
        "no", "mas", "o", "mi", "me", "te", "tu", "nos", "ya", "hay", "si",
        "pero", "esta", "este", "ese", "esa", "son", "ser", "fue", "han",
        "muy", "tambien", "puede", "desde", "hasta", "entre", "sobre",
        "sin", "cada", "todo", "todos", "toda", "todas", "otro", "otra",
    }
    tokens = _normalize(text).split()
    return [t for t in tokens if t not in stopwords and len(t) > 1]


def _compute_relevance(
    article: KnowledgeArticle,
    query_tokens: list[str],
    query_normalized: str,
) -> ArticleSearchResult | None:
    """Calcula la relevancia de un artículo para los tokens de búsqueda.

    Ponderación:
    - Coincidencia en título:   peso 10 por token
    - Coincidencia en tags:     peso 5 por token
    - Coincidencia en contenido: peso 1 por token
    - Bonus de +20 si la frase completa aparece en el título
    - Bonus de +8 si la frase completa aparece en los tags
    - Bonus de +3 si la frase completa aparece en el contenido
    """
    if not query_tokens:
        return None

    title_norm = _normalize(article.title)
    content_norm = _normalize(article.content)
    tags_norm = _normalize(article.tags or "")

    score = 0.0
    matched_terms: list[str] = []
    best_match = MatchType.CONTENT  # default, se actualiza

    # Bonus por frase completa
    if query_normalized in title_norm:
        score += 20.0
        best_match = MatchType.TITLE
    if query_normalized in tags_norm:
        score += 8.0
        if best_match != MatchType.TITLE:
            best_match = MatchType.TAG
    if query_normalized in content_norm:
        score += 3.0

    # Puntuación por token individual
    for token in query_tokens:
        in_title = token in title_norm
        in_tags = token in tags_norm
        in_content = token in content_norm

        if in_title:
            score += 10.0
            matched_terms.append(token)
            best_match = MatchType.TITLE
        if in_tags:
            score += 5.0
            if token not in matched_terms:
                matched_terms.append(token)
            if best_match == MatchType.CONTENT:
                best_match = MatchType.TAG
        if in_content:
            score += 1.0
            if token not in matched_terms:
                matched_terms.append(token)

    if score == 0:
        return None

    # Normalizar por cantidad de tokens para que queries largos no inflen
    score = score / len(query_tokens)

    return ArticleSearchResult(
        article=article,
        relevance_score=round(score, 2),
        match_type=best_match,
        matched_terms=matched_terms,
    )


# ---------------------------------------------------------------------------
# CRUD básico (mantenido de la versión original)
# ---------------------------------------------------------------------------


async def create_article(db: AsyncSession, data: ArticleCreate) -> KnowledgeArticle:
    """Crea un nuevo artículo en la base de conocimiento."""
    article = KnowledgeArticle(
        title=data.title,
        content=data.content,
        category=data.category,
        tags=data.tags,
    )
    db.add(article)
    await db.flush()
    await db.refresh(article)
    return article


async def get_article(db: AsyncSession, article_id: int) -> KnowledgeArticle | None:
    """Obtiene un artículo por su ID."""
    result = await db.execute(
        select(KnowledgeArticle).where(KnowledgeArticle.id == article_id)
    )
    return result.scalar_one_or_none()


async def get_articles_by_category(
    db: AsyncSession, category: str
) -> list[KnowledgeArticle]:
    """Lista artículos publicados de una categoría, ordenados por fecha."""
    result = await db.execute(
        select(KnowledgeArticle)
        .where(
            KnowledgeArticle.category == category,
            KnowledgeArticle.is_published.is_(True),
        )
        .order_by(KnowledgeArticle.updated_at.desc())
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Búsqueda mejorada con relevancia
# ---------------------------------------------------------------------------


async def search_articles(
    db: AsyncSession,
    query: str,
    category: str | None = None,
    limit: int = 10,
) -> list[ArticleSearchResult]:
    """Busca artículos y devuelve resultados ordenados por relevancia.

    El scoring pondera: título (10x) > tags (5x) > contenido (1x).
    Incluye bonus por coincidencia de la frase completa.
    """
    query_normalized = _normalize(query)
    query_tokens = _tokenize(query)

    if not query_tokens:
        return []

    # Traer candidatos de la DB usando LIKE (filtro grueso)
    search_pattern = f"%{query}%"
    token_patterns = [f"%{token}%" for token in query_tokens]

    # Construir condiciones OR para cada token
    token_conditions = []
    for pattern in token_patterns:
        token_conditions.append(KnowledgeArticle.title.ilike(pattern))
        token_conditions.append(KnowledgeArticle.content.ilike(pattern))
        token_conditions.append(KnowledgeArticle.tags.ilike(pattern))

    stmt = select(KnowledgeArticle).where(
        KnowledgeArticle.is_published.is_(True),
        or_(
            KnowledgeArticle.title.ilike(search_pattern),
            KnowledgeArticle.content.ilike(search_pattern),
            KnowledgeArticle.tags.ilike(search_pattern),
            *token_conditions,
        ),
    )

    if category:
        stmt = stmt.where(KnowledgeArticle.category == category)

    result = await db.execute(stmt)
    candidates = list(result.scalars().all())

    # Calcular relevancia para cada candidato
    scored_results: list[ArticleSearchResult] = []
    for article in candidates:
        search_result = _compute_relevance(article, query_tokens, query_normalized)
        if search_result is not None:
            scored_results.append(search_result)

    # Ordenar por relevancia descendente
    scored_results.sort(key=lambda r: r.relevance_score, reverse=True)

    return scored_results[:limit]


# ---------------------------------------------------------------------------
# Artículos relacionados
# ---------------------------------------------------------------------------


async def get_related_articles(
    db: AsyncSession,
    article_id: int,
    limit: int = 5,
) -> list[ArticleSearchResult]:
    """Encuentra artículos relacionados por categoría y tags compartidos.

    Prioriza artículos que comparten más tags y están en la misma categoría.
    """
    source = await get_article(db, article_id)
    if source is None:
        return []

    # Obtener todos los artículos publicados excepto el actual
    stmt = select(KnowledgeArticle).where(
        KnowledgeArticle.is_published.is_(True),
        KnowledgeArticle.id != article_id,
    )
    result = await db.execute(stmt)
    candidates = list(result.scalars().all())

    source_tags = {
        t.strip().lower() for t in (source.tags or "").split(",") if t.strip()
    }
    source_title_tokens = set(_tokenize(source.title))

    scored: list[ArticleSearchResult] = []

    for candidate in candidates:
        score = 0.0
        match_type = MatchType.CONTENT
        matched_terms: list[str] = []

        # Misma categoría: +5 puntos
        if candidate.category == source.category:
            score += 5.0

        # Tags compartidos: +3 por cada tag
        candidate_tags = {
            t.strip().lower()
            for t in (candidate.tags or "").split(",")
            if t.strip()
        }
        shared_tags = source_tags & candidate_tags
        if shared_tags:
            score += 3.0 * len(shared_tags)
            match_type = MatchType.TAG
            matched_terms.extend(shared_tags)

        # Tokens del título en común: +2 por cada token
        candidate_title_tokens = set(_tokenize(candidate.title))
        shared_title_tokens = source_title_tokens & candidate_title_tokens
        if shared_title_tokens:
            score += 2.0 * len(shared_title_tokens)
            if match_type != MatchType.TAG or not shared_tags:
                match_type = MatchType.TITLE
            matched_terms.extend(shared_title_tokens)

        if score > 0:
            scored.append(
                ArticleSearchResult(
                    article=candidate,
                    relevance_score=round(score, 2),
                    match_type=match_type,
                    matched_terms=matched_terms,
                )
            )

    scored.sort(key=lambda r: r.relevance_score, reverse=True)
    return scored[:limit]


# ---------------------------------------------------------------------------
# Auto-matching para tickets de soporte
# ---------------------------------------------------------------------------


async def get_article_for_ticket(
    db: AsyncSession,
    subject: str,
    description: str,
    limit: int = 3,
) -> list[ArticleSearchResult]:
    """Busca artículos relevantes para un ticket de soporte.

    Combina subject y description, extrae keywords principales y
    busca artículos que mejor coincidan. Útil para sugerir artículos
    al agente de soporte o al usuario.
    """
    # Combinar subject y description, dando más peso al subject
    combined_text = f"{subject} {subject} {description}"
    tokens = _tokenize(combined_text)

    if not tokens:
        return []

    # Traer todos los artículos publicados
    stmt = select(KnowledgeArticle).where(
        KnowledgeArticle.is_published.is_(True),
    )
    result = await db.execute(stmt)
    candidates = list(result.scalars().all())

    # Calcular relevancia para cada candidato usando los tokens del ticket
    query_normalized = _normalize(f"{subject} {description}")
    scored_results: list[ArticleSearchResult] = []

    for article in candidates:
        search_result = _compute_relevance(article, tokens, query_normalized)
        if search_result is not None:
            scored_results.append(search_result)

    scored_results.sort(key=lambda r: r.relevance_score, reverse=True)
    return scored_results[:limit]
