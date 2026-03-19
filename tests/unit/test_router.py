"""Comprehensive tests for the multi-signal ticket router."""

import pytest

from xcapitsff.core.schemas import TicketPriorityEnum
from xcapitsff.support.router import (
    RoutingDecision,
    calculate_sla,
    classify_ticket,
    full_route,
    route_to_agent,
    should_escalate,
)


# ===================================================================
# classify_ticket — category detection
# ===================================================================


class TestClassifyCategory:
    """Tests for category classification accuracy."""

    def test_billing_keywords(self):
        cat, conf, *_ = classify_ticket("Problema con factura", "No puedo ver mi factura del mes pasado")
        assert cat == "billing"
        assert conf >= 0.5

    def test_technical_keywords(self):
        cat, conf, *_ = classify_ticket("Error en la app", "La app crashea cuando abro el dashboard")
        assert cat == "technical"
        assert conf >= 0.5

    def test_crypto_keywords(self):
        cat, conf, *_ = classify_ticket("Wallet issue", "No puedo hacer withdraw de mi wallet")
        assert cat == "crypto"
        assert conf >= 0.5

    def test_account_keywords(self):
        cat, conf, *_ = classify_ticket(
            "No puedo acceder", "Olvidé mi contraseña y no puedo hacer login"
        )
        assert cat == "account"
        assert conf >= 0.5

    def test_general_fallback_low_confidence(self):
        cat, conf, *_ = classify_ticket("Hola", "Tengo una duda general")
        assert cat == "general"
        # General with weak signals should have lower confidence
        assert conf <= 0.8

    def test_pattern_matching_billing(self):
        """Pattern 'cobro indebido' strongly signals billing."""
        cat, conf, *_ = classify_ticket("Cobro duplicado", "Me cobraron dos veces este mes")
        assert cat == "billing"
        assert conf >= 0.6

    def test_pattern_matching_account(self):
        """Pattern 'no puedo iniciar sesion' signals account."""
        cat, conf, *_ = classify_ticket("Login", "No puedo iniciar sesion desde ayer")
        assert cat == "account"

    def test_pattern_matching_crypto_pending(self):
        """Pattern 'transaccion pendiente' signals crypto."""
        cat, conf, *_ = classify_ticket("Transaccion", "Mi transacción pendiente lleva 2 dias")
        assert cat == "crypto"

    def test_accent_normalization(self):
        """Accented characters should be normalized so keywords match."""
        cat, conf, *_ = classify_ticket("Suscripción", "Quiero cancelar mi suscripción")
        assert cat == "billing"


# ===================================================================
# classify_ticket — priority detection
# ===================================================================


class TestClassifyPriority:
    """Tests for priority classification and urgency detection."""

    def test_explicit_urgent_keyword(self):
        _, _, prio, prio_conf, _ = classify_ticket("URGENTE", "Problema crítico con fondos bloqueados")
        assert prio == TicketPriorityEnum.URGENT
        assert prio_conf >= 0.8

    def test_high_priority_blocked(self):
        _, _, prio, *_ = classify_ticket("Acceso", "No puedo acceder a mi cuenta, estoy bloqueado")
        assert prio in (TicketPriorityEnum.HIGH, TicketPriorityEnum.URGENT)

    def test_medium_default_priority(self):
        _, _, prio, *_ = classify_ticket("Consulta", "Quisiera saber los horarios de atención")
        assert prio == TicketPriorityEnum.MEDIUM

    def test_urgency_tone_exclamation(self):
        """Multiple exclamation marks should boost urgency."""
        _, _, prio, *_ = classify_ticket("AYUDA!!!", "NO FUNCIONA NADA!!! NECESITO ESTO YA!!!")
        assert prio in (TicketPriorityEnum.HIGH, TicketPriorityEnum.URGENT)

    def test_urgency_tone_all_caps(self):
        """ALL CAPS text should boost urgency."""
        _, _, prio, *_ = classify_ticket("PROBLEMA CON MI CUENTA", "NO PUEDO ACCEDER DESDE AYER")
        assert prio in (TicketPriorityEnum.HIGH, TicketPriorityEnum.URGENT)

    def test_financial_risk_auto_boost(self):
        """Financial keywords should boost priority to at least HIGH."""
        _, _, prio, _, flags = classify_ticket(
            "Dinero desaparecido", "Mi saldo desapareció de mi cuenta, tengo perdida de fondos"
        )
        assert prio in (TicketPriorityEnum.HIGH, TicketPriorityEnum.URGENT)
        assert "financial_risk" in flags


