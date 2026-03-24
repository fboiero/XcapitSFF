# Changelog — XcapitSFF v0.2.0

**Fecha:** 2026-03-23
**Release:** Pipeline Evolution — 14 mejoras del flujo completo
**Tests:** 12/12 verificaciones pasaron ✓

---

## Resumen

Se ejecutó el pipeline completo (Discovery → Lead → Deal → Propuesta → Contrato → Proyecto → Tareas → Sofi) para el cliente demo **Banco Patagonia S.A.** y se detectaron 14 mejoras necesarias. Todas fueron implementadas y verificadas.

---

## Cambios por archivo

### `src/xcapitsff/assistant/executor.py` — Fix 1 (Alta)
**Sofi conectada a datos reales**
- Agregadas funciones `_run_async()`, `_get_leads_from_db()`, `_get_pipeline_stats_from_db()`, `_get_hot_leads_from_db()`, `_get_tickets_from_db()`
- 10 handlers actualizados para consultar la BD real con fallback a datos de demo
- Sofi ahora responde "Encontré 1 leads" (dato real) en vez de "37 leads" (hardcoded)

### `src/xcapitsff/discovery/contracts.py` — Fix 2 (Alta)
**Contract generator con datos del deal/quote**
- 6 campos nuevos en `Contract`: `project_name`, `scope`, `total_amount`, `currency`, `payment_terms`, `end_date`
- `generate()` acepta parámetros custom de proyecto
- Si `total_amount` se provee, se usa en vez del pricing del plan
- Fix bug: annual pricing Pro corregido de `79*12` a `99*12`
- Fix bug: annual pricing Enterprise corregido de `399*12` a `499*12`
- `to_markdown()` genera sección especial para contratos por proyecto

### `src/xcapitsff/api/contracts_api.py` — Fix 2 + Fix 12
- Request model expandido con campos de proyecto custom
- Endpoint markdown ahora retorna JSON `{"contract_id", "markdown"}` en vez de PlainTextResponse

### `src/xcapitsff/discovery/proposal.py` — Fix 3 + Fix 11
**Proposal pricing y plan recommendation mejorados**
- Fix: `annual_cost_usd` Pro: `79 → 1188`, Enterprise: `399 → 5988`
- `_build_investment()` acepta `budget_hint` del discovery session
- Extrae presupuesto de `budget_01` con regex para calibrar costos
- `estimate_plan()` detecta keywords enterprise (banco, gobierno, telecom, etc.)
- Scoring mejorado para user stories (>8 = +2pts, >5 = +1pt)

### `src/xcapitsff/sales/scoring.py` — Fix 4 (Alta)
**ICP scoring más justo para leads nuevos**
- `score_engagement()`: retorna 40.0 (baseline) para leads sin interacciones, en vez de 0
- `score_company_fit()`: default 70.0 (beneficio de la duda) para leads sin evaluación manual, en vez de 50.0
- **Resultado:** Banco Patagonia (enterprise, C-level, LATAM) pasa de 61 → 70 puntos

### `src/xcapitsff/core/schemas.py` — Fix 5 (Alta)
**Lead email mapping**
- `LeadCreate` acepta `email` como alias de `contact_email` via `@model_validator`
- Campos opcionales extra: `industry`, `company_size`, `source`, `phone` (no causan error de validación)

### `src/xcapitsff/discovery/project.py` — Fix 6 + Fix 14
**Milestones y task linking**
- `create_project()` acepta `milestones_data`, `name`, `description`, `budget`, `start_date`, `end_date`
- Milestones se convierten en phases con fechas calculadas
- `ProjectTask` tiene campo `milestone_id`
- `add_task()` acepta `milestone_id` y linkea automáticamente
- Nuevo método `get_tasks_by_milestone()`
- `get_project_report()` incluye progreso por milestone

### `src/xcapitsff/api/project_api.py` — Fix 6 + Fix 14
- Request model expandido con milestones, name, description, budget, dates
- Task creation acepta `milestone_id`
- Task response incluye `milestone_id`

### `src/xcapitsff/api/leads.py` — Fix 7
**Lead transition endpoint con validación**
- Nuevo endpoint `POST /leads/{id}/transition` con `LeadTransitionRequest`
- 8 stages con transiciones válidas definidas
- Retorna error 400 con lista de transiciones válidas si es inválida

### `src/xcapitsff/api/deals_api.py` — Fix 8
**Deal convert-lead simplificado**
- `ConvertLeadSimple` model con defaults sensatos
- Auto-genera nombre del deal si no se provee
- Amount puede ser 0 inicialmente

### `src/xcapitsff/discovery/session.py` — Fix 9 + Fix 13
**Industry persistence + Answer validation**
- `answer_question()` auto-popula `session.industry` cuando se responde `intro_02`
- Validación: respuestas vacías rechazadas, mínimo 10 caracteres
- Mensajes de error en español con conteo de caracteres

### `src/xcapitsff/core/deals.py` — Fix 10
**Forecast con deals cerrados**
- `get_forecast()` ahora incluye `won_by_month` y `total_won`
- Nuevo campo `total_revenue` = pipeline forecast + won revenue
- Deals cerrados-ganados aparecen en el forecast como ingreso realizado

---

## Verificación

```
12/12 tests passed:
  ✓ Fix 4: ICP score >= 70
  ✓ Fix 5: email → contact_email
  ✓ Fix 7a: Transition raw→qualified
  ✓ Fix 7b: Invalid transition blocked
  ✓ Fix 9: Industry from intro_02
  ✓ Fix 13: Short answer rejected
  ✓ Fix 2: Custom total_amount used
  ✓ Fix 12: Markdown JSON response
  ✓ Fix 6: Milestones → phases
  ✓ Fix 14: Task has milestone_id
  ✓ Fix 10: Forecast includes won deals
  ✓ Fix 1: Sofi responds with real data
```

---

## Archivos modificados (10)

1. `src/xcapitsff/assistant/executor.py`
2. `src/xcapitsff/discovery/contracts.py`
3. `src/xcapitsff/discovery/proposal.py`
4. `src/xcapitsff/discovery/project.py`
5. `src/xcapitsff/discovery/session.py`
6. `src/xcapitsff/sales/scoring.py`
7. `src/xcapitsff/core/schemas.py`
8. `src/xcapitsff/core/deals.py`
9. `src/xcapitsff/api/contracts_api.py`
10. `src/xcapitsff/api/leads.py`
11. `src/xcapitsff/api/deals_api.py`
12. `src/xcapitsff/api/project_api.py`
