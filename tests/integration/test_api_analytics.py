"""Integration tests for the Analytics API."""

import pytest


@pytest.mark.asyncio
async def test_executive_summary(client):
    resp = await client.get("/api/v1/analytics/executive")
    assert resp.status_code == 200
    data = resp.json()
    assert "sales" in data
    assert "support" in data
    assert "alerts" in data


@pytest.mark.asyncio
async def test_sales_funnel(client):
    # Create a lead first
    await client.post("/api/v1/leads/", json={
        "region": "LATAM", "c_level": True, "afinidad": "HIGH",
    })

    resp = await client.get("/api/v1/analytics/sales/funnel")
    assert resp.status_code == 200
    data = resp.json()
    assert "funnel" in data
    assert len(data["funnel"]) > 0


@pytest.mark.asyncio
async def test_hot_leads(client):
    # Create a high-scoring lead
    await client.post("/api/v1/leads/", json={
        "region": "LATAM", "c_level": True, "afinidad": "HIGH", "score_icp": 80,
    })

    resp = await client.get("/api/v1/analytics/sales/hot-leads")
    assert resp.status_code == 200
    data = resp.json()
    assert "count" in data
    assert "leads" in data


@pytest.mark.asyncio
async def test_overdue_tickets(client):
    resp = await client.get("/api/v1/analytics/support/overdue")
    assert resp.status_code == 200
    data = resp.json()
    assert "count" in data
    assert data["count"] == 0  # no tickets yet
