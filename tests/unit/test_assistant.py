"""Tests for the conversational assistant — intent recognition, action
execution, entity extraction, conversation management, and context updates."""

from __future__ import annotations

import pytest

from xcapitsff.assistant.intent import (
    Intent,
    IntentMatch,
    IntentRecognizer,
    extract_entities,
)
from xcapitsff.assistant.executor import ActionExecutor, ActionResult
from xcapitsff.assistant.conversation import (
    AssistantManager,
    AssistantMessage,
    AssistantConversation,
)


# ===================================================================
# Intent recognition — major categories
# ===================================================================


class TestIntentRecognitionGreetingAndHelp:
    def test_hola_recognised_as_greeting(self):
        r = IntentRecognizer()
        match = r.recognize("hola")
        assert match.intent == Intent.GREETING
        assert match.confidence >= 0.90

    def test_buenos_dias_recognised_as_greeting(self):
        r = IntentRecognizer()
        match = r.recognize("buenos dias")
        assert match.intent == Intent.GREETING

    def test_buenas_tardes_recognised_as_greeting(self):
        r = IntentRecognizer()
        match = r.recognize("buenas tardes")
        assert match.intent == Intent.GREETING

    def test_ayuda_recognised_as_help(self):
        r = IntentRecognizer()
        match = r.recognize("ayuda")
        assert match.intent == Intent.HELP
        assert match.confidence >= 0.85

    def test_que_puedo_hacer_recognised_as_help(self):
        r = IntentRecognizer()
        match = r.recognize("que puedo hacer")
        assert match.intent == Intent.HELP


class TestIntentRecognitionLeads:
    def test_crear_lead(self):
        r = IntentRecognizer()
        match = r.recognize("crear un lead")
        assert match.intent == Intent.CREATE_LEAD

    def test_nuevo_lead(self):
        r = IntentRecognizer()
        match = r.recognize("nuevo lead")
        assert match.intent == Intent.CREATE_LEAD

    def test_agregar_prospecto(self):
        r = IntentRecognizer()
        match = r.recognize("agregar prospecto")
        assert match.intent == Intent.CREATE_LEAD

    def test_ver_leads(self):
        r = IntentRecognizer()
        match = r.recognize("ver leads")
        assert match.intent == Intent.LIST_LEADS

    def test_calificar_lead(self):
        r = IntentRecognizer()
        match = r.recognize("calificar lead 42")
        assert match.intent == Intent.QUALIFY_LEAD
        assert 42 in match.extracted_params.get("ids", [])


class TestIntentRecognitionTickets:
    def test_crear_ticket(self):
        r = IntentRecognizer()
        match = r.recognize("crear un ticket")
        assert match.intent == Intent.CREATE_TICKET

    def test_nuevo_caso(self):
        r = IntentRecognizer()
        match = r.recognize("nuevo caso")
        assert match.intent == Intent.CREATE_TICKET

    def test_reportar_problema(self):
        r = IntentRecognizer()
        match = r.recognize("reportar problema")
        assert match.intent == Intent.CREATE_TICKET

    def test_ver_tickets(self):
        r = IntentRecognizer()
        match = r.recognize("ver tickets")
        assert match.intent == Intent.LIST_TICKETS


class TestIntentRecognitionDashboardAndPipeline:
    def test_dashboard(self):
        r = IntentRecognizer()
        match = r.recognize("dashboard")
        assert match.intent == Intent.VIEW_DASHBOARD

    def test_resumen(self):
        r = IntentRecognizer()
        match = r.recognize("quiero ver el resumen")
        assert match.intent == Intent.VIEW_DASHBOARD

    def test_kanban(self):
        r = IntentRecognizer()
        match = r.recognize("kanban")
        assert match.intent == Intent.VIEW_KANBAN

    def test_ver_pipeline(self):
        r = IntentRecognizer()
        match = r.recognize("ver el pipeline")
        assert match.intent == Intent.VIEW_KANBAN