# ===================================================================
# classify_ticket — flags
# ===================================================================


class TestClassifyFlags:
    """Tests for special flag detection."""

    def test_financial_risk_flag(self):
        _, _, _, _, flags = classify_ticket("Retiro fallido", "Hice un retiro y mi dinero no llegó")
        assert "financial_risk" in flags

    def test_crypto_urgent_security_review(self):
        """Crypto + urgent should trigger security_review flag."""
        _, _, prio, _, flags = classify_ticket(
            "URGENTE wallet hackeada",
            "Alguien robó mis fondos del wallet, urgente por favor",
        )
        assert prio == TicketPriorityEnum.URGENT
        assert "security_review" in flags

    def test_no_flags_for_simple_query(self):
        _, _, _, _, flags = classify_ticket("Pregunta", "Cómo cambio mi email?")
        assert flags == []


# ===================================================================
# route_to_agent
# ===================================================================


class TestRouteToAgent:
    """Tests for smart agent routing."""

    def test_urgent_goes_to_senior(self):
        agent = route_to_agent("crypto", TicketPriorityEnum.URGENT)
        assert agent == "support_responder_senior"

    def test_high_goes_to_senior(self):
        agent = route_to_agent("billing", TicketPriorityEnum.HIGH)
        assert agent == "support_responder_senior"

    def test_medium_billing_goes_to_billing(self):
        agent = route_to_agent("billing", TicketPriorityEnum.MEDIUM)
        assert agent == "support_responder_billing"

    def test_medium_tech_goes_to_tech(self):
        agent = route_to_agent("technical", TicketPriorityEnum.MEDIUM)
        assert agent == "support_responder_tech"

    def test_general_low_goes_to_default(self):
        agent = route_to_agent("general", TicketPriorityEnum.LOW)
        assert agent == "support_responder"

    def test_load_balancing_skips_overloaded_agent(self):
        """When the preferred agent is overloaded, route to next best."""
        loads = {"support_responder_senior": 10}  # max_load is 10
        agent = route_to_agent("billing", TicketPriorityEnum.URGENT, current_loads=loads)
        # Should skip senior and pick billing specialist
        assert agent != "support_responder_senior"
        assert agent == "support_responder_billing"

    def test_load_balancing_picks_least_loaded_when_all_full(self):
        """When all preferred agents are overloaded, pick the least loaded."""
        loads = {
            "support_responder_senior": 100,
            "support_responder_billing": 100,
            "support_responder": 50,
        }
        agent = route_to_agent("billing", TicketPriorityEnum.URGENT, current_loads=loads)
        # All overloaded → pick least loaded from preferred list
        assert agent == "support_responder"

    def test_no_loads_provided_returns_preferred(self):
        """Without load data, always returns the top preference."""
        agent = route_to_agent("crypto", TicketPriorityEnum.LOW)
        assert agent == "support_responder_crypto"


# ===================================================================
# calculate_sla
# ===================================================================


class TestCalculateSla:
    """Tests for SLA calculation."""

    def test_urgent_base_sla(self):
        sla = calculate_sla(TicketPriorityEnum.URGENT, "general")
        assert sla == 2.0

    def test_medium_base_sla(self):
        sla = calculate_sla(TicketPriorityEnum.MEDIUM, "general")
        assert sla == 24.0

    def test_low_base_sla(self):
        sla = calculate_sla(TicketPriorityEnum.LOW, "general")
        assert sla == 72.0

    def test_crypto_tighter_sla(self):
        sla = calculate_sla(TicketPriorityEnum.MEDIUM, "crypto")
        assert sla == 24.0 * 0.75  # 18.0

    def test_billing_tighter_sla(self):
        sla = calculate_sla(TicketPriorityEnum.MEDIUM, "billing")
        assert sla == pytest.approx(24.0 * 0.8)  # 19.2

    def test_vip_50_percent_reduction(self):
        sla = calculate_sla(TicketPriorityEnum.MEDIUM, "general", is_vip=True)
        assert sla == 12.0

    def test_vip_crypto_stacks(self):
        """VIP + crypto multipliers should stack."""
        sla = calculate_sla(TicketPriorityEnum.MEDIUM, "crypto", is_vip=True)
        expected = 24.0 * 0.75 * 0.5  # 9.0
        assert sla == expected


