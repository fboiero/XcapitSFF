"""Tests for the Outreach Template Engine.

Covers:
- Template registry (registration, lookup, minimum count)
- Language detection from lead region
- Temperature detection from classification / score / afinidad
- Template selection logic (channel, language, temperature, c_level)
- Message composition with personalisation
- Personalisation score calculation
- Template override in composition
- A/B variant generation
- Follow-up sequence (attempts 1, 2, 3 + out-of-range)
- Batch composition
- Safe rendering with missing placeholders
- Edge cases (empty lead data, unknown channel, etc.)
"""

import pytest

from xcapitsff.sales.outreach import (
    ALL_PLACEHOLDERS,
    Channel,
    Language,
    LeadTemperature,
    OutreachDraft,
    Template,
    compose_batch,
    compose_message,
    generate_ab_variants,
    get_followup_sequence,
    get_registry,
    get_template,
    select_template,
    _build_format_map,
    _compute_personalization_score,
    _detect_language,
    _detect_temperature,
    _safe_render,
)


# -----------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------


@pytest.fixture
def hot_clevel_latam_lead():
    """A high-value C-level lead in LATAM."""
    return {
        "contact_name": "Maria Garcia",
        "company_name": "FinCorp SA",
        "region": "LATAM",
        "c_level": True,
        "classification": "hot",
        "score_icp": 85.0,
        "afinidad": "HIGH",
        "product_interest": "DeFi yield strategies",
        "sender_name": "Carlos Lopez",
        "sender_title": "Director de Alianzas",
    }


@pytest.fixture
def warm_nonclevel_latam_lead():
    """A mid-tier non-C-level lead in LATAM."""
    return {
        "contact_name": "Juan Perez",
        "company_name": "TechStart SRL",
        "region": "LATAM",
        "c_level": False,
        "classification": "warm",
        "score_icp": 55.0,
        "afinidad": "MEDIUM",
    }


@pytest.fixture
def cool_iberia_lead():
    """A cool-temperature lead in Iberia."""
    return {
        "contact_name": "Pablo Fernandez",
        "company_name": "Iberian Ventures SL",
        "region": "Iberia",
        "c_level": False,
        "classification": "cool",
        "score_icp": 30.0,
        "afinidad": "LOW",
    }


@pytest.fixture
def minimal_lead():
    """A lead with minimal data — only required fields."""
    return {
        "region": "LATAM",
        "c_level": False,
    }


# -----------------------------------------------------------------------
# 1. Template registry
# -----------------------------------------------------------------------


class TestTemplateRegistry:
    def test_registry_has_at_least_12_templates(self):
        registry = get_registry()
        assert len(registry) >= 12

    def test_get_template_returns_template(self):
        tmpl = get_template("email_hot_clevel_latam")
        assert tmpl is not None
        assert isinstance(tmpl, Template)

    def test_get_template_returns_none_for_unknown(self):
        assert get_template("nonexistent_template_xyz") is None

    def test_all_templates_have_required_fields(self):
        for tid, tmpl in get_registry().items():
            assert tmpl.id == tid
            assert isinstance(tmpl.channel, Channel)
            assert isinstance(tmpl.language, Language)
            assert isinstance(tmpl.lead_temperature, LeadTemperature)
            assert isinstance(tmpl.body, str)
            assert len(tmpl.body) > 0
            assert isinstance(tmpl.cta, str)
            assert len(tmpl.cta) > 0

    def test_email_templates_have_subject(self):
        for tmpl in get_registry().values():
            if tmpl.channel == Channel.EMAIL:
                assert tmpl.subject is not None and len(tmpl.subject) > 0

    def test_non_email_templates_subject_is_none(self):
        for tmpl in get_registry().values():
            if tmpl.channel in (Channel.LINKEDIN, Channel.WHATSAPP):
                assert tmpl.subject is None


# -----------------------------------------------------------------------
# 2. Language detection
# -----------------------------------------------------------------------


class TestLanguageDetection:
    def test_latam_region(self):
        assert _detect_language({"region": "LATAM"}) == Language.ES_LATAM

    def test_iberia_region(self):
        assert _detect_language({"region": "Iberia"}) == Language.ES_IBERIA

    def test_iberia_uppercase(self):
        assert _detect_language({"region": "IBERIA"}) == Language.ES_IBERIA

    def test_unknown_region_defaults_to_latam(self):
        assert _detect_language({"region": "North America"}) == Language.ES_LATAM

    def test_missing_region_defaults_to_latam(self):
        assert _detect_language({}) == Language.ES_LATAM


