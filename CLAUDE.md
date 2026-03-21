# XcapitSFF — CLAUDE.md
# Actualizado: 2026-03-21 (15 rondas de iteración)

## Stack
| Stack | Type | Language | Framework | Test Runner |
|-------|------|----------|-----------|-------------|
| python-fastapi | backend | Python 3.11+ | FastAPI + SQLAlchemy 2.0 | pytest |
| ai-agents | agents | Python | Anthropic SDK | pytest |
| argentor | agent-runtime | Rust | Custom (Argentor gateway) | — |
| docker-infra | infra | — | Docker Compose + GitHub Actions | — |

## Métricas
- 193 módulos Python, 75,479 LOC
- 2,206 tests (70+ files), 0 failures
- 486 API endpoints, 55+ routers
- 15 Claude Code agents, 13 skills, 4 hooks

## Estructura
```
src/xcapitsff/
  config.py, logging_config.py, cli.py
  core/
    database.py, models.py, schemas.py
    events.py            — Event bus (18 event types)
    notifications.py     — Alert routing (4 channels)
    notification_center.py — Notification feed + read/archive
    activity_log.py      — Entity history + audit trail export
    audit.py             — Audit log (12 action types)
    auth.py              — JWT + password hashing
    rbac.py              — 5 roles, 35 permissions
    billing.py           — Plans (Free/Pro/Enterprise) + subscriptions
    tenancy.py           — Multi-tenant isolation + plan gating
    feature_flags.py     — 25 features with plan-gating
    rate_limiter.py      — Token bucket per tenant/plan
    api_keys.py          — Scoped API keys with rotation
    email_verification.py — Verification + password reset + invitations
    validators.py        — Data validation
    data_quality.py      — DB quality checks
    search.py            — Unified search engine
    customer360.py       — Customer 360 view
    reporting.py         — Report formatting engine
    report_builder.py    — Custom reports (8 templates, 4 formats)
    scheduler.py         — Periodic task scheduler
    metrics.py           — Prometheus-style metrics
    retry.py             — Circuit breaker + dead letter queue
    inbox.py             — Smart inbox (10 item types)
    workflows.py         — Workflow engine (4 step types)
    custom_fields.py     — 9 field types per tenant
    tags.py              — Tagging system
    files.py             — File upload/download + checksums
    notes.py             — Notes/comments with @mentions
    saved_views.py       — Custom list views + filters
    contacts.py          — Contact management + merge
    companies.py         — Company profiles + hierarchy
    deals.py             — Deals pipeline (6 stages)
    quotes.py            — Quotes with line items + lifecycle
    tasks.py             — Tasks + reminders + recurring
    goals.py             — OKR tracking + key results
    email_templates.py   — 15 pre-built Spanish templates
    email_campaigns.py   — Campaign lifecycle + recipient tracking
    webhook_delivery.py  — Outbound webhooks + HMAC + retry
    realtime_analytics.py — Time series + funnels + cohorts
    dashboard_widgets.py — 12 widget types, customizable layout
    sla_policies.py      — Configurable SLA + breach detection
    integrations_hub.py  — 10 service types + sync logs
    bulk_operations.py   — Mass update/delete/tag/import
    data_import.py       — CSV import + field mapping + dedup
  sales/
    scoring.py       — Multi-factor weighted ICP scoring (5 dimensions)
    pipeline.py      — Lead CRUD, transitions, bulk ops, funnel
    importer.py      — CSV/TSV with validation, dedup, batch
    outreach.py      — 12+ templates ES, A/B variants, followups
    campaigns.py     — Campaign lifecycle + targeting + metrics
    sequences.py     — Multi-step outreach sequences
    automation.py    — 6 pre-configured rules, 8 operators
    predictions.py   — Pipeline forecast, churn risk
    enrichment.py    — Company/contact enrichment
    lifecycle.py     — Lead event tracking + conversion probability
    analytics.py     — Sales reports + lead health
    export.py        — CSV/JSON export engine
    kanban.py        — Kanban board (8 stages)
    meetings.py      — Meeting scheduler + availability
    territory.py     — 4 territories, round-robin assignment
    dedup.py         — Email + company name dedup
    leaderboard.py   — Top leads, C-level, ready-for-outreach
    ab_testing.py    — Experiments with z-test, Wilson CI
  support/
    tickets.py       — CRUD + SLA tracking + escalation
    router.py        — Multi-signal classification + load balancing
    knowledge.py     — KB search with relevance + auto-match
    sla_monitor.py   — Breach detection + auto-escalation
    escalation.py    — L1→L4 workflow + auto-rules
    templates.py     — 11 response templates (Spanish)
    satisfaction.py  — CSAT + NPS tracking
    analytics.py     — Support reports + agent performance
  agents/
    base.py          — BaseAgent (Anthropic API)
    sales.py         — Sales Qualifier + Outreach Composer
    support.py       — Support Responder + Ticket Router
    orchestrator.py  — Event→Agent dispatch (9 rules)
    dispatcher.py    — Argentor → local → dry-run fallback
    argentor_client.py — HTTP bridge to Argentor
    runner.py        — AgentRunner with conversation memory
    conversation.py  — Conversation persistence
  assistant/
    intent.py        — Multi-strategy intent recognition (25+ intents)
    executor.py      — Rich visual responses for every action
    conversation.py  — AssistantManager with context tracking
    visual.py        — 14 VisualComponent types
    guide.py         — Contextual suggestions
    personality.py   — "Sofi" personality (Argentine Spanish)
  selfservice/
    wizard.py        — 8-step setup wizard
    templates_catalog.py — 5 industry templates
    tutorials.py     — 6 interactive tutorials
    quickstart.py    — 8 instant-value actions
    health_score.py  — 20+ checks, grade A-F
    playground.py    — Agent playground
    conversational_onboarding.py — Config from natural chat
    role_dashboards.py — 4 role-specific dashboards
    gamification.py  — 16 achievements, 5 levels
    usage_insights.py — Weekly insights + feature adoption
    keyboard_shortcuts.py — 19 shortcuts
    command_palette.py — Ctrl+K search (20+ commands)
    notifications_preferences.py — Per-user notification config
  discovery/
    session.py       — 34 questions, 10 phases (Spanish)
    requirements.py  — Requirements generator
    proposal.py      — Proposal generator (markdown)
    contracts.py     — Contract generator
    project.py       — Project management + milestones
  integrations/
    email.py, slack.py, crm.py
  api/ (55+ routers, 486 endpoints)
```

## Comandos
```bash
make dev            # API local
make test           # 2206 tests
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
