# XcapitSFF — CLAUDE.md
# Actualizado: 2026-03-18 (11 rondas de iteración)

## Stack
| Stack | Type | Language | Framework | Test Runner |
|-------|------|----------|-----------|-------------|
| python-fastapi | backend | Python 3.11+ | FastAPI + SQLAlchemy 2.0 | pytest |
| ai-agents | agents | Python | Anthropic SDK | pytest |
| docker-infra | infra | — | Docker Compose + GitHub Actions | — |

## Métricas
- 57 módulos Python, 11,387 LOC
- 508 tests (24 files), 5,468 LOC tests
- 97 API endpoints, 21 routers
- 12 Claude Code agents, 9 skills, 4 hooks

## Estructura
```
src/xcapitsff/
  config.py, logging_config.py, cli.py
  core/
    database.py, models.py, schemas.py
    events.py        — Event bus (18 event types)
    notifications.py — Alert routing (4 channels)
    audit.py         — Audit log (12 action types)
    validators.py    — Data validation
    data_quality.py  — DB quality checks
    search.py        — Unified search engine
    customer360.py   — Customer 360 view
    reporting.py     — Report formatting engine
    scheduler.py     — Periodic task scheduler
  sales/
    scoring.py       — Multi-factor weighted ICP scoring (5 dimensions)
    pipeline.py      — Lead CRUD, transitions, bulk ops, funnel
    importer.py      — CSV/TSV with validation, dedup, batch
    outreach.py      — 12+ templates ES, A/B variants, followups
    campaigns.py     — Campaign lifecycle + targeting + metrics
    lifecycle.py     — Lead event tracking + conversion probability
    analytics.py     — Sales reports + lead health
    export.py        — CSV/JSON export engine
  support/
    tickets.py       — CRUD + SLA tracking + escalation
    router.py        — Multi-signal classification + load balancing
    knowledge.py     — KB search with relevance + auto-match
    sla_monitor.py   — Breach detection + auto-escalation
    analytics.py     — Support reports + agent performance
  agents/
    base.py          — BaseAgent (Anthropic API)
    sales.py         — Sales Qualifier + Outreach Composer
    support.py       — Support Responder + Ticket Router
    orchestrator.py  — Event→Agent dispatch (9 rules)
  api/ (21 routers, 97 endpoints)
    leads, tickets, customers, knowledge, analytics
    webhooks, outreach, campaigns, lifecycle
    agents, notifications, dashboard, reports
    search, batch, export, audit, data_quality
    customer360, scheduler, system
```

## Comandos
```bash
make dev            # API local
make test           # 508 tests
make seed-all       # Seed completo
make docker-up      # Docker
make lint           # Linter
make export-leads   # Export CSV
```

## Pipeline obligatorio
SPECIFY → PLAN → TASK → IMPLEMENT → VERIFY → CLOSE
- Planning/arch/security: opus model
- Implementation/review/tests: sonnet model
- Semi-auto: pausar antes de deploy, DB migrations
