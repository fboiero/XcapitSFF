# Factory State
Generado: 2026-03-18
Branch: master

## Estado: FUNCIONAL — 9 rondas de iteración (+ agents en progreso)

### Métricas finales
| Métrica | Valor |
|---------|-------|
| Módulos Python | 42 |
| Líneas de código (source) | 8,458 |
| Archivos de test | 16 |
| Líneas de test | 3,766 |
| Tests passing | 356/356 |
| API endpoints | 74 |
| Claude Code agents | 12 |
| Skills | 9 |
| Hooks | 4 |
| Archivos totales | 115 |

## Rondas completadas

### R1 — Bootstrap
Estructura, modelos, API básica, agentes, hooks, skills, CI/CD, Docker

### R2 — Core profundo
Scoring multi-factor, router multi-señal, importer robusto, pipeline bulk ops

### R3 — Infra
CLI, structured logging, middleware stack (RequestID, Logging, ErrorHandler)

### R4 — Negocio
Outreach templates (12+ ES, A/B, follow-ups), Knowledge base (20 artículos, relevancia, auto-match), Analytics avanzados (sales, support, SLA)

### R5 — Event-driven
Event bus (18 types), Agent orchestrator (9 rules), Webhooks (leads, tickets, generic), Notifications, SLA monitor, Dashboard

### R6 — Consolidación
Dashboard unificado, notification manager, SLA breach auto-escalation

### R7 — Calidad de datos
Validators (email, lead, ticket, customer, sanitize), Data quality checks, Alembic migrations setup, Business scenario tests, Comprehensive seed script

### R8 — Completitud
Audit log, Export engine (CSV/JSON), Outreach API (compose, A/B, followup, send, history, batch), System API, más integration tests

## Arquitectura

```
src/xcapitsff/
├── config.py, logging_config.py, cli.py
├── core/
│   ├── database.py, models.py, schemas.py
│   ├── events.py (Event bus — 18 event types)
│   ├── notifications.py (Alert routing)
│   ├── audit.py (Audit log)
│   ├── validators.py (Data validation)
│   └── data_quality.py (Quality checks)
├── sales/
│   ├── scoring.py (Multi-factor weighted ICP)
│   ├── pipeline.py (Lead CRUD + bulk ops)
│   ├── importer.py (CSV/TSV + validation + dedup)
│   ├── outreach.py (Templates + A/B + followups)
│   ├── analytics.py (Reports)
│   └── export.py (CSV/JSON export)
├── support/
│   ├── tickets.py (CRUD + SLA)
│   ├── router.py (Multi-signal classification)
│   ├── knowledge.py (Search + relevance + auto-match)
│   ├── sla_monitor.py (Breach detection)
│   └── analytics.py (Support reports)
├── agents/
│   ├── base.py, sales.py, support.py
│   └── orchestrator.py (Event→Agent dispatch)
└── api/ (14 router modules, 74 endpoints)
    ├── app.py, middleware.py
    ├── leads.py, tickets.py, customers.py
    ├── knowledge.py, analytics.py
    ├── webhooks.py, outreach_api.py
    ├── agents_api.py, notifications_api.py
    ├── dashboard.py, data_quality_api.py
    ├── export_api.py, audit_api.py
    └── system.py
```
