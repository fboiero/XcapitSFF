# XcapitSFF + Argentor — Arquitectura Híbrida

## Principio
- **Argentor (Rust)**: todo lo que es infraestructura de agentes AI
- **XcapitSFF (Python)**: toda la lógica de negocio
- **Comunicación**: HTTP REST entre ambos servicios

## Por qué esta separación

### Argentor maneja mejor:
- Runtime de agentes (14 LLM backends, circuit breaker, failover)
- Seguridad (WASM sandbox, capability permissions, audit trail)
- Compliance (GDPR, ISO 27001/42001)
- Orquestación multi-agente (DAG, replanning, budget tracking)
- Gateway (JWT, OAuth2, rate limiting, WebSocket)
- Performance (Rust, zero-cost abstractions, async Tokio)

### XcapitSFF maneja mejor:
- Lógica de negocio que cambia rápido (scoring, pipeline, outreach)
- Data processing (pandas, CSV/TSV import, analytics)
- Templates y contenido en español
- Iteración rápida (Python es más ágil para business logic)
- ORM + migrations (SQLAlchemy + Alembic)

## Arquitectura

```
┌─────────────────────────────────────────────────────┐
│                   CLIENTES                           │
│     Web App  ·  Mobile  ·  CRM  ·  Webhooks        │
└──────────────────┬──────────────────────────────────┘
                   │ HTTP/WS
┌──────────────────▼──────────────────────────────────┐
│              ARGENTOR GATEWAY (Rust)                  │
│  ┌──────────┐ ┌────────┐ ┌──────────┐ ┌─────────┐  │
│  │ Auth     │ │ Rate   │ │ Audit    │ │ MCP     │  │
│  │ JWT/OAuth│ │ Limit  │ │ Trail    │ │ Protocol│  │
│  └──────────┘ └────────┘ └──────────┘ └─────────┘  │
│  ┌──────────────────────────────────────────────┐   │
│  │         AGENT RUNTIME                         │   │
│  │  14 LLM Backends · Circuit Breaker           │   │
│  │  WASM Sandbox · Token Budgeting              │   │
│  │  DAG Orchestrator · Replanner                │   │
│  └──────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────┐   │
│  │         COMPLIANCE ENGINE                     │   │
│  │  GDPR · ISO 27001 · ISO 42001 · DPGA        │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  Endpoints: /api/v1/agent/chat, /agent/status       │
│             /sessions, /skills, /metrics             │
└──────────────────┬──────────────────────────────────┘
                   │ HTTP (internal network)
┌──────────────────▼──────────────────────────────────┐
│            XCAPITSFF BUSINESS API (Python)            │
│  ┌──────────────────────────────────────────────┐   │
│  │              SALES MODULE                     │   │
│  │  ICP Scoring · Pipeline · Outreach           │   │
│  │  Campaigns · Lifecycle · Leaderboard         │   │
│  │  Import/Export · Analytics                    │   │
│  └──────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────┐   │
│  │              SUPPORT MODULE                   │   │
│  │  Tickets · SLA · Routing · Knowledge Base    │   │
│  │  Templates · Escalation · Analytics          │   │
│  └──────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────┐   │
│  │              CUSTOMER MODULE                  │   │
│  │  Customer 360 · Data Quality · Search        │   │
│  │  Reporting · Notifications                   │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  Endpoints: /api/v1/leads, /tickets, /customers     │
│             /analytics, /outreach, /campaigns, ...  │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│              POSTGRESQL + REDIS                      │
└─────────────────────────────────────────────────────┘
```

## Flujo de datos

### Lead qualification (ejemplo)
1. Webhook llega al **Argentor Gateway** (autenticado, rate limited, audit logged)
2. Gateway rutea a **XcapitSFF** `/api/v1/webhooks/leads`
3. XcapitSFF crea el lead, calcula ICP score, guarda en DB
4. XcapitSFF llama a **Argentor** `/api/v1/agent/chat` pidiendo calificación AI
5. Argentor ejecuta el agente sales_qualifier (con failover, circuit breaker)
6. Respuesta vuelve a XcapitSFF, que actualiza el lead y emite evento
7. Si lead es hot → XcapitSFF llama a Argentor para draft outreach

### Ticket support (ejemplo)
1. Ticket llega via **Argentor Gateway** (compliance check, GDPR consent)
2. Gateway rutea a **XcapitSFF** `/api/v1/webhooks/tickets`
3. XcapitSFF clasifica (multi-signal router), asigna prioridad, SLA
4. XcapitSFF llama a **Argentor** `/api/v1/agent/chat` para generar respuesta
5. Argentor ejecuta support_responder (con context de KB)
6. Respuesta vuelve, XcapitSFF la muestra como draft para aprobación

## Docker Compose
```yaml
services:
  argentor:      # Rust binary — agent runtime + gateway
    ports: ["3000:3000"]
  xcapitsff:     # Python — business logic API
    ports: ["8000:8000"]
  postgres:      # Shared database
  redis:         # Shared cache/queue
```

## Beneficios de la arquitectura híbrida
1. **Cada stack en su fortaleza**: Rust para performance/security, Python para business logic
2. **Iteración independiente**: cambiar scoring no toca Argentor, cambiar LLM backend no toca Python
3. **Compliance real**: todo tráfico pasa por Argentor (audit, GDPR, ISO)
4. **Escalabilidad**: cada servicio escala independientemente
5. **Testeo aislado**: 593 tests Python + 1357 tests Rust, cada uno en su dominio
