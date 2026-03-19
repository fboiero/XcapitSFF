"""Ticket Router — multi-signal classification, smart routing, SLA and escalation engine."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from xcapitsff.core.schemas import TicketPriorityEnum

# ---------------------------------------------------------------------------
# RoutingDecision — the single return object every public function populates
# ---------------------------------------------------------------------------


@dataclass
class RoutingDecision:
    """Complete routing decision returned by ``full_route``."""

    category: str
    category_confidence: float
    priority: TicketPriorityEnum
    priority_confidence: float
    assigned_agent: str
    requires_human_review: bool
    escalation_needed: bool
    sla_hours: float
    flags: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Constants — keyword dictionaries, patterns, agent pools
# ---------------------------------------------------------------------------

# Expanded keyword dictionaries with weights.  Each keyword maps to a numeric
# weight so that more-specific terms score higher than generic ones.
CATEGORY_KEYWORDS: dict[str, dict[str, float]] = {
    "billing": {
        "pago": 1.0,
        "factura": 1.0,
        "cobro": 1.0,
        "precio": 0.8,
        "plan": 0.6,
        "suscripcion": 1.0,
        "billing": 1.0,
        "invoice": 1.0,
        "reembolso": 1.0,
        "refund": 1.0,
        "cargo": 0.9,
        "tarjeta": 0.8,
        "debito": 0.7,
        "credito": 0.7,
        "monto": 0.8,
        "dinero": 0.9,
        "comision": 0.9,
        "descuento": 0.7,
    },
    "technical": {
        "error": 1.0,
        "bug": 1.0,
        "no funciona": 1.2,
        "falla": 1.0,
        "crash": 1.0,
        "lento": 0.8,
        "api": 0.9,
        "integracion": 0.9,
        "pantalla": 0.6,
        "carga": 0.6,
        "timeout": 1.0,
        "500": 0.9,
        "404": 0.8,
        "caida": 0.9,
        "servidor": 0.8,
        "actualizacion": 0.6,
        "version": 0.5,
    },
    "account": {
        "cuenta": 0.9,
        "password": 1.0,
        "contrasena": 1.0,
        "acceso": 0.9,
        "login": 1.0,
        "registro": 0.8,
        "kyc": 1.2,
        "verificacion": 0.8,
        "email": 0.5,
        "perfil": 0.7,
        "sesion": 0.8,
        "autenticacion": 1.0,
        "2fa": 1.0,
        "bloqueo": 0.8,
    },
    "crypto": {
        "wallet": 1.2,
        "token": 1.0,
        "blockchain": 1.0,
        "transaccion": 1.0,
        "withdraw": 1.2,
        "deposit": 1.0,
        "swap": 1.0,
        "cripto": 1.0,
        "bitcoin": 1.0,
        "btc": 1.0,
        "ethereum": 1.0,
        "eth": 0.9,
        "usdt": 1.0,
        "staking": 1.0,
        "defi": 1.0,
        "nft": 0.8,
        "gas": 0.7,
        "red": 0.5,
        "mining": 0.8,
        "hash": 0.7,
    },
    "general": {
        "consulta": 0.6,
        "informacion": 0.5,
        "pregunta": 0.5,
        "ayuda": 0.4,
        "duda": 0.5,
        "como": 0.3,
        "quiero saber": 0.6,
    },
}

PRIORITY_KEYWORDS: dict[str, tuple[TicketPriorityEnum, float]] = {
    "urgente": (TicketPriorityEnum.URGENT, 1.0),
    "urgent": (TicketPriorityEnum.URGENT, 1.0),
    "critico": (TicketPriorityEnum.URGENT, 1.0),
    "critical": (TicketPriorityEnum.URGENT, 1.0),
    "emergencia": (TicketPriorityEnum.URGENT, 1.0),
    "no puedo acceder": (TicketPriorityEnum.HIGH, 0.9),
    "perdi": (TicketPriorityEnum.HIGH, 0.9),
    "fondos": (TicketPriorityEnum.HIGH, 0.85),
    "bloqueado": (TicketPriorityEnum.HIGH, 0.85),
    "importante": (TicketPriorityEnum.HIGH, 0.7),
    "pronto": (TicketPriorityEnum.HIGH, 0.6),
    "rapido": (TicketPriorityEnum.HIGH, 0.6),
}

# Financial risk keywords — presence triggers the "financial_risk" flag
FINANCIAL_RISK_KEYWORDS: set[str] = {
    "fondos",
    "dinero",
    "plata",
    "dolares",
    "pesos",
    "saldo",
    "transferencia",
    "retiro",
    "withdraw",
    "deposit",
    "perdida",
    "robo",
    "hack",
    "fraude",
    "estafa",
    "stolen",
    "desaparecio",
    "missing",
    "monto",
    "cobro indebido",
}

# Urgency tone signals (detected via patterns, not just keywords)
URGENCY_TONE_KEYWORDS: set[str] = {"urgente", "ya", "ahora", "inmediatamente", "rapido", "pronto", "asap"}

# Common patterns that strongly indicate a ticket type
CATEGORY_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "billing": [
        re.compile(r"cobr[oa]\s+(indebido|doble|extra|duplicado)", re.IGNORECASE),
        re.compile(r"no\s+(me\s+)?lleg[oa]\s+(la\s+)?factura", re.IGNORECASE),
        re.compile(r"me\s+cobr(aron|o)", re.IGNORECASE),
        re.compile(r"quiero\s+(cancelar|cambiar)\s+(mi\s+)?(plan|suscripcion)", re.IGNORECASE),
    ],
    "technical": [
        re.compile(r"(pantalla|pagina)\s+(en\s+)?blanc[oa]", re.IGNORECASE),
        re.compile(r"no\s+(me\s+)?carga", re.IGNORECASE),
        re.compile(r"error\s+\d{3}", re.IGNORECASE),
        re.compile(r"se\s+(cierra|cuelga|congela)", re.IGNORECASE),
    ],
    "account": [
        re.compile(r"no\s+puedo\s+(iniciar\s+sesion|hacer\s+login|entrar|acceder)", re.IGNORECASE),
        re.compile(r"olvid[eé]\s+(mi\s+)?(contrase[nñ]a|password|clave)", re.IGNORECASE),
        re.compile(r"cuenta\s+(bloqueada|suspendida|cerrada)", re.IGNORECASE),
    ],
    "crypto": [
        re.compile(r"(no\s+lleg[oa]|no\s+aparece)\s+(mi\s+)?(deposito|withdraw|transferencia)", re.IGNORECASE),
        re.compile(r"transacci[oó]n\s+(pendiente|fallida|no\s+confirmada)", re.IGNORECASE),
        re.compile(r"wallet\s+(vac[ií][oa]|no\s+aparece|error)", re.IGNORECASE),
    ],
}

# Agent pool with specialty tags
AGENT_POOL: dict[str, dict[str, object]] = {
    "support_responder_senior": {"specialties": {"all"}, "max_load": 10},
    "support_responder_billing": {"specialties": {"billing"}, "max_load": 20},
    "support_responder_tech": {"specialties": {"technical"}, "max_load": 20},
    "support_responder_account": {"specialties": {"account"}, "max_load": 20},
    "support_responder_crypto": {"specialties": {"crypto"}, "max_load": 15},
    "support_responder": {"specialties": {"general", "all"}, "max_load": 25},
}

# Priority numeric rank (higher = more urgent)
_PRIORITY_RANK: dict[TicketPriorityEnum, int] = {
    TicketPriorityEnum.LOW: 0,
    TicketPriorityEnum.MEDIUM: 1,
    TicketPriorityEnum.HIGH: 2,
    TicketPriorityEnum.URGENT: 3,
}

# Base SLA hours by priority
_BASE_SLA: dict[TicketPriorityEnum, float] = {
    TicketPriorityEnum.URGENT: 2.0,
    TicketPriorityEnum.HIGH: 8.0,
    TicketPriorityEnum.MEDIUM: 24.0,
    TicketPriorityEnum.LOW: 72.0,
}

# Categories that get tighter SLA (multiplier < 1.0)
_CATEGORY_SLA_MULTIPLIER: dict[str, float] = {
    "crypto": 0.75,
    "billing": 0.8,
}


# ---------------------------------------------------------------------------
# Text normalisation helpers
# ---------------------------------------------------------------------------


def _normalize(text: str) -> str:
    """Lower-case, strip accents, collapse whitespace.

    This provides a simple stemming-like normalization for Spanish text
    without requiring external NLP libraries.  Accented vowels are replaced
    by their plain equivalents (e.g. "ó" -> "o") so that "transacción" will
    match a keyword stored as "transaccion".
    """
    text = text.lower()
    # Decompose unicode and strip combining characters (accents)
    nfkd = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in nfkd if unicodedata.category(ch) != "Mn")
    # Replace ñ (which decompose strips) — we already handled it via NFKD
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _has_urgency_tone(raw_text: str) -> tuple[bool, float]:
    """Detect urgency from tone signals in the *raw* (un-normalised) text.

    Returns ``(is_urgent, intensity)`` where intensity is 0.0-1.0.
    """
    signals = 0.0

    # Exclamation marks — more = more urgent
    excl_count = raw_text.count("!")
    if excl_count >= 3:
        signals += 0.4
    elif excl_count >= 1:
        signals += 0.2

    # ALL-CAPS words (3+ chars) — proportion of caps words
    words = raw_text.split()
    if words:
        caps_words = [w for w in words if len(w) >= 3 and w.isupper()]
        caps_ratio = len(caps_words) / len(words)
        signals += min(caps_ratio * 1.5, 0.4)

    # Urgency keywords in normalised text
    norm = _normalize(raw_text)
    for kw in URGENCY_TONE_KEYWORDS:
        if kw in norm:
            signals += 0.15

    is_urgent = signals >= 0.3
    return is_urgent, min(signals, 1.0)


def _detect_financial_risk(norm_text: str) -> bool:
    """Return True when the text contains financial-risk keywords."""
    for kw in FINANCIAL_RISK_KEYWORDS:
        if kw in norm_text:
            return True
    return False


# ---------------------------------------------------------------------------
# Classification engine
# ---------------------------------------------------------------------------


def classify_ticket(
    subject: str,
    description: str,
) -> tuple[str, float, TicketPriorityEnum, float, list[str]]:
    """Classify a ticket using multi-signal analysis.

    Returns
    -------
    tuple
        ``(category, category_confidence, priority, priority_confidence, flags)``
    """
    raw_text = f"{subject} {description}"
    norm = _normalize(raw_text)
    flags: list[str] = []

    # ── 1. Category classification ──────────────────────────────────────
    category_scores: dict[str, float] = {cat: 0.0 for cat in CATEGORY_KEYWORDS}

    # 1a. Weighted keyword matching
    for cat, kw_weights in CATEGORY_KEYWORDS.items():
        for kw, weight in kw_weights.items():
            if kw in norm:
                category_scores[cat] += weight

    # 1b. Pattern matching (strong signal — adds 2.0 per match)
    for cat, patterns in CATEGORY_PATTERNS.items():
        for pat in patterns:
            if pat.search(raw_text):
                category_scores[cat] += 2.0

    # Pick the best category
    best_cat = max(category_scores, key=lambda c: category_scores[c])
    best_score = category_scores[best_cat]
    total_score = sum(category_scores.values())

    if total_score > 0 and best_score > 0:
        # Confidence = share of the best category in total + base from absolute score
        relative = best_score / total_score
        # Absolute component: score of 3+ → full confidence
        absolute = min(best_score / 3.0, 1.0)
        category_confidence = 0.5 * relative + 0.5 * absolute
    else:
        best_cat = "general"
        category_confidence = 0.2  # very low — nothing matched

    category_confidence = round(min(category_confidence, 1.0), 3)

    # ── 2. Priority classification ──────────────────────────────────────
    priority = TicketPriorityEnum.MEDIUM
    priority_conf = 0.5  # default medium confidence for medium priority

    # 2a. Keyword-based priority
    best_prio_rank = _PRIORITY_RANK[TicketPriorityEnum.MEDIUM]
    best_prio_weight = 0.0
    for kw, (prio, weight) in PRIORITY_KEYWORDS.items():
        if kw in norm:
            rank = _PRIORITY_RANK[prio]
            if rank > best_prio_rank or (rank == best_prio_rank and weight > best_prio_weight):
                best_prio_rank = rank
                best_prio_weight = weight
                priority = prio
                priority_conf = weight

    # 2b. Urgency tone boost
    tone_urgent, tone_intensity = _has_urgency_tone(raw_text)
    if tone_urgent:
        if _PRIORITY_RANK[priority] < _PRIORITY_RANK[TicketPriorityEnum.HIGH]:
            priority = TicketPriorityEnum.HIGH
            priority_conf = max(priority_conf, 0.5 + tone_intensity * 0.3)
        elif _PRIORITY_RANK[priority] == _PRIORITY_RANK[TicketPriorityEnum.HIGH]:
            # Could push to urgent if tone is very strong
            if tone_intensity >= 0.7:
                priority = TicketPriorityEnum.URGENT
                priority_conf = max(priority_conf, 0.7)

    # 2c. Financial risk auto-boost
    if _detect_financial_risk(norm):
        flags.append("financial_risk")
        if _PRIORITY_RANK[priority] < _PRIORITY_RANK[TicketPriorityEnum.HIGH]:
            priority = TicketPriorityEnum.HIGH
            priority_conf = max(priority_conf, 0.8)

    priority_conf = round(min(priority_conf, 1.0), 3)

    # ── 3. Special flags ────────────────────────────────────────────────
    if best_cat == "crypto" and _PRIORITY_RANK[priority] >= _PRIORITY_RANK[TicketPriorityEnum.URGENT]:
        if "security_review" not in flags:
            flags.append("security_review")

    return best_cat, category_confidence, priority, priority_conf, flags


# ---------------------------------------------------------------------------
# Smart routing with load balancing
# ---------------------------------------------------------------------------

# Preferred agent per category (ordered by preference)
_CATEGORY_AGENT_PREFERENCE: dict[str, list[str]] = {
    "billing": ["support_responder_billing", "support_responder_senior", "support_responder"],
    "technical": ["support_responder_tech", "support_responder_senior", "support_responder"],
    "account": ["support_responder_account", "support_responder_senior", "support_responder"],
    "crypto": ["support_responder_crypto", "support_responder_senior", "support_responder"],
    "general": ["support_responder", "support_responder_senior"],
}


def route_to_agent(
    category: str,
    priority: TicketPriorityEnum,
    current_loads: dict[str, int] | None = None,
) -> str:
    """Determine the best agent for a ticket, considering load balancing.

    Parameters
    ----------
    category:
        The classified category of the ticket.
    priority:
        The classified priority.
    current_loads:
        Optional mapping of ``{agent_name: current_ticket_count}``.
        When provided, an overloaded agent (at or above ``max_load``) is
        skipped in favour of the next-best option.

    Returns
    -------
    str
        The name of the agent that should handle the ticket.
    """
    # Urgent / high tickets go to senior by default
    if priority in (TicketPriorityEnum.URGENT, TicketPriorityEnum.HIGH):
        preferred = ["support_responder_senior"]
        # Append category specialist as fallback
        cat_prefs = _CATEGORY_AGENT_PREFERENCE.get(category, [])
        preferred.extend(p for p in cat_prefs if p not in preferred)
    else:
        preferred = list(_CATEGORY_AGENT_PREFERENCE.get(category, ["support_responder"]))

    if current_loads is None:
        return preferred[0]

    # Pick the first agent that is not overloaded
    for agent in preferred:
        agent_info = AGENT_POOL.get(agent, {})
        max_load: int = int(agent_info.get("max_load", 25))  # type: ignore[arg-type]
        if current_loads.get(agent, 0) < max_load:
            return agent

    # All preferred agents are overloaded — fall back to the one with lowest load
    return min(preferred, key=lambda a: current_loads.get(a, 0))


# ---------------------------------------------------------------------------
# SLA calculator
# ---------------------------------------------------------------------------


def calculate_sla(
    priority: TicketPriorityEnum,
    category: str,
    is_vip: bool = False,
) -> float:
    """Calculate the SLA deadline in hours.

    Parameters
    ----------
    priority:
        Ticket priority.
    category:
        Ticket category — crypto and billing get tighter SLAs.
    is_vip:
        VIP customers receive a 50 % reduction in SLA time.

    Returns
    -------
    float
        Deadline in hours from ticket creation.
    """
    base = _BASE_SLA.get(priority, 24.0)
    multiplier = _CATEGORY_SLA_MULTIPLIER.get(category, 1.0)
    sla = base * multiplier
    if is_vip:
        sla *= 0.5
    return round(sla, 2)


# ---------------------------------------------------------------------------
# Escalation rules
# ---------------------------------------------------------------------------


def should_escalate(
    ticket_age_hours: float,
    priority: TicketPriorityEnum,
    sla_deadline: float,
    num_interactions: int,
) -> bool:
    """Decide whether a ticket should be escalated.

    Escalation triggers:
    * Ticket age has reached 80 % of the SLA deadline.
    * Customer has sent 3+ messages without resolution.
    * Priority is ``URGENT`` and ticket is older than 1 hour.

    Parameters
    ----------
    ticket_age_hours:
        How many hours the ticket has been open.
    priority:
        Current ticket priority.
    sla_deadline:
        SLA deadline in hours (as returned by ``calculate_sla``).
    num_interactions:
        Number of customer messages / interactions on the ticket.

    Returns
    -------
    bool
        ``True`` if the ticket should be escalated.
    """
    # Rule 1: approaching SLA (>= 80 % consumed)
    if sla_deadline > 0 and ticket_age_hours >= sla_deadline * 0.8:
        return True

    # Rule 2: 3+ customer messages without resolution
    if num_interactions >= 3:
        return True

    # Rule 3: urgent ticket older than 1 hour
    if priority == TicketPriorityEnum.URGENT and ticket_age_hours >= 1.0:
        return True

    return False


# ---------------------------------------------------------------------------
# Full routing pipeline
# ---------------------------------------------------------------------------


def full_route(
    subject: str,
    description: str,
    is_vip: bool = False,
    current_loads: dict[str, int] | None = None,
    ticket_age_hours: float = 0.0,
    num_interactions: int = 0,
) -> RoutingDecision:
    """Run the entire routing pipeline and return a :class:`RoutingDecision`.

    This is the primary entry-point for callers that want a single call to
    obtain classification, routing, SLA and escalation information.
    """
    category, cat_conf, priority, prio_conf, flags = classify_ticket(subject, description)

    # Crypto + urgent → security flag (may already be added)
    if category == "crypto" and priority == TicketPriorityEnum.URGENT:
        if "security_review" not in flags:
            flags.append("security_review")

    agent = route_to_agent(category, priority, current_loads)
    sla = calculate_sla(priority, category, is_vip)

    requires_review = cat_conf < 0.5 or prio_conf < 0.5

    escalation = should_escalate(ticket_age_hours, priority, sla, num_interactions)

    return RoutingDecision(
        category=category,
        category_confidence=cat_conf,
        priority=priority,
        priority_confidence=prio_conf,
        assigned_agent=agent,
        requires_human_review=requires_review,
        escalation_needed=escalation,
        sla_hours=sla,
        flags=flags,
    )
