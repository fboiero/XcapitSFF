# Argentor Phase 2 — Funcionalidades avanzadas para XcapitSFF

Copiar desde aquí al hilo de Claude Code de Argentor:

---

## Contexto

Argentor ya tiene (o está en proceso de tener) el endpoint `/api/v1/agent/run-task` básico.
Ahora necesitamos funcionalidades avanzadas para que XcapitSFF pueda ofrecer un producto completo.

## 1. Streaming responses via SSE

XcapitSFF necesita mostrar respuestas de agentes en tiempo real (el usuario ve cómo se genera la respuesta, no espera 30 segundos).

```
POST /api/v1/agent/run-task-stream
Content-Type: application/json

{
  "agent_role": "support_responder",
  "context": "...",
  "session_id": "ses_123"
}

Response: text/event-stream
data: {"type": "token", "content": "Hola"}
data: {"type": "token", "content": " te"}
data: {"type": "token", "content": " ayudo"}
data: {"type": "done", "session_id": "ses_123", "tokens_input": 200, "tokens_output": 150}
```

Usar el `run_streaming` existente de AgentRunner, exponerlo via SSE en el gateway.

## 2. Agent tools — que los agentes consulten XcapitSFF

Los agentes necesitan poder consultar datos de negocio mientras responden. Por ejemplo, el support_responder necesita buscar artículos de KB, o el sales_qualifier necesita ver el historial del lead.

Implementar como skills de Argentor que hacen HTTP GET a XcapitSFF:

**Skill: xcapitsff_search**
- Input: `{"query": "..."}`
- Acción: GET `http://xcapitsff:8000/api/v1/search/?q={query}`
- Output: resultados de búsqueda

**Skill: xcapitsff_lead_info**
- Input: `{"lead_id": 123}`
- Acción: GET `http://xcapitsff:8000/api/v1/leads/{lead_id}`
- Output: datos del lead

**Skill: xcapitsff_ticket_info**
- Input: `{"ticket_id": 456}`
- Acción: GET `http://xcapitsff:8000/api/v1/tickets/{ticket_id}`
- Output: datos del ticket con mensajes

**Skill: xcapitsff_kb_search**
- Input: `{"subject": "...", "description": "..."}`
- Acción: GET `http://xcapitsff:8000/api/v1/knowledge/for-ticket?subject=...&description=...`
- Output: artículos relevantes

**Skill: xcapitsff_customer360**
- Input: `{"customer_id": 789}`
- Acción: GET `http://xcapitsff:8000/api/v1/customers/{customer_id}/360`
- Output: vista 360 del cliente

Estas skills deben registrarse como builtins con capability `NetworkAccess`. Los agentes de negocio las recibirán automáticamente en su tool set.

## 3. Cost tracking per tenant

XcapitSFF cobra por plan (free/pro/enterprise). Necesitamos saber cuánto gasta cada tenant en LLM para pricing y limits.

```
GET /api/v1/usage/tenant/{tenant_id}
Response: {
  "tenant_id": "t_123",
  "period": "2026-03",
  "total_tokens_input": 50000,
  "total_tokens_output": 25000,
  "total_cost_usd": 0.45,
  "by_agent": {
    "sales_qualifier": {"calls": 20, "tokens": 15000, "cost": 0.12},
    "support_responder": {"calls": 50, "tokens": 45000, "cost": 0.28}
  },
  "by_model": {
    "claude-sonnet-4-6": {"calls": 65, "tokens": 55000, "cost": 0.35},
    "gpt-4o-mini": {"calls": 5, "tokens": 5000, "cost": 0.05}
  }
}
```

Debe trackear por tenant_id (que XcapitSFF pasa en el header `X-Tenant-ID` o en el body del request).

## 4. Model routing inteligente

No todas las tareas necesitan Claude Opus. Implementar routing automático:

- **ticket_router** (clasificación simple) → modelo barato (gpt-4o-mini, haiku)
- **support_responder** (respuesta compleja) → modelo medio (sonnet)
- **sales_qualifier** (análisis) → modelo medio (sonnet)
- **outreach_composer** (creatividad) → modelo medio (sonnet)
- **product_manager** (discovery, estrategia) → modelo top (opus)
- **business_analyst** (especificaciones) → modelo top (opus)

```
POST /api/v1/agent/run-task
{
  "agent_role": "ticket_router",
  "routing_hint": "fast_cheap"  // opciones: fast_cheap, balanced, quality_max
}
```

Argentor elige el modelo basado en el `routing_hint` + agent profile config.

## 5. Response quality scoring

Después de cada respuesta de agente, evaluar automáticamente la calidad:

```
POST /api/v1/agent/evaluate
{
  "response": "...",
  "context": "...",
  "criteria": ["relevance", "helpfulness", "accuracy", "tone"]
}

Response: {
  "overall_score": 0.85,
  "by_criteria": {
    "relevance": 0.9,
    "helpfulness": 0.8,
    "accuracy": 0.85,
    "tone": 0.85
  },
  "suggestions": ["La respuesta podría incluir más empatía"]
}
```

Esto usa un modelo evaluador (puede ser el mismo, con prompt de evaluación). Se usa para:
- Filtrar respuestas malas antes de enviar al cliente
- Mejorar prompts con feedback
- Analytics de calidad por agente

## 6. WebSocket para chat en tiempo real

Para la UI de soporte donde el agente AI chatea con el equipo humano:

```
WS /ws/agent-chat
→ {"type": "user_message", "session_id": "s1", "content": "Calificá este lead"}
← {"type": "agent_thinking", "session_id": "s1"}
← {"type": "agent_token", "session_id": "s1", "content": "Anali"}
← {"type": "agent_token", "session_id": "s1", "content": "zando"}
← {"type": "agent_done", "session_id": "s1", "full_response": "..."}
← {"type": "tool_call", "session_id": "s1", "tool": "xcapitsff_lead_info", "params": {...}}
← {"type": "tool_result", "session_id": "s1", "result": {...}}
```

El WebSocket de Argentor ya existe para approval channels. Extenderlo para agent chat.

## 7. Agent personas configurables por tenant

Cada tenant puede customizar el tono/personalidad de sus agentes:

```
POST /api/v1/agent/personas
{
  "tenant_id": "t_123",
  "agent_role": "support_responder",
  "persona": {
    "name": "Sofía",
    "tone": "friendly_professional",
    "language_style": "es_latam_informal",
    "signature": "Sofía del equipo de [empresa]",
    "custom_instructions": "Siempre ofrecer videollamada para temas complejos"
  }
}
```

Se inyecta como parte del system prompt antes de enviar al LLM.

## Prioridad

1. **Skills xcapitsff_*** — esto es lo que hace a los agentes ÚTILES (pueden consultar datos reales)
2. **Streaming SSE** — UX crítica, el usuario no puede esperar 30s
3. **Cost tracking per tenant** — necesario para billing
4. **Model routing** — reduce costos 50-70%
5. **WebSocket chat** — para la UI interactiva
6. **Response quality** — calidad del servicio
7. **Agent personas** — diferenciador comercial

---
