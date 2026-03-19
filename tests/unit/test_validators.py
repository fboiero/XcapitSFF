"""Tests for xcapitsff.core.validators — data validation and sanitisation.

Covers:
- validate_email
- validate_lead
- validate_ticket
- validate_customer
- sanitize_text
- ValidationResult / ValidationError dataclasses
"""

import pytest

from xcapitsff.core.validators import (
    ValidationError,
    ValidationResult,
    validate_customer,
    validate_email,
    validate_lead,
    validate_ticket,
    sanitize_text,
)


# -----------------------------------------------------------------------
# 1. validate_email
# -----------------------------------------------------------------------


class TestValidateEmail:
    def test_valid_simple(self):
        ok, err = validate_email("user@example.com")
        assert ok is True
        assert err is None

    def test_valid_with_subdomain(self):
        ok, err = validate_email("user@mail.example.co.uk")
        assert ok is True
        assert err is None

    def test_valid_with_plus(self):
        ok, err = validate_email("user+tag@example.com")
        assert ok is True

    def test_empty_string(self):
        ok, err = validate_email("")
        assert ok is False
        assert err is not None

    def test_whitespace_only(self):
        ok, err = validate_email("   ")
        assert ok is False

    def test_missing_at(self):
        ok, err = validate_email("userexample.com")
        assert ok is False

    def test_missing_domain(self):
        ok, err = validate_email("user@")
        assert ok is False

    def test_consecutive_dots_in_domain(self):
        ok, err = validate_email("user@example..com")
        assert ok is False
        assert err is not None

    def test_too_long(self):
        long_email = "a" * 65 + "@" + "b" * 190 + ".com"
        ok, err = validate_email(long_email)
        assert ok is False

    def test_leading_trailing_whitespace_stripped(self):
        ok, err = validate_email("  user@example.com  ")
        assert ok is True


# -----------------------------------------------------------------------
# 2. validate_lead
# -----------------------------------------------------------------------


class TestValidateLead:
    def test_valid_lead(self):
        data = {
            "company_name": "Acme Corp",
            "contact_email": "john@acme.com",
            "region": "LATAM",
            "afinidad": "HIGH",
            "score_icp": 75.0,
        }
        result = validate_lead(data)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_invalid_region(self):
        data = {"region": "ANTARCTICA", "afinidad": "HIGH"}
        result = validate_lead(data)
        assert result.is_valid is False
        assert any(e.field == "region" for e in result.errors)

    def test_score_icp_out_of_range_high(self):
        data = {"region": "LATAM", "afinidad": "HIGH", "score_icp": 150}
        result = validate_lead(data)
        assert result.is_valid is False
        assert any(e.field == "score_icp" for e in result.errors)

    def test_score_icp_out_of_range_negative(self):
        data = {"region": "LATAM", "afinidad": "HIGH", "score_icp": -5}
        result = validate_lead(data)
        assert result.is_valid is False

    def test_score_icp_non_numeric(self):
        data = {"region": "LATAM", "afinidad": "HIGH", "score_icp": "abc"}
        result = validate_lead(data)
        assert result.is_valid is False

    def test_invalid_afinidad(self):
        data = {"region": "LATAM", "afinidad": "EXTREME"}
        result = validate_lead(data)
        assert result.is_valid is False
        assert any(e.field == "afinidad" for e in result.errors)

    def test_whitespace_company_name(self):
        data = {"region": "LATAM", "afinidad": "HIGH", "company_name": "   "}
        result = validate_lead(data)
        assert result.is_valid is False
        assert any(e.field == "company_name" for e in result.errors)

    def test_invalid_email(self):
        data = {"region": "LATAM", "afinidad": "HIGH", "contact_email": "not-an-email"}
        result = validate_lead(data)
        assert result.is_valid is False
        assert any(e.field == "contact_email" for e in result.errors)

    def test_warnings_for_missing_optional_fields(self):
        data = {"company_name": "Acme Corp"}
        result = validate_lead(data)
        # Should warn about missing region and afinidad
        assert len(result.warnings) > 0

    def test_score_icp_at_boundaries(self):
        for boundary_val in (0, 100, 50):
            data = {"region": "LATAM", "afinidad": "HIGH", "score_icp": boundary_val}
            result = validate_lead(data)
            assert not any(e.field == "score_icp" for e in result.errors)

    def test_iberia_region_valid(self):
        data = {"region": "Iberia", "afinidad": "MEDIUM"}
        result = validate_lead(data)
        assert not any(e.field == "region" for e in result.errors)

    def test_enum_region_value(self):
        """Passing an enum-like object with .value should work."""
        from xcapitsff.core.models import Region
        data = {"region": Region.LATAM, "afinidad": "HIGH"}
        result = validate_lead(data)
        assert not any(e.field == "region" for e in result.errors)


# -----------------------------------------------------------------------
# 3. validate_ticket
# -----------------------------------------------------------------------