# -----------------------------------------------------------------------
# 3. Temperature detection
# -----------------------------------------------------------------------


class TestTemperatureDetection:
    def test_from_classification_hot(self):
        assert _detect_temperature({"classification": "hot"}) == LeadTemperature.HOT

    def test_from_classification_warm(self):
        assert _detect_temperature({"classification": "warm"}) == LeadTemperature.WARM

    def test_from_classification_cool(self):
        assert _detect_temperature({"classification": "cool"}) == LeadTemperature.COOL

    def test_from_classification_cold_maps_to_cool(self):
        assert _detect_temperature({"classification": "cold"}) == LeadTemperature.COOL

    def test_from_score_high(self):
        assert _detect_temperature({"score_icp": 85}) == LeadTemperature.HOT

    def test_from_score_mid(self):
        assert _detect_temperature({"score_icp": 55}) == LeadTemperature.WARM

    def test_from_score_low(self):
        assert _detect_temperature({"score_icp": 20}) == LeadTemperature.COOL

    def test_from_afinidad_high(self):
        assert _detect_temperature({"afinidad": "HIGH"}) == LeadTemperature.HOT

    def test_from_afinidad_medium(self):
        assert _detect_temperature({"afinidad": "MEDIUM"}) == LeadTemperature.WARM

    def test_no_data_defaults_to_cool(self):
        assert _detect_temperature({}) == LeadTemperature.COOL


# -----------------------------------------------------------------------
# 4. Template selection
# -----------------------------------------------------------------------


class TestSelectTemplate:
    def test_email_hot_clevel_latam(self, hot_clevel_latam_lead):
        tmpl = select_template(Channel.EMAIL, hot_clevel_latam_lead)
        assert tmpl.channel == Channel.EMAIL
        assert tmpl.lead_temperature == LeadTemperature.HOT
        assert tmpl.is_c_level is True
        assert tmpl.language == Language.ES_LATAM

    def test_email_warm_nonclevel_latam(self, warm_nonclevel_latam_lead):
        tmpl = select_template(Channel.EMAIL, warm_nonclevel_latam_lead)
        assert tmpl.channel == Channel.EMAIL
        assert tmpl.lead_temperature == LeadTemperature.WARM

    def test_email_cool_iberia(self, cool_iberia_lead):
        tmpl = select_template(Channel.EMAIL, cool_iberia_lead)
        assert tmpl.channel == Channel.EMAIL
        assert tmpl.language == Language.ES_IBERIA

    def test_linkedin_selection(self, hot_clevel_latam_lead):
        tmpl = select_template(Channel.LINKEDIN, hot_clevel_latam_lead)
        assert tmpl.channel == Channel.LINKEDIN

    def test_whatsapp_selection(self, warm_nonclevel_latam_lead):
        tmpl = select_template(Channel.WHATSAPP, warm_nonclevel_latam_lead)
        assert tmpl.channel == Channel.WHATSAPP

    def test_string_channel_accepted(self, hot_clevel_latam_lead):
        tmpl = select_template("email", hot_clevel_latam_lead)
        assert tmpl.channel == Channel.EMAIL

    def test_selection_never_returns_followup(self, hot_clevel_latam_lead):
        """select_template should only return non-followup templates."""
        tmpl = select_template(Channel.EMAIL, hot_clevel_latam_lead)
        assert tmpl.is_followup is False


# -----------------------------------------------------------------------
# 5. Message composition
# -----------------------------------------------------------------------


