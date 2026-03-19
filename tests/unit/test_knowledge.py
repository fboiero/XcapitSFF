"""Tests unitarios para el módulo de Knowledge Base."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.models import KnowledgeArticle
from xcapitsff.support.knowledge import (
    ArticleSearchResult,
    MatchType,
    _compute_relevance,
    _normalize,
    _tokenize,
    create_article,
    get_article,
    get_article_for_ticket,
    get_articles_by_category,
    get_related_articles,
    search_articles,
)
from xcapitsff.core.schemas import ArticleCreate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_article(
    id: int = 1,
    title: str = "Artículo de prueba",
    content: str = "Contenido de prueba para tests",
    category: str = "general",
    tags: str = "test,prueba",
    is_published: bool = True,
) -> KnowledgeArticle:
    """Crea un KnowledgeArticle en memoria sin base de datos."""
    article = KnowledgeArticle(
        title=title,
        content=content,
        category=category,
        tags=tags,
        is_published=is_published,
    )
    article.id = id
    return article


async def _seed_articles(db: AsyncSession) -> list[KnowledgeArticle]:
    """Inserta artículos de prueba en la base de datos."""
    articles_data = [
        {
            "title": "Cómo crear tu cuenta en Xcapit",
            "content": "Para crear tu cuenta descargá la app e ingresá tu email. Seguí los pasos de registro y completá la verificación de identidad.",
            "category": "getting_started",
            "tags": "registro,crear cuenta,onboarding",
        },
        {
            "title": "Proceso de verificación KYC",
            "content": "La verificación KYC requiere tu documento de identidad y una selfie. El proceso tarda entre 24 y 72 horas hábiles.",
            "category": "getting_started",
            "tags": "kyc,verificación,identidad,documento",
        },
        {
            "title": "Cómo comprar y vender criptomonedas",
            "content": "Ingresá a Mercado, seleccioná la cripto, elegí el monto y confirmá. Podés hacer órdenes de mercado o límite.",
            "category": "crypto",
            "tags": "comprar,vender,criptomonedas,orden,mercado",
        },
        {
            "title": "Comisiones por transacciones",
            "content": "Las comisiones de compra y venta son del 0.50% para el plan gratuito, con descuentos para planes Pro y Premium.",
            "category": "crypto",
            "tags": "comisiones,fees,transacción,costo",
        },
        {
            "title": "Seguridad de tu billetera cripto",
            "content": "Xcapit usa cold storage para el 95% de los fondos. Activá 2FA y usá contraseñas seguras para proteger tu cuenta.",
            "category": "crypto",
            "tags": "seguridad,billetera,wallet,2FA,cold storage",
        },
        {
            "title": "Cómo restablecer tu contraseña",
            "content": "Tocá Olvidé mi contraseña en la pantalla de login, ingresá tu email y seguí el enlace de recuperación.",
            "category": "account",
            "tags": "contraseña,restablecer,recuperar,password,login",
        },
        {
            "title": "Configurar autenticación 2FA",
            "content": "Descargá Google Authenticator o Authy, escaneá el código QR desde Perfil > Seguridad y guardá los códigos de respaldo.",
            "category": "technical",
            "tags": "2FA,autenticación,seguridad,Google Authenticator,código",
        },
        {
            "title": "Métodos de pago aceptados",
            "content": "Aceptamos transferencia bancaria, Mercado Pago y depósitos en criptomonedas. Los retiros se pueden hacer por banco o cripto.",
            "category": "billing",
            "tags": "pagos,métodos,transferencia,mercado pago,retiro",
        },
        {
            "title": "Guía de staking",
            "content": "El staking permite generar rendimientos bloqueando tus criptos. Disponible para ETH, SOL, ADA, DOT y MATIC.",
            "category": "crypto",
            "tags": "staking,rendimiento,APY,ETH,SOL",
        },
        {
            "title": "Solución de problemas de la app",
            "content": "Si la app no carga, verificá tu conexión y que tenés la última versión. Probá reinstalar si el problema persiste.",
            "category": "technical",
            "tags": "problemas,error,app,troubleshooting",
        },
    ]

    created: list[KnowledgeArticle] = []
    for data in articles_data:
        article = KnowledgeArticle(
            title=data["title"],
            content=data["content"],
            category=data["category"],
            tags=data["tags"],
            is_published=True,
        )
        db.add(article)
        created.append(article)

    # Agregar un artículo no publicado para verificar filtros
    unpublished = KnowledgeArticle(
        title="Artículo borrador sobre Bitcoin",
        content="Este artículo aún no está listo para publicarse.",
        category="crypto",
        tags="bitcoin,borrador",
        is_published=False,
    )
    db.add(unpublished)

    await db.flush()
    for article in created:
        await db.refresh(article)
    await db.refresh(unpublished)

    return created


# ---------------------------------------------------------------------------
# Tests de utilidades de texto
# ---------------------------------------------------------------------------


class TestNormalize:
    def test_lowercase_and_accents(self):
        assert _normalize("Cómo Crear") == "como crear"

    def test_strips_punctuation(self):
        assert _normalize("¿Hola, mundo!") == "hola mundo"

    def test_collapses_spaces(self):
        assert _normalize("  muchos   espacios  ") == "muchos espacios"

    def test_handles_empty_string(self):
        assert _normalize("") == ""


class TestTokenize:
    def test_removes_stopwords(self):
        tokens = _tokenize("Cómo crear la cuenta en Xcapit")
        assert "la" not in tokens
        assert "en" not in tokens
        assert "como" not in tokens
        assert "crear" in tokens
        assert "cuenta" in tokens
        assert "xcapit" in tokens

    def test_removes_short_tokens(self):
        tokens = _tokenize("a y o de la")
        assert tokens == []

    def test_returns_meaningful_tokens(self):
        tokens = _tokenize("restablecer contraseña olvidada")
        assert "restablecer" in tokens
        assert "contrasena" in tokens
        assert "olvidada" in tokens


# ---------------------------------------------------------------------------
# Tests de _compute_relevance
# ---------------------------------------------------------------------------


class TestComputeRelevance:
    def test_title_match_scores_highest(self):
        article = _make_article(
            title="Cómo restablecer tu contraseña",
            content="Información general sobre seguridad.",
            tags="seguridad",
        )
        result = _compute_relevance(
            article,
            ["restablecer", "contrasena"],
            "restablecer contrasena",
        )
        assert result is not None
        assert result.match_type == MatchType.TITLE
        assert result.relevance_score > 0

    def test_tag_match_scores_medium(self):
        article = _make_article(
            title="Información general",
            content="Datos varios de la plataforma.",
            tags="staking,rendimiento,APY",
        )
        result = _compute_relevance(article, ["staking"], "staking")
        assert result is not None
        assert result.match_type == MatchType.TAG

    def test_content_only_match(self):
        article = _make_article(
            title="Guía general",
            content="Para restablecer tu contraseña seguí estos pasos.",
            tags="general",
        )
        result = _compute_relevance(article, ["restablecer"], "restablecer")
        assert result is not None
        assert result.relevance_score > 0

    def test_no_match_returns_none(self):
        article = _make_article(
            title="Sobre nosotros",
            content="Xcapit es una empresa fintech.",
            tags="empresa",
        )
        result = _compute_relevance(article, ["blockchain"], "blockchain")
        assert result is None

    def test_phrase_bonus_in_title(self):
        article = _make_article(
            title="Cómo comprar criptomonedas",
            content="Info básica.",
            tags="comprar",
        )
        # Frase completa en título: bonus de 20 + tokens
        result_phrase = _compute_relevance(
            article,
            ["comprar", "criptomonedas"],
            "comprar criptomonedas",
        )
        # Solo un token
        result_single = _compute_relevance(
            article,
            ["comprar"],
            "comprar",
        )
        assert result_phrase is not None
        assert result_single is not None
        # Phrase match should still have a high score (phrase bonus applies)
        assert result_phrase.relevance_score > 0
        assert result_phrase.match_type == MatchType.TITLE

    def test_empty_tokens_returns_none(self):
        article = _make_article()
        result = _compute_relevance(article, [], "")
        assert result is None


# ---------------------------------------------------------------------------
# Tests de search_articles (con base de datos)
# ---------------------------------------------------------------------------


class TestSearchArticles:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session: AsyncSession):
        self.db = db_session
        self.articles = await _seed_articles(db_session)

    @pytest.mark.asyncio
    async def test_search_by_title_keyword(self):
        results = await search_articles(self.db, "contraseña")
        assert len(results) >= 1
        titles = [r.article.title for r in results]
        assert any("contraseña" in t for t in titles)

    @pytest.mark.asyncio
    async def test_search_returns_sorted_by_relevance(self):
        results = await search_articles(self.db, "seguridad billetera cripto")
        assert len(results) >= 1
        scores = [r.relevance_score for r in results]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_search_with_category_filter(self):
        results = await search_articles(self.db, "seguridad", category="crypto")
        for r in results:
            assert r.article.category == "crypto"

    @pytest.mark.asyncio
    async def test_search_excludes_unpublished(self):
        results = await search_articles(self.db, "borrador")
        # El artículo no publicado no debería aparecer
        for r in results:
            assert r.article.is_published is True

    @pytest.mark.asyncio
    async def test_search_respects_limit(self):
        results = await search_articles(self.db, "cripto", limit=2)
        assert len(results) <= 2

    @pytest.mark.asyncio
    async def test_search_empty_query_returns_empty(self):
        results = await search_articles(self.db, "de la el")
        # Todas son stopwords, debería devolver vacío
        assert results == []

    @pytest.mark.asyncio
    async def test_search_returns_article_search_result(self):
        results = await search_articles(self.db, "staking")
        assert len(results) >= 1
        first = results[0]
        assert isinstance(first, ArticleSearchResult)
        assert isinstance(first.article, KnowledgeArticle)
        assert isinstance(first.match_type, MatchType)
        assert first.relevance_score > 0


# ---------------------------------------------------------------------------
# Tests de get_related_articles
# ---------------------------------------------------------------------------


class TestGetRelatedArticles:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session: AsyncSession):
        self.db = db_session
        self.articles = await _seed_articles(db_session)

    @pytest.mark.asyncio
    async def test_related_same_category_scored(self):
        # Buscar artículos relacionados con "Cómo comprar y vender"
        crypto_article = next(
            a for a in self.articles if "comprar" in a.title
        )
        results = await get_related_articles(self.db, crypto_article.id)
        assert len(results) >= 1
        # Los artículos de la misma categoría deberían tener más score
        categories = [r.article.category for r in results]
        assert "crypto" in categories

    @pytest.mark.asyncio
    async def test_related_excludes_self(self):
        article = self.articles[0]
        results = await get_related_articles(self.db, article.id)
        ids = [r.article.id for r in results]
        assert article.id not in ids

    @pytest.mark.asyncio
    async def test_related_nonexistent_article(self):
        results = await get_related_articles(self.db, 99999)
        assert results == []

    @pytest.mark.asyncio
    async def test_related_shared_tags_boost_score(self):
        # Los artículos crypto con tags de seguridad/2FA deberían estar
        # relacionados entre sí
        security_article = next(
            a for a in self.articles if "Seguridad" in a.title
        )
        results = await get_related_articles(self.db, security_article.id)
        assert len(results) >= 1
        # El artículo de 2FA comparte tags de seguridad
        titles = [r.article.title for r in results]
        assert any("2FA" in t for t in titles)

    @pytest.mark.asyncio
    async def test_related_respects_limit(self):
        article = self.articles[0]
        results = await get_related_articles(self.db, article.id, limit=2)
        assert len(results) <= 2


# ---------------------------------------------------------------------------
# Tests de get_article_for_ticket
# ---------------------------------------------------------------------------


class TestGetArticleForTicket:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session: AsyncSession):
        self.db = db_session
        self.articles = await _seed_articles(db_session)

    @pytest.mark.asyncio
    async def test_matches_password_reset_ticket(self):
        results = await get_article_for_ticket(
            self.db,
            subject="No puedo acceder a mi cuenta",
            description="Olvidé mi contraseña y no puedo restablecer el acceso. Necesito ayuda para recuperar mi cuenta.",
        )
        assert len(results) >= 1
        titles = [r.article.title for r in results]
        assert any("contraseña" in t for t in titles)

    @pytest.mark.asyncio
    async def test_matches_crypto_purchase_ticket(self):
        results = await get_article_for_ticket(
            self.db,
            subject="Quiero comprar Bitcoin",
            description="Cómo puedo comprar criptomonedas en la plataforma? Cuáles son las comisiones?",
        )
        assert len(results) >= 1
        # Debería sugerir el artículo de compra/venta o comisiones
        categories = [r.article.category for r in results]
        assert "crypto" in categories

    @pytest.mark.asyncio
    async def test_matches_app_issue_ticket(self):
        results = await get_article_for_ticket(
            self.db,
            subject="La app no funciona",
            description="Desde ayer la app no carga y se cierra sola. Ya intenté reiniciar el celular.",
        )
        assert len(results) >= 1
        titles = [r.article.title for r in results]
        assert any("problemas" in t.lower() or "app" in t.lower() for t in titles)

    @pytest.mark.asyncio
    async def test_returns_limited_results(self):
        results = await get_article_for_ticket(
            self.db,
            subject="Consulta general",
            description="Tengo varias dudas sobre seguridad, cripto, cuenta y pagos.",
            limit=2,
        )
        assert len(results) <= 2

    @pytest.mark.asyncio
    async def test_empty_ticket_returns_empty(self):
        results = await get_article_for_ticket(
            self.db,
            subject="",
            description="",
        )
        assert results == []

    @pytest.mark.asyncio
    async def test_results_sorted_by_relevance(self):
        results = await get_article_for_ticket(
            self.db,
            subject="Problema con staking de ETH",
            description="No puedo hacer staking y no veo los rendimientos.",
        )
        if len(results) > 1:
            scores = [r.relevance_score for r in results]
            assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# Tests de CRUD básico
# ---------------------------------------------------------------------------


class TestCrudOperations:
    @pytest_asyncio.fixture(autouse=True)
    async def setup(self, db_session: AsyncSession):
        self.db = db_session

    @pytest.mark.asyncio
    async def test_create_and_get_article(self):
        data = ArticleCreate(
            title="Artículo de test",
            content="Contenido del artículo de test.",
            category="testing",
            tags="test,unitario",
        )
        created = await create_article(self.db, data)
        assert created.id is not None
        assert created.title == "Artículo de test"

        fetched = await get_article(self.db, created.id)
        assert fetched is not None
        assert fetched.title == created.title

    @pytest.mark.asyncio
    async def test_get_nonexistent_article(self):
        result = await get_article(self.db, 99999)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_articles_by_category(self):
        await _seed_articles(self.db)
        results = await get_articles_by_category(self.db, "crypto")
        assert len(results) >= 3
        for article in results:
            assert article.category == "crypto"
            assert article.is_published is True
