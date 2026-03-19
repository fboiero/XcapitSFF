"""Integration tests for Search and Batch APIs."""

import pytest


@pytest.mark.asyncio
async def test_search_empty_db(client):
    resp = await client.get("/api/v1/search/?q=test")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_search_finds_lead(client):
    await client.post("/api/v1/leads/", json={
        "company_name": "Acme Fintech",
        "contact_name": "Carlos",
        "region": "LATAM",
        "c_level": True,
        "afinidad": "HIGH",
    })
    resp = await client.get("/api/v1/search/?q=Acme")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert data["results"][0]["type"] == "lead"


@pytest.mark.asyncio
async def test_search_type_filter(client):
    await client.post("/api/v1/leads/", json={
        "company_name": "Filtered Corp", "region": "LATAM", "c_level": False, "afinidad": "LOW",
    })
    resp = await client.get("/api/v1/search/?q=Filtered&types=ticket")
    assert resp.status_code == 200
    # Should not find the lead since we filtered to tickets only
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_search_short_query(client):
    resp = await client.get("/api/v1/search/?q=a")
    assert resp.status_code == 422  # too short


@pytest.mark.asyncio
async def test_batch_create_leads(client):
    resp = await client.post("/api/v1/batch/leads", json={
        "leads": [
            {"company_name": "Batch A", "region": "LATAM", "c_level": True, "afinidad": "HIGH"},
            {"company_name": "Batch B", "region": "Iberia", "c_level": False, "afinidad": "MEDIUM"},
        ],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] == 2
    assert data["errors"] == 0


@pytest.mark.asyncio
async def test_batch_actions(client):
    # Create some leads first
    await client.post("/api/v1/leads/", json={
        "region": "LATAM", "c_level": True, "afinidad": "HIGH", "score_icp": 80,
    })

    resp = await client.post("/api/v1/batch/actions", json={
        "actions": [
            {"action": "bulk_qualify", "params": {"score_threshold": 50}},
            {"action": "bulk_rescore", "params": {}},
        ],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert all(r["status"] == "completed" for r in data["results"])


@pytest.mark.asyncio
async def test_batch_unknown_action(client):
    resp = await client.post("/api/v1/batch/actions", json={
        "actions": [{"action": "unknown_action"}],
    })
    assert resp.status_code == 200
    assert resp.json()["results"][0]["status"] == "error"


@pytest.mark.asyncio
async def test_report_executive_json(client):
    resp = await client.get("/api/v1/reports/executive?format=json")
    assert resp.status_code == 200
    data = resp.json()
    assert "title" in data
    assert "sections" in data


@pytest.mark.asyncio
async def test_report_executive_text(client):
    resp = await client.get("/api/v1/reports/executive?format=text")
    assert resp.status_code == 200
    assert "XcapitSFF" in resp.text


@pytest.mark.asyncio
async def test_report_executive_markdown(client):
    resp = await client.get("/api/v1/reports/executive?format=markdown")
    assert resp.status_code == 200
    assert "# " in resp.text
