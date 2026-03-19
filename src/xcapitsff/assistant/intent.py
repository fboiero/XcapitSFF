"""Intent recognition engine for the conversational assistant.

Detects user intent from Spanish natural language using keyword and
pattern matching, and extracts structured entities (IDs, emails,
company references) from the input text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class Intent(Enum):
    """All possible user intents the assistant can handle."""

    GREETING = "greeting"
    HELP = "help"
    CREATE_LEAD = "create_lead"
    LIST_LEADS = "list_leads"
    QUALIFY_LEAD = "qualify_lead"
    SEARCH = "search"
    VIEW_PIPELINE = "view_pipeline"
    VIEW_DASHBOARD = "view_dashboard"
    CREATE_TICKET = "create_ticket"
    LIST_TICKETS = "list_tickets"
    VIEW_TICKET = "view_ticket"
    COMPOSE_OUTREACH = "compose_outreach"
    IMPORT_DATA = "import_data"
    EXPORT_DATA = "export_data"
    VIEW_ANALYTICS = "view_analytics"
    VIEW_HEALTH_SCORE = "view_health_score"
    CONFIGURE_SETTINGS = "configure_settings"
    START_CAMPAIGN = "start_campaign"
    VIEW_CAMPAIGNS = "view_campaigns"
    SCHEDULE_MEETING = "schedule_meeting"
    VIEW_KANBAN = "view_kanban"
    SEARCH_KB = "search_kb"
    CREATE_KB_ARTICLE = "create_kb_article"
    VIEW_CUSTOMER = "view_customer"
    VIEW_PREDICTIONS = "view_predictions"
    RUN_AUTOMATION = "run_automation"
    UNKNOWN = "unknown"


@dataclass
class IntentMatch:
    """Result of intent recognition on a user message."""

    intent: Intent
    confidence: float
    extracted_params: dict = field(default_factory=dict)
    original_text: str = ""


# ---------------------------------------------------------------------------
# Pattern definitions: each entry maps a compiled regex to an Intent and a
# base confidence score.  Patterns are evaluated in order; the first match
# with the highest confidence wins.
# ---------------------------------------------------------------------------

_INTENT_PATTERNS: list[tuple[re.Pattern[str], Intent, float]] = [
    # --- Greeting ---
    (re.compile(r"\b(hola|buenos\s*d[ií]as|buenas\s*(tardes|noches)?|hey|saludos|qu[eé]\s*tal)\b", re.I), Intent.GREETING, 0.95),

    # --- Help ---
    (re.compile(r"\b(ayuda|c[oó]mo|qu[eé]\s*puedo|help|opciones|funciones|qu[eé]\s*hac[eé]s)\b", re.I), Intent.HELP, 0.90),

    # --- Create Lead ---
    (re.compile(r"\b(crear\s*(un\s*)?lead|nuevo\s*lead|agregar\s*(un\s*)?prospecto|a[nñ]adir\s*(un\s*)?lead|registrar\s*(un\s*)?lead)\b", re.I), Intent.CREATE_LEAD, 0.95),

    # --- List Leads ---
    (re.compile(r"\b(ver\s*leads|listar\s*leads|mostrar\s*leads|mis\s*leads|todos\s*los\s*leads)\b", re.I), Intent.LIST_LEADS, 0.90),

    # --- Qualify Lead ---
    (re.compile(r"\b(calificar|scoring|puntuar|evaluar\s*(lead|prospecto)|score\s*(del?\s*)?lead)\b", re.I), Intent.QUALIFY_LEAD, 0.90),

    # --- View Kanban / Pipeline ---
    (re.compile(r"\b(ver\s*(el\s*)?pipeline|mostrar\s*(el\s*)?embudo|kanban|tablero\s*(de\s*)?(leads|ventas)?)\b", re.I), Intent.VIEW_KANBAN, 0.90),
    (re.compile(r"\b(pipeline|embudo\s*(de\s*)?ventas|funnel)\b", re.I), Intent.VIEW_PIPELINE, 0.85),

    # --- Create Ticket ---
    (re.compile(r"\b(crear\s*(un\s*)?ticket|nuevo\s*(ticket|caso)|reportar\s*(un\s*)?problema|abrir\s*(un\s*)?(ticket|caso))\b", re.I), Intent.CREATE_TICKET, 0.95),

    # --- List Tickets ---
    (re.compile(r"\b(ver\s*tickets|listar\s*tickets|mostrar\s*tickets|mis\s*tickets|todos\s*los\s*tickets)\b", re.I), Intent.LIST_TICKETS, 0.90),

    # --- View Ticket ---
    (re.compile(r"\b(ver\s*(el\s*)?ticket\s*#?\d+|detalle\s*(del?\s*)?ticket|estado\s*(del?\s*)?ticket)\b", re.I), Intent.VIEW_TICKET, 0.90),

    # --- Dashboard ---
    (re.compile(r"\b(dashboard|resumen|m[eé]tricas|panel\s*(de\s*)?control|vista\s*general)\b", re.I), Intent.VIEW_DASHBOARD, 0.90),

    # --- Compose Outreach ---
    (re.compile(r"\b(enviar\s*(un\s*)?mensaje|outreach|contactar|redactar\s*(un\s*)?(email|correo|mensaje)|escribir(le)?)\b", re.I), Intent.COMPOSE_OUTREACH, 0.90),

    # --- Import Data ---
    (re.compile(r"\b(importar|subir\s*datos|cargar\s*(un\s*)?(csv|archivo|excel)|importaci[oó]n)\b", re.I), Intent.IMPORT_DATA, 0.90),

    # --- Export Data ---
    (re.compile(r"\b(exportar|descargar|bajar\s*(datos|csv|excel|archivo)|exportaci[oó]n)\b", re.I), Intent.EXPORT_DATA, 0.90),

    # --- Analytics ---
    (re.compile(r"\b(anal[ií]tica|estad[ií]sticas|reportes|informes|an[aá]lisis)\b", re.I), Intent.VIEW_ANALYTICS, 0.85),

    # --- Health Score ---
    (re.compile(r"\b(health\s*score|salud\s*(del?\s*)?(sistema|cuenta|cliente)|puntuaci[oó]n\s*(de\s*)?salud)\b", re.I), Intent.VIEW_HEALTH_SCORE, 0.90),

    # --- Configure Settings ---
    (re.compile(r"\b(configurar|configuraci[oó]n|ajustes|settings|preferencias)\b", re.I), Intent.CONFIGURE_SETTINGS, 0.85),

    # --- Campaigns ---
    (re.compile(r"\b(iniciar\s*(una\s*)?campa[nñ]a|nueva\s*campa[nñ]a|crear\s*(una\s*)?campa[nñ]a|lanzar\s*(una\s*)?secuencia)\b", re.I), Intent.START_CAMPAIGN, 0.90),
    (re.compile(r"\b(ver\s*campa[nñ]as|mis\s*campa[nñ]as|listar\s*campa[nñ]as|campa[nñ]as\s*activas)\b", re.I), Intent.VIEW_CAMPAIGNS, 0.90),
    (re.compile(r"\b(campa[nñ]a|secuencia)\b", re.I), Intent.VIEW_CAMPAIGNS, 0.70),

    # --- Schedule Meeting ---
    (re.compile(r"\b(reuni[oó]n|agendar|meeting|programar\s*(una\s*)?(reuni[oó]n|llamada)|agenda)\b", re.I), Intent.SCHEDULE_MEETING, 0.90),

    # --- Search KB ---
    (re.compile(r"\b(buscar\s*(en\s*)?((la\s*)?base\s*(de\s*)?conocimiento|kb|art[ií]culos))\b", re.I), Intent.SEARCH_KB, 0.90),

    # --- Create KB Article ---
    (re.compile(r"\b(crear\s*(un\s*)?art[ií]culo|nuevo\s*art[ií]culo|escribir\s*(un\s*)?art[ií]culo)\b", re.I), Intent.CREATE_KB_ARTICLE, 0.90),

    # --- View Customer ---
    (re.compile(r"\b(ver\s*(el\s*)?cliente|detalle\s*(del?\s*)?cliente|360\s*(del?\s*)?cliente|customer\s*360|perfil\s*(del?\s*)?cliente)\b", re.I), Intent.VIEW_CUSTOMER, 0.90),

    # --- Predictions ---
    (re.compile(r"\b(predicci[oó]n(es)?|forecast|pron[oó]stico(s)?|predecir|proyecci[oó]n(es)?)\b", re.I), Intent.VIEW_PREDICTIONS, 0.90),

    # --- Automation ---
    (re.compile(r"\b(automatizar|regla|workflow|flujo\s*(de\s*)?trabajo|automatizaci[oó]n)\b", re.I), Intent.RUN_AUTOMATION, 0.90),

    # --- Generic Search (lower priority) ---
    (re.compile(r"\b(buscar|encontrar|d[oó]nde\s*est[aá])\b", re.I), Intent.SEARCH, 0.80),
]


# ---------------------------------------------------------------------------
# Entity extraction helpers
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_NUMBER_RE = re.compile(r"\b(\d+)\b")
_COMPANY_RE = re.compile(
    r"\b(?:de|para|empresa|compa[nñ][ií]a)\s+([A-Z\u00C0-\u024F][a-zA-Z\u00C0-\u024F]{1,}(?:\s+[A-Z\u00C0-\u024F][a-zA-Z\u00C0-\u024F]{1,})*)",
    re.UNICODE,
)
_QUOTED_RE = re.compile(r'["\u201c\u201d]([^"\u201c\u201d]+)["\u201c\u201d]')


def extract_entities(text: str) -> dict:
    """Extract structured data from natural text.

    Returns a dict that may contain:
    - ``ids``: list of numeric IDs found
    - ``email``: first email address found
    - ``company``: company name reference
    - ``search_query``: quoted search term
    """
    entities: dict = {}

    # IDs / numbers
    numbers = _NUMBER_RE.findall(text)
    if numbers:
        entities["ids"] = [int(n) for n in numbers]

    # Email
    emails = _EMAIL_RE.findall(text)
    if emails:
        entities["email"] = emails[0]

    # Company name (after "de", "para", "empresa", "compania")
    company_match = _COMPANY_RE.search(text)
    if company_match:
        entities["company"] = company_match.group(1).strip()

    # Quoted strings (search terms / names)
    quoted = _QUOTED_RE.findall(text)
    if quoted:
        entities["search_query"] = quoted[0]

    return entities


# ---------------------------------------------------------------------------
# IntentRecognizer
# ---------------------------------------------------------------------------


class IntentRecognizer:
    """Recognise user intent from Spanish natural language."""

    def recognize(self, text: str) -> IntentMatch:
        """Analyse *text* and return the best-matching :class:`IntentMatch`.

        The method evaluates all patterns and returns the one with the
        highest confidence.  If nothing matches, ``Intent.UNKNOWN`` is
        returned with confidence ``0.0``.
        """
        text_clean = text.strip()
        if not text_clean:
            return IntentMatch(
                intent=Intent.UNKNOWN,
                confidence=0.0,
                extracted_params={},
                original_text=text,
            )

        best: IntentMatch | None = None

        for pattern, intent, base_confidence in _INTENT_PATTERNS:
            match = pattern.search(text_clean)
            if match:
                # Boost confidence slightly when the text is short and
                # focused (fewer extraneous words).
                word_count = len(text_clean.split())
                confidence = base_confidence
                if word_count <= 4:
                    confidence = min(1.0, confidence + 0.05)

                if best is None or confidence > best.confidence:
                    best = IntentMatch(
                        intent=intent,
                        confidence=round(confidence, 2),
                        extracted_params=extract_entities(text_clean),
                        original_text=text,
                    )

        if best is not None:
            return best

        # Fallback — still extract any entities that might be useful.
        return IntentMatch(
            intent=Intent.UNKNOWN,
            confidence=0.0,
            extracted_params=extract_entities(text_clean),
            original_text=text,
        )
