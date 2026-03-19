"""Tests for lead data importer."""

from xcapitsff.sales.importer import parse_leads_tsv


SAMPLE_TSV = """Region\tC-Level\tScore ICP\tAfinidad Xcapit
LATAM\tSi\t35\tHIGH
LATAM\tSi\t45\tHIGH
LATAM\tNo\t\tMEDIUM
Iberia\tNo\t23\tMEDIUM
\t\t\t
LATAM\tSi\t70\tHIGH"""


def test_parse_tsv_basic():
    leads = parse_leads_tsv(SAMPLE_TSV)
    assert len(leads) == 5


def test_parse_tsv_fields():
    leads = parse_leads_tsv(SAMPLE_TSV)
    first = leads[0]
    assert first["region"] == "LATAM"
    assert first["c_level"] is True
    assert first["score_icp"] == 35.0
    assert first["afinidad"] == "HIGH"


def test_parse_tsv_no_score():
    leads = parse_leads_tsv(SAMPLE_TSV)
    no_score = leads[2]  # LATAM, No, empty, MEDIUM
    assert no_score["score_icp"] is None
    assert no_score["c_level"] is False


def test_parse_tsv_skips_empty_rows():
    leads = parse_leads_tsv(SAMPLE_TSV)
    # 6 data rows minus 1 empty = 5
    assert len(leads) == 5


def test_parse_tsv_iberia():
    leads = parse_leads_tsv(SAMPLE_TSV)
    iberia = [l for l in leads if l["region"] == "Iberia"]
    assert len(iberia) == 1
    assert iberia[0]["score_icp"] == 23.0


def test_parse_empty_content():
    leads = parse_leads_tsv("")
    assert leads == []


def test_parse_header_only():
    leads = parse_leads_tsv("Region\tC-Level\tScore ICP\tAfinidad Xcapit\n")
    assert leads == []