class TestValidateTicket:
    def test_valid_ticket(self):
        data = {
            "subject": "Cannot login",
            "description": "I am locked out of my account.",
            "priority": "high",
            "customer_id": 1,
        }
        result = validate_ticket(data)
        assert result.is_valid is True

    def test_empty_subject(self):
        data = {"subject": "", "description": "details", "priority": "low", "customer_id": 1}
        result = validate_ticket(data)
        assert result.is_valid is False
        assert any(e.field == "subject" for e in result.errors)

    def test_subject_too_long(self):
        data = {
            "subject": "x" * 501,
            "description": "details",
            "priority": "low",
            "customer_id": 1,
        }
        result = validate_ticket(data)
        assert result.is_valid is False
        assert any(e.field == "subject" for e in result.errors)

    def test_empty_description(self):
        data = {"subject": "Help", "description": "", "priority": "low", "customer_id": 1}
        result = validate_ticket(data)
        assert result.is_valid is False
        assert any(e.field == "description" for e in result.errors)

    def test_invalid_priority(self):
        data = {
            "subject": "Help",
            "description": "Details",
            "priority": "ASAP",
            "customer_id": 1,
        }
        result = validate_ticket(data)
        assert result.is_valid is False
        assert any(e.field == "priority" for e in result.errors)

    def test_negative_customer_id(self):
        data = {
            "subject": "Help",
            "description": "Details",
            "priority": "low",
            "customer_id": -1,
        }
        result = validate_ticket(data)
        assert result.is_valid is False
        assert any(e.field == "customer_id" for e in result.errors)

    def test_missing_customer_id(self):
        data = {"subject": "Help", "description": "Details", "priority": "low"}
        result = validate_ticket(data)
        assert result.is_valid is False
        assert any(e.field == "customer_id" for e in result.errors)

    def test_no_category_warning(self):
        data = {
            "subject": "Help",
            "description": "Details",
            "priority": "medium",
            "customer_id": 1,
        }
        result = validate_ticket(data)
        assert any("category" in w.lower() for w in result.warnings)

    def test_valid_with_enum_priority(self):
        from xcapitsff.core.models import TicketPriority
        data = {
            "subject": "Help",
            "description": "Details",
            "priority": TicketPriority.URGENT,
            "customer_id": 1,
        }
        result = validate_ticket(data)
        assert not any(e.field == "priority" for e in result.errors)


# -----------------------------------------------------------------------
# 4. validate_customer
# -----------------------------------------------------------------------


class TestValidateCustomer:
    def test_valid_customer(self):
        data = {
            "company_name": "Acme Corp",
            "contact_name": "Jane Doe",
            "contact_email": "jane@acme.com",
            "region": "LATAM",
        }
        result = validate_customer(data)
        assert result.is_valid is True

    def test_missing_company_name(self):
        data = {"contact_name": "Jane", "contact_email": "jane@acme.com"}
        result = validate_customer(data)
        assert result.is_valid is False
        assert any(e.field == "company_name" for e in result.errors)

    def test_missing_contact_name(self):
        data = {"company_name": "Acme", "contact_email": "jane@acme.com"}
        result = validate_customer(data)
        assert result.is_valid is False
        assert any(e.field == "contact_name" for e in result.errors)

    def test_missing_contact_email(self):
        data = {"company_name": "Acme", "contact_name": "Jane"}
        result = validate_customer(data)
        assert result.is_valid is False
        assert any(e.field == "contact_email" for e in result.errors)

    def test_invalid_email(self):
        data = {
            "company_name": "Acme",
            "contact_name": "Jane",
            "contact_email": "not-valid",
        }
        result = validate_customer(data)
        assert result.is_valid is False

    def test_invalid_region(self):
        data = {
            "company_name": "Acme",
            "contact_name": "Jane",
            "contact_email": "jane@acme.com",
            "region": "MARS",
        }
        result = validate_customer(data)
        assert result.is_valid is False
        assert any(e.field == "region" for e in result.errors)


# -----------------------------------------------------------------------
# 5. sanitize_text
# -----------------------------------------------------------------------


class TestSanitizeText:
    def test_removes_script_tags(self):
        text = 'Hello <script>alert("xss")</script> World'
        assert "<script" not in sanitize_text(text)
        assert "alert" not in sanitize_text(text)

    def test_removes_event_handlers(self):
        text = '<img onerror="alert(1)" src=x>'
        cleaned = sanitize_text(text)
        assert "onerror" not in cleaned

    def test_removes_javascript_uri(self):
        text = '<a href="javascript:alert(1)">click</a>'
        cleaned = sanitize_text(text)
        assert "javascript:" not in cleaned.lower()

    def test_normalises_whitespace(self):
        text = "  hello   world  \n\t foo  "
        assert sanitize_text(text) == "hello world foo"

    def test_empty_string(self):
        assert sanitize_text("") == ""

    def test_plain_text_unchanged(self):
        text = "This is perfectly normal text."
        assert sanitize_text(text) == text

    def test_removes_iframe(self):
        text = 'before <iframe src="evil.com"></iframe> after'
        cleaned = sanitize_text(text)
        assert "iframe" not in cleaned.lower()


# -----------------------------------------------------------------------
# 6. Dataclass behaviour
# -----------------------------------------------------------------------


class TestDataclasses:
    def test_validation_error_is_frozen(self):
        ve = ValidationError(field="name", value="x", message="bad")
        with pytest.raises(AttributeError):
            ve.field = "changed"  # type: ignore[misc]

    def test_validation_result_add_error(self):
        vr = ValidationResult()
        assert vr.is_valid is True
        vr.add_error("f", "v", "msg")
        assert vr.is_valid is False
        assert len(vr.errors) == 1

    def test_validation_result_add_warning(self):
        vr = ValidationResult()
        vr.add_warning("Watch out")
        assert vr.is_valid is True
        assert len(vr.warnings) == 1

    def test_multiple_errors_accumulate(self):
        vr = ValidationResult()
        vr.add_error("a", 1, "err1")
        vr.add_error("b", 2, "err2")
        assert len(vr.errors) == 2
        assert vr.is_valid is False
