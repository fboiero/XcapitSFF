"""Conversational Onboarding — the wizard as a chat conversation.

Instead of filling forms step by step, the user talks to the assistant
and the system extracts the configuration from the conversation naturally.

"Somos una fintech de Buenos Aires, 20 personas, vendemos a empresas grandes"
→ System extracts: industry=fintech, region=LATAM, size=11-50, b2b=true
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class OnboardingState:
    tenant_id: str
    company_name: str | None = None
    industry: str | None = None
    company_size: str | None = None
    market: str | None = None  # LATAM, Iberia, Global
    use_sales: bool = True
    use_support: bool = True
    use_agents: bool = True
    import_source: str | None = None  # csv, salesforce, hubspot
    agent_language: str = "es_latam"
    completed_topics: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)

    @property
    def completion_rate(self) -> float:
        required = ["company_name", "industry", "market"]
        done = sum(1 for f in required if getattr(self, f))
        return round(done / len(required) * 100, 1)

    @property
    def is_ready(self) -> bool:
        return self.company_name is not None and self.industry is not None


INDUSTRY_KEYWORDS = {
    "fintech": ["fintech", "financiera", "banco", "pagos", "crypto", "cripto", "inversión", "inversiones", "billetera", "wallet"],
    "technology": ["software", "tecnología", "tech", "saas", "plataforma", "app", "desarrollo"],
    "consulting": ["consultoría", "consultora", "asesoría", "advisory"],
    "ecommerce": ["ecommerce", "tienda", "comercio", "venta online", "marketplace"],
    "healthcare": ["salud", "médico", "pharma", "farmacéutica", "hospital"],
    "education": ["educación", "universidad", "escuela", "edtech", "cursos"],
    "real_estate": ["inmobiliaria", "real estate", "propiedades", "construcción"],
}

SIZE_PATTERNS = [
    (r"\b(\d+)\s*(personas?|empleados?|gente)\b", lambda m: _size_from_number(int(m.group(1)))),
    (r"\bsomos\s+(\d+)\b", lambda m: _size_from_number(int(m.group(1)))),
    (r"\bstartup\b", lambda _: "1-10"),
    (r"\bpyme\b", lambda _: "11-50"),
    (r"\bempresa\s+grande\b", lambda _: "200+"),
    (r"\bcorporaci[oó]n\b", lambda _: "200+"),
]

MARKET_KEYWORDS = {
    "LATAM": ["latam", "latinoamérica", "argentina", "buenos aires", "méxico", "colombia", "chile", "perú", "uruguay", "brasil"],
    "Iberia": ["iberia", "españa", "madrid", "barcelona", "portugal", "lisboa"],
    "Global": ["global", "mundial", "internacional", "varios países"],
}


def _size_from_number(n: int) -> str:
    if n <= 10:
        return "1-10"
    if n <= 50:
        return "11-50"
    if n <= 200:
        return "51-200"
    return "200+"


def extract_onboarding_data(text: str, state: OnboardingState) -> tuple[OnboardingState, list[str]]:
    """Extract configuration data from natural conversation text.

    Returns updated state and list of what was extracted (for feedback to user).
    """
    lower = text.lower()
    extracted = []

    # Company name — look for quotes or "somos X" / "empresa X" / "se llama X"
    if not state.company_name:
        name_patterns = [
            r'(?:somos|empresa|compañía|se llama|nos llamamos)\s+["\']?([A-Z][A-Za-z\s]{2,30})',
            r'"([^"]{3,40})"',
            r"'([^']{3,40})'",
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text)
            if match:
                state.company_name = match.group(1).strip()
                extracted.append(f"empresa: {state.company_name}")
                break

    # Industry
    if not state.industry:
        for industry, keywords in INDUSTRY_KEYWORDS.items():
            if any(kw in lower for kw in keywords):
                state.industry = industry
                extracted.append(f"industria: {industry}")
                break

    # Company size
    if not state.company_size:
        for pattern, extractor in SIZE_PATTERNS:
            match = re.search(pattern, lower)
            if match:
                state.company_size = extractor(match)
                extracted.append(f"tamaño: {state.company_size}")
                break

    # Market
    if not state.market:
        for market, keywords in MARKET_KEYWORDS.items():
            if any(kw in lower for kw in keywords):
                state.market = market
                extracted.append(f"mercado: {market}")
                break

    # Modules
    if "soporte" in lower or "ticket" in lower or "atención" in lower:
        state.use_support = True
        if "soporte" not in state.completed_topics:
            extracted.append("módulo: soporte activado")
            state.completed_topics.append("soporte")

    if "no necesito soporte" in lower or "sin soporte" in lower:
        state.use_support = False
        extracted.append("módulo: soporte desactivado")

    if "ventas" in lower or "leads" in lower or "pipeline" in lower or "comercial" in lower:
        state.use_sales = True
        if "ventas" not in state.completed_topics:
            extracted.append("módulo: ventas activado")
            state.completed_topics.append("ventas")

    # Import source
    if "salesforce" in lower:
        state.import_source = "salesforce"
        extracted.append("importar desde: Salesforce")
    elif "hubspot" in lower:
        state.import_source = "hubspot"
        extracted.append("importar desde: HubSpot")
    elif "csv" in lower or "excel" in lower or "planilla" in lower:
        state.import_source = "csv"
        extracted.append("importar desde: CSV")

    # Language
    if "españa" in lower or "iberia" in lower or "madrid" in lower:
        state.agent_language = "es_iberia"
        extracted.append("idioma agentes: español peninsular")

    return state, extracted


def get_next_question(state: OnboardingState) -> str:
    """Get the next question to ask based on what's missing."""
    if not state.company_name:
        return "¿Cómo se llama tu empresa?"
    if not state.industry:
        return "¿En qué industria están? (fintech, tech, consultoría, ecommerce, etc.)"
    if not state.company_size:
        return "¿Cuántas personas son en el equipo?"
    if not state.market:
        return "¿En qué mercado operan? (LATAM, Iberia, Global)"
    if state.import_source is None and "import" not in state.completed_topics:
        return "¿Tienen datos existentes que quieran importar? (CSV, Salesforce, HubSpot, o empezar de cero)"
    return ""  # All basic info gathered


