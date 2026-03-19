"""Tests for lead deduplication."""

from xcapitsff.sales.dedup import _company_similarity, _normalize_company, _normalize_email


def test_normalize_company_basic():
    # "Corp" and "SA" are both stripped as suffixes
    assert _normalize_company("Acme Corp SA") == "acme"


def test_normalize_company_srl():
    assert _normalize_company("Tech Solutions S.R.L.") == "tech solutions"


def test_normalize_company_accents():
    assert _normalize_company("Tecnología Avanzada") == "tecnologia avanzada"


def test_normalize_company_none():
    assert _normalize_company(None) == ""


def test_normalize_email():
    assert _normalize_email("User@Company.COM") == "user@company.com"


def test_normalize_email_none():
    assert _normalize_email(None) == ""


def test_similarity_exact():
    assert _company_similarity("acme corp", "acme corp") == 1.0


def test_similarity_contains():
    sim = _company_similarity("acme", "acme international")
    assert sim > 0.2  # "acme" is contained in "acme international"


def test_similarity_different():
    sim = _company_similarity("apple", "orange")
    assert sim == 0.0


def test_similarity_token_overlap():
    sim = _company_similarity("tech solutions", "tech innovations")
    assert sim > 0.0  # "tech" overlaps


def test_similarity_empty():
    assert _company_similarity("", "anything") == 0.0
    assert _company_similarity("anything", "") == 0.0
