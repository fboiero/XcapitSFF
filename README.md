# XcapitSFF — AI-Powered Software Factory

Software Factory completa con agentes de IA para **Desarrollo**, **Ventas** y **Atención al cliente**.

## Quick Start

```bash
# 1. Instalar dependencias
python3 -m venv .venv && source .venv/bin/activate
pip install fastapi uvicorn sqlalchemy pydantic pydantic-settings httpx \
    python-multipart anthropic python-dotenv aiosqlite greenlet

# 2. Seed de datos
PYTHONPATH=src python scripts/seed_all.py

# 3. Levantar API
PYTHONPATH=src uvicorn xcapitsff.api.app:app --reload

# 4. Abrir docs interactivos
open http://localhost:8000/docs
```

O con Docker:
```bash
cp .env.example .env  # configurar ANTHROPIC_API_KEY
docker-compose up
```

## Arquitectura

```
src/xcapitsff/
├── core/           # Database, events, notifications, audit, validators, search
├── sales/          # Scoring, pipeline, outreach, campaigns, lifecycle, analytics
├── support/        # Tickets, routing, knowledge base, SLA monitor, analytics
├── agents/         # AI agent orchestrator + business agents
└── api/            # 97 REST endpoints across 21 routers
```

## Módulos

| Módulo | Descripción | Endpoints |
|--------|-------------|-----------|
| **Sales** | ICP scoring multi-factor, pipeline, import/export, outreach A/B, campaigns | `/api/v1/leads`, `/api/v1/outreach`, `/api/v1/campaigns` |
| **Support** | Tickets con SLA, routing inteligente, knowledge base, escalation | `/api/v1/tickets`, `/api/v1/knowledge` |
| **Analytics** | Reportes de ventas, soporte, SLA compliance, executive dashboard | `/api/v1/analytics`, `/api/v1/dashboard`, `/api/v1/reports` |
| **Agents** | Orchestrator event-driven, task queue, 9 automation rules | `/api/v1/agents` |
| **Webhooks** | Ingesta de leads y tickets desde fuentes externas | `/api/v1/webhooks` |
| **Search** | Búsqueda unificada (leads, tickets, customers, KB) | `/api/v1/search` |
| **Customer 360** | Vista consolidada de cada cliente con risk scoring | `/api/v1/customers/{id}/360` |
| **System** | Health checks, config, scheduler, audit log | `/api/v1/system`, `/api/v1/scheduler`, `/api/v1/audit` |

## Software Factory (Claude Code)

12 agentes especializados, 9 skills operativos, 4 hooks de seguridad:

```bash
/factory-start "feature"    # Pipeline completo
/qualify-lead              # Calificar leads
/draft-outreach            # Componer mensajes
/handle-ticket             # Gestionar tickets
/analytics                 # Reportes
/security-scan             # Revisión de seguridad
```

## Tests

```bash
make test           # 508 tests
make test-cov       # Con coverage
make test-unit      # Solo unitarios
make test-integration  # Solo integración
```

## Stack

- **Python 3.11+** / FastAPI / SQLAlchemy 2.0 / Pydantic v2
- **Anthropic SDK** para agentes de IA
- **Docker** + GitHub Actions CI
- **SQLite** (dev) / **PostgreSQL** (prod)

## Licencia

MIT
