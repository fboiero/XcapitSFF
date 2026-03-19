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