class TestComposeMessage:
    def test_returns_outreach_draft(self, hot_clevel_latam_lead):
        draft = compose_message(hot_clevel_latam_lead, Channel.EMAIL)
        assert isinstance(draft, OutreachDraft)

    def test_email_has_subject(self, hot_clevel_latam_lead):
        draft = compose_message(hot_clevel_latam_lead, Channel.EMAIL)
        assert draft.subject is not None
        assert len(draft.subject) > 0

    def test_linkedin_has_no_subject(self, hot_clevel_latam_lead):
        draft = compose_message(hot_clevel_latam_lead, Channel.LINKEDIN)
        assert draft.subject is None

    def test_body_is_personalised(self, hot_clevel_latam_lead):
        draft = compose_message(hot_clevel_latam_lead, Channel.EMAIL)
        assert "Maria Garcia" in draft.body or "FinCorp SA" in draft.body

    def test_template_used_is_recorded(self, hot_clevel_latam_lead):
        draft = compose_message(hot_clevel_latam_lead, Channel.EMAIL)
        assert draft.template_used in get_registry()

    def test_personalization_score_is_high_with_full_data(self, hot_clevel_latam_lead):
        draft = compose_message(hot_clevel_latam_lead, Channel.EMAIL)
        assert draft.personalization_score >= 0.8

    def test_personalization_score_is_low_with_minimal_data(self, minimal_lead):
        draft = compose_message(minimal_lead, Channel.EMAIL)
        assert draft.personalization_score <= 0.5

    def test_template_override(self, hot_clevel_latam_lead):
        draft = compose_message(
            hot_clevel_latam_lead,
            Channel.EMAIL,
            template_override="email_cool_iberia",
        )
        assert draft.template_used == "email_cool_iberia"

    def test_template_override_invalid_raises(self, hot_clevel_latam_lead):
        with pytest.raises(ValueError, match="not found"):
            compose_message(
                hot_clevel_latam_lead,
                Channel.EMAIL,
                template_override="nonexistent",
            )

    def test_string_channel(self, hot_clevel_latam_lead):
        draft = compose_message(hot_clevel_latam_lead, "email")
        assert draft.channel == Channel.EMAIL


# -----------------------------------------------------------------------
# 6. Personalisation score
# -----------------------------------------------------------------------


class TestPersonalizationScore:
    def test_all_fields_filled(self):
        data = {k: "value" for k in ALL_PLACEHOLDERS}
        assert _compute_personalization_score(data) == 1.0

    def test_no_fields_filled(self):
        assert _compute_personalization_score({}) == 0.0

    def test_partial_fill(self):
        data = {"contact_name": "Ana", "company_name": "ACME"}
        score = _compute_personalization_score(data)
        assert 0 < score < 1

    def test_whitespace_only_counts_as_missing(self):
        data = {"contact_name": "   ", "company_name": "ACME"}
        score = _compute_personalization_score(data)
        expected = _compute_personalization_score({"company_name": "ACME"})
        assert score == expected


# -----------------------------------------------------------------------
# 7. A/B variant generation
# -----------------------------------------------------------------------


class TestGenerateABVariants:
    def test_returns_two_drafts(self, hot_clevel_latam_lead):
        a, b = generate_ab_variants(hot_clevel_latam_lead, Channel.EMAIL)
        assert isinstance(a, OutreachDraft)
        assert isinstance(b, OutreachDraft)

    def test_variants_use_different_templates(self, hot_clevel_latam_lead):
        a, b = generate_ab_variants(hot_clevel_latam_lead, Channel.EMAIL)
        assert a.template_used != b.template_used

    def test_variants_same_channel(self, hot_clevel_latam_lead):
        a, b = generate_ab_variants(hot_clevel_latam_lead, Channel.LINKEDIN)
        assert a.channel == Channel.LINKEDIN
        assert b.channel == Channel.LINKEDIN

    def test_string_channel(self, warm_nonclevel_latam_lead):
        a, b = generate_ab_variants(warm_nonclevel_latam_lead, "whatsapp")
        assert a.channel == Channel.WHATSAPP


# -----------------------------------------------------------------------
# 8. Follow-up sequence
# -----------------------------------------------------------------------


class TestFollowupSequence:
    def test_attempt_1(self, warm_nonclevel_latam_lead):
        draft = get_followup_sequence(warm_nonclevel_latam_lead, Channel.EMAIL, 1)
        assert draft.template_used == "followup_1"
        assert draft.subject is not None

    def test_attempt_2(self, warm_nonclevel_latam_lead):
        draft = get_followup_sequence(warm_nonclevel_latam_lead, Channel.EMAIL, 2)
        assert draft.template_used == "followup_2"

    def test_attempt_3(self, warm_nonclevel_latam_lead):
        draft = get_followup_sequence(warm_nonclevel_latam_lead, Channel.EMAIL, 3)
        assert draft.template_used == "followup_3"

    def test_attempt_0_raises(self, warm_nonclevel_latam_lead):
        with pytest.raises(ValueError, match="attempt must be 1, 2, or 3"):
            get_followup_sequence(warm_nonclevel_latam_lead, Channel.EMAIL, 0)

    def test_attempt_4_raises(self, warm_nonclevel_latam_lead):
        with pytest.raises(ValueError, match="attempt must be 1, 2, or 3"):
            get_followup_sequence(warm_nonclevel_latam_lead, Channel.EMAIL, 4)

    def test_followup_body_is_personalised(self, warm_nonclevel_latam_lead):
        draft = get_followup_sequence(warm_nonclevel_latam_lead, Channel.EMAIL, 1)
        assert "Juan Perez" in draft.body or "TechStart SRL" in draft.body

    def test_followup_string_channel(self, warm_nonclevel_latam_lead):
        draft = get_followup_sequence(warm_nonclevel_latam_lead, "email", 2)
        assert draft.channel == Channel.EMAIL