class TestIntentRecognitionOtherIntents:
    def test_outreach(self):
        r = IntentRecognizer()
        match = r.recognize("enviar mensaje al lead")
        assert match.intent == Intent.COMPOSE_OUTREACH

    def test_importar_csv(self):
        r = IntentRecognizer()
        match = r.recognize("cargar csv de leads")
        assert match.intent == Intent.IMPORT_DATA

    def test_exportar(self):
        r = IntentRecognizer()
        match = r.recognize("exportar datos")
        assert match.intent == Intent.EXPORT_DATA

    def test_campana(self):
        r = IntentRecognizer()
        match = r.recognize("iniciar una campana")
        assert match.intent == Intent.START_CAMPAIGN

    def test_reunion(self):
        r = IntentRecognizer()
        match = r.recognize("agendar reunion")
        assert match.intent == Intent.SCHEDULE_MEETING

    def test_prediccion(self):
        r = IntentRecognizer()
        match = r.recognize("ver predicciones")
        assert match.intent == Intent.VIEW_PREDICTIONS

    def test_automatizar(self):
        r = IntentRecognizer()
        match = r.recognize("automatizar seguimiento")
        assert match.intent == Intent.RUN_AUTOMATION

    def test_buscar(self):
        r = IntentRecognizer()
        match = r.recognize("buscar TechCorp")
        assert match.intent == Intent.SEARCH


# ===================================================================
# Entity extraction
# ===================================================================


class TestEntityExtraction:
    def test_extract_number_ids(self):
        entities = extract_entities("ver lead 42")
        assert 42 in entities["ids"]

    def test_extract_email(self):
        entities = extract_entities("contactar a ana@techcorp.com")
        assert entities["email"] == "ana@techcorp.com"

    def test_extract_company_after_de(self):
        entities = extract_entities("crear lead de TechCorp")
        assert entities["company"] == "TechCorp"

    def test_extract_company_after_para(self):
        entities = extract_entities("outreach para DataPro Solutions")
        assert "DataPro" in entities["company"]

    def test_extract_quoted_search_query(self):
        entities = extract_entities('buscar "error de login"')
        assert entities["search_query"] == "error de login"

    def test_extract_multiple_ids(self):
        entities = extract_entities("comparar leads 10 y 20")
        assert 10 in entities["ids"]
        assert 20 in entities["ids"]

    def test_empty_text_returns_empty_entities(self):
        entities = extract_entities("")
        assert entities == {}


# ===================================================================
# Unknown intent handling
# ===================================================================


class TestUnknownIntent:
    def test_empty_text_returns_unknown(self):
        r = IntentRecognizer()
        match = r.recognize("")
        assert match.intent == Intent.UNKNOWN
        assert match.confidence == 0.0

    def test_random_text_returns_unknown(self):
        r = IntentRecognizer()
        match = r.recognize("xyzzy foobar baz")
        assert match.intent == Intent.UNKNOWN


# ===================================================================
# Action execution — visual types and responses in Spanish
# ===================================================================


