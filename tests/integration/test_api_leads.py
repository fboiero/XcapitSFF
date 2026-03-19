"""Integration tests for the Leads API."""

import pytest


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_create_lead(client):
    resp = await client.post("/api/v1/leads/", json={
        "company_name": "Acme Corp",
        "contact_name": "John Doe",
        "contact_email": "john@acme.com",
        "region": "LATAM",
        "c_level": True,
        "afinidad": "HIGH",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["company_name"] == "Acme Corp"
    assert data["c_level"] is True
    assert data["score_icp"] is not None
    assert data["score_icp"] > 0
    assert data["stage"] == "raw"


@pytest.mark.asyncio
async def test_list_leads_empty(client):
    resp = await client.get("/api/v1/leads/")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_leads_with_filter(client):
    # Create two leads
    await client.post("/api/v1/leads/", json={
        "region": "LATAM", "c_level": True, "afinidad": "HIGH",
    })
    await client.post("/api/v1/leads/", json={
        "region": "Iberia", "c_level": False, "afinidad": "LOW",
    })

    # Filter by region
    resp = await client.get("/api/v1/leads/?region=LATAM")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["region"] == "LATAM"


@pytest.mark.asyncio
async def test_get_lead_by_id(client):
    create_resp = await client.post("/api/v1/leads/", json={
        "company_name": "Test Co",
        "region": "LATAM",
        "c_level": False,
        "afinidad": "MEDIUM",
    })
    lead_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/leads/{lead_id}")
    assert resp.status_code == 200
    assert resp.json()["company_name"] == "Test Co"


@pytest.mark.asyncio
async def test_get_lead_not_found(client):
    resp = await client.get("/api/v1/leads/999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_lead_stage(client):
    create_resp = await client.post("/api/v1/leads/", json={
        "region": "LATAM", "c_level": True, "afinidad": "HIGH",
    })
    lead_id = create_resp.json()["id"]

    # Valid transition: raw -> qualified
    resp = await client.patch(f"/api/v1/leads/{lead_id}", json={
        "stage": "qualified",
    })
    assert resp.status_code == 200
    assert resp.json()["stage"] == "qualified"


@pytest.mark.asyncio
async def test_update_lead_invalid_transition(client):
    create_resp = await client.post("/api/v1/leads/", json={
        "region": "LATAM", "c_level": True, "afinidad": "HIGH",
    })
    lead_id = create_resp.json()["id"]

    # Invalid: raw -> won
    resp = await client.patch(f"/api/v1/leads/{lead_id}", json={
        "stage": "won",
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_pipeline_stats(client):
    await client.post("/api/v1/leads/", json={
        "region": "LATAM", "c_level": True, "afinidad": "HIGH",
    })
    await client.post("/api/v1/leads/", json={
        "region": "Iberia", "c_level": False, "afinidad": "LOW",
    })

    resp = await client.get("/api/v1/leads/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_leads"] == 2
    assert data["c_level_count"] == 1


@pytest.mark.asyncio
async def test_import_leads_tsv(client):
    tsv_content = "Region\tC-Level\tScore ICP\tAfinidad Xcapit\nLATAM\tSi\t45\tHIGH\nLATAM\tNo\t\tMEDIUM\n"
    resp = await client.post(
        "/api/v1/leads/import",
        files={"file": ("leads.tsv", tsv_content, "text/tab-separated-values")},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["imported"] >= 2
