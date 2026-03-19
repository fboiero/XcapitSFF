"""CRM integration adapters for importing/exporting data with popular CRM systems.

Provides a provider-based architecture for CRM integration:

- ``CrmProvider``: abstract base for CRM backends.
- ``SalesforceAdapter``: Salesforce REST API integration.
- ``HubSpotAdapter``: HubSpot CRM API integration.
- ``CsvAdapter``: local CSV file import/export (always available).
- ``CrmSyncEngine``: orchestrates import/export and deduplication.
- ``CrmFactory``: creates the correct provider by name.

Typical usage::

    provider = CrmFactory.get_provider("salesforce", {"access_token": "..."})
    leads = provider.import_leads()
"""

from __future__ import annotations

import csv
import io
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ExportResult:
    """Outcome of an export operation to a CRM.

    Attributes:
        success: Whether the overall export succeeded.
        exported_count: Number of records successfully exported.
        errors: List of error messages for failed records.
        ids: CRM-side IDs assigned to exported records.
    """

    success: bool
    exported_count: int = 0
    errors: list[str] = field(default_factory=list)
    ids: list[str] = field(default_factory=list)


@dataclass
class SyncResult:
    """Outcome of a sync operation between XcapitSFF and a CRM.

    Attributes:
        imported: Number of records imported from CRM.
        exported: Number of records exported to CRM.
        updated: Number of existing records updated.
        skipped: Number of duplicate/unchanged records skipped.
        errors: List of error messages encountered during sync.
    """

    imported: int = 0
    exported: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class CrmFieldMapping:
    """Maps XcapitSFF internal field names to CRM-specific field names.

    Attributes:
        provider_name: Name of the CRM provider this mapping applies to.
        field_map: Dict mapping XcapitSFF field names to CRM field names.
        reverse_map: Dict mapping CRM field names back to XcapitSFF field names.
    """

    provider_name: str
    field_map: dict[str, str] = field(default_factory=dict)
    reverse_map: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.field_map and not self.reverse_map:
            self.reverse_map = {v: k for k, v in self.field_map.items()}

    def to_crm(self, data: dict[str, Any]) -> dict[str, Any]:
        """Convert XcapitSFF field names to CRM field names."""
        return {
            self.field_map.get(k, k): v
            for k, v in data.items()
            if self.field_map.get(k, k) is not None
        }

    def from_crm(self, data: dict[str, Any]) -> dict[str, Any]:
        """Convert CRM field names to XcapitSFF field names."""
        return {
            self.reverse_map.get(k, k): v
            for k, v in data.items()
            if self.reverse_map.get(k, k) is not None
        }


# ---------------------------------------------------------------------------
# Default field mappings per provider
# ---------------------------------------------------------------------------


SALESFORCE_FIELD_MAPPING = CrmFieldMapping(
    provider_name="salesforce",
    field_map={
        "company_name": "Company",
        "contact_name": "Name",
        "contact_email": "Email",
        "region": "Region__c",
        "stage": "Status",
        "score_icp": "LeadScore__c",
        "notes": "Description",
        "c_level": "IsExecutive__c",
    },
)

HUBSPOT_FIELD_MAPPING = CrmFieldMapping(
    provider_name="hubspot",
    field_map={
        "company_name": "company",
        "contact_name": "firstname",
        "contact_email": "email",
        "region": "region",
        "stage": "lifecyclestage",
        "score_icp": "lead_score",
        "notes": "notes",
        "c_level": "is_executive",
    },
)

PIPEDRIVE_FIELD_MAPPING = CrmFieldMapping(
    provider_name="pipedrive",
    field_map={
        "company_name": "org_name",
        "contact_name": "name",
        "contact_email": "email",
        "region": "region",
        "stage": "stage_id",
        "score_icp": "lead_score",
        "notes": "notes",
        "c_level": "is_c_level",
    },
)

