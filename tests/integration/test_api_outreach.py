"""Integration tests for the Outreach API."""

import pytest


async def _create_lead(client, **overrides) -> int:
    data = {
        "company_name": "Outreach Test Corp",
        "contact_name": "Carlos Lopez",
        "contact_email": "carlos@test.com",
        "region": "LATAM",
        "c_level": True,
        "afinidad": "HIGH",
        **overrides,
    }
    resp = await client.post("/api/v1/leads/", json=data)
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_compose_outreach_email(client):
    lead_id = await _create_lead(client)
    resp = await client.post(f"/api/v1/outreach/compose/{lead_id}?channel=email")
    assert resp.status_code == 200
    data = resp.json()
    assert data["lead_id"] == lead_id
    assert data["channel"] == "email"
    assert data["subject"] is not None
    assert len(data["body"]) > 0
    assert data["personalization_score"] > 0


@pytest.mark.asyncio
async def test_compose_outreach_whatsapp(client):
    lead_id = await _create_lead(client)
    resp = await client.post(f"/api/v1/outreach/compose/{lead_id}?channel=whatsapp")
    assert resp.status_code == 200
    data = resp.json()
    assert data["channel"] == "whatsapp"


@pytest.mark.asyncio
async def test_compose_outreach_not_found(client):
    resp = await client.post("/api/v1/outreach/compose/9999?channel=email")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_ab_variants(client):
    lead_id = await _create_lead(client)
    resp = await client.post(f"/api/v1/outreach/ab-test/{lead_id}?channel=email")
    assert resp.status_code == 200
    data = resp.json()
    assert "variant_a" in data
    assert "variant_b" in data
    assert data["variant_a"]["body"] != data["variant_b"]["body"]


@pytest.mark.asyncio
async def test_followup(client):
    lead_id = await _create_lead(client)
    resp = await client.post(f"/api/v1/outreach/followup/{lead_id}?attempt=1&channel=email")
    assert resp.status_code == 200
    data = resp.json()
    assert data["attempt"] == 1
    assert len(data["body"]) > 0


@pytest.mark.asyncio
async def test_send_outreach(client):
    lead_id = await _create_lead(client)
    resp = await client.post(
        f"/api/v1/outreach/send/{lead_id}",
        params={
            "channel": "email",
            "subject": "Test Subject",
            "body": "Este es un mensaje de prueba para el lead.",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "sent"
    assert data["message_id"] > 0


@pytest.mark.asyncio
async def test_outreach_history(client):
    lead_id = await _create_lead(client)
    # Send one message first
    await client.post(
        f"/api/v1/outreach/send/{lead_id}",
        params={"channel": "linkedin", "body": "Hola, te contacto desde Xcapit."},
    )

    resp = await client.get(f"/api/v1/outreach/history/{lead_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["lead_id"] == lead_id


@pytest.mark.asyncio
async def test_system_info(client):
    resp = await client.get("/api/v1/system/info")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "XcapitSFF"
    assert "version" in data


@pytest.mark.asyncio
async def test_system_status(client):
    resp = await client.get("/api/v1/system/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "operational"
    assert "agents" in data
    assert "events" in data


@pytest.mark.asyncio
async def test_system_modules(client):
    resp = await client.get("/api/v1/system/modules")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["modules"]) >= 5


@pytest.mark.asyncio
async def test_dashboard_full(client):
    resp = await client.get("/api/v1/dashboard/")
    assert resp.status_code == 200
    data = resp.json()
    assert "sales" in data
    assert "support" in data
    assert "agents" in data
    assert "notifications" in data


@pytest.mark.asyncio
async def test_notifications_endpoint(client):
    resp = await client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    data = resp.json()
    assert "count" in data
    assert "notifications" in data


@pytest.mark.asyncio
async def test_notifications_counts(client):
    resp = await client.get("/api/v1/notifications/counts")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
