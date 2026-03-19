"""Intent recognition engine for the conversational assistant.

Detects user intent from Spanish natural language using a multi-strategy
approach (exact command, regex, fuzzy keyword, contextual fallback) and
extracts structured entities (IDs, emails, company references, regions,
priorities, stages, channels) from the input text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


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
# Exact command map — slash-like commands or very precise short phrases.
# Confidence: 0.95+
# ---------------------------------------------------------------------------

_EXACT_COMMANDS: dict[str, Intent] = {
    # Greeting
    "hola": Intent.GREETING,
    "hey": Intent.GREETING,
    "saludos": Intent.GREETING,
    "buenos dias": Intent.GREETING,
    "buenos días": Intent.GREETING,
    "buenas tardes": Intent.GREETING,
    "buenas noches": Intent.GREETING,
    "buenas": Intent.GREETING,
    "qué tal": Intent.GREETING,
    "que tal": Intent.GREETING,
    # Help
    "ayuda": Intent.HELP,
    "help": Intent.HELP,
    "opciones": Intent.HELP,
    "funciones": Intent.HELP,
    # Leads
    "crear lead": Intent.CREATE_LEAD,
    "nuevo lead": Intent.CREATE_LEAD,
    "nueva lead": Intent.CREATE_LEAD,
    "ver leads": Intent.LIST_LEADS,
    "mis leads": Intent.LIST_LEADS,
    "listar leads": Intent.LIST_LEADS,
    "mostrar leads": Intent.LIST_LEADS,
    # Tickets
    "crear ticket": Intent.CREATE_TICKET,
    "nuevo ticket": Intent.CREATE_TICKET,
    "ver tickets": Intent.LIST_TICKETS,
    "mis tickets": Intent.LIST_TICKETS,
    "listar tickets": Intent.LIST_TICKETS,
    "mostrar tickets": Intent.LIST_TICKETS,
    # Dashboard / Pipeline / Kanban
    "dashboard": Intent.VIEW_DASHBOARD,
    "resumen": Intent.VIEW_DASHBOARD,
    "kanban": Intent.VIEW_KANBAN,
    "pipeline": Intent.VIEW_PIPELINE,
    # Other
    "exportar": Intent.EXPORT_DATA,
    "importar": Intent.IMPORT_DATA,
    "buscar": Intent.SEARCH,
    "configurar": Intent.CONFIGURE_SETTINGS,
    "predicciones": Intent.VIEW_PREDICTIONS,
}

# ---------------------------------------------------------------------------
# Pattern definitions: each entry maps a compiled regex to an Intent and a
# base confidence score.  Patterns are evaluated in order; the first match
# with the highest confidence wins.
# ---------------------------------------------------------------------------

_INTENT_PATTERNS: list[tuple[re.Pattern[str], Intent, float]] = [
    # --- Greeting ---
    (re.compile(
        r"\b(hola|buenos\s*d[ií]as|buenas\s*(tardes|noches)?|hey|saludos|qu[eé]\s*tal)\b", re.I,
    ), Intent.GREETING, 0.95),

    # --- Help ---
    (re.compile(
        r"\b(ayuda|c[oó]mo|qu[eé]\s*puedo|help|opciones|funciones|qu[eé]\s*hac[eé]s)\b", re.I,
    ), Intent.HELP, 0.90),

    # --- Create Lead (expanded) ---
    (re.compile(
        r"\b(crear|generar|hacer|armar|registrar|agregar|a[nñ]adir)\s+"
        r"(un[ao]?\s+)?(lead|prospecto|contacto|oportunidad)\b", re.I,
    ), Intent.CREATE_LEAD, 0.95),
    (re.compile(
        r"\b(nuev[oa]\s+(lead|prospecto|contacto|oportunidad))\b", re.I,
    ), Intent.CREATE_LEAD, 0.95),

    # --- List Leads (expanded with colloquial) ---
    (re.compile(
        r"\b(ver|listar|mostrar|mostr[aá](me|nos)|dame|necesito|ense[nñ]ame|quiero\s+ver)\s+"
        r"(los\s+|mis\s+|todos\s+los\s+)?(leads|prospectos|oportunidades)\b", re.I,
    ), Intent.LIST_LEADS, 0.90),
    (re.compile(
        r"\b(mis|todos\s+los)\s+(leads|prospectos|oportunidades)\b", re.I,
    ), Intent.LIST_LEADS, 0.88),

    # --- Qualify Lead ---
    (re.compile(
        r"\b(calificar|scoring|puntuar|evaluar)\s*(un\s+)?(lead|prospecto|el\s+lead)?\b", re.I,
    ), Intent.QUALIFY_LEAD, 0.90),
    (re.compile(
        r"\bscore\s*(del?\s*)?(lead|prospecto)?\b", re.I,
    ), Intent.QUALIFY_LEAD, 0.85),

    # --- View Kanban / Pipeline ---
    (re.compile(
        r"\b(ver|mostrar|mostr[aá]me)\s+(el\s+)?(pipeline|embudo|kanban|tablero)\b", re.I,
    ), Intent.VIEW_KANBAN, 0.90),
    (re.compile(
        r"\b(tablero\s*(de\s*)?(leads|ventas)?)\b", re.I,
    ), Intent.VIEW_KANBAN, 0.88),
    (re.compile(
        r"\b(pipeline|embudo\s*(de\s*)?ventas|funnel)\b", re.I,
    ), Intent.VIEW_PIPELINE, 0.85),

    # --- Create Ticket (expanded) ---
    (re.compile(
        r"\b(crear|generar|hacer|armar|abrir|reportar)\s+"
        r"(un[ao]?\s+)?(ticket|caso|problema|incidencia)\b", re.I,
    ), Intent.CREATE_TICKET, 0.95),
    (re.compile(
        r"\b(nuev[oa]\s+(ticket|caso|incidencia))\b", re.I,
    ), Intent.CREATE_TICKET, 0.95),

    # --- List Tickets (expanded) ---
    (re.compile(
        r"\b(ver|listar|mostrar|mostr[aá](me|nos)|dame|necesito|quiero\s+ver)\s+"
        r"(los\s+|mis\s+|todos\s+los\s+)?(tickets|casos|incidencias)\b", re.I,
    ), Intent.LIST_TICKETS, 0.90),
    (re.compile(
        r"\b(mis|todos\s+los)\s+(tickets|casos|incidencias)\b", re.I,
    ), Intent.LIST_TICKETS, 0.88),
    (re.compile(
        r"\bcu[aá]nt[oa]s\s+tickets\b", re.I,
    ), Intent.LIST_TICKETS, 0.88),

    # --- View Ticket ---
    (re.compile(
        r"\b(ver|mostrar|detalle|estado)\s+(el\s+|del?\s+)?ticket\s*#?\d+\b", re.I,
    ), Intent.VIEW_TICKET, 0.90),

    # --- Dashboard ---
    (re.compile(
        r"\b(dashboard|resumen|m[eé]tricas|panel\s*(de\s*)?control|vista\s*general)\b", re.I,
    ), Intent.VIEW_DASHBOARD, 0.90),

    # --- Compose Outreach ---
    (re.compile(
        r"\b(enviar|mandar|redactar|escribir(le)?|contactar)\s+"
        r"(un[ao]?\s+)?(mensaje|email|correo|mail|whatsapp)\b", re.I,
    ), Intent.COMPOSE_OUTREACH, 0.90),
    (re.compile(
        r"\b(outreach|contactar)\b", re.I,
    ), Intent.COMPOSE_OUTREACH, 0.85),

    # --- Import Data ---
    (re.compile(
        r"\b(importar|subir\s*datos|cargar\s*(un[ao]?\s*)?(csv|archivo|excel)|importaci[oó]n)\b", re.I,
    ), Intent.IMPORT_DATA, 0.90),

    # --- Export Data ---
    (re.compile(
        r"\b(exportar|descargar|bajar\s*(datos|csv|excel|archivo)|exportaci[oó]n)\b", re.I,
    ), Intent.EXPORT_DATA, 0.90),

    # --- Analytics ---
    (re.compile(
        r"\b(anal[ií]tica|estad[ií]sticas|reportes|informes|an[aá]lisis)\b", re.I,
    ), Intent.VIEW_ANALYTICS, 0.85),

    # --- Health Score ---
    (re.compile(
        r"\b(health\s*score|salud\s*(del?\s*)?(sistema|cuenta|cliente)|puntuaci[oó]n\s*(de\s*)?salud)\b", re.I,
    ), Intent.VIEW_HEALTH_SCORE, 0.90),

    # --- Configure Settings ---
    (re.compile(
        r"\b(configurar|configuraci[oó]n|ajustes|settings|preferencias)\b", re.I,
    ), Intent.CONFIGURE_SETTINGS, 0.85),

    # --- Campaigns ---
    (re.compile(
        r"\b(iniciar|lanzar|crear|generar|armar)\s+(una\s+)?campa[nñ]a\b", re.I,
    ), Intent.START_CAMPAIGN, 0.90),
    (re.compile(
        r"\b(nueva\s+campa[nñ]a|lanzar\s+(una\s+)?secuencia)\b", re.I,
    ), Intent.START_CAMPAIGN, 0.90),
    (re.compile(
        r"\b(ver|listar|mostrar|mis)\s*campa[nñ]as\b", re.I,
    ), Intent.VIEW_CAMPAIGNS, 0.90),
    (re.compile(
        r"\bcampa[nñ]as?\s*activas?\b", re.I,
    ), Intent.VIEW_CAMPAIGNS, 0.88),
    (re.compile(
        r"\b(campa[nñ]a|secuencia)\b", re.I,
    ), Intent.VIEW_CAMPAIGNS, 0.70),

    # --- Schedule Meeting ---
    (re.compile(
        r"\b(reuni[oó]n|agendar|meeting|programar\s*(una\s*)?(reuni[oó]n|llamada)|agenda)\b", re.I,
    ), Intent.SCHEDULE_MEETING, 0.90),

    # --- Search KB ---
    (re.compile(
        r"\b(buscar\s*(en\s*)?((la\s*)?base\s*(de\s*)?conocimiento|kb|art[ií]culos))\b", re.I,
    ), Intent.SEARCH_KB, 0.90),

    # --- Create KB Article ---
    (re.compile(
        r"\b(crear|nuevo|escribir)\s*(un[ao]?\s*)?art[ií]culo\b", re.I,
    ), Intent.CREATE_KB_ARTICLE, 0.90),

    # --- View Customer ---
    (re.compile(
        r"\b(ver|detalle|360|perfil)\s*(el\s*|del?\s*)?cliente\b", re.I,
    ), Intent.VIEW_CUSTOMER, 0.90),
    (re.compile(
        r"\bcustomer\s*360\b", re.I,
    ), Intent.VIEW_CUSTOMER, 0.90),

    # --- Predictions ---
    (re.compile(
        r"\b(predicci[oó]n(es)?|forecast|pron[oó]stico(s)?|predecir|proyecci[oó]n(es)?)\b", re.I,
    ), Intent.VIEW_PREDICTIONS, 0.90),

    # --- Automation ---
    (re.compile(
        r"\b(automatizar|regla|workflow|flujo\s*(de\s*)?trabajo|automatizaci[oó]n)\b", re.I,
    ), Intent.RUN_AUTOMATION, 0.90),

    # --- Generic Search (lower priority) ---
    (re.compile(
        r"\b(buscar|encontrar|d[oó]nde\s*est[aá])\b", re.I,
    ), Intent.SEARCH, 0.80),
]


# ---------------------------------------------------------------------------
# Fuzzy keyword map — maps individual keywords / short colloquial phrases
# to intents for the fuzzy-match strategy.  Each keyword carries a weight.
# ---------------------------------------------------------------------------

_FUZZY_KEYWORDS: list[tuple[list[str], Intent, float]] = [
    # View / list intents (colloquial verbs)
    (["mostrame", "mostrá", "mostráme", "mostrame", "enseñame",
      "enseñá", "enseñáme", "dame", "necesito", "quiero ver",
      "decime", "pasame", "pasáme"], Intent.LIST_LEADS, 0.40),

    # Hot / classification keywords
    (["hot", "calientes", "caliente", "mejores", "top",
      "prioritarios", "destacados"], Intent.LIST_LEADS, 0.45),

    # Create intents
    (["crear", "creá", "generar", "generá", "hacer", "hacé",
      "armar", "armá", "nuevo", "nueva", "agregar", "agregá",
      "añadir", "añadí", "registrar", "registrá"], Intent.CREATE_LEAD, 0.40),

    # Delete intents (mapped to UNKNOWN with entity hints for now)
    (["borrar", "borrá", "eliminar", "eliminá", "sacar", "sacá",
      "quitar", "quitá", "remover"], Intent.UNKNOWN, 0.35),

    # Update intents
    (["cambiar", "cambiá", "mover", "mové", "actualizar", "actualizá",
      "editar", "editá", "modificar", "modificá"], Intent.UNKNOWN, 0.35),

    # Count / stats intents
    (["cuántos", "cuántas", "cuantos", "cuantas", "cantidad",
      "total", "estadísticas", "estadisticas"], Intent.VIEW_ANALYTICS, 0.45),

    # Priority / urgency
    (["urgente", "urgentes", "importante", "importantes",
      "prioritario", "prioritarios", "rápido", "rapido",
      "crítico", "critico"], Intent.LIST_TICKETS, 0.40),

    # Lead-related nouns
    (["lead", "leads", "prospecto", "prospectos",
      "oportunidad", "oportunidades"], Intent.LIST_LEADS, 0.35),

    # Ticket-related nouns
    (["ticket", "tickets", "caso", "casos",
      "incidencia", "incidencias", "problema"], Intent.LIST_TICKETS, 0.35),

    # Campaign nouns
    (["campaña", "campana", "secuencia"], Intent.VIEW_CAMPAIGNS, 0.35),

    # Meeting
    (["reunión", "reunion", "meeting", "llamada", "agenda"], Intent.SCHEDULE_MEETING, 0.35),
]


# ---------------------------------------------------------------------------
# Entity extraction helpers
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_NUMBER_RE = re.compile(r"\b(\d+)\b")
_COMPANY_RE = re.compile(
    r"\b(?:de|para|empresa|compa[nñ][ií]a)\s+"
    r"([A-Z\u00C0-\u024F][a-zA-Z\u00C0-\u024F]{1,}(?:\s+[A-Z\u00C0-\u024F][a-zA-Z\u00C0-\u024F]{1,})*)",
    re.UNICODE,
)
_QUOTED_RE = re.compile(r'["\u201c\u201d]([^"\u201c\u201d]+)["\u201c\u201d]')

# Regions
_REGIONS = {
    "latam": "LATAM",
    "iberia": "Iberia",
    "argentina": "Argentina",
    "méxico": "México",
    "mexico": "México",
    "colombia": "Colombia",
    "chile": "Chile",
    "perú": "Perú",
    "peru": "Perú",
    "brasil": "Brasil",
    "brazil": "Brasil",
    "españa": "España",
    "espana": "España",
    "portugal": "Portugal",
    "europa": "Europa",
    "usa": "USA",
    "estados unidos": "USA",
    "norteamérica": "Norteamérica",
    "norteamerica": "Norteamérica",
}

# Priority keywords
_PRIORITIES = {
    "urgente": "urgent",
    "urgentes": "urgent",
    "alta": "high",
    "altas": "high",
    "media": "medium",
    "medias": "medium",
    "baja": "low",
    "bajas": "low",
    "crítica": "critical",
    "critica": "critical",
    "crítico": "critical",
    "critico": "critical",
    "importante": "high",
    "importantes": "high",
    "prioritario": "high",
    "prioritarios": "high",
}

# Classification keywords
_CLASSIFICATIONS = {
    "hot": "hot",
    "caliente": "hot",
    "calientes": "hot",
    "warm": "warm",
    "tibio": "warm",
    "tibios": "warm",
    "cold": "cold",
    "frío": "cold",
    "frio": "cold",
    "fríos": "cold",
    "frios": "cold",
    "mejores": "hot",
    "top": "hot",
    "prioritarios": "hot",
    "destacados": "hot",
}

# Stage keywords
_STAGES = {
    "nuevo": "new",
    "nueva": "new",
    "calificado": "qualified",
    "calificada": "qualified",
    "contactado": "contacted",
    "contactada": "contacted",
    "reunión": "meeting",
    "reunion": "meeting",
    "propuesta": "proposal",
    "negociación": "negotiation",
    "negociacion": "negotiation",
    "ganado": "won",
    "ganada": "won",
    "perdido": "lost",
    "perdida": "lost",
    "cerrado": "closed",
    "cerrada": "closed",
}

# Status keywords
_STATUSES = {
    "abierto": "open",
    "abierta": "open",
    "abiertos": "open",
    "abiertas": "open",
    "cerrado": "closed",
    "cerrada": "closed",
    "cerrados": "closed",
    "cerradas": "closed",
    "pendiente": "pending",
    "pendientes": "pending",
    "resuelto": "resolved",
    "resuelta": "resolved",
    "resueltos": "resolved",
    "resueltas": "resolved",
    "en progreso": "in_progress",
    "en curso": "in_progress",
}

# Channel keywords
_CHANNELS = {
    "email": "email",
    "correo": "email",
    "mail": "email",
    "linkedin": "linkedin",
    "whatsapp": "whatsapp",
    "teléfono": "phone",
    "telefono": "phone",
    "llamada": "phone",
}

# Contact name pattern (after "contacto", "persona", "nombre")
_CONTACT_RE = re.compile(
    r"\b(?:contacto|persona|nombre)\s+(?:es\s+|de\s+)?"
    r"([A-Z\u00C0-\u024F][a-z\u00C0-\u024F]+(?:\s+[A-Z\u00C0-\u024F][a-z\u00C0-\u024F]+)*)",
    re.UNICODE,
)

# Score reference pattern
_SCORE_RE = re.compile(
    r"\bscore\s*(?:mayor|>|>=|superior|encima)\s*(?:a|de|que)?\s*(\d+)\b", re.I,
)
_ICP_HIGH_RE = re.compile(
    r"\b(ICP\s*alto|puntuaci[oó]n\s*alta|score\s*alto|alto\s*ICP)\b", re.I,
)

# C-level detection
_C_LEVEL_RE = re.compile(
    r"\b(CEO|CTO|CFO|COO|CMO|CIO|CISO|VP|Director|C-level|c.level|directivo|gerente\s*general)\b",
    re.I,
)


def extract_entities(text: str) -> dict:
    """Extract structured data from natural text.

    Returns a dict that may contain:
    - ``ids``: list of numeric IDs found
    - ``email``: first email address found
    - ``company``: company name reference
    - ``search_query``: quoted search term
    - ``region``: detected region/country
    - ``priority``: detected priority level
    - ``classification``: lead classification (hot/warm/cold)
    - ``stage``: pipeline stage
    - ``status``: ticket/lead status
    - ``channel``: communication channel
    - ``contact_name``: contact person name
    - ``score_threshold``: numeric score threshold
    - ``high_icp``: boolean if high ICP/score mentioned
    - ``c_level``: boolean if C-level role detected
    """
    entities: dict = {}
    text_lower = text.lower()

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

    # Region detection
    for keyword, region in _REGIONS.items():
        if keyword in text_lower:
            entities["region"] = region
            break

    # Priority detection
    for keyword, priority in _PRIORITIES.items():
        if re.search(r"\b" + re.escape(keyword) + r"\b", text_lower):
            entities["priority"] = priority
            break

    # Classification detection
    for keyword, classification in _CLASSIFICATIONS.items():
        if re.search(r"\b" + re.escape(keyword) + r"\b", text_lower):
            entities["classification"] = classification
            break

    # Stage detection
    for keyword, stage in _STAGES.items():
        if re.search(r"\b" + re.escape(keyword) + r"\b", text_lower):
            entities["stage"] = stage
            break

    # Status detection
    for keyword, status in _STATUSES.items():
        if keyword in text_lower:
            entities["status"] = status
            break

    # Channel detection
    for keyword, channel in _CHANNELS.items():
        if re.search(r"\b" + re.escape(keyword) + r"\b", text_lower):
            entities["channel"] = channel
            break

    # Contact name
    contact_match = _CONTACT_RE.search(text)
    if contact_match:
        entities["contact_name"] = contact_match.group(1).strip()

    # Score threshold
    score_match = _SCORE_RE.search(text)
    if score_match:
        entities["score_threshold"] = int(score_match.group(1))

    # High ICP
    if _ICP_HIGH_RE.search(text):
        entities["high_icp"] = True

    # C-level detection
    if _C_LEVEL_RE.search(text):
        entities["c_level"] = True

    return entities


# ---------------------------------------------------------------------------
# IntentRecognizer — multi-strategy engine
# ---------------------------------------------------------------------------


class IntentRecognizer:
    """Recognise user intent from Spanish natural language.

    Uses a four-strategy pipeline evaluated in order:
    1. Exact command match (confidence 0.95+)
    2. Regex pattern match (confidence 0.80+)
    3. Fuzzy keyword match (confidence 0.60+)
    4. Context-aware fallback (confidence 0.30-0.50)

    The method returns the single best match.
    """

    # ----- public API -----

    def recognize(self, text: str) -> IntentMatch:
        """Analyse *text* and return the best-matching :class:`IntentMatch`.

        The method tries each strategy in order and returns the first
        result that exceeds the confidence floor for that strategy.
        If nothing matches, ``Intent.UNKNOWN`` is returned with
        confidence ``0.0``.
        """
        text_clean = text.strip()
        if not text_clean:
            return IntentMatch(
                intent=Intent.UNKNOWN,
                confidence=0.0,
                extracted_params={},
                original_text=text,
            )

        entities = extract_entities(text_clean)

        # Strategy 1: exact command match
        result = self._try_exact_match(text_clean, entities)
        if result is not None:
            return result

        # Strategy 2: regex pattern match
        result = self._try_regex_match(text_clean, entities)
        if result is not None:
            return result

        # Strategy 3: fuzzy keyword match
        result = self._try_fuzzy_match(text_clean, entities)
        if result is not None:
            return result

        # Strategy 4: context-aware fallback
        result = self._try_contextual_fallback(text_clean, entities)
        if result is not None:
            return result

        # Nothing matched
        return IntentMatch(
            intent=Intent.UNKNOWN,
            confidence=0.0,
            extracted_params=entities,
            original_text=text,
        )

    # ----- Strategy 1: exact command match -----

    def _try_exact_match(
        self, text: str, entities: dict,
    ) -> Optional[IntentMatch]:
        """Match against exact command strings (confidence 0.95+)."""
        normalized = self._normalize(text)

        if normalized in _EXACT_COMMANDS:
            intent = _EXACT_COMMANDS[normalized]
            return IntentMatch(
                intent=intent,
                confidence=0.98,
                extracted_params=entities,
                original_text=text,
            )
        return None

    # ----- Strategy 2: regex pattern match -----

    def _try_regex_match(
        self, text: str, entities: dict,
    ) -> Optional[IntentMatch]:
        """Evaluate regex patterns and return the best match (confidence 0.80+)."""
        best: IntentMatch | None = None

        for pattern, intent, base_confidence in _INTENT_PATTERNS:
            match = pattern.search(text)
            if match:
                word_count = len(text.split())
                confidence = base_confidence
                if word_count <= 4:
                    confidence = min(1.0, confidence + 0.05)

                if best is None or confidence > best.confidence:
                    best = IntentMatch(
                        intent=intent,
                        confidence=round(confidence, 2),
                        extracted_params=entities,
                        original_text=text,
                    )

        return best

    # ----- Strategy 3: fuzzy keyword match -----

    def _try_fuzzy_match(
        self, text: str, entities: dict,
    ) -> Optional[IntentMatch]:
        """Score text against keyword lists; return best above 0.60 threshold."""
        text_lower = text.lower()
        words = set(re.findall(r"\w+", text_lower))

        best_intent: Intent | None = None
        best_score: float = 0.0

        for keywords, intent, base_weight in _FUZZY_KEYWORDS:
            hits = 0
            for kw in keywords:
                # Support multi-word keywords
                if " " in kw:
                    if kw in text_lower:
                        hits += 1
                elif kw in words:
                    hits += 1

            if hits == 0:
                continue

            # Score: base_weight + bonus for multiple hits, capped at 0.78
            score = min(0.78, base_weight + (hits - 1) * 0.08)

            if score > best_score:
                best_score = score
                best_intent = intent

        # Refine intent when we have both a verb group and a noun group.
        # For example, "mostrame leads" → verb fuzzy hits LIST_LEADS noun,
        # but "creá ticket" → verb hits CREATE_LEAD while noun hits LIST_TICKETS.
        # We resolve by checking nouns explicitly.
        if best_intent is not None and best_score >= 0.35:
            refined_intent = self._refine_fuzzy_with_nouns(text_lower, best_intent, entities)
            # Boost confidence because we matched multiple signals
            effective_confidence = min(0.78, best_score + 0.15) if refined_intent != best_intent else best_score + 0.10
            effective_confidence = min(0.78, effective_confidence)

            if effective_confidence >= 0.60:
                return IntentMatch(
                    intent=refined_intent,
                    confidence=round(effective_confidence, 2),
                    extracted_params=entities,
                    original_text=text,
                )
            elif effective_confidence >= 0.40:
                # Still return it, but at lower confidence
                return IntentMatch(
                    intent=refined_intent,
                    confidence=round(effective_confidence, 2),
                    extracted_params=entities,
                    original_text=text,
                )

        return None

    def _refine_fuzzy_with_nouns(
        self, text_lower: str, base_intent: Intent, entities: dict,
    ) -> Intent:
        """Given a base intent from fuzzy verb matching, refine using nouns."""
        noun_to_intent: dict[str, Intent] = {
            "lead": Intent.LIST_LEADS,
            "leads": Intent.LIST_LEADS,
            "prospecto": Intent.LIST_LEADS,
            "prospectos": Intent.LIST_LEADS,
            "oportunidad": Intent.LIST_LEADS,
            "oportunidades": Intent.LIST_LEADS,
            "ticket": Intent.LIST_TICKETS,
            "tickets": Intent.LIST_TICKETS,
            "caso": Intent.LIST_TICKETS,
            "casos": Intent.LIST_TICKETS,
            "campaña": Intent.VIEW_CAMPAIGNS,
            "campana": Intent.VIEW_CAMPAIGNS,
            "reunión": Intent.SCHEDULE_MEETING,
            "reunion": Intent.SCHEDULE_MEETING,
        }

        # Map for create verbs
        create_verb_to_intent: dict[str, Intent] = {
            "lead": Intent.CREATE_LEAD,
            "leads": Intent.CREATE_LEAD,
            "prospecto": Intent.CREATE_LEAD,
            "prospectos": Intent.CREATE_LEAD,
            "oportunidad": Intent.CREATE_LEAD,
            "ticket": Intent.CREATE_TICKET,
            "tickets": Intent.CREATE_TICKET,
            "caso": Intent.CREATE_TICKET,
            "casos": Intent.CREATE_TICKET,
            "campaña": Intent.START_CAMPAIGN,
            "campana": Intent.START_CAMPAIGN,
            "artículo": Intent.CREATE_KB_ARTICLE,
            "articulo": Intent.CREATE_KB_ARTICLE,
            "reunión": Intent.SCHEDULE_MEETING,
            "reunion": Intent.SCHEDULE_MEETING,
        }

        words = set(re.findall(r"\w+", text_lower))

        # Check if the base intent was from create-type keywords
        create_keywords = {"crear", "creá", "generar", "generá", "hacer", "hacé",
                           "armar", "armá", "nuevo", "nueva", "agregar", "agregá",
                           "añadir", "añadí", "registrar", "registrá"}
        is_create = bool(words & create_keywords)

        # Check if the base intent was from view-type keywords
        view_keywords = {"mostrame", "mostrá", "mostráme", "dame", "necesito",
                         "enseñame", "enseñá", "quiero", "decime", "pasame",
                         "ver", "listar", "mostrar"}
        is_view = bool(words & view_keywords)

        # Check if count-type
        count_keywords = {"cuántos", "cuántas", "cuantos", "cuantas", "cantidad", "total"}
        is_count = bool(words & count_keywords)

        intent_map = create_verb_to_intent if is_create else noun_to_intent

        for noun, intent in intent_map.items():
            if noun in words:
                return intent

        # For count queries, check what they're counting
        if is_count:
            for noun in ("leads", "lead", "prospectos", "prospecto"):
                if noun in words:
                    return Intent.LIST_LEADS
            for noun in ("tickets", "ticket", "casos", "caso"):
                if noun in words:
                    return Intent.LIST_TICKETS

        return base_intent

    # ----- Strategy 4: contextual fallback -----

    def _try_contextual_fallback(
        self, text: str, entities: dict,
    ) -> Optional[IntentMatch]:
        """Make a best-guess based on extracted entities (confidence 0.30-0.50)."""
        text_lower = text.lower()

        # If we found a company name and no other strong signal, probably lead-related
        if "company" in entities:
            return IntentMatch(
                intent=Intent.LIST_LEADS,
                confidence=0.40,
                extracted_params=entities,
                original_text=text,
            )

        # If "urgente" or priority detected, probably tickets
        if "priority" in entities:
            return IntentMatch(
                intent=Intent.LIST_TICKETS,
                confidence=0.40,
                extracted_params=entities,
                original_text=text,
            )

        # If classification detected (hot/warm/cold), probably leads
        if "classification" in entities:
            return IntentMatch(
                intent=Intent.LIST_LEADS,
                confidence=0.40,
                extracted_params=entities,
                original_text=text,
            )

        # If score/ICP references, probably qualify lead
        if "score_threshold" in entities or "high_icp" in entities:
            return IntentMatch(
                intent=Intent.QUALIFY_LEAD,
                confidence=0.35,
                extracted_params=entities,
                original_text=text,
            )

        # If only IDs and nothing else recognized
        if "ids" in entities and len(entities) == 1:
            return IntentMatch(
                intent=Intent.SEARCH,
                confidence=0.30,
                extracted_params=entities,
                original_text=text,
            )

        # If region detected, probably leads
        if "region" in entities:
            return IntentMatch(
                intent=Intent.LIST_LEADS,
                confidence=0.35,
                extracted_params=entities,
                original_text=text,
            )

        return None

    # ----- helpers -----

    @staticmethod
    def _normalize(text: str) -> str:
        """Lowercase, strip, collapse whitespace, remove trailing punctuation."""
        text = text.lower().strip()
        text = re.sub(r"\s+", " ", text)
        text = text.rstrip("?!.,;:")
        return text