CSV_FIELD_MAPPING = CrmFieldMapping(
    provider_name="csv",
    field_map={
        "company_name": "company_name",
        "contact_name": "contact_name",
        "contact_email": "contact_email",
        "region": "region",
        "stage": "stage",
        "score_icp": "score_icp",
        "notes": "notes",
        "c_level": "c_level",
    },
)

DEFAULT_MAPPINGS: dict[str, CrmFieldMapping] = {
    "salesforce": SALESFORCE_FIELD_MAPPING,
    "hubspot": HUBSPOT_FIELD_MAPPING,
    "pipedrive": PIPEDRIVE_FIELD_MAPPING,
    "csv": CSV_FIELD_MAPPING,
}


# ---------------------------------------------------------------------------
# Provider ABC
# ---------------------------------------------------------------------------


class CrmProvider(ABC):
    """Abstract base class for CRM integration backends."""

    @abstractmethod
    def import_leads(self) -> list[dict]:
        """Import leads from the CRM.

        Returns:
            A list of dicts with XcapitSFF field names.
        """

    @abstractmethod
    def export_leads(self, leads: list[dict]) -> ExportResult:
        """Export leads to the CRM.

        Args:
            leads: List of lead dicts with XcapitSFF field names.

        Returns:
            An ``ExportResult`` indicating success/failure.
        """

    @abstractmethod
    def import_contacts(self) -> list[dict]:
        """Import contacts from the CRM.

        Returns:
            A list of dicts with XcapitSFF field names.
        """

    @abstractmethod
    def sync_status(self, lead_id: str, stage: str) -> bool:
        """Sync a lead's stage/status back to the CRM.

        Args:
            lead_id: The CRM-side lead identifier.
            stage: The new stage value.

        Returns:
            True if the update succeeded.
        """


# ---------------------------------------------------------------------------
# Salesforce adapter
# ---------------------------------------------------------------------------


_SALESFORCE_MOCK_LEADS = [
    {
        "Id": "00Q1234567890AB",
        "Company": "Fintech Austral SA",
        "Name": "Carlos Lopez",
        "Email": "carlos@fintechaustral.com.ar",
        "Region__c": "LATAM",
        "Status": "Open - Not Contacted",
        "LeadScore__c": 85.0,
        "Description": "Interested in DeFi solutions",
        "IsExecutive__c": True,
    },
    {
        "Id": "00Q1234567890CD",
        "Company": "Iberia Crypto SL",
        "Name": "Maria Garcia",
        "Email": "maria@iberiacrypto.es",
        "Region__c": "Iberia",
        "Status": "Working - Contacted",
        "LeadScore__c": 72.0,
        "Description": "Evaluating portfolio management",
        "IsExecutive__c": False,
    },
]