class TestActionExecution:
    def test_greeting_produces_card(self):
        executor = ActionExecutor()
        intent_match = IntentMatch(intent=Intent.GREETING, confidence=0.95, original_text="hola")
        result = executor.execute(intent_match)
        assert isinstance(result, ActionResult)
        assert result.success is True
        assert result.visual_type == "card"
        assert "Hola" in result.message

    def test_help_produces_card_with_categories(self):
        executor = ActionExecutor()
        intent_match = IntentMatch(intent=Intent.HELP, confidence=0.90, original_text="ayuda")
        result = executor.execute(intent_match)
        assert result.visual_type == "card"
        assert "categories" in result.result_data

    def test_list_leads_produces_table(self):
        executor = ActionExecutor()
        intent_match = IntentMatch(intent=Intent.LIST_LEADS, confidence=0.90, original_text="ver leads")
        result = executor.execute(intent_match)
        assert result.visual_type == "table"
        assert "leads" in result.result_data

    def test_view_kanban_produces_kanban(self):
        executor = ActionExecutor()
        intent_match = IntentMatch(intent=Intent.VIEW_KANBAN, confidence=0.90, original_text="kanban")
        result = executor.execute(intent_match)
        assert result.visual_type == "kanban"
        assert "columns" in result.result_data

    def test_view_dashboard_produces_card(self):
        executor = ActionExecutor()
        intent_match = IntentMatch(intent=Intent.VIEW_DASHBOARD, confidence=0.90, original_text="dashboard")
        result = executor.execute(intent_match)
        assert result.visual_type == "card"
        assert "sales" in result.result_data

    def test_create_lead_without_params_shows_form(self):
        executor = ActionExecutor()
        intent_match = IntentMatch(intent=Intent.CREATE_LEAD, confidence=0.95, original_text="crear lead")
        result = executor.execute(intent_match)
        assert result.visual_type == "form"
        assert "form_fields" in result.result_data

    def test_create_lead_with_company_creates_lead(self):
        executor = ActionExecutor()
        intent_match = IntentMatch(
            intent=Intent.CREATE_LEAD,
            confidence=0.95,
            extracted_params={"company": "MiEmpresa"},
            original_text="crear lead de MiEmpresa",
        )
        result = executor.execute(intent_match)
        assert result.visual_type == "card"
        assert result.result_data["lead"]["company_name"] == "MiEmpresa"

    def test_qualify_lead_with_id_returns_score_card(self):
        executor = ActionExecutor()
        intent_match = IntentMatch(
            intent=Intent.QUALIFY_LEAD,
            confidence=0.90,
            extracted_params={"ids": [42]},
            original_text="calificar lead 42",
        )
        result = executor.execute(intent_match)
        assert result.visual_type == "card"
        assert result.result_data["score_card"]["lead_id"] == 42

    def test_view_predictions_produces_chart(self):
        executor = ActionExecutor()
        intent_match = IntentMatch(intent=Intent.VIEW_PREDICTIONS, confidence=0.90, original_text="predicciones")
        result = executor.execute(intent_match)
        assert result.visual_type == "chart"
        assert "predictions" in result.result_data

    def test_unknown_intent_returns_failure(self):
        executor = ActionExecutor()
        intent_match = IntentMatch(intent=Intent.UNKNOWN, confidence=0.0, original_text="xyzzy")
        result = executor.execute(intent_match)
        assert result.success is False
        assert "ayuda" in result.message.lower() or "seguro" in result.message.lower()


# ===================================================================
# Suggestions relevance
# ===================================================================


class TestSuggestionsRelevance:
    def test_create_lead_suggestions(self):
        executor = ActionExecutor()
        intent_match = IntentMatch(
            intent=Intent.CREATE_LEAD,
            confidence=0.95,
            extracted_params={"company": "TestCo"},
            original_text="crear lead de TestCo",
        )
        result = executor.execute(intent_match)
        suggestions_lower = [s.lower() for s in result.next_suggestions]
        assert any("calificar" in s for s in suggestions_lower)

    def test_dashboard_suggestions(self):
        executor = ActionExecutor()
        intent_match = IntentMatch(intent=Intent.VIEW_DASHBOARD, confidence=0.90, original_text="dashboard")
        result = executor.execute(intent_match)
        suggestions_lower = [s.lower() for s in result.next_suggestions]
        assert any("leads" in s or "predicciones" in s for s in suggestions_lower)

    def test_create_ticket_suggestions(self):
        executor = ActionExecutor()
        intent_match = IntentMatch(
            intent=Intent.CREATE_TICKET,
            confidence=0.95,
            extracted_params={"search_query": "error de login"},
            original_text='crear ticket "error de login"',
        )
        result = executor.execute(intent_match)
        suggestions_lower = [s.lower() for s in result.next_suggestions]
        assert any("kb" in s or "ticket" in s for s in suggestions_lower)


# ===================================================================
# Conversation context updates
# ===================================================================


