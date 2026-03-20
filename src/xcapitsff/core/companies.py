"""Company management — CRUD, search, hierarchy, enrichment, stats."""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


VALID_SIZES = {"1-10", "11-50", "51-200", "201-1000", "1001+"}


@dataclass
class Company:
    id: str
    tenant_id: str
    name: str
    domain: str | None = None
    industry: str | None = None
    size: str | None = None  # 1-10, 11-50, 51-200, 201-1000, 1001+
    revenue_range: str | None = None
    country: str | None = None
    city: str | None = None
    address: str | None = None
    phone: str | None = None
    website: str | None = None
    logo_url: str | None = None
    description: str | None = None
    tags: list[str] = field(default_factory=list)
    custom_fields: dict[str, Any] = field(default_factory=dict)
    parent_company_id: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    owner_id: str | None = None


# Heuristic enrichment data keyed by domain suffix
_ENRICHMENT_DB: dict[str, dict[str, str]] = {
    ".com": {"country": "US", "revenue_range": "$1M-$10M"},
    ".co.uk": {"country": "UK", "revenue_range": "$1M-$10M"},
    ".com.ar": {"country": "AR", "revenue_range": "$100K-$1M"},
    ".com.br": {"country": "BR", "revenue_range": "$1M-$10M"},
    ".es": {"country": "ES", "revenue_range": "$1M-$10M"},
    ".mx": {"country": "MX", "revenue_range": "$100K-$1M"},
}