class SalesforceAdapter(CrmProvider):
    """Salesforce CRM adapter using the REST API.

    Uses ``httpx`` for HTTP calls. When no ``access_token`` is provided,
    operates in mock mode and returns sample data.

    Args:
        config: Dict with ``access_token``, ``instance_url``, etc.
    """

    API_VERSION = "v58.0"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.access_token: str | None = self.config.get("access_token")
        self.instance_url: str = self.config.get(
            "instance_url", "https://login.salesforce.com"
        )
        self.mock_mode = not bool(self.access_token)
        self.field_mapping = SALESFORCE_FIELD_MAPPING

        if self.mock_mode:
            logger.info("SalesforceAdapter running in MOCK mode (no credentials)")

    def _base_url(self) -> str:
        return f"{self.instance_url}/services/data/{self.API_VERSION}"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def import_leads(self) -> list[dict]:
        """GET /services/data/v58.0/query with SOQL to fetch leads."""
        if self.mock_mode:
            logger.info("Salesforce mock: returning %d sample leads", len(_SALESFORCE_MOCK_LEADS))
            return [self.field_mapping.from_crm(lead) for lead in _SALESFORCE_MOCK_LEADS]

        import httpx

        soql = (
            "SELECT Id, Company, Name, Email, Region__c, Status, "
            "LeadScore__c, Description, IsExecutive__c FROM Lead"
        )
        url = f"{self._base_url()}/query"
        response = httpx.get(url, headers=self._headers(), params={"q": soql})
        response.raise_for_status()

        records = response.json().get("records", [])
        return [self.field_mapping.from_crm(r) for r in records]

    def export_leads(self, leads: list[dict]) -> ExportResult:
        """POST /services/data/v58.0/sobjects/Lead for each lead."""
        if self.mock_mode:
            ids = [f"00Q{uuid.uuid4().hex[:12].upper()}" for _ in leads]
            logger.info("Salesforce mock: exported %d leads", len(leads))
            return ExportResult(success=True, exported_count=len(leads), ids=ids)

        import httpx

        url = f"{self._base_url()}/sobjects/Lead"
        exported_ids: list[str] = []
        errors: list[str] = []

        for lead in leads:
            crm_data = self.field_mapping.to_crm(lead)
            try:
                response = httpx.post(url, headers=self._headers(), json=crm_data)
                response.raise_for_status()
                result = response.json()
                exported_ids.append(result.get("id", "unknown"))
            except Exception as exc:
                errors.append(f"Failed to export lead: {exc}")

        return ExportResult(
            success=len(errors) == 0,
            exported_count=len(exported_ids),
            errors=errors,
            ids=exported_ids,
        )

    def import_contacts(self) -> list[dict]:
        """Import contacts from Salesforce (uses Contact sObject)."""
        if self.mock_mode:
            return [
                {
                    "contact_name": "Carlos Lopez",
                    "contact_email": "carlos@fintechaustral.com.ar",
                    "company_name": "Fintech Austral SA",
                },
            ]

        import httpx

        soql = "SELECT Id, Name, Email, Account.Name FROM Contact"
        url = f"{self._base_url()}/query"
        response = httpx.get(url, headers=self._headers(), params={"q": soql})
        response.raise_for_status()

        records = response.json().get("records", [])
        return [
            {
                "contact_name": r.get("Name", ""),
                "contact_email": r.get("Email", ""),
                "company_name": (r.get("Account") or {}).get("Name", ""),
            }
            for r in records
        ]

    def sync_status(self, lead_id: str, stage: str) -> bool:
        """PATCH /services/data/v58.0/sobjects/Lead/{lead_id} to update status."""
        if self.mock_mode:
            logger.info("Salesforce mock: sync_status %s -> %s", lead_id, stage)
            return True

        import httpx

        url = f"{self._base_url()}/sobjects/Lead/{lead_id}"
        try:
            response = httpx.patch(
                url,
                headers=self._headers(),
                json={"Status": stage},
            )
            response.raise_for_status()
            return True
        except Exception as exc:
            logger.error("Salesforce sync_status failed: %s", exc)
            return False


# ---------------------------------------------------------------------------
# HubSpot adapter
# ---------------------------------------------------------------------------


_HUBSPOT_MOCK_CONTACTS = [
    {
        "id": "hs-101",
        "properties": {
            "company": "LatAm Blockchain Labs",
            "firstname": "Ana Martinez",
            "email": "ana@latamblockchain.com",
            "region": "LATAM",
            "lifecyclestage": "lead",
            "lead_score": "90",
            "notes": "High-value prospect",
            "is_executive": "true",
        },
    },
    {
        "id": "hs-102",
        "properties": {
            "company": "EuroTech Ventures",
            "firstname": "Pedro Sanchez",
            "email": "pedro@eurotech.es",
            "region": "Iberia",
            "lifecyclestage": "subscriber",
            "lead_score": "55",
            "notes": "Exploring options",
            "is_executive": "false",
        },
    },
]