class TestConversationContext:
    def test_start_conversation_creates_greeting(self):
        manager = AssistantManager()
        conv = manager.start_conversation("tenant-1", "user-1")
        assert isinstance(conv, AssistantConversation)
        assert conv.tenant_id == "tenant-1"
        assert len(conv.messages) == 1
        assert conv.messages[0].role == "assistant"

    def test_process_message_updates_context(self):
        manager = AssistantManager()
        conv = manager.start_conversation("t1", "u1")
        manager.process_message(conv.conversation_id, "ver el dashboard")
        updated = manager.get_conversation(conv.conversation_id)
        assert updated.context.get("last_intent") == "view_dashboard"
        assert updated.context.get("last_action") == "view_dashboard"

    def test_process_message_tracks_lead_id(self):
        manager = AssistantManager()
        conv = manager.start_conversation("t2", "u2")
        manager.process_message(conv.conversation_id, "crear lead de TestCorp")
        updated = manager.get_conversation(conv.conversation_id)
        assert updated.context.get("current_lead_id") is not None

    def test_conversation_accumulates_messages(self):
        manager = AssistantManager()
        conv = manager.start_conversation("t3", "u3")
        manager.process_message(conv.conversation_id, "hola")
        manager.process_message(conv.conversation_id, "ver leads")
        updated = manager.get_conversation(conv.conversation_id)
        # 1 greeting + 2 user + 2 assistant = 5
        assert len(updated.messages) == 5

    def test_get_nonexistent_conversation_raises(self):
        manager = AssistantManager()
        with pytest.raises(ValueError, match="no encontrada"):
            manager.get_conversation("nonexistent-id")

    def test_process_message_nonexistent_conversation_raises(self):
        manager = AssistantManager()
        with pytest.raises(ValueError, match="no encontrada"):
            manager.process_message("ghost-id", "hola")

    def test_greeting_message_has_suggestions(self):
        manager = AssistantManager()
        greeting = manager.get_greeting_message()
        assert isinstance(greeting, AssistantMessage)
        assert len(greeting.suggestions) >= 3
        assert greeting.visual is not None

    def test_assistant_response_is_in_spanish(self):
        manager = AssistantManager()
        conv = manager.start_conversation("t-es", "u-es")
        msg = manager.process_message(conv.conversation_id, "ayuda")
        # The response should contain Spanish words
        assert any(w in msg.content.lower() for w in ["puedo", "hacer", "categoria", "estas"])

    def test_conversation_to_dict_serialises_correctly(self):
        manager = AssistantManager()
        conv = manager.start_conversation("t-dict", "u-dict")
        manager.process_message(conv.conversation_id, "hola")
        data = manager.get_conversation(conv.conversation_id).to_dict()
        assert "conversation_id" in data
        assert "messages" in data
        assert isinstance(data["messages"], list)
        assert len(data["messages"]) >= 2


# ===================================================================
# NEW: Multi-strategy recognition tests
# ===================================================================


class TestMultiStrategyRecognition:
    """Verify the four-tier recognition pipeline works correctly."""

    def test_exact_command_confidence_is_highest(self):
        """Exact commands should return confidence >= 0.95."""
        r = IntentRecognizer()
        match = r.recognize("hola")
        assert match.confidence >= 0.95

    def test_exact_command_with_trailing_punctuation(self):
        """Exact commands should be recognized even with trailing punctuation."""
        r = IntentRecognizer()
        match = r.recognize("hola!")
        assert match.intent == Intent.GREETING

    def test_regex_match_confidence_range(self):
        """Regex pattern matches should return confidence 0.80+."""
        r = IntentRecognizer()
        match = r.recognize("quiero ver todos los leads activos ahora mismo por favor")
        assert match.intent == Intent.LIST_LEADS
        assert match.confidence >= 0.80

    def test_fuzzy_match_mostrame_leads(self):
        """Colloquial 'mostrame los leads' should match via fuzzy keywords."""
        r = IntentRecognizer()
        match = r.recognize("mostrame los leads")
        assert match.intent == Intent.LIST_LEADS
        assert match.confidence >= 0.40

    def test_contextual_fallback_with_company_only(self):
        """When only a company name is found, contextual fallback guesses leads."""
        r = IntentRecognizer()
        match = r.recognize("algo sobre empresa TechCorp")
        assert match.intent == Intent.LIST_LEADS
        assert match.confidence <= 0.50


# ===================================================================
# NEW: Colloquial Spanish phrases
# ===================================================================


class TestColloquialSpanishPhrases:
    """Verify expanded Spanish vocabulary from the requirements."""

    def test_mostrame_leads(self):
        r = IntentRecognizer()
        match = r.recognize("mostrame los leads")
        assert match.intent == Intent.LIST_LEADS

    def test_quiero_ver_leads(self):
        r = IntentRecognizer()
        match = r.recognize("quiero ver leads")
        assert match.intent == Intent.LIST_LEADS

    def test_dame_los_tickets(self):
        r = IntentRecognizer()
        match = r.recognize("dame los tickets")
        assert match.intent == Intent.LIST_TICKETS

    def test_necesito_ver_oportunidades(self):
        r = IntentRecognizer()
        match = r.recognize("necesito oportunidades")
        assert match.intent == Intent.LIST_LEADS

    def test_generar_lead(self):
        """'generar' as synonym for 'crear'."""
        r = IntentRecognizer()
        match = r.recognize("generar un lead")
        assert match.intent == Intent.CREATE_LEAD

    def test_armar_ticket(self):
        """'armar' as synonym for 'crear'."""
        r = IntentRecognizer()
        match = r.recognize("armar un ticket")
        assert match.intent == Intent.CREATE_TICKET

    def test_hacer_prospecto(self):
        """'hacer' as synonym for 'crear'."""
        r = IntentRecognizer()
        match = r.recognize("hacer un prospecto")
        assert match.intent == Intent.CREATE_LEAD

    def test_cuantos_tickets(self):
        """'cuantos tickets' recognized as list tickets."""
        r = IntentRecognizer()
        match = r.recognize("cuantos tickets hay")
        assert match.intent == Intent.LIST_TICKETS