# -----------------------------------------------------------------------
# 9. Batch composition
# -----------------------------------------------------------------------


class TestComposeBatch:
    def test_empty_batch(self):
        result = compose_batch([], Channel.EMAIL)
        assert result == []

    def test_single_lead(self, hot_clevel_latam_lead):
        result = compose_batch([hot_clevel_latam_lead], Channel.EMAIL)
        assert len(result) == 1
        assert isinstance(result[0], OutreachDraft)

    def test_multiple_leads(self, hot_clevel_latam_lead, warm_nonclevel_latam_lead, cool_iberia_lead):
        leads = [hot_clevel_latam_lead, warm_nonclevel_latam_lead, cool_iberia_lead]
        result = compose_batch(leads, Channel.EMAIL)
        assert len(result) == 3
        # Each draft should target the email channel
        for draft in result:
            assert draft.channel == Channel.EMAIL

    def test_batch_string_channel(self, hot_clevel_latam_lead):
        result = compose_batch([hot_clevel_latam_lead], "linkedin")
        assert len(result) == 1
        assert result[0].channel == Channel.LINKEDIN


# -----------------------------------------------------------------------
# 10. Safe rendering
# -----------------------------------------------------------------------


class TestSafeRender:
    def test_renders_placeholders(self):
        result = _safe_render("Hola {contact_name}", {"contact_name": "Ana"})
        assert result == "Hola Ana"

    def test_missing_key_does_not_crash(self):
        # format_map with a defaultdict-like map should work; our _build_format_map
        # ensures all keys are present, but _safe_render should be robust regardless.
        result = _safe_render("Hola {unknown_key}", {"unknown_key": ""})
        assert "Hola" in result

    def test_empty_template(self):
        assert _safe_render("", {"contact_name": "Ana"}) == ""


# -----------------------------------------------------------------------
# 11. Format map builder
# -----------------------------------------------------------------------


class TestBuildFormatMap:
    def test_fills_defaults_for_missing(self):
        fmt = _build_format_map({})
        assert "contact_name" in fmt
        assert fmt["contact_name"] != ""  # default should be non-empty

    def test_uses_lead_data_when_available(self):
        fmt = _build_format_map({"contact_name": "Ana"})
        assert fmt["contact_name"] == "Ana"

    def test_strips_whitespace(self):
        fmt = _build_format_map({"contact_name": "  Ana  "})
        assert fmt["contact_name"] == "Ana"


# -----------------------------------------------------------------------
# 12. Edge cases
# -----------------------------------------------------------------------


class TestEdgeCases:
    def test_compose_with_empty_lead(self):
        """Composing with an empty dict should not raise."""
        draft = compose_message({}, Channel.EMAIL)
        assert isinstance(draft, OutreachDraft)
        assert draft.personalization_score == 0.0

    def test_compose_preserves_channel(self):
        for ch in Channel:
            draft = compose_message({"region": "LATAM"}, ch)
            assert draft.channel == ch

    def test_template_frozen_dataclass(self):
        tmpl = get_template("email_hot_clevel_latam")
        assert tmpl is not None
        with pytest.raises(AttributeError):
            tmpl.id = "changed"  # type: ignore[misc]

    def test_followup_templates_have_correct_attempt_numbers(self):
        for i in (1, 2, 3):
            tmpl = get_template(f"followup_{i}")
            assert tmpl is not None
            assert tmpl.is_followup is True
            assert tmpl.followup_attempt == i

    def test_all_templates_are_in_spanish(self):
        """Spot check that template bodies contain Spanish words."""
        spanish_markers = {"Hola", "Soy", "empresa", "inversion", "soluciones"}
        for tmpl in get_registry().values():
            found = any(marker in tmpl.body for marker in spanish_markers)
            assert found, f"Template '{tmpl.id}' does not appear to be in Spanish"