def generate_onboarding_response(text: str, state: OnboardingState) -> tuple[str, OnboardingState, dict | None]:
    """Process user message during onboarding and generate response.

    Returns (response_text, updated_state, visual_component_or_None)
    """
    state, extracted = extract_onboarding_data(text, state)

    if extracted:
        ack = "Entendido. " + ", ".join(extracted) + "."
    else:
        ack = ""

    next_q = get_next_question(state)

    if state.is_ready and not next_q:
        # Onboarding complete — show summary
        summary = (
            f"{'✓ ' + ack + chr(10) if ack else ''}"
            f"¡Perfecto! Ya tengo todo lo que necesito.\n\n"
            f"**Resumen de configuración:**\n"
            f"- Empresa: {state.company_name}\n"
            f"- Industria: {state.industry}\n"
            f"- Tamaño: {state.company_size or 'No especificado'}\n"
            f"- Mercado: {state.market or 'No especificado'}\n"
            f"- Ventas: {'Sí' if state.use_sales else 'No'}\n"
            f"- Soporte: {'Sí' if state.use_support else 'No'}\n"
            f"- Agentes AI: {'Sí' if state.use_agents else 'No'}\n"
            f"- Importar desde: {state.import_source or 'Empezar de cero'}\n\n"
            f"¿Querés que active tu workspace con esta configuración?"
        )
        visual = {
            "type": "progress_bar",
            "title": "Onboarding",
            "data": {"current": 100, "total": 100, "percentage": 100, "label": "¡Completo!"},
        }
        return summary, state, visual

    # Still gathering info
    pct = state.completion_rate
    response = f"{ack}\n\n{next_q}" if ack else next_q
    visual = {
        "type": "progress_bar",
        "title": "Configuración",
        "data": {"current": int(pct), "total": 100, "percentage": pct, "label": f"{pct:.0f}% completado"},
    }
    return response.strip(), state, visual
