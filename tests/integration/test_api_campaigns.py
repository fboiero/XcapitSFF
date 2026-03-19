"""Integration tests for the Campaigns API."""

import pytest


@pytest.mark.asyncio
async def test_create_campaign(client):
    resp = await client.post("/api/v1/campaigns/", json={
        "name": "Q1 LATAM Outreach",
        "campaign_type": "outreach",
        "channel": "email",
        "regions": ["LATAM"],
        "score_min": 50,
        "c_level_only": True,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["campaign_id"].startswith("CAMP-")
    assert data["status"] == "draft"
    assert data["target"]["c_level_only"] is True


@pytest.mark.asyncio
async def test_list_campaigns(client):
    await client.post("/api/v1/campaigns/", json={
        "name": "Campaign A", "campaign_type": "outreach",
    })
    await client.post("/api/v1/campaigns/", json={
        "name": "Campaign B", "campaign_type": "nurturing",
    })
    resp = await client.get("/api/v1/campaigns/")
    assert resp.status_code == 200
    assert resp.json()["count"] >= 2


@pytest.mark.asyncio
async def test_campaign_lifecycle(client):
    # Create
    create_resp = await client.post("/api/v1/campaigns/", json={
        "name": "Lifecycle Test", "campaign_type": "outreach",
    })
    campaign_id = create_resp.json()["campaign_id"]

    # Start
    start_resp = await client.post(f"/api/v1/campaigns/{campaign_id}/start")
    assert start_resp.status_code == 200
    assert start_resp.json()["status"] == "active"

    # Pause
    pause_resp = await client.post(f"/api/v1/campaigns/{campaign_id}/pause")
    assert pause_resp.json()["status"] == "paused"

    # Complete
    complete_resp = await client.post(f"/api/v1/campaigns/{campaign_id}/complete")
    assert complete_resp.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_campaign_stats(client):
    await client.post("/api/v1/campaigns/", json={
        "name": "Stats Test", "campaign_type": "outreach",
    })
    resp = await client.get("/api/v1/campaigns/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_campaigns" in data
    assert data["total_campaigns"] >= 1


@pytest.mark.asyncio
async def test_campaign_not_found(client):
    resp = await client.get("/api/v1/campaigns/CAMP-9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cannot_start_twice(client):
    create_resp = await client.post("/api/v1/campaigns/", json={
        "name": "Double Start", "campaign_type": "outreach",
    })
    cid = create_resp.json()["campaign_id"]
    await client.post(f"/api/v1/campaigns/{cid}/start")
    resp = await client.post(f"/api/v1/campaigns/{cid}/start")
    assert resp.status_code == 400
