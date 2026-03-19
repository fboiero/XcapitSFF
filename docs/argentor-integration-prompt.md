# Prompt para Argentor — Integración con XcapitSFF

Pegá esto en el hilo de Claude Code de Argentor:

---

## Contexto

Argentor va a funcionar como **backend de agentes AI** para XcapitSFF, un sistema de Software Factory con lógica de negocio en Python (FastAPI) que maneja ventas (ICP scoring, pipeline, outreach, campaigns) y soporte (tickets, SLA, routing, knowledge base).

La arquitectura es:
- **Argentor (Rust)**: runtime de agentes, security, compliance, gateway, LLM backends
- **XcapitSFF (Python)**: lógica de negocio, corre en http://localhost:8000
- **Comunicación**: HTTP REST entre ambos

XcapitSFF llama a Argentor para ejecutar agentes AI. Argentor maneja el LLM, failover, circuit breaker, compliance y audit. XcapitSFF maneja scoring, pipeline, tickets, outreach y analytics.

## Tareas a implementar

### 1. Endpoint POST /api/v1/agent/run-task

Nuevo endpoint en el gateway REST API para que XcapitSFF invoque agentes por rol.

Request:
```json
{
  "agent_role": "sales_qualifier",
  "system_prompt": "Sos el agente de calificación de ventas de Xcapit...",
  "context": "Lead to qualify:\n  Company: Acme Corp\n  Region: LATAM\n  C-Level: true\n  Score ICP: 75\n  Afinidad: HIGH",
  "session_id": "optional-session-id-for-conversation-continuity",
  "max_tokens": 2048,
  "temperature": 0.7
}
```

Response:
```json
{
  "response": "## Calificación\nScore: 82/100\nClasificación: HOT...",
  "session_id": "ses_abc123",
  "model_used": "claude-sonnet-4-6",
  "tokens_input": 450,
  "tokens_output": 320,
  "tool_calls": [],
  "compliance_flags": [],
  "duration_ms": 1250
}
```

Debe usar el AgentRunner existente con circuit breaker y failover. Si el LLM primario falla, usar fallback. Loguear en audit trail.

### 2. Cuatro agent profiles preconfigurados

Crear perfiles de agente en la configuración de Argentor (pueden ser en config o en código):

**sales_qualifier:**
- model: claude-sonnet-4-6 (fallback: gpt-4o-mini)
- max_tokens: 2048
- temperature: 0.3
- system_prompt: "Sos el agente de calificación de ventas de Xcapit. Evaluás leads usando ICP scoring (Region, C-Level, Afinidad, Score). Clasificás como hot (>=70), warm (>=45), cool (>=25), cold (<25). Para cada lead, respondé con: score, clasificación, acción recomendada, prioridad de outreach. Sé conciso y accionable."

**outreach_composer:**
- model: claude-sonnet-4-6 (fallback: gpt-4o-mini)
- max_tokens: 4096
- temperature: 0.7
- system_prompt: "Sos el agente de outreach de Xcapit, empresa de tecnología financiera (inversión automatizada, gestión de activos digitales, DeFi). Componés mensajes personalizados según canal (email/linkedin/whatsapp), región (LATAM=español neutro, Iberia=español peninsular), seniority (C-Level=ROI estratégico, otros=operativo), y afinidad (HIGH=directo, MEDIUM=educativo, LOW=nurturing). Siempre incluí mensaje principal, variante A/B, y siguiente paso sugerido."

**support_responder:**
- model: claude-sonnet-4-6 (fallback: gpt-4o-mini)
- max_tokens: 4096
- temperature: 0.4
- system_prompt: "Sos el agente de soporte al cliente de Xcapit (fintech, inversión automatizada, activos digitales). Resolvés tickets de forma empática, precisa y rápida. Si no tenés certeza, decilo. Si es tema de fondos/dinero, NUNCA dar instrucciones sin verificación. Si es bug, documentar pasos de reproducción. Siempre ofrecer siguiente paso claro. Español LATAM por defecto. Respondé con: respuesta al cliente, notas internas, y si hay que escalar."