class CompanyManager:
    """In-memory company management with multi-tenant isolation."""

    def __init__(self, contact_manager: Any | None = None) -> None:
        self._companies: dict[str, Company] = {}
        self._contact_manager = contact_manager

    # --- CRUD ---

    def create(self, tenant_id: str, name: str, **kwargs: Any) -> Company:
        if not tenant_id or not tenant_id.strip():
            raise ValueError("tenant_id is required")
        if not name or not name.strip():
            raise ValueError("name is required")

        size = kwargs.get("size")
        if size is not None and size not in VALID_SIZES:
            raise ValueError(f"Invalid size: {size}. Must be one of {VALID_SIZES}")

        company_id = str(uuid.uuid4())
        now = datetime.now(tz=None)
        company = Company(
            id=company_id,
            tenant_id=tenant_id,
            name=name.strip(),
            domain=kwargs.get("domain"),
            industry=kwargs.get("industry"),
            size=size,
            revenue_range=kwargs.get("revenue_range"),
            country=kwargs.get("country"),
            city=kwargs.get("city"),
            address=kwargs.get("address"),
            phone=kwargs.get("phone"),
            website=kwargs.get("website"),
            logo_url=kwargs.get("logo_url"),
            description=kwargs.get("description"),
            tags=list(kwargs.get("tags", [])),
            custom_fields=dict(kwargs.get("custom_fields", {})),
            parent_company_id=kwargs.get("parent_company_id"),
            created_at=now,
            updated_at=now,
            owner_id=kwargs.get("owner_id"),
        )
        self._companies[company_id] = company
        logger.info("Company created: id=%s tenant=%s name=%s", company_id, tenant_id, name)
        return company

    def update(self, company_id: str, **kwargs: Any) -> Company:
        company = self._companies.get(company_id)
        if not company:
            raise KeyError(f"Company not found: {company_id}")

        if "size" in kwargs and kwargs["size"] is not None and kwargs["size"] not in VALID_SIZES:
            raise ValueError(f"Invalid size: {kwargs['size']}. Must be one of {VALID_SIZES}")

        changed: dict[str, Any] = {}
        for key, value in kwargs.items():
            if hasattr(company, key) and key not in ("id", "tenant_id", "created_at"):
                old = getattr(company, key)
                setattr(company, key, value)
                changed[key] = {"old": old, "new": value}

        company.updated_at = datetime.now(tz=None)
        logger.info("Company updated: id=%s fields=%s", company_id, list(changed.keys()))
        return company

    def delete(self, company_id: str) -> bool:
        company = self._companies.pop(company_id, None)
        if company is None:
            return False
        logger.info("Company deleted: id=%s", company_id)
        return True

    def get(self, company_id: str) -> Company:
        company = self._companies.get(company_id)
        if not company:
            raise KeyError(f"Company not found: {company_id}")
        return company

    def list_companies(
        self,
        tenant_id: str,
        industry: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Company]:
        results = [c for c in self._companies.values() if c.tenant_id == tenant_id]

        if industry is not None:
            results = [c for c in results if c.industry and c.industry.lower() == industry.lower()]
        if search:
            q = search.lower()
            results = [
                c
                for c in results
                if q in c.name.lower()
                or (c.domain and q in c.domain.lower())
                or (c.industry and q in c.industry.lower())
            ]

        results.sort(key=lambda c: c.created_at, reverse=True)
        return results[offset : offset + limit]

    def search(self, tenant_id: str, query: str) -> list[Company]:
        if not query or not query.strip():
            return []
        q = query.lower().strip()
        results: list[Company] = []
        for c in self._companies.values():
            if c.tenant_id != tenant_id:
                continue
            searchable = " ".join(
                filter(
                    None,
                    [
                        c.name,
                        c.domain or "",
                        c.industry or "",
                        c.country or "",
                        c.city or "",
                        c.description or "",
                        " ".join(c.tags),
                    ],
                )
            ).lower()
            if q in searchable:
                results.append(c)
        results.sort(key=lambda c: c.created_at, reverse=True)
        return results

    def get_hierarchy(self, company_id: str) -> dict[str, Any]:
        company = self._companies.get(company_id)
        if not company:
            raise KeyError(f"Company not found: {company_id}")

        parent: Company | None = None
        if company.parent_company_id:
            parent = self._companies.get(company.parent_company_id)

        # Siblings share the same parent
        siblings: list[Company] = []
        if company.parent_company_id:
            siblings = [
                c
                for c in self._companies.values()
                if c.parent_company_id == company.parent_company_id and c.id != company_id
            ]

        # Children have this company as parent
        children = [c for c in self._companies.values() if c.parent_company_id == company_id]

        return {
            "company": company,
            "parent": parent,
            "siblings": siblings,
            "children": children,
        }

    def get_company_contacts(self, company_id: str) -> list:
        """Delegates to ContactManager if available."""
        if not self._companies.get(company_id):
            raise KeyError(f"Company not found: {company_id}")
        if self._contact_manager:
            return self._contact_manager.get_contacts_by_company(company_id)
        return []

    def merge_companies(self, primary_id: str, secondary_id: str) -> Company:
        primary = self._companies.get(primary_id)
        secondary = self._companies.get(secondary_id)
        if not primary:
            raise KeyError(f"Primary company not found: {primary_id}")
        if not secondary:
            raise KeyError(f"Secondary company not found: {secondary_id}")
        if primary.tenant_id != secondary.tenant_id:
            raise ValueError("Cannot merge companies from different tenants")

        # Fill empty fields from secondary
        fillable_fields = [
            "domain", "industry", "size", "revenue_range", "country", "city",
            "address", "phone", "website", "logo_url", "description",
        ]
        for attr in fillable_fields:
            if not getattr(primary, attr) and getattr(secondary, attr):
                setattr(primary, attr, getattr(secondary, attr))

        # Merge tags (union)
        primary.tags = list(set(primary.tags + secondary.tags))

        # Merge custom fields (primary takes precedence)
        for key, value in secondary.custom_fields.items():
            if key not in primary.custom_fields:
                primary.custom_fields[key] = value

        # Re-parent children of secondary to primary
        for c in self._companies.values():
            if c.parent_company_id == secondary_id:
                c.parent_company_id = primary_id

        # Re-assign contacts from secondary to primary
        if self._contact_manager:
            for contact in self._contact_manager.get_contacts_by_company(secondary_id):
                contact.company_id = primary_id

        primary.updated_at = datetime.now(tz=None)

        # Remove secondary
        self._companies.pop(secondary_id, None)

        logger.info("Companies merged: primary=%s secondary=%s", primary_id, secondary_id)
        return primary

    def enrich(self, company_id: str) -> Company:
        company = self._companies.get(company_id)
        if not company:
            raise KeyError(f"Company not found: {company_id}")

        if not company.domain:
            logger.info("No domain to enrich: id=%s", company_id)
            return company

        domain = company.domain.lower()

        # Derive website from domain if missing
        if not company.website:
            company.website = f"https://{domain}"

        # Heuristic: match domain suffix
        for suffix, data in _ENRICHMENT_DB.items():
            if domain.endswith(suffix):
                if not company.country and "country" in data:
                    company.country = data["country"]
                if not company.revenue_range and "revenue_range" in data:
                    company.revenue_range = data["revenue_range"]
                break

        company.updated_at = datetime.now(tz=None)
        logger.info("Company enriched: id=%s domain=%s", company_id, domain)
        return company

    def get_stats(self, company_id: str) -> dict[str, Any]:
        company = self._companies.get(company_id)
        if not company:
            raise KeyError(f"Company not found: {company_id}")

        contact_count = 0
        if self._contact_manager:
            contact_count = len(self._contact_manager.get_contacts_by_company(company_id))

        return {
            "company_id": company_id,
            "company_name": company.name,
            "contact_count": contact_count,
            "lead_count": 0,
            "ticket_count": 0,
            "total_revenue": 0.0,
        }

    def add_tag(self, company_id: str, tag: str) -> Company:
        company = self._companies.get(company_id)
        if not company:
            raise KeyError(f"Company not found: {company_id}")
        tag = tag.strip().lower()
        if not tag:
            raise ValueError("Tag cannot be empty")
        if tag not in company.tags:
            company.tags.append(tag)
            company.updated_at = datetime.now(tz=None)
        return company

    def remove_tag(self, company_id: str, tag: str) -> Company:
        company = self._companies.get(company_id)
        if not company:
            raise KeyError(f"Company not found: {company_id}")
        tag = tag.strip().lower()
        if tag in company.tags:
            company.tags.remove(tag)
            company.updated_at = datetime.now(tz=None)
        return company
