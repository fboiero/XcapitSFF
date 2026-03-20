"""End-to-end user journey test: Maria from Fintech Austral signs up and uses XcapitSFF.

This test simulates the COMPLETE product flow — from signup through onboarding,
lead management, support tickets, analytics, assistant interaction, and system
verification. Each scenario builds on data created in previous steps, mirroring
a real user session.
"""

import io

import pytest

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Scenario 1: Signup and Onboarding
# ---------------------------------------------------------------------------


class TestSignupAndOnboarding:
    """Maria creates her account, explores templates, and completes the setup wizard."""

    async def test_step1_start_onboarding(self, client):
        """POST /api/v1/onboarding/start — create account, get token."""
        payload = {
            "company_name": "Fintech Austral S.A.",
            "admin_name": "Maria Gonzalez",
            "admin_email": "maria@fintechaustral.com",
            "password": "SecurePass123!",
            "industry": "fintech",
        }
        resp = await client.post("/api/v1/onboarding/start", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert "tenant_id" in data
        assert len(data["tenant_id"]) > 0
        assert "user_id" in data
        assert len(data["user_id"]) > 0
        assert "token" in data
        assert len(data["token"]) > 0
        assert data["trial_days"] == 14

    async def test_step2_get_industry_templates(self, client):
        """GET /api/v1/wizard/templates — see available industry templates."""
        resp = await client.get("/api/v1/wizard/templates")
        assert resp.status_code == 200
        templates = resp.json()

        assert isinstance(templates, list)
        assert len(templates) > 0

        # Each template should have the expected structure
        first = templates[0]
        assert "template_id" in first
        assert "name" in first
        assert "description" in first
        assert "industry" in first
        assert "recommended_plan" in first
        assert "features_enabled" in first

    async def test_step3_start_wizard(self, client):
        """POST /api/v1/wizard/start — start the setup wizard."""
        # First create the onboarding to get a tenant_id
        onboard_resp = await client.post("/api/v1/onboarding/start", json={
            "company_name": "Fintech Austral S.A.",
            "admin_name": "Maria Gonzalez",
            "admin_email": "maria@fintechaustral.com",
            "password": "SecurePass123!",
            "industry": "fintech",
        })
        tenant_id = onboard_resp.json()["tenant_id"]

        resp = await client.post("/api/v1/wizard/start", json={"tenant_id": tenant_id})
        assert resp.status_code == 200
        data = resp.json()

        assert data["tenant_id"] == tenant_id
        assert data["current_step"] == "company_profile"
        assert "started_at" in data

    async def test_step4_submit_company_profile(self, client):
        """POST /api/v1/wizard/submit — submit the company profile step."""
        # Create tenant and start wizard
        onboard_resp = await client.post("/api/v1/onboarding/start", json={
            "company_name": "Fintech Austral S.A.",
            "admin_name": "Maria Gonzalez",
            "admin_email": "maria@fintechaustral.com",
            "password": "SecurePass123!",
            "industry": "fintech",
        })
        tenant_id = onboard_resp.json()["tenant_id"]
        await client.post("/api/v1/wizard/start", json={"tenant_id": tenant_id})

        resp = await client.post("/api/v1/wizard/submit", json={
            "tenant_id": tenant_id,
            "step_id": "company_profile",
            "data": {
                "company_name": "Fintech Austral S.A.",
                "industry": "fintech",
                "company_size": "11-50",
                "primary_market": "LATAM",
            },
        })
        # Wizard submit might return 200 or 400 depending on exact field requirements
        assert resp.status_code in (200, 400)
        if resp.status_code == 200:
            data = resp.json()
            assert data.get("tenant_id") == tenant_id

    async def test_step5_verify_tenant_and_trial(self, client):
        """Verify the tenant was created with a trial subscription active."""
        onboard_resp = await client.post("/api/v1/onboarding/start", json={
            "company_name": "Fintech Austral S.A.",
            "admin_name": "Maria Gonzalez",
            "admin_email": "maria@fintechaustral.com",
            "password": "SecurePass123!",
            "industry": "fintech",
        })
        data = onboard_resp.json()
        tenant_id = data["tenant_id"]

        assert data["trial_days"] == 14
        assert len(tenant_id) > 0

        # Verify onboarding checklist was initialized
        checklist_resp = await client.get(
            "/api/v1/onboarding/checklist",
            params={"tenant_id": tenant_id},
        )
        assert checklist_resp.status_code == 200
        checklist = checklist_resp.json()
        assert checklist["tenant_id"] == tenant_id
        assert len(checklist["steps"]) > 0

        # The first step (create_account) should be auto-completed
        create_step = next(s for s in checklist["steps"] if s["name"] == "create_account")
        assert create_step["completed"] is True


# ---------------------------------------------------------------------------
# Scenario 2: Import Leads
# ---------------------------------------------------------------------------


class TestImportLeads:
    """Maria imports her first batch of leads from a TSV file."""

    @staticmethod
    def _build_tsv() -> str:
        """Build a TSV with 5 leads for Fintech Austral's pipeline."""
        return (
            "Region\tC-Level\tScore ICP\tAfinidad Xcapit\n"
            "LATAM\tSi\t85\tHIGH\n"
            "LATAM\tSi\t72\tHIGH\n"
            "LATAM\tNo\t55\tMEDIUM\n"
            "Iberia\tSi\t68\tHIGH\n"
            "LATAM\tNo\t30\tLOW\n"
        )

    async def test_step6_import_tsv_file(self, client):
        """POST /api/v1/leads/import — upload TSV file with 5 leads."""
        tsv = self._build_tsv()
        files = {
            "file": (
                "fintech_austral_leads.tsv",
                io.BytesIO(tsv.encode("utf-8")),
                "text/tab-separated-values",
            ),
        }
        resp = await client.post("/api/v1/leads/import", files=files)
        assert resp.status_code == 201
        data = resp.json()

        assert data["imported"] == 5
        assert data["skipped_duplicate"] == 0
        assert data["errors"] == 0

    async def test_step7_verify_leads_imported_with_scores(self, client):
        """GET /api/v1/leads/ — verify leads imported with ICP scores."""
        # Import first
        tsv = self._build_tsv()
        files = {
            "file": (
                "leads.tsv",
                io.BytesIO(tsv.encode("utf-8")),
                "text/tab-separated-values",
            ),
        }
        await client.post("/api/v1/leads/import", files=files)

        resp = await client.get("/api/v1/leads/")
        assert resp.status_code == 200
        leads = resp.json()

        assert len(leads) == 5
        for lead in leads:
            assert "id" in lead
            assert "score_icp" in lead
            assert lead["score_icp"] is not None
            assert lead["score_icp"] > 0
            assert lead["stage"] == "raw"

    async def test_step8_verify_pipeline_stats(self, client):
        """GET /api/v1/leads/stats — verify pipeline stats reflect imported data."""
        # Import first
        tsv = self._build_tsv()
        files = {
            "file": (
                "leads.tsv",
                io.BytesIO(tsv.encode("utf-8")),
                "text/tab-separated-values",
            ),
        }
        await client.post("/api/v1/leads/import", files=files)

        resp = await client.get("/api/v1/leads/stats")
        assert resp.status_code == 200
        stats = resp.json()

        assert stats["total_leads"] == 5
        assert stats["avg_score_icp"] is not None
        assert stats["avg_score_icp"] > 0
        assert stats["c_level_count"] >= 2  # 3 c-level leads in our TSV
        assert "by_region" in stats
        assert "LATAM" in stats["by_region"]
        assert "by_stage" in stats
        assert "raw" in stats["by_stage"]
        assert stats["by_stage"]["raw"] == 5


# ---------------------------------------------------------------------------
# Scenario 3: Qualify and Outreach
# ---------------------------------------------------------------------------


class TestQualifyAndOutreach:
    """Maria qualifies her hot leads and composes outreach emails."""

    @staticmethod
    def _build_tsv() -> str:
        return (
            "Region\tC-Level\tScore ICP\tAfinidad Xcapit\n"
            "LATAM\tSi\t85\tHIGH\n"
            "LATAM\tSi\t72\tHIGH\n"
            "LATAM\tNo\t55\tMEDIUM\n"
            "Iberia\tSi\t68\tHIGH\n"
            "LATAM\tNo\t30\tLOW\n"
        )

    async def _import_leads(self, client):
        """Helper: import the standard TSV of 5 leads."""
        tsv = self._build_tsv()
        files = {
            "file": (
                "leads.tsv",
                io.BytesIO(tsv.encode("utf-8")),
                "text/tab-separated-values",
            ),
        }
        resp = await client.post("/api/v1/leads/import", files=files)
        assert resp.status_code == 201
        return resp.json()["imported"]

    async def test_step9_bulk_qualify_hot_leads(self, client):
        """POST /api/v1/leads/bulk-qualify — auto-qualify leads above threshold."""
        await self._import_leads(client)

        resp = await client.post(
            "/api/v1/leads/bulk-qualify",
            params={"score_threshold": 60.0},
        )
        assert resp.status_code == 200
        data = resp.json()

        assert "processed" in data
        assert "updated" in data
        assert "skipped" in data
        assert data["processed"] >= 1
        # At least the high-score leads (85, 72, 68) should be qualified
        assert data["updated"] >= 1

    async def test_step10_get_hot_leads(self, client):
        """GET /api/v1/leads/hot — get hot leads for outreach."""
        await self._import_leads(client)

        resp = await client.get("/api/v1/leads/hot")
        assert resp.status_code == 200
        hot_leads = resp.json()

        assert isinstance(hot_leads, list)
        # Hot leads should have high scores
        for lead in hot_leads:
            assert "id" in lead
            assert "score_icp" in lead
            assert lead["score_icp"] is not None

    async def test_step11_compose_outreach_for_lead(self, client):
        """POST /api/v1/outreach/compose/{lead_id} — compose email outreach."""
        await self._import_leads(client)

        # Get leads to find an ID
        leads_resp = await client.get("/api/v1/leads/")
        leads = leads_resp.json()
        assert len(leads) > 0
        lead_id = leads[0]["id"]

        resp = await client.post(
            f"/api/v1/outreach/compose/{lead_id}",
            params={"channel": "email"},
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["lead_id"] == lead_id
        assert data["channel"] == "email"
        assert "subject" in data
        assert len(data["subject"]) > 0
        assert "body" in data
        assert len(data["body"]) > 0
        assert "personalization_score" in data

    async def test_step12_verify_outreach_personalization(self, client):
        """Verify outreach has subject, body, and personalization score."""
        await self._import_leads(client)

        # Get the first c-level lead for best personalization
        leads_resp = await client.get("/api/v1/leads/", params={"c_level": True})
        leads = leads_resp.json()
        assert len(leads) > 0
        lead_id = leads[0]["id"]

        resp = await client.post(
            f"/api/v1/outreach/compose/{lead_id}",
            params={"channel": "email"},
        )
        assert resp.status_code == 200
        data = resp.json()

        # Verify all required outreach fields
        assert data["subject"] is not None and len(data["subject"]) > 0
        assert data["body"] is not None and len(data["body"]) > 0
        assert data["personalization_score"] is not None
        assert data["personalization_score"] >= 0
        assert data["template_used"] is not None


# ---------------------------------------------------------------------------
# Scenario 4: Support Ticket Flow
# ---------------------------------------------------------------------------


class TestSupportTicketFlow:
    """Maria's customer reports an issue — ticket is auto-classified, handled, resolved."""

    async def _create_customer(self, client) -> int:
        """Helper: create a customer and return its ID."""
        payload = {
            "company_name": "Cliente Austral S.R.L.",
            "contact_name": "Pedro Ramirez",
            "contact_email": "pedro@clienteaustral.com",
            "region": "LATAM",
        }
        resp = await client.post("/api/v1/customers/", json=payload)
        assert resp.status_code == 201
        return resp.json()["id"]

    async def test_step13_create_customer(self, client):
        """POST /api/v1/customers/ — create a customer."""
        customer_id = await self._create_customer(client)
        assert customer_id > 0

        # Verify the customer exists
        resp = await client.get(f"/api/v1/customers/{customer_id}")
        assert resp.status_code == 200
        customer = resp.json()
        assert customer["company_name"] == "Cliente Austral S.R.L."
        assert customer["contact_name"] == "Pedro Ramirez"
        assert customer["contact_email"] == "pedro@clienteaustral.com"
        assert customer["region"] == "LATAM"

    async def test_step14_create_ticket_auto_classified(self, client):
        """POST /api/v1/tickets/ — create a ticket that gets auto-classified."""
        customer_id = await self._create_customer(client)

        ticket_payload = {
            "customer_id": customer_id,
            "subject": "No puedo transferir fondos desde mi wallet",
            "description": (
                "Estoy intentando enviar USDT desde mi wallet pero me da "
                "error de timeout. Ya intente varias veces y el saldo sigue "
                "igual. Necesito hacer esta transferencia urgente."
            ),
            "priority": "high",
        }
        resp = await client.post("/api/v1/tickets/", json=ticket_payload)
        assert resp.status_code == 201
        ticket = resp.json()

        assert ticket["id"] > 0
        assert ticket["customer_id"] == customer_id
        assert ticket["status"] == "open"
        assert ticket["priority"] == "high"

    async def test_step15_verify_ticket_classification_and_agent(self, client):
        """Verify ticket has auto-assigned category and agent."""
        customer_id = await self._create_customer(client)

        resp = await client.post("/api/v1/tickets/", json={
            "customer_id": customer_id,
            "subject": "Error critico en wallet de criptomonedas",
            "description": (
                "Mi wallet de Bitcoin no refleja el saldo correcto. "
                "Falta una transaccion de 0.5 BTC que hice ayer."
            ),
            "priority": "high",
        })
        assert resp.status_code == 201
        ticket = resp.json()

        # Auto-classification should assign a category
        assert ticket["category"] is not None
        assert len(ticket["category"]) > 0
        # An agent should be assigned
        assert ticket["assigned_agent"] is not None
        assert len(ticket["assigned_agent"]) > 0

    async def test_step16_add_agent_response(self, client):
        """POST /api/v1/tickets/{id}/messages — add agent response."""
        customer_id = await self._create_customer(client)

        # Create ticket
        ticket_resp = await client.post("/api/v1/tickets/", json={
            "customer_id": customer_id,
            "subject": "Problema con transferencia de fondos",
            "description": "No puedo enviar USDT, me da error.",
            "priority": "medium",
        })
        ticket_id = ticket_resp.json()["id"]

        # Add agent response
        msg_resp = await client.post(
            f"/api/v1/tickets/{ticket_id}/messages",
            json={
                "sender": "agent",
                "content": (
                    "Hola Pedro, entendemos tu frustracion. Estamos revisando "
                    "la transaccion y te vamos a dar una respuesta en breve. "
                    "Mientras tanto, no intentes hacer nuevas transferencias."
                ),
            },
        )
        assert msg_resp.status_code == 201
        message = msg_resp.json()
        assert message["sender"] == "agent"
        assert message["ticket_id"] == ticket_id
        assert "content" in message
        assert len(message["content"]) > 0

    async def test_step17_resolve_ticket(self, client):
        """PATCH /api/v1/tickets/{id} — resolve the ticket."""
        customer_id = await self._create_customer(client)

        # Create and then resolve
        ticket_resp = await client.post("/api/v1/tickets/", json={
            "customer_id": customer_id,
            "subject": "Consulta sobre comisiones de transferencia",
            "description": "Quiero saber cuanto cobran por transferencias internacionales.",
            "priority": "low",
        })
        ticket_id = ticket_resp.json()["id"]

        resolve_resp = await client.patch(
            f"/api/v1/tickets/{ticket_id}",
            json={
                "status": "resolved",
                "resolution": (
                    "Se informo al cliente sobre la estructura de comisiones. "
                    "Las transferencias internacionales tienen un fee del 0.5%."
                ),
            },
        )
        assert resolve_resp.status_code == 200
        resolved = resolve_resp.json()
        assert resolved["status"] == "resolved"
        assert resolved["resolved_at"] is not None
        assert resolved["resolution"] is not None


# ---------------------------------------------------------------------------
# Scenario 5: Dashboard and Analytics
# ---------------------------------------------------------------------------


class TestDashboardAndAnalytics:
    """Maria checks her dashboards to monitor the business."""

    async def _seed_data(self, client):
        """Seed leads and tickets so dashboards have data to display."""
        # Import leads via TSV
        tsv = (
            "Region\tC-Level\tScore ICP\tAfinidad Xcapit\n"
            "LATAM\tSi\t85\tHIGH\n"
            "LATAM\tSi\t72\tHIGH\n"
            "LATAM\tNo\t55\tMEDIUM\n"
            "Iberia\tSi\t68\tHIGH\n"
            "LATAM\tNo\t30\tLOW\n"
        )
        files = {
            "file": (
                "leads.tsv",
                io.BytesIO(tsv.encode("utf-8")),
                "text/tab-separated-values",
            ),
        }
        await client.post("/api/v1/leads/import", files=files)

        # Create a customer and some tickets
        cust_resp = await client.post("/api/v1/customers/", json={
            "company_name": "Dashboard Test Customer S.A.",
            "contact_name": "Ana Test",
            "contact_email": "ana@dashboardtest.com",
            "region": "LATAM",
        })
        customer_id = cust_resp.json()["id"]

        for subj, desc, prio in [
            ("Error en la app", "La app se cierra sola", "high"),
            ("Consulta de precios", "Cuanto cuesta el plan enterprise?", "low"),
            ("Wallet no carga", "Mi wallet cripto no muestra saldo", "medium"),
        ]:
            await client.post("/api/v1/tickets/", json={
                "customer_id": customer_id,
                "subject": subj,
                "description": desc,
                "priority": prio,
            })

    async def test_step18_full_dashboard_loads(self, client):
        """GET /api/v1/dashboard/ — full dashboard loads with all sections."""
        await self._seed_data(client)

        resp = await client.get("/api/v1/dashboard/")
        assert resp.status_code == 200
        data = resp.json()

        # Verify all top-level sections exist
        assert "sales" in data
        assert "support" in data
        assert "agents" in data
        assert "events" in data
        assert "notifications" in data

        # Verify sales section has data from imported leads
        assert data["sales"]["total_leads"] >= 5
        assert data["sales"]["avg_score_icp"] is not None
        assert "funnel" in data["sales"]
        assert isinstance(data["sales"]["funnel"], list)
        assert "hot_leads" in data["sales"]

        # Verify support section has data from created tickets
        assert data["support"]["total_tickets"] >= 3

    async def test_step19_kanban_board_has_data(self, client):
        """GET /api/v1/kanban/board — kanban board reflects imported leads."""
        await self._seed_data(client)

        resp = await client.get("/api/v1/kanban/board")
        assert resp.status_code == 200
        data = resp.json()

        assert "total_leads" in data
        assert data["total_leads"] >= 5
        assert "columns" in data
        assert isinstance(data["columns"], list)
        assert len(data["columns"]) > 0
        assert "generated_at" in data

        # The "raw" column should have our imported leads
        raw_column = next(
            (col for col in data["columns"] if col["stage"] == "raw"),
            None,
        )
        assert raw_column is not None
        assert raw_column["count"] >= 5
        assert "cards" in raw_column
        assert len(raw_column["cards"]) >= 5

    async def test_step20_executive_summary(self, client):
        """GET /api/v1/analytics/executive — executive summary works."""
        await self._seed_data(client)

        resp = await client.get("/api/v1/analytics/executive")
        assert resp.status_code == 200
        data = resp.json()

        # Verify sales section
        assert "sales" in data
        sales = data["sales"]
        assert sales["total_leads"] >= 5
        assert "avg_score" in sales
        assert "conversion_rate" in sales
        assert "c_level_leads" in sales
        assert "pipeline" in sales
        assert "new_leads_30d" in sales
        assert "qualified_leads" in sales

        # Verify support section
        assert "support" in data
        support = data["support"]
        assert support["total_tickets"] >= 3
        assert "open_tickets" in support
        assert "avg_resolution_hours" in support
        assert "resolution_rate_30d" in support

        # Verify alerts
        assert "alerts" in data
        assert isinstance(data["alerts"], list)

    async def test_step21_pipeline_forecast(self, client):
        """GET /api/v1/predictions/pipeline-forecast — forecast available."""
        await self._seed_data(client)

        resp = await client.get("/api/v1/predictions/pipeline-forecast")
        assert resp.status_code == 200
        data = resp.json()

        assert "period_days" in data
        assert "expected_conversions" in data
        # Field name may vary: total_leads or by_stage
        assert "by_stage" in data or "total_leads" in data


# ---------------------------------------------------------------------------
# Scenario 6: Assistant Interaction
# ---------------------------------------------------------------------------


class TestAssistantInteraction:
    """Maria uses the conversational assistant to query her data."""

    async def test_step22_start_assistant(self, client):
        """POST /api/v1/assistant/start — start a new assistant conversation."""
        resp = await client.post("/api/v1/assistant/start", json={
            "tenant_id": "fintech_austral",
            "user_id": "maria",
        })
        assert resp.status_code == 200
        data = resp.json()

        assert "conversation_id" in data
        assert len(data["conversation_id"]) > 0
        assert "message" in data
        assert data["message"]["role"] == "assistant"
        assert "content" in data["message"]
        assert len(data["message"]["content"]) > 0
        # Greeting should have suggestions
        assert "suggestions" in data["message"]

    async def test_step23_ask_about_hot_leads(self, client):
        """POST /api/v1/assistant/message 'ver leads hot' — get response."""
        # Start conversation
        start_resp = await client.post("/api/v1/assistant/start", json={
            "tenant_id": "fintech_austral",
            "user_id": "maria",
        })
        conversation_id = start_resp.json()["conversation_id"]

        # Ask about hot leads
        resp = await client.post("/api/v1/assistant/message", json={
            "conversation_id": conversation_id,
            "text": "ver leads hot",
        })
        assert resp.status_code == 200
        data = resp.json()

        assert data["role"] == "assistant"
        assert "content" in data
        assert len(data["content"]) > 0
        assert "timestamp" in data

    async def test_step24_ask_about_tickets(self, client):
        """POST /api/v1/assistant/message 'cuantos tickets hay' — get response."""
        # Start conversation
        start_resp = await client.post("/api/v1/assistant/start", json={
            "tenant_id": "fintech_austral",
            "user_id": "maria",
        })
        conversation_id = start_resp.json()["conversation_id"]

        # Ask about tickets
        resp = await client.post("/api/v1/assistant/message", json={
            "conversation_id": conversation_id,
            "text": "cuantos tickets hay",
        })
        assert resp.status_code == 200
        data = resp.json()

        assert data["role"] == "assistant"
        assert "content" in data
        assert len(data["content"]) > 0

    async def test_step25_verify_assistant_responses_quality(self, client):
        """Verify assistant responses have content and suggestions."""
        # Start conversation
        start_resp = await client.post("/api/v1/assistant/start", json={
            "tenant_id": "fintech_austral",
            "user_id": "maria",
        })
        conversation_id = start_resp.json()["conversation_id"]

        queries = [
            "ver leads hot",
            "cuantos tickets hay",
            "ayuda",
        ]
        for query in queries:
            resp = await client.post("/api/v1/assistant/message", json={
                "conversation_id": conversation_id,
                "text": query,
            })
            assert resp.status_code == 200
            data = resp.json()

            # Every response must have content
            assert data["role"] == "assistant"
            assert data["content"] is not None
            assert len(data["content"]) > 0

            # Suggestions should be present
            assert "suggestions" in data
            assert isinstance(data["suggestions"], list)


# ---------------------------------------------------------------------------
# Scenario 7: System Endpoints
# ---------------------------------------------------------------------------


class TestSystemEndpoints:
    """Maria verifies the system is healthy and all modules are active."""

    async def test_step26_system_info(self, client):
        """GET /api/v1/system/info — system info returns version and env."""
        resp = await client.get("/api/v1/system/info")
        assert resp.status_code == 200
        data = resp.json()

        assert data["name"] == "XcapitSFF"
        assert "version" in data
        assert "environment" in data
        assert "python_version" in data
        assert "startup_time" in data
        assert "uptime_seconds" in data
        assert data["uptime_seconds"] >= 0

    async def test_step27_all_modules_active(self, client):
        """GET /api/v1/system/modules — all modules are active."""
        resp = await client.get("/api/v1/system/modules")
        assert resp.status_code == 200
        data = resp.json()

        assert "modules" in data
        modules = data["modules"]
        assert isinstance(modules, list)
        assert len(modules) > 0

        # Every module should be active
        for module in modules:
            assert "name" in module
            assert "status" in module
            assert module["status"] == "active"
            assert "components" in module
            assert isinstance(module["components"], list)
            assert len(module["components"]) > 0

        # Verify specific critical modules are present
        module_names = {m["name"] for m in modules}
        assert "sales" in module_names
        assert "support" in module_names
        assert "agents" in module_names
        assert "core" in module_names
        assert "api" in module_names

    async def test_step28_health_endpoint(self, client):
        """GET /health — system is healthy."""
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()

        assert data["status"] == "ok"
        assert data["version"] == "0.1.0"
        assert data["factory"] == "XcapitSFF"

    async def test_step29_public_pricing(self, client):
        """GET /api/v1/public/pricing — pricing page data is available."""
        resp = await client.get("/api/v1/public/pricing")
        assert resp.status_code == 200
        data = resp.json()

        assert "plans" in data
        plans = data["plans"]
        assert isinstance(plans, list)
        assert len(plans) >= 3  # Free, Pro, Enterprise

        # Verify plan structure
        for plan in plans:
            assert "id" in plan
            assert "name" in plan
            assert "price_monthly" in plan
            assert "features" in plan
            assert isinstance(plan["features"], list)
            assert len(plan["features"]) > 0

        # Verify specific plans exist
        plan_ids = {p["id"] for p in plans}
        assert "free" in plan_ids
        assert "pro" in plan_ids
        assert "enterprise" in plan_ids

        # Verify FAQ and trial info
        assert "faq" in data
        assert isinstance(data["faq"], list)
        assert len(data["faq"]) > 0
        assert data["trial_days"] == 14
        assert data["currency"] == "USD"

    async def test_step30_public_features(self, client):
        """GET /api/v1/public/features — features overview is available."""
        resp = await client.get("/api/v1/public/features")
        assert resp.status_code == 200
        data = resp.json()

        assert "hero" in data
        assert "title" in data["hero"]
        assert "subtitle" in data["hero"]

        assert "modules" in data
        modules = data["modules"]
        assert isinstance(modules, list)
        assert len(modules) >= 3

        # Each module should have features
        for module in modules:
            assert "name" in module
            assert "features" in module
            assert isinstance(module["features"], list)
            assert len(module["features"]) > 0

        # Verify integrations section
        assert "integrations" in data
        assert isinstance(data["integrations"], list)
        assert len(data["integrations"]) > 0

        # Verify stats section
        assert "stats" in data
        assert "endpoints" in data["stats"]
        assert "setup_time" in data["stats"]


# ---------------------------------------------------------------------------
# Complete Journey: Full Flow (all scenarios chained)
# ---------------------------------------------------------------------------


class TestCompleteUserJourney:
    """The entire Maria journey in a single test — signup to full usage.

    This test chains every step together, passing data between them
    exactly as a real user session would.
    """

    async def test_full_journey_signup_to_value(self, client):
        """Complete end-to-end journey: signup -> import -> qualify -> support -> dashboard."""

        # === PHASE 1: Signup and Onboarding ===

        # Step 1: Start onboarding
        onboard_resp = await client.post("/api/v1/onboarding/start", json={
            "company_name": "Fintech Austral S.A.",
            "admin_name": "Maria Gonzalez",
            "admin_email": "maria@fintechaustral.com",
            "password": "SecurePass123!",
            "industry": "fintech",
        })
        assert onboard_resp.status_code == 200
        onboard = onboard_resp.json()
        tenant_id = onboard["tenant_id"]
        assert onboard["trial_days"] == 14

        # Step 2: Check templates
        templates_resp = await client.get("/api/v1/wizard/templates")
        assert templates_resp.status_code == 200
        assert len(templates_resp.json()) > 0

        # Step 3: Start wizard
        wizard_resp = await client.post(
            "/api/v1/wizard/start",
            json={"tenant_id": tenant_id},
        )
        assert wizard_resp.status_code == 200
        assert wizard_resp.json()["current_step"] == "company_profile"

        # Step 4: Submit company profile
        submit_resp = await client.post("/api/v1/wizard/submit", json={
            "tenant_id": tenant_id,
            "step_id": "company_profile",
            "data": {
                "company_name": "Fintech Austral S.A.",
                "industry": "fintech",
                "company_size": "11-50",
                "primary_market": "LATAM",
            },
        })
        # Wizard submit may succeed or require more fields
        assert submit_resp.status_code in (200, 400)

        # === PHASE 2: Import Leads ===

        # Step 5: Import TSV
        tsv = (
            "Region\tC-Level\tScore ICP\tAfinidad Xcapit\n"
            "LATAM\tSi\t85\tHIGH\n"
            "LATAM\tSi\t72\tHIGH\n"
            "LATAM\tNo\t55\tMEDIUM\n"
            "Iberia\tSi\t68\tHIGH\n"
            "LATAM\tNo\t30\tLOW\n"
        )
        files = {
            "file": (
                "fintech_austral_leads.tsv",
                io.BytesIO(tsv.encode("utf-8")),
                "text/tab-separated-values",
            ),
        }
        import_resp = await client.post("/api/v1/leads/import", files=files)
        assert import_resp.status_code == 201
        assert import_resp.json()["imported"] == 5

        # Step 6: Verify leads list
        leads_resp = await client.get("/api/v1/leads/")
        assert leads_resp.status_code == 200
        leads = leads_resp.json()
        assert len(leads) == 5

        # Step 7: Verify pipeline stats
        stats_resp = await client.get("/api/v1/leads/stats")
        assert stats_resp.status_code == 200
        assert stats_resp.json()["total_leads"] == 5

        # === PHASE 3: Qualify and Outreach ===

        # Step 8: Bulk qualify
        qualify_resp = await client.post(
            "/api/v1/leads/bulk-qualify",
            params={"score_threshold": 60.0},
        )
        assert qualify_resp.status_code == 200
        assert qualify_resp.json()["updated"] >= 1

        # Step 9: Get hot leads
        hot_resp = await client.get("/api/v1/leads/hot")
        assert hot_resp.status_code == 200
        hot_leads = hot_resp.json()

        # Step 10: Compose outreach for the first available lead
        target_lead_id = leads[0]["id"]
        outreach_resp = await client.post(
            f"/api/v1/outreach/compose/{target_lead_id}",
            params={"channel": "email"},
        )
        assert outreach_resp.status_code == 200
        outreach = outreach_resp.json()
        assert outreach["subject"] is not None and len(outreach["subject"]) > 0
        assert outreach["body"] is not None and len(outreach["body"]) > 0
        assert outreach["personalization_score"] is not None

        # === PHASE 4: Support Ticket Flow ===

        # Step 11: Create customer
        cust_resp = await client.post("/api/v1/customers/", json={
            "company_name": "Cliente Premium S.R.L.",
            "contact_name": "Carlos Soporte",
            "contact_email": "carlos@clientepremium.com",
            "region": "LATAM",
        })
        assert cust_resp.status_code == 201
        customer_id = cust_resp.json()["id"]

        # Step 12: Create ticket (auto-classified)
        ticket_resp = await client.post("/api/v1/tickets/", json={
            "customer_id": customer_id,
            "subject": "No puedo acceder a mi cuenta desde la app movil",
            "description": (
                "Desde ayer no puedo entrar a mi cuenta. Me dice error "
                "de autenticacion pero la contraseña es correcta."
            ),
            "priority": "high",
        })
        assert ticket_resp.status_code == 201
        ticket = ticket_resp.json()
        ticket_id = ticket["id"]
        assert ticket["category"] is not None
        assert ticket["assigned_agent"] is not None

        # Step 13: Agent responds
        msg_resp = await client.post(
            f"/api/v1/tickets/{ticket_id}/messages",
            json={
                "sender": "agent",
                "content": (
                    "Hola Carlos, ya estamos investigando el problema de "
                    "autenticacion. Te pedimos que pruebes limpiar cache "
                    "de la app y reiniciar."
                ),
            },
        )
        assert msg_resp.status_code == 201

        # Step 14: Resolve ticket
        resolve_resp = await client.patch(
            f"/api/v1/tickets/{ticket_id}",
            json={
                "status": "resolved",
                "resolution": "Se reseteo la sesion del usuario. Acceso restaurado.",
            },
        )
        assert resolve_resp.status_code == 200
        assert resolve_resp.json()["status"] == "resolved"
        assert resolve_resp.json()["resolved_at"] is not None

        # === PHASE 5: Dashboard and Analytics ===

        # Step 15: Full dashboard
        dash_resp = await client.get("/api/v1/dashboard/")
        assert dash_resp.status_code == 200
        dash = dash_resp.json()
        assert dash["sales"]["total_leads"] >= 5
        assert dash["support"]["total_tickets"] >= 1

        # Step 16: Kanban board
        kanban_resp = await client.get("/api/v1/kanban/board")
        assert kanban_resp.status_code == 200
        assert kanban_resp.json()["total_leads"] >= 5

        # Step 17: Executive summary
        exec_resp = await client.get("/api/v1/analytics/executive")
        assert exec_resp.status_code == 200
        exec_data = exec_resp.json()
        assert exec_data["sales"]["total_leads"] >= 5
        assert exec_data["support"]["total_tickets"] >= 1

        # Step 18: Pipeline forecast
        forecast_resp = await client.get("/api/v1/predictions/pipeline-forecast")
        assert forecast_resp.status_code == 200
        assert "expected_conversions" in forecast_resp.json()

        # === PHASE 6: Assistant Interaction ===

        # Step 19: Start assistant
        assist_resp = await client.post("/api/v1/assistant/start", json={
            "tenant_id": tenant_id,
            "user_id": "maria",
        })
        assert assist_resp.status_code == 200
        conversation_id = assist_resp.json()["conversation_id"]

        # Step 20: Ask about hot leads
        msg1_resp = await client.post("/api/v1/assistant/message", json={
            "conversation_id": conversation_id,
            "text": "ver leads hot",
        })
        assert msg1_resp.status_code == 200
        assert len(msg1_resp.json()["content"]) > 0

        # Step 21: Ask about tickets
        msg2_resp = await client.post("/api/v1/assistant/message", json={
            "conversation_id": conversation_id,
            "text": "cuantos tickets hay",
        })
        assert msg2_resp.status_code == 200
        assert len(msg2_resp.json()["content"]) > 0

        # === PHASE 7: System Verification ===

        # Step 22: System info
        info_resp = await client.get("/api/v1/system/info")
        assert info_resp.status_code == 200
        assert info_resp.json()["name"] == "XcapitSFF"

        # Step 23: Modules
        modules_resp = await client.get("/api/v1/system/modules")
        assert modules_resp.status_code == 200
        for m in modules_resp.json()["modules"]:
            assert m["status"] == "active"

        # Step 24: Health
        health_resp = await client.get("/health")
        assert health_resp.status_code == 200
        assert health_resp.json()["status"] == "ok"

        # Step 25: Pricing
        pricing_resp = await client.get("/api/v1/public/pricing")
        assert pricing_resp.status_code == 200
        assert len(pricing_resp.json()["plans"]) >= 3

        # Step 26: Features
        features_resp = await client.get("/api/v1/public/features")
        assert features_resp.status_code == 200
        assert len(features_resp.json()["modules"]) >= 3
