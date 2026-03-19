"""Tests for CRM integration adapters."""

import csv
import io
import tempfile
from pathlib import Path

from xcapitsff.integrations.crm import (
    CSV_FIELD_MAPPING,
    CrmFactory,
    CrmFieldMapping,
    CrmSyncEngine,
    CsvAdapter,
    DEFAULT_MAPPINGS,
    ExportResult,
    HUBSPOT_FIELD_MAPPING,
    HubSpotAdapter,
    SALESFORCE_FIELD_MAPPING,
    SalesforceAdapter,
    SyncResult,
)


# ---------------------------------------------------------------------------
# CsvAdapter — import
# ---------------------------------------------------------------------------


def test_csv_import_from_content():
    """CsvAdapter imports leads from in-memory CSV content."""
    csv_text = "company_name,contact_name,contact_email\nAcme,John,john@acme.com\nBeta,Jane,jane@beta.com"
    adapter = CsvAdapter({"csv_content": csv_text})
    leads = adapter.import_leads()
    assert len(leads) == 2
    assert leads[0]["company_name"] == "Acme"
    assert leads[1]["contact_email"] == "jane@beta.com"


def test_csv_import_from_file():
    """CsvAdapter imports leads from a real CSV file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["company_name", "contact_name", "contact_email"])
        writer.writerow(["TestCo", "Alice", "alice@testco.com"])
        f.flush()
        path = f.name

    adapter = CsvAdapter({"file_path": path})
    leads = adapter.import_leads()
    assert len(leads) == 1
    assert leads[0]["contact_name"] == "Alice"

    Path(path).unlink(missing_ok=True)


def test_csv_import_auto_detect_aliases():
    """CsvAdapter auto-detects Spanish/alternate header names."""
    csv_text = "empresa,nombre,correo\nXcapit,Carlos,carlos@xcapit.com"
    adapter = CsvAdapter({"csv_content": csv_text})
    leads = adapter.import_leads()
    assert len(leads) == 1
    assert leads[0]["company_name"] == "Xcapit"
    assert leads[0]["contact_name"] == "Carlos"
    assert leads[0]["contact_email"] == "carlos@xcapit.com"


def test_csv_import_empty():
    """CsvAdapter returns empty list when no content/file provided."""
    adapter = CsvAdapter({})
    leads = adapter.import_leads()
    assert leads == []


# ---------------------------------------------------------------------------
# CsvAdapter — export
# ---------------------------------------------------------------------------


def test_csv_export_in_memory():
    """CsvAdapter exports leads to an in-memory buffer."""
    adapter = CsvAdapter({})
    leads = [
        {"company_name": "Acme", "contact_name": "John", "contact_email": "john@acme.com"},
        {"company_name": "Beta", "contact_name": "Jane", "contact_email": "jane@beta.com"},
    ]
    result = adapter.export_leads(leads)
    assert result.success is True
    assert result.exported_count == 2
    assert len(result.ids) == 2
    assert adapter.get_exported_data() == leads


def test_csv_export_to_file():
    """CsvAdapter exports leads to a CSV file on disk."""
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
        path = f.name

    leads = [
        {"company_name": "FileCo", "contact_email": "info@fileco.com"},
    ]
    adapter = CsvAdapter({"output_path": path})
    result = adapter.export_leads(leads)
    assert result.success is True
    assert result.exported_count == 1

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["company_name"] == "FileCo"

    Path(path).unlink(missing_ok=True)


def test_csv_export_empty():
    """CsvAdapter handles empty export gracefully."""
    adapter = CsvAdapter({})
    result = adapter.export_leads([])
    assert result.success is True
    assert result.exported_count == 0


# ---------------------------------------------------------------------------
# CsvAdapter — contacts & sync_status
# ---------------------------------------------------------------------------


def test_csv_import_contacts():
    """CsvAdapter.import_contacts returns same as import_leads."""
    csv_text = "company_name,contact_email\nAcme,a@acme.com"
    adapter = CsvAdapter({"csv_content": csv_text})
    contacts = adapter.import_contacts()
    assert len(contacts) == 1
    assert contacts[0]["contact_email"] == "a@acme.com"


def test_csv_sync_status_returns_false():
    """CsvAdapter.sync_status always returns False (no-op)."""
    adapter = CsvAdapter({})
    assert adapter.sync_status("123", "qualified") is False


# ---------------------------------------------------------------------------
# Field mapping correctness
# ---------------------------------------------------------------------------


def test_salesforce_field_mapping_to_crm():
    """Salesforce mapping converts XcapitSFF fields to SF field names."""
    data = {"company_name": "Acme", "contact_email": "a@acme.com", "stage": "qualified"}
    crm_data = SALESFORCE_FIELD_MAPPING.to_crm(data)
    assert crm_data["Company"] == "Acme"
    assert crm_data["Email"] == "a@acme.com"
    assert crm_data["Status"] == "qualified"


def test_salesforce_field_mapping_from_crm():
    """Salesforce mapping converts SF field names to XcapitSFF fields."""
    crm_data = {"Company": "Acme", "Email": "a@acme.com", "Status": "Open"}
    data = SALESFORCE_FIELD_MAPPING.from_crm(crm_data)
    assert data["company_name"] == "Acme"
    assert data["contact_email"] == "a@acme.com"
    assert data["stage"] == "Open"


def test_hubspot_field_mapping_to_crm():
    """HubSpot mapping converts XcapitSFF fields to HS field names."""
    data = {"company_name": "Beta", "contact_email": "b@beta.com"}
    crm_data = HUBSPOT_FIELD_MAPPING.to_crm(data)
    assert crm_data["company"] == "Beta"
    assert crm_data["email"] == "b@beta.com"


def test_hubspot_field_mapping_from_crm():
    """HubSpot mapping converts HS field names to XcapitSFF fields."""
    crm_data = {"company": "Beta", "email": "b@beta.com", "lifecyclestage": "lead"}
    data = HUBSPOT_FIELD_MAPPING.from_crm(crm_data)
    assert data["company_name"] == "Beta"
    assert data["contact_email"] == "b@beta.com"
    assert data["stage"] == "lead"


def test_field_mapping_reverse_auto_generated():
    """CrmFieldMapping auto-generates reverse_map from field_map."""
    mapping = CrmFieldMapping(
        provider_name="test",
        field_map={"a": "X", "b": "Y"},
    )
    assert mapping.reverse_map == {"X": "a", "Y": "b"}


def test_all_default_mappings_exist():
    """DEFAULT_MAPPINGS contains entries for salesforce, hubspot, pipedrive, csv."""
    assert "salesforce" in DEFAULT_MAPPINGS
    assert "hubspot" in DEFAULT_MAPPINGS
    assert "pipedrive" in DEFAULT_MAPPINGS
    assert "csv" in DEFAULT_MAPPINGS


# ---------------------------------------------------------------------------
# Mock mode for Salesforce / HubSpot
# ---------------------------------------------------------------------------


def test_salesforce_mock_import():
    """SalesforceAdapter in mock mode returns sample leads."""
    adapter = SalesforceAdapter()
    assert adapter.mock_mode is True
    leads = adapter.import_leads()
    assert len(leads) >= 1
    assert "company_name" in leads[0]
    assert "contact_email" in leads[0]


def test_salesforce_mock_export():
    """SalesforceAdapter in mock mode returns export result with IDs."""
    adapter = SalesforceAdapter()
    result = adapter.export_leads([{"company_name": "Test"}])
    assert result.success is True
    assert result.exported_count == 1
    assert len(result.ids) == 1


def test_salesforce_mock_sync_status():
    """SalesforceAdapter in mock mode sync_status returns True."""
    adapter = SalesforceAdapter()
    assert adapter.sync_status("00Q123", "qualified") is True


def test_salesforce_mock_import_contacts():
    """SalesforceAdapter in mock mode import_contacts returns contacts."""
    adapter = SalesforceAdapter()
    contacts = adapter.import_contacts()
    assert len(contacts) >= 1
    assert "contact_name" in contacts[0]


def test_hubspot_mock_import():
    """HubSpotAdapter in mock mode returns sample contacts as leads."""
    adapter = HubSpotAdapter()
    assert adapter.mock_mode is True
    leads = adapter.import_leads()
    assert len(leads) >= 1
    assert "company_name" in leads[0]


def test_hubspot_mock_export():
    """HubSpotAdapter in mock mode returns export result with IDs."""
    adapter = HubSpotAdapter()
    result = adapter.export_leads([{"company_name": "Test"}])
    assert result.success is True
    assert result.exported_count == 1
    assert len(result.ids) == 1


def test_hubspot_mock_sync_status():
    """HubSpotAdapter in mock mode sync_status returns True."""
    adapter = HubSpotAdapter()
    assert adapter.sync_status("hs-101", "qualified") is True


# ---------------------------------------------------------------------------
# SyncResult tracking
# ---------------------------------------------------------------------------


def test_sync_result_defaults():
    """SyncResult has zeroed defaults and empty error list."""
    result = SyncResult()
    assert result.imported == 0
    assert result.exported == 0
    assert result.updated == 0
    assert result.skipped == 0
    assert result.errors == []


def test_sync_from_crm_dedup():
    """CrmSyncEngine.sync_from_crm deduplicates by contact_email."""
    csv_text = (
        "company_name,contact_email\n"
        "Acme,a@acme.com\n"
        "Beta,b@beta.com\n"
        "Gamma,c@gamma.com\n"
    )
    adapter = CsvAdapter({"csv_content": csv_text})
    existing = [{"contact_email": "a@acme.com"}]
    result = CrmSyncEngine.sync_from_crm(adapter, existing)
    assert result.imported == 2
    assert result.skipped == 1


def test_sync_to_crm():
    """CrmSyncEngine.sync_to_crm tracks exported count."""
    adapter = CsvAdapter({})
    leads = [
        {"company_name": "A", "contact_email": "a@a.com"},
        {"company_name": "B", "contact_email": "b@b.com"},
    ]
    result = CrmSyncEngine.sync_to_crm(adapter, leads)
    assert result.exported == 2
    assert result.errors == []


def test_sync_to_crm_empty():
    """CrmSyncEngine.sync_to_crm with no leads returns zero."""
    adapter = CsvAdapter({})
    result = CrmSyncEngine.sync_to_crm(adapter, [])
    assert result.exported == 0


def test_two_way_sync():
    """CrmSyncEngine.two_way_sync combines import and export stats."""
    csv_text = "company_name,contact_email\nNew,new@co.com"
    adapter = CsvAdapter({"csv_content": csv_text})
    leads_to_export = [{"company_name": "Out", "contact_email": "out@co.com"}]

    result = CrmSyncEngine.two_way_sync(
        adapter,
        existing_leads=[],
        leads_to_export=leads_to_export,
    )
    assert result.imported == 1
    assert result.exported == 1


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def test_factory_returns_salesforce():
    """CrmFactory returns SalesforceAdapter for 'salesforce'."""
    provider = CrmFactory.get_provider("salesforce")
    assert isinstance(provider, SalesforceAdapter)


def test_factory_returns_hubspot():
    """CrmFactory returns HubSpotAdapter for 'hubspot'."""
    provider = CrmFactory.get_provider("hubspot")
    assert isinstance(provider, HubSpotAdapter)


def test_factory_returns_csv():
    """CrmFactory returns CsvAdapter for 'csv'."""
    provider = CrmFactory.get_provider("csv")
    assert isinstance(provider, CsvAdapter)


def test_factory_case_insensitive():
    """CrmFactory is case-insensitive."""
    provider = CrmFactory.get_provider("Salesforce")
    assert isinstance(provider, SalesforceAdapter)
    provider = CrmFactory.get_provider("HUBSPOT")
    assert isinstance(provider, HubSpotAdapter)


def test_factory_unknown_raises():
    """CrmFactory raises ValueError for unknown provider."""
    try:
        CrmFactory.get_provider("unknown_crm")
        assert False, "Should have raised ValueError"
    except ValueError as exc:
        assert "unknown_crm" in str(exc).lower() or "Unknown" in str(exc)


def test_factory_list_providers():
    """CrmFactory.list_providers returns all supported providers."""
    providers = CrmFactory.list_providers()
    assert "salesforce" in providers
    assert "hubspot" in providers
    assert "csv" in providers


# ---------------------------------------------------------------------------
# ExportResult
# ---------------------------------------------------------------------------


def test_export_result_defaults():
    """ExportResult has sensible defaults."""
    result = ExportResult(success=True)
    assert result.exported_count == 0
    assert result.errors == []
    assert result.ids == []
