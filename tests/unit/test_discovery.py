"""Tests para el sistema de Product Discovery, Requerimientos y Propuestas."""

import pytest
from datetime import datetime, timezone

from xcapitsff.discovery.session import (
    AnswerType,
    DiscoveryEngine,
    DiscoveryPhase,
    DiscoveryQuestion,
    DiscoverySession,
    PHASE_ORDER,
    QUESTION_BANK,
    QUESTION_INDEX,
    SessionStatus,
    get_questions_for_phase,
)
from xcapitsff.discovery.requirements import (
    EFFORT_HOURS,
    EffortSize,
    Priority,
    Requirement,
    RequirementType,
    RequirementsDocument,
    RequirementsGenerator,
)
from xcapitsff.discovery.proposal import (
    PLAN_PRICING,
    ProjectPhase,
    Proposal,
    ProposalGenerator,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_engine_with_session() -> tuple[DiscoveryEngine, str]:
    """Crea un engine con una sesión iniciada y devuelve (engine, session_id)."""
    engine = DiscoveryEngine()
    session = engine.start_session("Acme Corp", "contacto@acme.com")
    return engine, session.session_id


def _answer_all_required_in_phase(
    engine: DiscoveryEngine, session_id: str, phase: DiscoveryPhase
) -> None:
    """Responde todas las preguntas requeridas de una fase."""
    questions = get_questions_for_phase(phase)
    for q in questions:
        if q.required:
            engine.answer_question(session_id, q.question_id, f"Respuesta a {q.question_id}")


def _build_full_session() -> DiscoverySession:
    """Crea una sesión con respuestas de ejemplo para generar requerimientos."""
    engine = DiscoveryEngine()
    session = engine.start_session("TechStartup SA", "info@techstartup.com")
    sid = session.session_id

    # INTRO
    engine.answer_question(sid, "intro_01", "TechStartup SA")
    engine.answer_question(sid, "intro_02", "Fintech")
    engine.answer_question(sid, "intro_03", "50")
    engine.answer_question(sid, "intro_04", "CTO")
    engine.advance_phase(sid)

    # BUSINESS_CONTEXT
    engine.answer_question(sid, "biz_01", "Plataforma de pagos para LATAM")
    engine.answer_question(sid, "biz_02", "Empresas medianas B2B")
    engine.answer_question(sid, "biz_03", "LATAM")
    engine.answer_question(sid, "biz_04", "SaaS")
    engine.advance_phase(sid)

    # PROBLEM_DEFINITION
    engine.answer_question(sid, "prob_01", "Gestión manual de conciliaciones bancarias")
    engine.answer_question(sid, "prob_02", "Hojas de Excel compartidas")
    engine.answer_question(
        sid, "prob_03", "20 horas semanales perdidas, errores frecuentes"
    )
    engine.answer_question(sid, "prob_04", "2 años")
    engine.advance_phase(sid)

    # USERS_AND_PERSONAS
    engine.answer_question(sid, "user_01", "Analista financiero, Gerente, Admin")
    engine.answer_question(sid, "user_02", "10 analistas, 3 gerentes, 2 admins")
    engine.answer_question(sid, "user_03", "intermedio")
    engine.advance_phase(sid)

    # CURRENT_WORKFLOW
    engine.answer_question(
        sid, "flow_01", "Descargar extractos, comparar en Excel, marcar diferencias"
    )
    engine.answer_question(sid, "flow_02", "Excel, email, banco online")
    engine.answer_question(
        sid, "flow_03", "Comparación manual de extractos bancarios"
    )
    engine.answer_question(sid, "flow_04", "API del banco, sistema contable SAP")
    engine.advance_phase(sid)

    # PAIN_POINTS
    engine.answer_question(
        sid,
        "pain_01",
        "Errores en conciliación, demora en reportes, falta de trazabilidad",
    )
    engine.answer_question(sid, "pain_02", "La comparación manual en Excel")
    engine.answer_question(
        sid, "pain_03", "Se pierden transacciones al copiar entre archivos"
    )
    engine.advance_phase(sid)

    # SUCCESS_CRITERIA
    engine.answer_question(
        sid, "success_01", "Reducir el tiempo de conciliación en un 80%"
    )
    engine.answer_question(
        sid, "success_02", "Tiempo de conciliación, tasa de error, satisfacción"
    )
    engine.answer_question(
        sid, "success_03", "Que no haya más errores y el proceso sea automático"
    )
    engine.advance_phase(sid)

    # TECHNICAL_CONTEXT
    engine.answer_question(sid, "tech_01", "Sí, 3 developers")
    engine.answer_question(sid, "tech_02", "Preferencia por Python y React")
    engine.answer_question(sid, "tech_03", "web y mobile")
    engine.answer_question(sid, "tech_04", "PCI-DSS por datos financieros")
    engine.advance_phase(sid)

    # BUDGET_TIMELINE
    engine.answer_question(sid, "budget_01", "USD 50.000 - 80.000")
    engine.answer_question(sid, "budget_02", "En 3 meses")
    engine.answer_question(sid, "budget_03", "Regulación nueva en 6 meses")
    engine.answer_question(sid, "budget_04", "MVP primero, luego iterar")

    return engine.get_session(sid)


# ===========================================================================
# Tests de sesión - Ciclo de vida
# ===========================================================================


class TestSessionLifecycle:
    """Tests del ciclo de vida de las sesiones de descubrimiento."""

    def test_start_session_creates_valid_session(self):
        engine, sid = _create_engine_with_session()
        session = engine.get_session(sid)
        assert session.client_name == "Acme Corp"
        assert session.client_email == "contacto@acme.com"
        assert session.status == SessionStatus.IN_PROGRESS
        assert session.current_phase == DiscoveryPhase.INTRO

    def test_start_session_generates_unique_ids(self):
        engine = DiscoveryEngine()
        s1 = engine.start_session("A", "a@a.com")
        s2 = engine.start_session("B", "b@b.com")
        assert s1.session_id != s2.session_id

    def test_list_sessions_returns_all(self):
        engine = DiscoveryEngine()
        engine.start_session("A", "a@a.com")
        engine.start_session("B", "b@b.com")
        sessions = engine.list_sessions()
        assert len(sessions) == 2

    def test_get_session_not_found_raises(self):
        engine = DiscoveryEngine()
        with pytest.raises(KeyError):
            engine.get_session("nonexistent")

    def test_answer_question_records_answer(self):
        engine, sid = _create_engine_with_session()
        answer = engine.answer_question(sid, "intro_01", "Mi Empresa")
        assert answer.answer == "Mi Empresa"
        assert answer.question_id == "intro_01"
        assert answer.phase == DiscoveryPhase.INTRO

    def test_answer_question_updates_existing(self):
        engine, sid = _create_engine_with_session()
        engine.answer_question(sid, "intro_01", "Primera respuesta")
        engine.answer_question(sid, "intro_01", "Segunda respuesta")
        session = engine.get_session(sid)
        assert len(session.answers) == 1
        assert session.answers[0].answer == "Segunda respuesta"

    def test_answer_wrong_phase_raises(self):
        engine, sid = _create_engine_with_session()
        with pytest.raises(ValueError, match="fase"):
            engine.answer_question(sid, "biz_01", "Respuesta")

    def test_answer_invalid_question_raises(self):
        engine, sid = _create_engine_with_session()
        with pytest.raises(KeyError, match="no encontrada"):
            engine.answer_question(sid, "fake_question", "Respuesta")

    def test_advance_phase_moves_forward(self):
        engine, sid = _create_engine_with_session()
        _answer_all_required_in_phase(engine, sid, DiscoveryPhase.INTRO)
        new_phase = engine.advance_phase(sid)
        assert new_phase == DiscoveryPhase.BUSINESS_CONTEXT

    def test_advance_phase_without_required_raises(self):
        engine, sid = _create_engine_with_session()
        # No respondemos las requeridas
        with pytest.raises(ValueError, match="requeridas"):
            engine.advance_phase(sid)

    def test_advance_beyond_last_phase_raises(self):
        engine, sid = _create_engine_with_session()
        # Avanzar por todas las fases
        for phase in PHASE_ORDER[:-1]:
            _answer_all_required_in_phase(engine, sid, phase)
            engine.advance_phase(sid)
        # Ahora estamos en SUMMARY, no se puede avanzar más
        with pytest.raises(ValueError, match="última fase"):
            engine.advance_phase(sid)

    def test_complete_session_sets_status(self):
        engine, sid = _create_engine_with_session()
        session = engine.complete_session(sid)
        assert session.status == SessionStatus.COMPLETED
        assert session.completed_at is not None

    def test_complete_already_completed_raises(self):
        engine, sid = _create_engine_with_session()
        engine.complete_session(sid)
        with pytest.raises(ValueError, match="no está en progreso"):
            engine.complete_session(sid)

    def test_answer_completed_session_raises(self):
        engine, sid = _create_engine_with_session()
        engine.complete_session(sid)
        with pytest.raises(ValueError, match="no está en progreso"):
            engine.answer_question(sid, "intro_01", "Respuesta")


# ===========================================================================
# Tests del banco de preguntas
# ===========================================================================


class TestQuestionBank:
    """Tests de completitud y estructura del banco de preguntas."""

    def test_question_bank_has_at_least_30_questions(self):
        assert len(QUESTION_BANK) >= 30

    def test_all_phases_have_questions(self):
        """Todas las fases excepto SUMMARY deben tener preguntas."""
        for phase in DiscoveryPhase:
            if phase == DiscoveryPhase.SUMMARY:
                continue
            questions = get_questions_for_phase(phase)
            assert len(questions) > 0, f"La fase {phase.value} no tiene preguntas"

    def test_all_questions_are_in_spanish(self):
        """Verificar que las preguntas contienen caracteres en español."""
        spanish_chars = set("áéíóúñ¿¡")
        for q in QUESTION_BANK:
            has_spanish = any(c in spanish_chars for c in q.question_text)
            assert has_spanish, (
                f"La pregunta '{q.question_id}' no parece estar en español: "
                f"'{q.question_text}'"
            )

    def test_question_ids_are_unique(self):
        ids = [q.question_id for q in QUESTION_BANK]
        assert len(ids) == len(set(ids))

    def test_question_index_matches_bank(self):
        assert len(QUESTION_INDEX) == len(QUESTION_BANK)
        for q in QUESTION_BANK:
            assert q.question_id in QUESTION_INDEX

    def test_intro_phase_has_4_questions(self):
        intro_qs = get_questions_for_phase(DiscoveryPhase.INTRO)
        assert len(intro_qs) == 4


# ===========================================================================
# Tests de completitud
# ===========================================================================


class TestCompletionPercentage:
    """Tests del cálculo de porcentaje de completitud."""

    def test_empty_session_is_zero_percent(self):
        engine, sid = _create_engine_with_session()
        pct = engine.get_completion_percentage(sid)
        assert pct == 0.0

    def test_answering_increases_percentage(self):
        engine, sid = _create_engine_with_session()
        engine.answer_question(sid, "intro_01", "Mi Empresa")
        pct = engine.get_completion_percentage(sid)
        assert pct > 0.0

    def test_full_session_percentage(self):
        session = _build_full_session()
        engine = DiscoveryEngine()
        engine._sessions[session.session_id] = session
        pct = engine.get_completion_percentage(session.session_id)
        # Debe ser un valor alto ya que respondimos todas las preguntas
        assert pct > 80.0


# ===========================================================================
# Tests de resumen de sesión
# ===========================================================================


class TestSessionSummary:
    """Tests del resumen de sesión."""

    def test_summary_contains_session_info(self):
        engine, sid = _create_engine_with_session()
        engine.answer_question(sid, "intro_01", "Mi Empresa")
        summary = engine.get_session_summary(sid)
        assert summary["session_id"] == sid
        assert summary["client_name"] == "Acme Corp"
        assert "intro" in summary["phases"]

    def test_summary_organizes_by_phase(self):
        session = _build_full_session()
        engine = DiscoveryEngine()
        engine._sessions[session.session_id] = session
        summary = engine.get_session_summary(session.session_id)
        assert "intro" in summary["phases"]
        assert "business_context" in summary["phases"]
        assert "problem_definition" in summary["phases"]


# ===========================================================================
# Tests de generación de requerimientos
# ===========================================================================


class TestRequirementsGeneration:
    """Tests de la generación de requerimientos."""

    def test_generate_from_full_session(self):
        session = _build_full_session()
        gen = RequirementsGenerator()
        doc = gen.generate_from_discovery(session)
        assert doc.client_name == "TechStartup SA"
        assert doc.session_id == session.session_id
        assert len(doc.requirements) > 0

    def test_functional_requirements_from_problem(self):
        session = _build_full_session()
        gen = RequirementsGenerator()
        doc = gen.generate_from_discovery(session)
        # Debe haber un requerimiento sobre el problema principal
        titles = [r.title for r in doc.requirements]
        assert "Resolución del problema principal" in titles

    def test_non_functional_requirements_generated(self):
        session = _build_full_session()
        gen = RequirementsGenerator()
        doc = gen.generate_from_discovery(session)
        assert len(doc.non_functional) > 0

    def test_security_requirement_from_compliance(self):
        session = _build_full_session()
        gen = RequirementsGenerator()
        doc = gen.generate_from_discovery(session)
        security_reqs = [r for r in doc.non_functional if "seguridad" in r.title.lower()]
        assert len(security_reqs) > 0

    def test_constraints_include_budget(self):
        session = _build_full_session()
        gen = RequirementsGenerator()
        doc = gen.generate_from_discovery(session)
        budget_constraints = [c for c in doc.constraints if "presupuesto" in c.lower()]
        assert len(budget_constraints) > 0

    def test_assumptions_are_generated(self):
        session = _build_full_session()
        gen = RequirementsGenerator()
        doc = gen.generate_from_discovery(session)
        assert len(doc.assumptions) >= 3

    def test_out_of_scope_is_generated(self):
        session = _build_full_session()
        gen = RequirementsGenerator()
        doc = gen.generate_from_discovery(session)
        assert len(doc.out_of_scope) > 0


# ===========================================================================
# Tests de historias de usuario
# ===========================================================================


class TestUserStoryGeneration:
    """Tests de la generación de historias de usuario."""

    def test_user_stories_generated(self):
        session = _build_full_session()
        gen = RequirementsGenerator()
        stories = gen.generate_user_stories(session)
        assert len(stories) > 0

    def test_stories_have_role_action_benefit(self):
        session = _build_full_session()
        gen = RequirementsGenerator()
        stories = gen.generate_user_stories(session)
        for story in stories:
            assert story.as_a != ""
            assert story.i_want != ""
            assert story.so_that != ""

    def test_stories_include_additional_roles(self):
        session = _build_full_session()
        gen = RequirementsGenerator()
        stories = gen.generate_user_stories(session)
        roles = {s.as_a for s in stories}
        # Debe tener al menos el rol primario y algún rol adicional
        assert len(roles) >= 2

    def test_stories_have_acceptance_criteria(self):
        session = _build_full_session()
        gen = RequirementsGenerator()
        stories = gen.generate_user_stories(session)
        for story in stories:
            assert len(story.acceptance_criteria) > 0


# ===========================================================================
# Tests de estimación de esfuerzo
# ===========================================================================


class TestEffortEstimation:
    """Tests de la estimación de esfuerzo."""

    def test_estimate_effort_total_hours(self):
        gen = RequirementsGenerator()
        reqs = [
            Requirement(
                req_id="R1",
                title="Test",
                description="Test",
                estimated_effort=EffortSize.M,
            ),
            Requirement(
                req_id="R2",
                title="Test 2",
                description="Test 2",
                estimated_effort=EffortSize.S,
            ),
        ]
        estimate = gen.estimate_effort(reqs)
        expected = EFFORT_HOURS[EffortSize.M] + EFFORT_HOURS[EffortSize.S]
        assert estimate["total_hours"] == expected

    def test_estimate_by_size_breakdown(self):
        gen = RequirementsGenerator()
        reqs = [
            Requirement(req_id="R1", title="T", description="D", estimated_effort=EffortSize.L),
            Requirement(req_id="R2", title="T", description="D", estimated_effort=EffortSize.L),
            Requirement(req_id="R3", title="T", description="D", estimated_effort=EffortSize.S),
        ]
        estimate = gen.estimate_effort(reqs)
        assert estimate["by_size"]["L"] == 2
        assert estimate["by_size"]["S"] == 1

    def test_suggest_modules_includes_base(self):
        gen = RequirementsGenerator()
        reqs = [
            Requirement(req_id="R1", title="T", description="D", module="automation"),
        ]
        modules = gen.suggest_modules(reqs)
        assert "dashboard" in modules
        assert "notifications" in modules
        assert "analytics" in modules
        assert "automation" in modules


# ===========================================================================
# Tests de propuestas
# ===========================================================================


class TestProposalGeneration:
    """Tests de la generación de propuestas comerciales."""

    def test_generate_proposal_from_session(self):
        session = _build_full_session()
        req_gen = RequirementsGenerator()
        doc = req_gen.generate_from_discovery(session)
        prop_gen = ProposalGenerator()
        proposal = prop_gen.generate_proposal(session, doc)
        assert proposal.client_name == "TechStartup SA"
        assert proposal.proposal_id != ""

    def test_proposal_has_executive_summary(self):
        session = _build_full_session()
        req_gen = RequirementsGenerator()
        doc = req_gen.generate_from_discovery(session)
        prop_gen = ProposalGenerator()
        proposal = prop_gen.generate_proposal(session, doc)
        assert "TechStartup SA" in proposal.executive_summary
        assert len(proposal.executive_summary) > 50

    def test_proposal_has_phases(self):
        session = _build_full_session()
        req_gen = RequirementsGenerator()
        doc = req_gen.generate_from_discovery(session)
        prop_gen = ProposalGenerator()
        proposal = prop_gen.generate_proposal(session, doc)
        assert len(proposal.phases) >= 3

    def test_proposal_has_investment(self):
        session = _build_full_session()
        req_gen = RequirementsGenerator()
        doc = req_gen.generate_from_discovery(session)
        prop_gen = ProposalGenerator()
        proposal = prop_gen.generate_proposal(session, doc)
        assert "plan" in proposal.investment
        assert "development_cost_usd" in proposal.investment
        assert proposal.investment["development_cost_usd"] > 0

    def test_proposal_has_terms(self):
        session = _build_full_session()
        req_gen = RequirementsGenerator()
        doc = req_gen.generate_from_discovery(session)
        prop_gen = ProposalGenerator()
        proposal = prop_gen.generate_proposal(session, doc)
        assert "TÉRMINOS" in proposal.terms

    def test_proposal_to_markdown(self):
        session = _build_full_session()
        req_gen = RequirementsGenerator()
        doc = req_gen.generate_from_discovery(session)
        prop_gen = ProposalGenerator()
        proposal = prop_gen.generate_proposal(session, doc)
        md = prop_gen.to_markdown(proposal)
        assert "# Propuesta Comercial" in md
        assert "TechStartup SA" in md
        assert "## Resumen Ejecutivo" in md
        assert "## Inversión" in md

    def test_markdown_contains_all_sections(self):
        session = _build_full_session()
        req_gen = RequirementsGenerator()
        doc = req_gen.generate_from_discovery(session)
        prop_gen = ProposalGenerator()
        proposal = prop_gen.generate_proposal(session, doc)
        md = prop_gen.to_markdown(proposal)
        assert "## Alcance del Proyecto" in md
        assert "## Plan de Implementación" in md
        assert "## Cronograma" in md
        assert "## Términos y Condiciones" in md


# ===========================================================================
# Tests de recomendación de plan
# ===========================================================================


class TestPlanRecommendation:
    """Tests de la lógica de recomendación de plan."""

    def test_complex_project_recommends_enterprise(self):
        session = _build_full_session()
        req_gen = RequirementsGenerator()
        doc = req_gen.generate_from_discovery(session)
        prop_gen = ProposalGenerator()
        plan = prop_gen.estimate_plan(doc)
        # Con integraciones, security y mobile, debería ser enterprise o pro
        assert plan in ("enterprise", "pro")

    def test_simple_project_recommends_free_or_pro(self):
        prop_gen = ProposalGenerator()
        doc = RequirementsDocument(
            doc_id="test",
            client_name="Simple Co",
            session_id="test",
            requirements=[
                Requirement(req_id="R1", title="T", description="simple task"),
            ],
            user_stories=[],
            non_functional=[],
        )
        plan = prop_gen.estimate_plan(doc)
        assert plan in ("free", "pro")

    def test_plan_pricing_has_all_plans(self):
        assert "free" in PLAN_PRICING
        assert "pro" in PLAN_PRICING
        assert "enterprise" in PLAN_PRICING

    def test_free_plan_is_zero_cost(self):
        assert PLAN_PRICING["free"]["monthly_cost_usd"] == 0

    def test_enterprise_is_most_expensive(self):
        assert (
            PLAN_PRICING["enterprise"]["monthly_cost_usd"]
            > PLAN_PRICING["pro"]["monthly_cost_usd"]
        )
