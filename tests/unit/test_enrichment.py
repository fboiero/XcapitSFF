"""Tests for lead enrichment."""

from xcapitsff.sales.enrichment import (
    enrich_lead,
    enrich_leads_batch,
    extract_name_from_email,
    infer_company_size,
    infer_country_from_email,
    infer_industry,
    infer_region_from_country,
    infer_seniority_from_email,
)


def test_infer_industry_fintech():
    assert infer_industry("CryptoVault SA", None) == "fintech"


def test_infer_industry_from_email():
    assert infer_industry(None, "admin@bankplus.com") == "fintech"


def test_infer_industry_tech():
    assert infer_industry("CloudSoft Solutions", None) == "technology"


def test_infer_industry_none():
    assert infer_industry("Acme Corp", "user@acme.com") is None


def test_company_size_personal_email():
    assert infer_company_size("user@gmail.com") == "small"


def test_company_size_corporate_email():
    assert infer_company_size("user@bigcorp.com") == "medium_large"


def test_company_size_none():
    assert infer_company_size(None) is None


def test_country_from_email_ar():
    assert infer_country_from_email("user@empresa.com.ar") == "Argentina"


def test_country_from_email_mx():
    assert infer_country_from_email("user@empresa.mx") == "Mexico"


def test_country_from_email_es():
    assert infer_country_from_email("user@empresa.es") == "Spain"


def test_country_none():
    assert infer_country_from_email("user@gmail.com") is None


def test_region_latam():
    assert infer_region_from_country("Argentina") == "LATAM"
    assert infer_region_from_country("Colombia") == "LATAM"


def test_region_iberia():
    assert infer_region_from_country("Spain") == "Iberia"
    assert infer_region_from_country("Portugal") == "Iberia"


def test_seniority_ceo():
    assert infer_seniority_from_email("ceo@company.com") is True


def test_seniority_founder():
    assert infer_seniority_from_email("founder@startup.com") is True


def test_seniority_regular():
    assert infer_seniority_from_email("jsmith@company.com") is None


def test_extract_name():
    assert extract_name_from_email("juan.perez@company.com") == "Juan Perez"


def test_extract_name_underscore():
    assert extract_name_from_email("maria_garcia@empresa.com") == "Maria Garcia"


def test_extract_name_info():
    assert extract_name_from_email("info@company.com") is None


def test_enrich_lead_full():
    result = enrich_lead({
        "id": 1,
        "company_name": "CryptoVault Austral SA",
        "contact_email": "ceo@cryptovault.com.ar",
        "region": "LATAM",
    })
    assert "industry" in result.fields_enriched
    assert result.fields_inferred["industry"] == "fintech"
    assert result.fields_inferred["country"] == "Argentina"
    assert result.confidence > 0


def test_enrich_lead_name_extraction():
    result = enrich_lead({
        "contact_email": "carlos.lopez@empresa.com",
    })
    assert result.fields_inferred.get("contact_name") == "Carlos Lopez"


def test_enrich_lead_region_mismatch():
    result = enrich_lead({
        "contact_email": "user@empresa.es",
        "region": "LATAM",
    })
    assert any("mismatch" in note for note in result.notes)


def test_enrich_batch():
    results = enrich_leads_batch([
        {"company_name": "Bank SA", "contact_email": "a@bank.com.ar"},
        {"company_name": "Tech Corp"},
    ])
    assert len(results) == 2


def test_enrich_empty_lead():
    result = enrich_lead({})
    assert result.confidence == 0
    assert len(result.fields_enriched) == 0