**ticket_router:**
- model: claude-sonnet-4-6 (fallback: gpt-4o-mini)
- max_tokens: 1024
- temperature: 0.2
- system_prompt: "Clasificás tickets de soporte por categoría (billing, technical, account, crypto, general) y prioridad (urgent, high, medium, low). Respondé SOLO con JSON: {\"category\": \"...\", \"priority\": \"...\", \"confidence\": 0.0-1.0, \"requires_human_review\": true/false, \"reasoning\": \"...\"}."

### 3. Endpoint POST /api/v1/agent/batch

Para ejecutar múltiples agent tasks en paralelo (por ejemplo, calificar 10 leads de una vez).

Request:
```json
{
  "tasks": [
    {"agent_role": "sales_qualifier", "context": "Lead 1: ...", "max_tokens": 1024},
    {"agent_role": "sales_qualifier", "context": "Lead 2: ...", "max_tokens": 1024},
    {"agent_role": "outreach_composer", "context": "Draft for lead 3: ...", "max_tokens": 2048}
  ],
  "max_concurrent": 5
}
```

Response:
```json
{
  "results": [
    {"index": 0, "success": true, "response": "...", "tokens_input": 200, "tokens_output": 150},
    {"index": 1, "success": true, "response": "...", "tokens_input": 180, "tokens_output": 140},
    {"index": 2, "success": false, "error": "timeout", "response": ""}
  ],
  "total": 3,
  "succeeded": 2,
  "failed": 1,
  "total_tokens": 670,
  "total_duration_ms": 3200
}
```

Usar el batch_processor existente de argentor-agent. Respetar token budgets.

### 4. Webhook proxy con compliance

Nuevo endpoint que recibe webhooks externos, valida autenticación, agrega audit trail de compliance, y los forwardea a XcapitSFF.

```
POST /api/v1/proxy/webhook
Headers: X-Webhook-Secret: <hmac-sha256>
Body: { "event": "lead.created", "data": {...}, "source": "hubspot" }

→ Argentor valida HMAC, registra en audit log, chequea compliance
→ Forward a http://xcapitsff:8000/api/v1/webhooks/generic
→ Retorna resultado del forward al caller
```

Config necesaria:
```toml
[xcapitsff]
url = "http://localhost:8000"
health_check_interval = 30  # seconds

[webhook_proxy]
allowed_sources = ["hubspot", "salesforce", "stripe", "intercom"]
hmac_secret = "${WEBHOOK_SECRET}"
```

### 5. Health check cruzado

El endpoint GET /api/v1/health de Argentor debe incluir el status de XcapitSFF:

```json
{
  "status": "ok",
  "version": "0.1.0",
  "checks": {
    "llm_backends": "ok",
    "xcapitsff": "ok",
    "compliance": "ok"
  },
  "xcapitsff": {
    "url": "http://localhost:8000",
    "status": "ok",
    "last_check": "2026-03-18T12:00:00Z"
  }
}
```

Hacer health check periódico (cada 30s) a XcapitSFF GET /health.

### 6. CORS y networking

Configurar CORS para permitir requests desde XcapitSFF:
```toml
[cors]
allowed_origins = ["http://localhost:8000", "http://xcapitsff:8000"]
allowed_methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
```

### 7. Docker compose compartido

Argentor debe poder correr junto a XcapitSFF en docker-compose:

```yaml
services:
  argentor:
    build: ./Argentor
    ports: ["3000:3000"]
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - XCAPITSFF_URL=http://xcapitsff:8000
      - WEBHOOK_SECRET=${WEBHOOK_SECRET}
    depends_on:
      xcapitsff:
        condition: service_healthy

  xcapitsff:
    build: ./XcapitSFF
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=postgresql+asyncpg://xcapit:xcapit@postgres:5432/xcapitsff
      - ARGENTOR_URL=http://argentor:3000
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    depends_on:
      postgres:
        condition: service_healthy
```

### Prioridad de implementación

1. **/api/v1/agent/run-task** — esto desbloquea toda la integración
2. **4 agent profiles** — para que XcapitSFF pueda invocar por rol
3. **Health check cruzado** — para monitoreo
4. **/api/v1/agent/batch** — para operaciones masivas
5. **Webhook proxy** — para compliance en ingesta
6. **CORS + Docker** — para deployment

---
