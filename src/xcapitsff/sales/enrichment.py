"""Lead Enrichment — derive additional data points from existing lead information.

Enrichment runs automatically on new leads to fill in missing data
and improve scoring accuracy. No external API calls — uses heuristics
and pattern matching on available data.
"""

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class EnrichmentResult:
    lead_id: int | None = None
    fields_enriched: list[str] = field(default_factory=list)
    fields_inferred: dict = field(default_factory=dict)
    confidence: float = 0.0
    notes: list[str] = field(default_factory=list)


# Company domain → industry mapping
INDUSTRY_PATTERNS: dict[str, list[str]] = {
    "fintech": ["bank", "banco", "finance", "finanz", "capital", "invest", "crypto", "defi", "pay", "pago", "wallet"],
    "technology": ["tech", "software", "digital", "data", "cloud", "app", "sys", "dev", "code"],
    "consulting": ["consult", "advisory", "asesora", "strategy"],
    "ecommerce": ["shop", "store", "commerce", "retail", "tienda", "venta"],
    "healthcare": ["health", "salud", "medic", "pharma", "bio"],
    "education": ["edu", "learn", "university", "universidad", "academy", "escuela"],
    "energy": ["energy", "solar", "wind", "petrol", "gas", "mining", "miner"],
    "real_estate": ["real estate", "inmobili", "property", "construccion"],
}

# Email domain → company size heuristic
LARGE_COMPANY_DOMAINS = {
    "gmail.com", "hotmail.com", "yahoo.com", "outlook.com", "live.com",
    "icloud.com", "protonmail.com", "tutanota.com",
}

# Country TLDs
COUNTRY_TLDS: dict[str, str] = {
    ".ar": "Argentina", ".mx": "Mexico", ".co": "Colombia",
    ".cl": "Chile", ".pe": "Peru", ".uy": "Uruguay",
    ".br": "Brazil", ".ve": "Venezuela", ".ec": "Ecuador",
    ".bo": "Bolivia", ".py": "Paraguay",
    ".es": "Spain", ".pt": "Portugal",
}

LATAM_COUNTRIES = {"Argentina", "Mexico", "Colombia", "Chile", "Peru", "Uruguay",
                   "Brazil", "Venezuela", "Ecuador", "Bolivia", "Paraguay"}


def infer_industry(company_name: str | None, email: str | None) -> str | None:
    """Infer industry from company name and email domain."""
    text = f"{company_name or ''} {email or ''}".lower()
    for industry, keywords in INDUSTRY_PATTERNS.items():
        if any(kw in text for kw in keywords):
            return industry
    return None


def infer_company_size(email: str | None) -> str | None:
    """Infer company size from email domain.
    Free email = likely small/individual. Corporate domain = likely bigger.
    """
    if not email:
        return None
    domain = email.split("@")[-1].lower() if "@" in email else ""
    if domain in LARGE_COMPANY_DOMAINS:
        return "small"  # personal email = likely small company or individual
    if domain:
        return "medium_large"  # corporate email = established company
    return None


def infer_country_from_email(email: str | None) -> str | None:
    """Infer country from email TLD."""
    if not email or "@" not in email:
        return None
    domain = email.split("@")[-1].lower()
    for tld, country in COUNTRY_TLDS.items():
        if domain.endswith(tld):
            return country
    return None


def infer_region_from_country(country: str | None) -> str | None:
    """Map country to business region."""
    if not country:
        return None
    if country in LATAM_COUNTRIES:
        return "LATAM"
    if country in ("Spain", "Portugal"):
        return "Iberia"
    return None


def infer_seniority_from_email(email: str | None) -> bool | None:
    """Guess if contact is C-level from email prefix patterns."""
    if not email:
        return None
    prefix = email.split("@")[0].lower()
    c_level_patterns = ["ceo", "cto", "cfo", "coo", "cmo", "cio", "cpo",
                        "director", "vp", "president", "founder", "fundador",
                        "gerente.general", "gerente_general"]
    for pattern in c_level_patterns:
        if pattern in prefix:
            return True
    return None


def extract_name_from_email(email: str | None) -> str | None:
    """Try to extract a human name from email prefix."""
    if not email or "@" not in email:
        return None
    prefix = email.split("@")[0]
    # Remove common prefixes
    prefix = re.sub(r"^(info|admin|contact|ventas|sales|support|hello|hola)$", "", prefix)
    if not prefix:
        return None
    # Replace separators with spaces
    name = re.sub(r"[._-]", " ", prefix)
    # Capitalize
    name = " ".join(word.capitalize() for word in name.split() if len(word) > 1)
    return name if name else None


def enrich_lead(lead_data: dict) -> EnrichmentResult:
    """Run all enrichment heuristics on a lead.

    Takes a lead dict and returns enrichment suggestions.
    Does NOT modify the lead — caller decides what to apply.
    """
    result = EnrichmentResult(lead_id=lead_data.get("id"))

    company = lead_data.get("company_name")
    email = lead_data.get("contact_email")
    contact = lead_data.get("contact_name")
    region = lead_data.get("region")

    enrichments = 0

    # Industry
    industry = infer_industry(company, email)
    if industry:
        result.fields_inferred["industry"] = industry
        result.fields_enriched.append("industry")
        enrichments += 1

    # Company size
    size = infer_company_size(email)
    if size:
        result.fields_inferred["company_size"] = size
        result.fields_enriched.append("company_size")
        enrichments += 1

    # Country from email
    country = infer_country_from_email(email)
    if country:
        result.fields_inferred["country"] = country
        result.fields_enriched.append("country")
        enrichments += 1

        # Validate region matches
        inferred_region = infer_region_from_country(country)
        if inferred_region and region and inferred_region != region:
            result.notes.append(
                f"Region mismatch: lead says {region} but email TLD suggests {inferred_region} ({country})"
            )

    # C-level from email
    if not lead_data.get("c_level"):
        c_level = infer_seniority_from_email(email)
        if c_level:
            result.fields_inferred["c_level_inferred"] = True
            result.fields_enriched.append("c_level_inferred")
            result.notes.append("C-level status inferred from email pattern")
            enrichments += 1

    # Contact name from email
    if not contact and email:
        name = extract_name_from_email(email)
        if name:
            result.fields_inferred["contact_name"] = name
            result.fields_enriched.append("contact_name")
            enrichments += 1

    # Confidence based on how much we could enrich
    max_possible = 5
    result.confidence = round(enrichments / max_possible, 2)

    return result


def enrich_leads_batch(leads: list[dict]) -> list[EnrichmentResult]:
    """Enrich a batch of leads."""
    return [enrich_lead(lead) for lead in leads]
