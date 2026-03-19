"""Integration tests for the Webhook API."""

import pytest


@pytest.mark.asyncio
async def test_lead_webhook(client):
    resp = await client.post("/api/v1/webhooks/leads", json={
        "company_name": "Webhook Corp",
        "contact_name": "Maria Garcia",
        "contact_email": "maria@webhook.com",
        "region": "LATAM",
        "c_level": True,
        "afinidad": "HIGH",
        "source": "landing_page",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "created"
    assert data["lead_id"] > 0
    assert data["score_icp"] is not None


@pytest.mark.asyncio
async def test_ticket_webhook(client):
    # First create a customer
    await client.post("/api/v1/customers/", json={
        "company_name": "Support Customer",
        "contact_name": "Juan",
        "contact_email": "juan@support.com",
        "region": "LATAM",
    })

    resp = await client.post("/api/v1/webhooks/tickets", json={
        "customer_email": "juan@support.com",
        "subject": "No puedo hacer login",
        "description": "Olvidé mi contraseña y el reset no funciona",
        "source": "support_form",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "created"
    assert data["ticket_id"] > 0
    assert data["category"] == "account"
    assert data["assigned_agent"] is not None


@pytest.mark.asyncio
async def test_ticket_webhook_new_customer(client):
    """Webhook should auto-create customer if not found."""
    resp = await client.post("/api/v1/webhooks/tickets", json={
        "customer_email": "new@user.com",
        "subject": "Pregunta general",
        "description": "Quiero saber más sobre el producto",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "created"


@pytest.mark.asyncio
async def test_generic_webhook(client):
    resp = await client.post("/api/v1/webhooks/generic", json={
        "event": "lead.created",
        "data": {"lead_id": 99, "source": "crm"},
        "source": "salesforce",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"


@pytest.mark.asyncio
async def test_generic_webhook_unknown_event(client):
    resp = await client.post("/api/v1/webhooks/generic", json={
        "event": "unknown.event",
        "data": {},
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_events_endpoint(client):
    resp = await client.get("/api/v1/webhooks/events")
    assert resp.status_code == 200
    data = resp.json()
    assert "count" in data
    assert "events" in data


@pytest.mark.asyncio
async def test_agents_status(client):
    resp = await client.get("/api/v1/agents/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_tasks_processed" in data
    assert "rules_count" in data


@pytest.mark.asyncio
async def test_agents_rules(client):
    resp = await client.get("/api/v1/agents/rules")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] > 0
    assert len(data["rules"]) > 0
