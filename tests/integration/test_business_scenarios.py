"""End-to-end business scenario tests using the API client.

These tests exercise complete workflows through the HTTP API layer,
verifying that all components (routing, scoring, classification, analytics)
work together correctly in realistic business scenarios.
"""

import io

import pytest
import pytest_asyncio

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Scenario 1: New lead from webhook -> auto-qualify -> draft outreach
# ---------------------------------------------------------------------------


class TestLeadWebhookToOutreachScenario:
    """Scenario: A new lead arrives via webhook, gets scored, then bulk-qualified."""

    async def test_post_lead_via_webhook(self, client):
        """POST a lead via the webhook endpoint and verify it is created with a score."""
        payload = {
            "company_name": "TestCorp Argentina S.A.",
            "contact_name": "Juan Perez",
            "contact_email": "jperez@testcorp.com.ar",
            "region": "LATAM",
            "c_level": True,
            "score_icp": 75.0,
            "afinidad": "HIGH",
            "source": "website_form",
        }
        resp = await client.post("/api/v1/webhooks/leads", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "created"
        assert data["lead_id"] is not None
        assert data["score_icp"] is not None
        assert data["score_icp"] > 0

    async def test_lead_created_with_score_and_stage(self, client):
        """Verify a webhook-created lead has stage=raw and a computed score."""
        # Create the lead
        payload = {
            "company_name": "Fintech Patagonia S.R.L.",
            "contact_name": "Maria Lopez",
            "contact_email": "mlopez@fintechpatagonia.com",
            "region": "LATAM",
            "c_level": True,
            "score_icp": 80.0,
            "afinidad": "HIGH",
        }
        create_resp = await client.post("/api/v1/webhooks/leads", json=payload)
        assert create_resp.status_code == 200
        lead_id = create_resp.json()["lead_id"]

        # Fetch the lead directly
        get_resp = await client.get(f"/api/v1/leads/{lead_id}")
        assert get_resp.status_code == 200
        lead = get_resp.json()
        assert lead["stage"] == "raw"
        assert lead["score_icp"] is not None
        assert lead["region"] == "LATAM"
        assert lead["c_level"] is True

    async def test_bulk_qualify_changes_stage(self, client):
        """POST bulk-qualify and verify high-score leads change from raw to qualified."""
        # Create a high-score lead
        payload = {
            "company_name": "HighScore Corp",
            "contact_name": "Carlos Senior",
            "contact_email": "csenior@highscore.com",
            "region": "LATAM",
            "c_level": True,
            "score_icp": 90.0,
            "afinidad": "HIGH",
        }
        create_resp = await client.post("/api/v1/webhooks/leads", json=payload)
        assert create_resp.status_code == 200
        lead_id = create_resp.json()["lead_id"]

        # Verify it starts as raw
        lead_resp = await client.get(f"/api/v1/leads/{lead_id}")
        assert lead_resp.json()["stage"] == "raw"

        # Bulk qualify with a threshold that this lead should exceed
        qualify_resp = await client.post(
            "/api/v1/leads/bulk-qualify", params={"score_threshold": 50.0}
        )
        assert qualify_resp.status_code == 200
        qualify_data = qualify_resp.json()
        assert qualify_data["updated"] >= 1

        # Verify the lead is now qualified
        lead_resp_after = await client.get(f"/api/v1/leads/{lead_id}")
        assert lead_resp_after.json()["stage"] == "qualified"

    async def test_full_webhook_to_qualify_flow(self, client):
        """Complete flow: webhook -> verify score -> bulk-qualify -> verify stage change."""
        # Step 1: Create lead via webhook
        payload = {
            "company_name": "FlowTest S.A.",
            "contact_name": "Ana Director",
            "contact_email": "adirector@flowtest.com",
            "region": "LATAM",
            "c_level": True,
            "score_icp": 85.0,
            "afinidad": "HIGH",
            "source": "crm_integration",
        }
        resp = await client.post("/api/v1/webhooks/leads", json=payload)
        assert resp.status_code == 200
        lead_id = resp.json()["lead_id"]
        initial_score = resp.json()["score_icp"]
        assert initial_score > 60

        # Step 2: Verify lead in list
        list_resp = await client.get("/api/v1/leads/", params={"c_level": True})
        assert list_resp.status_code == 200
        lead_ids = [l["id"] for l in list_resp.json()]
        assert lead_id in lead_ids

        # Step 3: Bulk qualify
        qualify_resp = await client.post(
            "/api/v1/leads/bulk-qualify", params={"score_threshold": 60.0}
        )
        assert qualify_resp.status_code == 200

        # Step 4: Verify qualified
        lead_resp = await client.get(f"/api/v1/leads/{lead_id}")
        assert lead_resp.json()["stage"] == "qualified"


# ---------------------------------------------------------------------------
# Scenario 2: Urgent support ticket lifecycle
# ---------------------------------------------------------------------------


class TestUrgentTicketLifecycleScenario:
    """Scenario: Customer reports stolen funds -> auto-classified -> assigned -> resolved."""

    async def _create_customer(self, client) -> int:
        """Helper: create a customer and return its ID."""
        payload = {
            "company_name": "Crypto Emergencia S.A.",
            "contact_name": "Roberto Urgente",
            "contact_email": f"roberto.urgente@cryptoemergencia.com",
            "region": "LATAM",
        }
        resp = await client.post("/api/v1/customers/", json=payload)
        assert resp.status_code == 201
        return resp.json()["id"]

    async def test_create_customer(self, client):
        """Verify customer creation works via API."""
        cid = await self._create_customer(client)
        assert cid > 0

        # Verify we can fetch it
        resp = await client.get(f"/api/v1/customers/{cid}")
        assert resp.status_code == 200
        assert resp.json()["company_name"] == "Crypto Emergencia S.A."

    async def test_urgent_ticket_auto_classification(self, client):
        """Create an urgent ticket about stolen funds and verify auto-classification."""
        customer_id = await self._create_customer(client)

        ticket_payload = {
            "customer_id": customer_id,
            "subject": "URGENTE - Me robaron los fondos de mi wallet!!!",
            "description": (
                "Acabo de entrar a mi cuenta y mi wallet esta vacia! "
                "Tenia 3 BTC y 15.000 USDT. No hice ninguna transferencia. "
                "Creo que me hackearon. Necesito que bloqueen todo AHORA!!!"
            ),
            "priority": "urgent",
        }
        resp = await client.post("/api/v1/tickets/", json=ticket_payload)
        assert resp.status_code == 201
        ticket = resp.json()

        # Verify auto-classification assigned a category
        assert ticket["category"] is not None
        # The router should detect crypto-related keywords
        assert ticket["category"] in ("crypto", "account", "billing")
        # Verify priority is preserved as urgent
        assert ticket["priority"] == "urgent"
        # Verify an agent was assigned
        assert ticket["assigned_agent"] is not None

    async def test_urgent_ticket_assigned_to_senior_agent(self, client):
        """Verify an urgent crypto ticket is routed to a senior agent."""
        customer_id = await self._create_customer(client)

        ticket_payload = {
            "customer_id": customer_id,
            "subject": "URGENTE fondos desaparecidos de mi wallet cripto",
            "description": (
                "Mis fondos de Bitcoin desaparecieron de la wallet. "
                "Es urgente, necesito ayuda inmediata. Creo que fue un hackeo."
            ),
            "priority": "urgent",
        }
        resp = await client.post("/api/v1/tickets/", json=ticket_payload)
        assert resp.status_code == 201
        ticket = resp.json()

        # Urgent tickets should go to senior agent
        assert ticket["assigned_agent"] is not None
        assert "senior" in ticket["assigned_agent"] or "crypto" in ticket["assigned_agent"]

    async def test_add_customer_message_to_ticket(self, client):
        """Add a customer follow-up message to a ticket."""
        customer_id = await self._create_customer(client)

        # Create ticket
        ticket_resp = await client.post("/api/v1/tickets/", json={
            "customer_id": customer_id,
            "subject": "Problema urgente con mi wallet",
            "description": "No puedo acceder a mis fondos cripto.",
            "priority": "high",
        })
        assert ticket_resp.status_code == 201
        ticket_id = ticket_resp.json()["id"]

        # Add customer message
        msg_resp = await client.post(
            f"/api/v1/tickets/{ticket_id}/messages",
            json={"sender": "customer", "content": "Siguen sin resolverme el problema!"},
        )
        assert msg_resp.status_code == 201
        msg = msg_resp.json()
        assert msg["sender"] == "customer"
        assert msg["ticket_id"] == ticket_id

        # Verify message appears in the list
        msgs_resp = await client.get(f"/api/v1/tickets/{ticket_id}/messages")
        assert msgs_resp.status_code == 200
        messages = msgs_resp.json()
        assert len(messages) >= 1
        assert any(m["sender"] == "customer" for m in messages)

    async def test_resolve_ticket_sets_resolved_at(self, client):
        """Resolve a ticket and verify resolved_at is set."""
        customer_id = await self._create_customer(client)

        # Create ticket
        ticket_resp = await client.post("/api/v1/tickets/", json={
            "customer_id": customer_id,
            "subject": "Problema con retiro de cripto",
            "description": "Mi retiro de USDT no se proceso.",
            "priority": "medium",
        })
        assert ticket_resp.status_code == 201
        ticket_id = ticket_resp.json()["id"]
        assert ticket_resp.json()["resolved_at"] is None

        # Resolve the ticket
        resolve_resp = await client.patch(
            f"/api/v1/tickets/{ticket_id}",
            json={
                "status": "resolved",
                "resolution": "Se proceso el retiro manualmente. Fondos acreditados.",
            },
        )
        assert resolve_resp.status_code == 200
        resolved_ticket = resolve_resp.json()
        assert resolved_ticket["status"] == "resolved"
        assert resolved_ticket["resolved_at"] is not None
        assert resolved_ticket["resolution"] is not None

    async def test_full_urgent_ticket_lifecycle(self, client):
        """Complete lifecycle: create customer -> urgent ticket -> messages -> resolve."""
        # Step 1: Create customer
        customer_id = await self._create_customer(client)

        # Step 2: Create urgent ticket about stolen funds
        ticket_resp = await client.post("/api/v1/tickets/", json={
            "customer_id": customer_id,
            "subject": "URGENTE - Fondos robados de mi wallet!!!",
            "description": (
                "AYUDA!!! Mi wallet esta vacia, tenia 5 BTC. "
                "Creo que me hackearon. Bloqueen todo inmediatamente!"
            ),
            "priority": "urgent",
        })
        assert ticket_resp.status_code == 201
        ticket = ticket_resp.json()
        ticket_id = ticket["id"]
        assert ticket["category"] is not None
        assert ticket["assigned_agent"] is not None

        # Step 3: Customer sends a follow-up
        await client.post(
            f"/api/v1/tickets/{ticket_id}/messages",
            json={"sender": "customer", "content": "Por favor respondan, es urgente!!!"},
        )

        # Step 4: Agent responds
        agent_msg = await client.post(
            f"/api/v1/tickets/{ticket_id}/messages",
            json={
                "sender": "agent",
                "content": (
                    "Recibimos tu reporte. Estamos bloqueando la cuenta y revisando "
                    "las transacciones. Te contactamos en breve."
                ),
            },
        )
        assert agent_msg.status_code == 201

        # Step 5: Verify ticket moved to in_progress after agent response
        ticket_after = await client.get(f"/api/v1/tickets/{ticket_id}")
        assert ticket_after.json()["status"] == "in_progress"

        # Step 6: Resolve the ticket
        resolve_resp = await client.patch(
            f"/api/v1/tickets/{ticket_id}",
            json={
                "status": "resolved",
                "resolution": (
                    "Investigacion completada. Se detecto acceso no autorizado. "
                    "Fondos congelados y proceso de restitucion iniciado."
                ),
            },
        )
        assert resolve_resp.status_code == 200
        assert resolve_resp.json()["resolved_at"] is not None


# ---------------------------------------------------------------------------
# Scenario 3: Analytics after data
# ---------------------------------------------------------------------------


class TestAnalyticsAfterDataScenario:
    """Scenario: Create leads and tickets, then verify executive dashboard KPIs."""

    async def _seed_data(self, client):
        """Create multiple leads and tickets for analytics testing."""
        # Create leads with various profiles
        lead_profiles = [
            {"region": "LATAM", "c_level": True, "score_icp": 80.0, "afinidad": "HIGH"},
            {"region": "LATAM", "c_level": True, "score_icp": 65.0, "afinidad": "HIGH"},
            {"region": "LATAM", "c_level": False, "score_icp": 45.0, "afinidad": "MEDIUM"},
            {"region": "Iberia", "c_level": True, "score_icp": 70.0, "afinidad": "HIGH"},
            {"region": "LATAM", "c_level": False, "score_icp": 20.0, "afinidad": "LOW"},
        ]
        for i, profile in enumerate(lead_profiles):
            await client.post("/api/v1/leads/", json={
                "company_name": f"Analytics Test Corp {i+1}",
                "contact_name": f"Contact {i+1}",
                "contact_email": f"contact{i+1}@analyticstest.com",
                **profile,
            })

        # Create a customer and tickets
        cust_resp = await client.post("/api/v1/customers/", json={
            "company_name": "Analytics Customer S.A.",
            "contact_name": "Test User",
            "contact_email": "test.analytics@example.com",
            "region": "LATAM",
        })
        customer_id = cust_resp.json()["id"]

        ticket_scenarios = [
            {"subject": "Error en la app", "description": "La app no carga", "priority": "high"},
            {"subject": "Consulta sobre comisiones", "description": "Cuanto cobran por operar?", "priority": "low"},
            {"subject": "Wallet no funciona", "description": "Mi wallet cripto no muestra saldo", "priority": "medium"},
        ]
        for scenario in ticket_scenarios:
            await client.post("/api/v1/tickets/", json={
                "customer_id": customer_id,
                **scenario,
            })

    async def test_executive_dashboard_has_all_kpis(self, client):
        """Verify executive dashboard returns all expected KPI fields."""
        await self._seed_data(client)

        resp = await client.get("/api/v1/analytics/executive")
        assert resp.status_code == 200
        data = resp.json()

        # Verify sales section
        assert "sales" in data
        sales = data["sales"]
        assert "total_leads" in sales
        assert sales["total_leads"] is not None
        assert sales["total_leads"] > 0
        assert "avg_score" in sales
        assert "conversion_rate" in sales
        assert "c_level_leads" in sales
        assert "hot_leads_needing_action" in sales
        assert "pipeline" in sales
        assert "new_leads_30d" in sales
        assert "qualified_leads" in sales

        # Verify support section
        assert "support" in data
        support = data["support"]
        assert "total_tickets" in support
        assert support["total_tickets"] is not None
        assert support["total_tickets"] > 0
        assert "open_tickets" in support
        assert "avg_resolution_hours" in support
        assert "overdue_tickets" in support

        # Verify alerts section exists
        assert "alerts" in data
        assert isinstance(data["alerts"], list)

    async def test_sales_stats_reflect_created_leads(self, client):
        """Verify sales stats match the data we just created."""
        await self._seed_data(client)

        resp = await client.get("/api/v1/leads/stats")
        assert resp.status_code == 200
        stats = resp.json()
        assert stats["total_leads"] >= 5
        assert stats["avg_score_icp"] is not None
        assert stats["c_level_count"] >= 2  # We created 3 c-level leads

    async def test_support_stats_reflect_created_tickets(self, client):
        """Verify support stats match the data we just created."""
        await self._seed_data(client)

        resp = await client.get("/api/v1/tickets/stats")
        assert resp.status_code == 200
        stats = resp.json()
        assert stats["total_tickets"] >= 3
        assert stats["open_tickets"] >= 0

    async def test_full_dashboard_endpoint(self, client):
        """Verify the full dashboard returns all sections."""
        await self._seed_data(client)

        resp = await client.get("/api/v1/dashboard/")
        assert resp.status_code == 200
        data = resp.json()

        assert "sales" in data
        assert "support" in data
        assert "agents" in data
        assert "events" in data
        assert "notifications" in data

        # Verify sales KPIs
        assert data["sales"]["total_leads"] >= 5
        assert "funnel" in data["sales"]
        assert isinstance(data["sales"]["funnel"], list)

        # Verify support KPIs
        assert data["support"]["total_tickets"] >= 3


# ---------------------------------------------------------------------------
# Scenario 4: Lead import and pipeline flow
# ---------------------------------------------------------------------------


class TestLeadImportPipelineScenario:
    """Scenario: Import leads via TSV file -> list with filters -> get pipeline stats."""

    async def test_import_tsv_via_api(self, client):
        """Import a small TSV file via the API and verify imported count."""
        tsv_content = (
            "Region\tC-Level\tScore ICP\tAfinidad Xcapit\n"
            "LATAM\tSi\t70\tHIGH\n"
            "LATAM\tSi\t55\tMEDIUM\n"
            "Iberia\tNo\t30\tLOW\n"
            "LATAM\tNo\t45\tMEDIUM\n"
            "LATAM\tSi\t80\tHIGH\n"
        )
        files = {"file": ("test_leads.tsv", io.BytesIO(tsv_content.encode("utf-8")), "text/tab-separated-values")}
        resp = await client.post("/api/v1/leads/import", files=files)
        assert resp.status_code == 201
        data = resp.json()
        assert data["imported"] == 5
        assert data["errors"] == 0

    async def test_list_leads_with_region_filter(self, client):
        """Import leads then filter by region."""
        # Import
        tsv_content = (
            "Region\tC-Level\tScore ICP\tAfinidad Xcapit\n"
            "LATAM\tSi\t70\tHIGH\n"
            "LATAM\tNo\t45\tMEDIUM\n"
            "Iberia\tSi\t60\tHIGH\n"
        )
        files = {"file": ("leads.tsv", io.BytesIO(tsv_content.encode("utf-8")), "text/tab-separated-values")}
        await client.post("/api/v1/leads/import", files=files)

        # Filter by LATAM
        resp = await client.get("/api/v1/leads/", params={"region": "LATAM"})
        assert resp.status_code == 200
        leads = resp.json()
        assert all(l["region"] == "LATAM" for l in leads)

        # Filter by Iberia
        resp_iberia = await client.get("/api/v1/leads/", params={"region": "Iberia"})
        assert resp_iberia.status_code == 200
        iberia_leads = resp_iberia.json()
        assert all(l["region"] == "Iberia" for l in iberia_leads)

    async def test_list_leads_with_afinidad_filter(self, client):
        """Import leads then filter by afinidad."""
        tsv_content = (
            "Region\tC-Level\tScore ICP\tAfinidad Xcapit\n"
            "LATAM\tSi\t70\tHIGH\n"
            "LATAM\tNo\t30\tLOW\n"
            "LATAM\tSi\t50\tMEDIUM\n"
        )
        files = {"file": ("leads.tsv", io.BytesIO(tsv_content.encode("utf-8")), "text/tab-separated-values")}
        await client.post("/api/v1/leads/import", files=files)

        resp = await client.get("/api/v1/leads/", params={"afinidad": "HIGH"})
        assert resp.status_code == 200
        high_leads = resp.json()
        assert all(l["afinidad"] == "HIGH" for l in high_leads)

    async def test_pipeline_stats_after_import(self, client):
        """Import leads and verify pipeline stats reflect the imported data."""
        tsv_content = (
            "Region\tC-Level\tScore ICP\tAfinidad Xcapit\n"
            "LATAM\tSi\t70\tHIGH\n"
            "LATAM\tSi\t55\tMEDIUM\n"
            "Iberia\tNo\t30\tLOW\n"
            "LATAM\tNo\t45\tMEDIUM\n"
            "LATAM\tSi\t80\tHIGH\n"
            "LATAM\tSi\t90\tHIGH\n"
            "Iberia\tSi\t65\tHIGH\n"
        )
        files = {"file": ("leads.tsv", io.BytesIO(tsv_content.encode("utf-8")), "text/tab-separated-values")}
        import_resp = await client.post("/api/v1/leads/import", files=files)
        assert import_resp.status_code == 201
        imported_count = import_resp.json()["imported"]

        # Get pipeline stats
        stats_resp = await client.get("/api/v1/leads/stats")
        assert stats_resp.status_code == 200
        stats = stats_resp.json()

        # Verify total matches what we imported
        assert stats["total_leads"] == imported_count
        assert stats["avg_score_icp"] is not None
        assert stats["avg_score_icp"] > 0

        # Verify by_stage has 'raw' since all new imports start as raw
        assert "raw" in stats["by_stage"]
        assert stats["by_stage"]["raw"] == imported_count

        # Verify by_region
        assert "LATAM" in stats["by_region"]
        assert "Iberia" in stats["by_region"]
        assert stats["by_region"]["LATAM"] + stats["by_region"]["Iberia"] == imported_count

    async def test_full_import_filter_stats_flow(self, client):
        """Complete flow: import -> filter -> stats -> verify consistency."""
        # Step 1: Import leads
        tsv_content = (
            "Region\tC-Level\tScore ICP\tAfinidad Xcapit\n"
            "LATAM\tSi\t85\tHIGH\n"
            "LATAM\tSi\t60\tHIGH\n"
            "LATAM\tNo\t40\tMEDIUM\n"
            "Iberia\tNo\t25\tLOW\n"
        )
        files = {"file": ("leads.tsv", io.BytesIO(tsv_content.encode("utf-8")), "text/tab-separated-values")}
        import_resp = await client.post("/api/v1/leads/import", files=files)
        assert import_resp.status_code == 201
        total_imported = import_resp.json()["imported"]
        assert total_imported == 4

        # Step 2: List all leads
        all_resp = await client.get("/api/v1/leads/")
        assert all_resp.status_code == 200
        all_leads = all_resp.json()
        assert len(all_leads) == 4

        # Step 3: Filter c-level leads
        clevel_resp = await client.get("/api/v1/leads/", params={"c_level": True})
        clevel_leads = clevel_resp.json()
        assert len(clevel_leads) == 2

        # Step 4: Pipeline stats
        stats_resp = await client.get("/api/v1/leads/stats")
        stats = stats_resp.json()
        assert stats["total_leads"] == 4
        assert stats["c_level_count"] == 2

        # Step 5: Funnel — all should be in 'raw' stage
        funnel_resp = await client.get("/api/v1/analytics/sales/funnel")
        assert funnel_resp.status_code == 200
        funnel = funnel_resp.json()["funnel"]
        raw_stage = next(s for s in funnel if s["stage"] == "raw")
        assert raw_stage["count"] == 4