class HubSpotAdapter(CrmProvider):
    """HubSpot CRM adapter using the CRM v3 API.

    Uses ``httpx`` for HTTP calls. When no ``api_key`` is provided,
    operates in mock mode and returns sample data.

    Args:
        config: Dict with ``api_key`` (private app token).
    """

    BASE_URL = "https://api.hubapi.com"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.api_key: str | None = self.config.get("api_key")
        self.mock_mode = not bool(self.api_key)
        self.field_mapping = HUBSPOT_FIELD_MAPPING

        if self.mock_mode:
            logger.info("HubSpotAdapter running in MOCK mode (no credentials)")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _parse_hubspot_contact(self, raw: dict) -> dict:
        """Convert HubSpot contact response into flat dict, then map fields."""
        props = raw.get("properties", {})
        props["_hubspot_id"] = raw.get("id", "")
        return self.field_mapping.from_crm(props)

    def import_leads(self) -> list[dict]:
        """GET /crm/v3/objects/contacts to fetch contacts as leads."""
        if self.mock_mode:
            logger.info("HubSpot mock: returning %d sample contacts", len(_HUBSPOT_MOCK_CONTACTS))
            return [self._parse_hubspot_contact(c) for c in _HUBSPOT_MOCK_CONTACTS]

        import httpx

        url = f"{self.BASE_URL}/crm/v3/objects/contacts"
        params = {
            "limit": 100,
            "properties": "company,firstname,email,region,lifecyclestage,lead_score,notes,is_executive",
        }
        response = httpx.get(url, headers=self._headers(), params=params)
        response.raise_for_status()

        results = response.json().get("results", [])
        return [self._parse_hubspot_contact(r) for r in results]

    def export_leads(self, leads: list[dict]) -> ExportResult:
        """POST /crm/v3/objects/contacts/batch/create to export leads."""
        if self.mock_mode:
            ids = [f"hs-{uuid.uuid4().hex[:8]}" for _ in leads]
            logger.info("HubSpot mock: exported %d leads", len(leads))
            return ExportResult(success=True, exported_count=len(leads), ids=ids)

        import httpx

        url = f"{self.BASE_URL}/crm/v3/objects/contacts/batch/create"
        inputs = []
        for lead in leads:
            crm_data = self.field_mapping.to_crm(lead)
            inputs.append({"properties": crm_data})

        try:
            response = httpx.post(
                url,
                headers=self._headers(),
                json={"inputs": inputs},
            )
            response.raise_for_status()
            results = response.json().get("results", [])
            ids = [r.get("id", "unknown") for r in results]
            return ExportResult(success=True, exported_count=len(ids), ids=ids)
        except Exception as exc:
            return ExportResult(
                success=False, exported_count=0, errors=[str(exc)]
            )

    def import_contacts(self) -> list[dict]:
        """Import contacts (same as import_leads for HubSpot)."""
        return self.import_leads()

    def sync_status(self, lead_id: str, stage: str) -> bool:
        """PATCH /crm/v3/objects/contacts/{lead_id} to update lifecycle stage."""
        if self.mock_mode:
            logger.info("HubSpot mock: sync_status %s -> %s", lead_id, stage)
            return True

        import httpx

        url = f"{self.BASE_URL}/crm/v3/objects/contacts/{lead_id}"
        try:
            response = httpx.patch(
                url,
                headers=self._headers(),
                json={"properties": {"lifecyclestage": stage}},
            )
            response.raise_for_status()
            return True
        except Exception as exc:
            logger.error("HubSpot sync_status failed: %s", exc)
            return False


# ---------------------------------------------------------------------------
# CSV adapter
# ---------------------------------------------------------------------------


# Common alternate header names that map to XcapitSFF field names
_CSV_HEADER_ALIASES: dict[str, str] = {
    "company": "company_name",
    "company name": "company_name",
    "empresa": "company_name",
    "nombre empresa": "company_name",
    "name": "contact_name",
    "contact": "contact_name",
    "nombre": "contact_name",
    "nombre contacto": "contact_name",
    "email": "contact_email",
    "correo": "contact_email",
    "e-mail": "contact_email",
    "mail": "contact_email",
    "region": "region",
    "zona": "region",
    "stage": "stage",
    "etapa": "stage",
    "estado": "stage",
    "score": "score_icp",
    "puntaje": "score_icp",
    "notes": "notes",
    "notas": "notes",
    "comentarios": "notes",
    "c_level": "c_level",
    "ejecutivo": "c_level",
    "is_executive": "c_level",
}


