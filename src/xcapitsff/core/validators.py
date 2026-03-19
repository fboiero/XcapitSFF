"""Comprehensive data validation and sanitization for XcapitSFF entities.

Provides validation functions for leads, tickets, customers, and common fields
like email addresses. Also includes text sanitization to strip potentially
dangerous content and normalise whitespace.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ValidationError:
    """Single validation error tied to a specific field."""

    field: str
    value: object
    message: str


@dataclass
class ValidationResult:
    """Aggregate result of validating an entity."""

    is_valid: bool = True
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, field_name: str, value: object, message: str) -> None:
        self.errors.append(ValidationError(field=field_name, value=value, message=message))
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Accepted values — kept in sync with xcapitsff.core.models enums.
VALID_REGIONS = {"LATAM", "Iberia"}
VALID_AFINIDAD = {"HIGH", "MEDIUM", "LOW"}
VALID_PRIORITIES = {"low", "medium", "high", "urgent"}
VALID_TICKET_STATUSES = {"open", "in_progress", "waiting_customer", "resolved", "closed"}
VALID_LEAD_STAGES = {
    "raw", "qualified", "contacted", "meeting",
    "proposal", "negotiation", "won", "lost",
}

# RFC-5322 simplified email regex — intentionally permissive but catches the
# most common formatting mistakes.
_EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+"
    r"@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
)

# Patterns commonly associated with XSS / HTML injection.
_XSS_PATTERNS = [
    re.compile(r"<script\b[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),
    re.compile(r"<\s*/?\s*script\b", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"on\w+\s*=", re.IGNORECASE),
    re.compile(r"<\s*iframe\b[^>]*>", re.IGNORECASE),
    re.compile(r"<\s*object\b[^>]*>", re.IGNORECASE),
    re.compile(r"<\s*embed\b[^>]*>", re.IGNORECASE),
    re.compile(r"<\s*img\b[^>]*\bonerror\b", re.IGNORECASE),
]

TICKET_SUBJECT_MAX_LENGTH = 500

# ---------------------------------------------------------------------------
# Email validation
# ---------------------------------------------------------------------------


def validate_email(email: str) -> tuple[bool, str | None]:
    """Validate an email address.

    Returns ``(True, None)`` when the email is valid, or
    ``(False, error_message)`` otherwise.
    """
    if not email or not email.strip():
        return False, "Email must not be empty"

    email = email.strip()

    if len(email) > 254:
        return False, "Email exceeds maximum length of 254 characters"

    if not _EMAIL_RE.match(email):
        return False, f"Invalid email format: {email}"

    # Basic structural checks
    local, _, domain = email.rpartition("@")
    if len(local) > 64:
        return False, "Local part of email exceeds 64 characters"

    if ".." in domain:
        return False, "Domain contains consecutive dots"

    return True, None


# ---------------------------------------------------------------------------
# Lead validation
# ---------------------------------------------------------------------------


def validate_lead(data: dict) -> ValidationResult:
    """Validate a lead dictionary before import or creation.

    Checks:
    - ``region`` must be a recognised value.
    - ``score_icp`` must be in [0, 100] when present.
    - ``afinidad`` must be HIGH / MEDIUM / LOW.
    - ``contact_email`` must be a valid email when present.
    - ``company_name`` should not be only whitespace.
    """
    result = ValidationResult()

    # region
    region = data.get("region")
    if region is not None:
        region_str = str(region.value) if hasattr(region, "value") else str(region)
        if region_str not in VALID_REGIONS:
            result.add_error("region", region, f"Invalid region '{region}'. Must be one of: {', '.join(sorted(VALID_REGIONS))}")
    else:
        result.add_warning("No region specified; will default to LATAM")

    # score_icp
    score = data.get("score_icp")
    if score is not None:
        try:
            score_val = float(score)
            if score_val < 0 or score_val > 100:
                result.add_error("score_icp", score, "ICP score must be between 0 and 100")
        except (TypeError, ValueError):
            result.add_error("score_icp", score, "ICP score must be a number")

    # afinidad
    afinidad = data.get("afinidad")
    if afinidad is not None:
        afinidad_str = str(afinidad.value) if hasattr(afinidad, "value") else str(afinidad)
        if afinidad_str.upper() not in VALID_AFINIDAD:
            result.add_error(
                "afinidad", afinidad,
                f"Invalid afinidad '{afinidad}'. Must be one of: {', '.join(sorted(VALID_AFINIDAD))}",
            )
    else:
        result.add_warning("No afinidad specified; will default to MEDIUM")

    # contact_email
    email = data.get("contact_email")
    if email is not None and str(email).strip():
        is_valid, err = validate_email(str(email))
        if not is_valid:
            result.add_error("contact_email", email, err or "Invalid email")

    # company_name
    company = data.get("company_name")
    if company is not None:
        if isinstance(company, str) and not company.strip():
            result.add_error("company_name", company, "Company name must not be empty or whitespace only")
    else:
        result.add_warning("No company name provided")

    # contact_name — optional soft check
    contact_name = data.get("contact_name")
    if contact_name is None and email is None:
        result.add_warning(
            "Lead has neither contact_name nor contact_email; it may be difficult to follow up"
        )

    return result


# ---------------------------------------------------------------------------
# Ticket validation
# ---------------------------------------------------------------------------


def validate_ticket(data: dict) -> ValidationResult:
    """Validate ticket data before creation.

    Checks:
    - ``subject`` must be non-empty and at most 500 characters.
    - ``description`` must be non-empty.
    - ``priority`` must be a valid priority value.
    - ``customer_id`` must be a positive integer.
    """
    result = ValidationResult()

    # subject
    subject = data.get("subject")
    if subject is None or (isinstance(subject, str) and not subject.strip()):
        result.add_error("subject", subject, "Subject must not be empty")
    elif isinstance(subject, str) and len(subject) > TICKET_SUBJECT_MAX_LENGTH:
        result.add_error(
            "subject", subject[:50] + "...",
            f"Subject exceeds maximum length of {TICKET_SUBJECT_MAX_LENGTH} characters",
        )

    # description
    description = data.get("description")
    if description is None or (isinstance(description, str) and not description.strip()):
        result.add_error("description", description, "Description must not be empty")

    # priority
    priority = data.get("priority")
    if priority is not None:
        priority_str = str(priority.value) if hasattr(priority, "value") else str(priority)
        if priority_str.lower() not in VALID_PRIORITIES:
            result.add_error(
                "priority", priority,
                f"Invalid priority '{priority}'. Must be one of: {', '.join(sorted(VALID_PRIORITIES))}",
            )

    # customer_id
    customer_id = data.get("customer_id")
    if customer_id is None:
        result.add_error("customer_id", customer_id, "customer_id is required")
    else:
        try:
            cid = int(customer_id)
            if cid <= 0:
                result.add_error("customer_id", customer_id, "customer_id must be a positive integer")
        except (TypeError, ValueError):
            result.add_error("customer_id", customer_id, "customer_id must be a positive integer")

    # category — optional but warn when absent
    if data.get("category") is None:
        result.add_warning("No category provided; ticket will need manual classification")

    return result


# ---------------------------------------------------------------------------
# Customer validation
# ---------------------------------------------------------------------------


def validate_customer(data: dict) -> ValidationResult:
    """Validate customer data before creation.

    Checks:
    - ``company_name`` must be non-empty.
    - ``contact_name`` must be non-empty.
    - ``contact_email`` must be a valid email.
    - ``region`` must be a valid region if present.
    - ``plan`` should be non-empty if provided.
    """
    result = ValidationResult()

    # company_name
    company = data.get("company_name")
    if company is None or (isinstance(company, str) and not company.strip()):
        result.add_error("company_name", company, "Company name is required and must not be empty")

    # contact_name
    name = data.get("contact_name")
    if name is None or (isinstance(name, str) and not name.strip()):
        result.add_error("contact_name", name, "Contact name is required and must not be empty")

    # contact_email
    email = data.get("contact_email")
    if email is None or (isinstance(email, str) and not email.strip()):
        result.add_error("contact_email", email, "Contact email is required")
    else:
        is_valid, err = validate_email(str(email))
        if not is_valid:
            result.add_error("contact_email", email, err or "Invalid email")

    # region (optional — defaults on model)
    region = data.get("region")
    if region is not None:
        region_str = str(region.value) if hasattr(region, "value") else str(region)
        if region_str not in VALID_REGIONS:
            result.add_error(
                "region", region,
                f"Invalid region '{region}'. Must be one of: {', '.join(sorted(VALID_REGIONS))}",
            )

    # plan — warn if empty string
    plan = data.get("plan")
    if plan is not None and isinstance(plan, str) and not plan.strip():
        result.add_warning("Plan is provided but empty; consider setting to None instead")

    return result


# ---------------------------------------------------------------------------
# Text sanitization
# ---------------------------------------------------------------------------


def sanitize_text(text: str) -> str:
    """Strip XSS-like patterns and normalise whitespace.

    * Removes ``<script>`` blocks, event-handler attributes, ``javascript:``
      URIs, and dangerous HTML tags (``iframe``, ``object``, ``embed``).
    * Collapses consecutive whitespace to a single space.
    * Strips leading/trailing whitespace.
    """
    if not text:
        return text

    cleaned = text
    for pattern in _XSS_PATTERNS:
        cleaned = pattern.sub("", cleaned)

    # Strip remaining HTML tags as a final safety net
    cleaned = re.sub(r"<[^>]+>", "", cleaned)

    # Normalise whitespace
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()