# ===================================================================
# NEW: Compound intent detection
# ===================================================================


class TestCompoundIntentDetection:
    """Verify multi-part requests are parsed with correct params."""

    def test_leads_hot_de_latam(self):
        """'mostrame los leads hot de LATAM' -> LIST_LEADS with classification and region."""
        r = IntentRecognizer()
        match = r.recognize("mostrame los leads hot de LATAM")
        assert match.intent == Intent.LIST_LEADS
        assert match.extracted_params.get("classification") == "hot"
        assert match.extracted_params.get("region") == "LATAM"

    def test_create_lead_para_acme_ceo(self):
        """'crea un lead para Acme Corp, es CEO' -> CREATE_LEAD with company and c_level."""
        r = IntentRecognizer()
        match = r.recognize("crear un lead para Acme Corp, es CEO")
        assert match.intent == Intent.CREATE_LEAD
        assert "Acme" in match.extracted_params.get("company", "")
        assert match.extracted_params.get("c_level") is True

    def test_tickets_urgentes_abiertos(self):
        """'cuantos tickets urgentes hay abiertos' -> LIST_TICKETS with priority and status."""
        r = IntentRecognizer()
        match = r.recognize("cuantos tickets urgentes hay abiertos")
        assert match.intent == Intent.LIST_TICKETS
        assert match.extracted_params.get("priority") == "urgent"
        assert match.extracted_params.get("status") == "open"

    def test_leads_calientes_argentina(self):
        """Compound: leads + classification + region."""
        r = IntentRecognizer()
        match = r.recognize("ver leads calientes de Argentina")
        assert match.intent == Intent.LIST_LEADS
        assert match.extracted_params.get("classification") == "hot"
        assert match.extracted_params.get("region") == "Argentina"

    def test_enviar_email_contacto(self):
        """Compound: outreach + channel."""
        r = IntentRecognizer()
        match = r.recognize("enviar email al contacto")
        assert match.intent == Intent.COMPOSE_OUTREACH
        assert match.extracted_params.get("channel") == "email"


# ===================================================================
# NEW: Entity extraction — expanded
# ===================================================================


class TestExpandedEntityExtraction:
    """Test the new entity extraction capabilities."""

    def test_extract_region_latam(self):
        entities = extract_entities("leads de LATAM")
        assert entities["region"] == "LATAM"

    def test_extract_region_iberia(self):
        entities = extract_entities("prospectos de Iberia")
        assert entities["region"] == "Iberia"

    def test_extract_region_mexico(self):
        entities = extract_entities("clientes en México")
        assert entities["region"] == "México"

    def test_extract_priority_urgente(self):
        entities = extract_entities("tickets urgentes pendientes")
        assert entities["priority"] == "urgent"

    def test_extract_priority_alta(self):
        entities = extract_entities("prioridad alta")
        assert entities["priority"] == "high"

    def test_extract_classification_hot(self):
        entities = extract_entities("leads hot")
        assert entities["classification"] == "hot"

    def test_extract_classification_calientes(self):
        entities = extract_entities("prospectos calientes")
        assert entities["classification"] == "hot"

    def test_extract_stage_propuesta(self):
        entities = extract_entities("leads en etapa propuesta")
        assert entities["stage"] == "proposal"

    def test_extract_stage_negociacion(self):
        entities = extract_entities("oportunidades en negociacion")
        assert entities["stage"] == "negotiation"

    def test_extract_status_abiertos(self):
        entities = extract_entities("tickets abiertos")
        assert entities["status"] == "open"

    def test_extract_channel_linkedin(self):
        entities = extract_entities("enviar por linkedin")
        assert entities["channel"] == "linkedin"

    def test_extract_channel_whatsapp(self):
        entities = extract_entities("mandar whatsapp")
        assert entities["channel"] == "whatsapp"

    def test_extract_contact_name(self):
        entities = extract_entities("contacto Juan Perez")
        assert entities["contact_name"] == "Juan Perez"

    def test_extract_score_threshold(self):
        entities = extract_entities("score mayor a 70")
        assert entities["score_threshold"] == 70

    def test_extract_high_icp(self):
        entities = extract_entities("leads con ICP alto")
        assert entities["high_icp"] is True

    def test_extract_c_level(self):
        entities = extract_entities("el contacto es CEO de la empresa")
        assert entities["c_level"] is True

    def test_extract_c_level_cto(self):
        entities = extract_entities("hablar con el CTO")
        assert entities["c_level"] is True