class CsvAdapter(CrmProvider):
    """CSV file import/export adapter — always available, no API needed.

    Supports auto-detection of column mapping from header names, including
    Spanish aliases.

    Args:
        config: Dict with optional ``file_path`` (for import) and
            ``output_path`` (for export). Can also pass ``csv_content``
            as a string for in-memory operation.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.file_path: str | None = self.config.get("file_path")
        self.output_path: str | None = self.config.get("output_path")
        self.csv_content: str | None = self.config.get("csv_content")
        self.field_mapping = CSV_FIELD_MAPPING
        self._exported_data: list[dict] = []

    @staticmethod
    def _normalize_header(header: str) -> str:
        """Normalize a CSV header for alias matching."""
        return header.strip().lower().replace("_", " ").replace("-", " ")

    @classmethod
    def _detect_mapping(cls, headers: list[str]) -> dict[str, str]:
        """Auto-detect column mapping from CSV header names.

        Returns a dict mapping CSV column name -> XcapitSFF field name.
        """
        mapping: dict[str, str] = {}
        for header in headers:
            normalized = cls._normalize_header(header)
            if normalized in _CSV_HEADER_ALIASES:
                mapping[header] = _CSV_HEADER_ALIASES[normalized]
            elif normalized.replace(" ", "_") in (
                "company_name",
                "contact_name",
                "contact_email",
                "region",
                "stage",
                "score_icp",
                "notes",
                "c_level",
            ):
                mapping[header] = normalized.replace(" ", "_")
            else:
                mapping[header] = header
        return mapping

    def _read_csv(self) -> list[dict]:
        """Read CSV from file or in-memory content."""
        if self.csv_content is not None:
            reader = csv.DictReader(io.StringIO(self.csv_content))
        elif self.file_path:
            with open(self.file_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                return self._map_rows(reader)
        else:
            return []
        return self._map_rows(reader)

    def _map_rows(self, reader: csv.DictReader) -> list[dict]:
        """Apply auto-detected column mapping to rows."""
        rows: list[dict] = []
        headers = reader.fieldnames or []
        col_mapping = self._detect_mapping(list(headers))

        for row in reader:
            mapped_row: dict[str, Any] = {}
            for csv_col, value in row.items():
                xcapit_field = col_mapping.get(csv_col, csv_col)
                mapped_row[xcapit_field] = value
            rows.append(mapped_row)

        return rows

    def import_leads(self) -> list[dict]:
        """Import leads from a CSV file."""
        leads = self._read_csv()
        logger.info("CSV import: %d leads read", len(leads))
        return leads

    def export_leads(self, leads: list[dict]) -> ExportResult:
        """Export leads to a CSV file or in-memory buffer."""
        if not leads:
            return ExportResult(success=True, exported_count=0)

        all_fields = list(leads[0].keys())
        for lead in leads[1:]:
            for k in lead:
                if k not in all_fields:
                    all_fields.append(k)

        try:
            if self.output_path:
                with open(self.output_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=all_fields)
                    writer.writeheader()
                    writer.writerows(leads)
            else:
                buf = io.StringIO()
                writer = csv.DictWriter(buf, fieldnames=all_fields)
                writer.writeheader()
                writer.writerows(leads)
                self._exported_data = leads

            logger.info("CSV export: %d leads written", len(leads))
            return ExportResult(
                success=True,
                exported_count=len(leads),
                ids=[str(i) for i in range(len(leads))],
            )
        except Exception as exc:
            return ExportResult(success=False, exported_count=0, errors=[str(exc)])

    def import_contacts(self) -> list[dict]:
        """Import contacts from CSV (same format as leads)."""
        return self.import_leads()

    def sync_status(self, lead_id: str, stage: str) -> bool:
        """CSV adapter does not support live status sync."""
        logger.warning("CsvAdapter.sync_status is a no-op: %s -> %s", lead_id, stage)
        return False

    def get_exported_data(self) -> list[dict]:
        """Return data from the last in-memory export (for testing)."""
        return self._exported_data


# ---------------------------------------------------------------------------
# Sync engine
# ---------------------------------------------------------------------------


class CrmSyncEngine:
    """Orchestrates import/export between XcapitSFF and a CRM provider.

    Handles deduplication by ``contact_email`` and tracks sync results.
    """

    @staticmethod
    def sync_from_crm(
        provider: CrmProvider,
        existing_leads: list[dict] | None = None,
    ) -> SyncResult:
        """Import leads from a CRM, deduplicating against existing leads.

        Args:
            provider: The CRM provider to import from.
            existing_leads: Optional list of existing leads (dicts with
                ``contact_email``) for deduplication.

        Returns:
            A ``SyncResult`` with import stats.
        """
        result = SyncResult()
        existing_emails: set[str] = set()

        if existing_leads:
            for lead in existing_leads:
                email = lead.get("contact_email", "")
                if email:
                    existing_emails.add(email.lower())

        try:
            crm_leads = provider.import_leads()
        except Exception as exc:
            result.errors.append(f"Import failed: {exc}")
            return result

        for lead in crm_leads:
            email = lead.get("contact_email", "")
            if email and email.lower() in existing_emails:
                result.skipped += 1
            else:
                result.imported += 1
                if email:
                    existing_emails.add(email.lower())

        return result

    @staticmethod
    def sync_to_crm(
        provider: CrmProvider,
        leads: list[dict],
    ) -> SyncResult:
        """Export leads to a CRM.

        Args:
            provider: The CRM provider to export to.
            leads: List of lead dicts to export.

        Returns:
            A ``SyncResult`` with export stats.
        """
        result = SyncResult()

        if not leads:
            return result

        try:
            export_result = provider.export_leads(leads)
            result.exported = export_result.exported_count
            result.errors.extend(export_result.errors)
        except Exception as exc:
            result.errors.append(f"Export failed: {exc}")

        return result

    @staticmethod
    def two_way_sync(
        provider: CrmProvider,
        existing_leads: list[dict] | None = None,
        leads_to_export: list[dict] | None = None,
    ) -> SyncResult:
        """Perform a two-way sync: import from CRM, then export to CRM.

        Args:
            provider: The CRM provider.
            existing_leads: Existing leads for dedup during import.
            leads_to_export: Leads to export to the CRM.

        Returns:
            A combined ``SyncResult``.
        """
        import_result = CrmSyncEngine.sync_from_crm(provider, existing_leads)
        export_result = CrmSyncEngine.sync_to_crm(provider, leads_to_export or [])

        return SyncResult(
            imported=import_result.imported,
            exported=export_result.exported,
            updated=import_result.updated + export_result.updated,
            skipped=import_result.skipped + export_result.skipped,
            errors=import_result.errors + export_result.errors,
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


class CrmFactory:
    """Factory that creates CRM provider instances by name.

    Supported providers: ``"salesforce"``, ``"hubspot"``, ``"csv"``.
    """

    _PROVIDERS: dict[str, type[CrmProvider]] = {
        "salesforce": SalesforceAdapter,
        "hubspot": HubSpotAdapter,
        "csv": CsvAdapter,
    }

    @classmethod
    def get_provider(cls, name: str, config: dict[str, Any] | None = None) -> CrmProvider:
        """Create a CRM provider by name.

        Args:
            name: Provider name (case-insensitive).
            config: Configuration dict passed to the provider constructor.

        Returns:
            A ``CrmProvider`` instance.

        Raises:
            ValueError: If the provider name is not supported.
        """
        key = name.lower().strip()
        provider_cls = cls._PROVIDERS.get(key)
        if provider_cls is None:
            supported = ", ".join(sorted(cls._PROVIDERS.keys()))
            raise ValueError(
                f"Unknown CRM provider '{name}'. Supported: {supported}"
            )
        return provider_cls(config or {})

    @classmethod
    def list_providers(cls) -> list[str]:
        """Return sorted list of supported provider names."""
        return sorted(cls._PROVIDERS.keys())