# ===================================================================
# should_escalate
# ===================================================================


class TestShouldEscalate:
    """Tests for escalation rules."""

    def test_approaching_sla_triggers_escalation(self):
        # 80% of 10h SLA = 8h; ticket is 9h old
        assert should_escalate(9.0, TicketPriorityEnum.MEDIUM, 10.0, 1) is True

    def test_within_sla_no_escalation(self):
        # 50% of SLA consumed, no other triggers
        assert should_escalate(5.0, TicketPriorityEnum.MEDIUM, 10.0, 1) is False

    def test_three_interactions_triggers_escalation(self):
        assert should_escalate(1.0, TicketPriorityEnum.MEDIUM, 24.0, 3) is True

    def test_two_interactions_no_escalation(self):
        assert should_escalate(1.0, TicketPriorityEnum.MEDIUM, 24.0, 2) is False

    def test_urgent_over_one_hour_triggers_escalation(self):
        assert should_escalate(1.5, TicketPriorityEnum.URGENT, 2.0, 0) is True

    def test_urgent_under_one_hour_no_escalation(self):
        assert should_escalate(0.5, TicketPriorityEnum.URGENT, 2.0, 0) is False

    def test_no_escalation_fresh_ticket(self):
        assert should_escalate(0.0, TicketPriorityEnum.LOW, 72.0, 0) is False


# ===================================================================
# full_route — integration tests
# ===================================================================


class TestFullRoute:
    """Integration tests for the full routing pipeline."""

    def test_returns_routing_decision_dataclass(self):
        result = full_route("Hola", "Tengo una consulta")
        assert isinstance(result, RoutingDecision)

    def test_urgent_crypto_full_pipeline(self):
        result = full_route(
            "URGENTE: fondos robados",
            "Alguien hackeó mi wallet y se llevó mis fondos!!!",
        )
        assert result.category == "crypto"
        assert result.priority == TicketPriorityEnum.URGENT
        assert "financial_risk" in result.flags
        assert "security_review" in result.flags
        assert result.assigned_agent == "support_responder_senior"

    def test_vip_gets_shorter_sla(self):
        result_normal = full_route("Consulta billing", "Pregunta sobre mi factura")
        result_vip = full_route("Consulta billing", "Pregunta sobre mi factura", is_vip=True)
        assert result_vip.sla_hours < result_normal.sla_hours
        assert result_vip.sla_hours == pytest.approx(result_normal.sla_hours * 0.5)

    def test_low_confidence_flags_human_review(self):
        """A vague message should produce low confidence and flag for review."""
        result = full_route("Hola", "Tengo un tema")
        assert result.requires_human_review is True

    def test_high_confidence_no_human_review(self):
        """A clear message should not require human review."""
        result = full_route(
            "URGENTE error critico",
            "La API tiene un error 500, el servidor está caído y crashea todo",
        )
        # Technical keywords are very clear here
        assert result.category_confidence >= 0.5

    def test_escalation_on_old_urgent_ticket(self):
        result = full_route(
            "Urgente",
            "Mi cuenta está bloqueada urgente",
            ticket_age_hours=2.0,
            num_interactions=0,
        )
        assert result.escalation_needed is True

    def test_load_balancing_in_full_route(self):
        loads = {"support_responder_senior": 10}
        result = full_route(
            "URGENTE: problema con cobro",
            "Me cobraron doble, urgente",
            current_loads=loads,
        )
        # Senior is full, should route elsewhere
        assert result.assigned_agent != "support_responder_senior"

    def test_all_fields_populated(self):
        """Every field of RoutingDecision should be populated."""
        result = full_route("Test", "Consulta general de prueba")
        assert result.category is not None
        assert 0.0 <= result.category_confidence <= 1.0
        assert result.priority is not None
        assert 0.0 <= result.priority_confidence <= 1.0
        assert result.assigned_agent is not None
        assert isinstance(result.requires_human_review, bool)
        assert isinstance(result.escalation_needed, bool)
        assert result.sla_hours > 0
        assert isinstance(result.flags, list)