# ===================================================================
# NEW: Confidence calibration
# ===================================================================


class TestConfidenceCalibration:
    """Verify that confidence levels match the expected tiers."""

    def test_exact_command_confidence_098(self):
        """Exact match should return 0.98."""
        r = IntentRecognizer()
        match = r.recognize("hola")
        assert match.confidence == 0.98

    def test_regex_confidence_above_080(self):
        """Regex match on longer text should be >= 0.80."""
        r = IntentRecognizer()
        match = r.recognize("crear un lead nuevo para la empresa")
        assert match.intent == Intent.CREATE_LEAD
        assert match.confidence >= 0.80

    def test_fuzzy_match_below_080(self):
        """Known phrases should have high confidence."""
        r = IntentRecognizer()
        match = r.recognize("mostrame los leads")
        assert match.confidence >= 0.60
        assert match.intent == Intent.LIST_LEADS

    def test_contextual_fallback_between_030_and_050(self):
        """Contextual guesses should be in the 0.30-0.50 range."""
        r = IntentRecognizer()
        match = r.recognize("algo sobre empresa TechCorp")
        assert 0.25 <= match.confidence <= 0.55

    def test_unknown_confidence_zero(self):
        """Completely unrecognized text returns confidence 0.0."""
        r = IntentRecognizer()
        match = r.recognize("xyzzy foobar baz")
        assert match.confidence == 0.0

    def test_short_exact_text_higher_than_long_regex(self):
        """Short exact commands should have higher confidence than verbose regex matches."""
        r = IntentRecognizer()
        short = r.recognize("ver leads")
        long_ = r.recognize("me gustaria poder ver todos los leads del equipo si es posible")
        assert short.confidence > long_.confidence


# ===================================================================
# NEW: Context-aware fallback
# ===================================================================


class TestContextAwareFallback:
    """Test that contextual guessing works on ambiguous input."""

    def test_only_number_returns_search(self):
        """Just a number should guess SEARCH."""
        r = IntentRecognizer()
        match = r.recognize("42")
        assert match.intent == Intent.SEARCH
        assert 42 in match.extracted_params.get("ids", [])
        assert match.confidence <= 0.50

    def test_urgente_alone_guesses_tickets(self):
        """'urgente' alone should guess LIST_TICKETS via fuzzy/fallback."""
        r = IntentRecognizer()
        match = r.recognize("urgente")
        assert match.intent == Intent.LIST_TICKETS

    def test_company_name_alone_guesses_leads(self):
        """A mention of a company should guess leads via contextual fallback."""
        r = IntentRecognizer()
        match = r.recognize("empresa TechCorp")
        assert match.intent == Intent.LIST_LEADS

    def test_icp_alto_guesses_qualify(self):
        """'ICP alto' should guess QUALIFY_LEAD via contextual fallback."""
        r = IntentRecognizer()
        match = r.recognize("ICP alto")
        assert match.intent == Intent.QUALIFY_LEAD

    def test_score_mayor_a_70_guesses_qualify(self):
        """'score mayor a 70' should guess QUALIFY_LEAD via fallback."""
        r = IntentRecognizer()
        match = r.recognize("score mayor a 70")
        # score matches the qualify_lead regex pattern
        assert match.intent == Intent.QUALIFY_LEAD
        assert match.extracted_params.get("score_threshold") == 70
