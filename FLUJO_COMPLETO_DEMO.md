# XcapitSFF — Flujo Completo: Alta de Cliente → Desarrollo de Software

**Fecha:** 2026-03-23
**Cliente Demo:** Banco Patagonia S.A.
**Objetivo:** Documentar el pipeline end-to-end para evolucionar el sistema

---

## Resumen del Pipeline

```
DISCOVERY → LEAD → DEAL → PROPUESTA → CONTRATO → PROYECTO → TAREAS
    ↓          ↓       ↓        ↓           ↓          ↓         ↓
 26 preguntas  ICP   Quote   Markdown    Firmado    10 tasks   468 hrs
 10 fases     61pts  USD154K  auto-gen   CTR-0001   PROJ-0001  estimadas
```

---

## Paso 1: Discovery Session

**Endpoint:** `POST /api/v1/discovery/sessions`

### Crear sesión
```bash
curl -X POST http://localhost:8000/api/v1/discovery/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "client_name": "Banco Patagonia",
    "client_email": "innovacion@bancopatagonia.com.ar",
    "client_company": "Banco Patagonia S.A.",
    "industry": "fintech"
  }'
```

**Resultado:** `session_id: b3f944c0a6ee4639`

### Fases del Discovery (10 fases, 34 preguntas posibles)

| # | Fase | Preguntas Requeridas | Ejemplo de Respuesta |
|---|------|---------------------|---------------------|
| 1 | `intro` | intro_01, intro_02, intro_04 | Quiénes son, qué necesitan, timeline/budget |
| 2 | `business_context` | biz_01..biz_04 | Empresa, stack actual, competencia, regulaciones |
| 3 | `problem_definition` | prob_01..prob_03 | Problema principal, impacto económico, solución deseada |
| 4 | `users_and_personas` | user_01, user_03 | Tipos de usuario, volúmenes |
| 5 | `current_workflow` | flow_01..flow_03 | Flujo actual, herramientas, pain points |
| 6 | `pain_points` | pain_01..pain_03 | Dolores principales, errores, pérdidas |
| 7 | `success_criteria` | success_01..success_03 | KPIs, métricas, revisión |
| 8 | `technical_context` | tech_01, tech_03 | Stack, equipo técnico |
| 9 | `budget_timeline` | budget_01, budget_02, budget_04 | Presupuesto, equipo, enfoque |
| 10 | `summary` | (ninguna) | Revisión final |

### Flujo de respuestas
```bash
# Responder pregunta
curl -X POST /api/v1/discovery/sessions/{id}/answer \
  -d '{"question_id":"intro_01","answer":"..."}'

# Avanzar fase (valida que las requeridas estén respondidas)
curl -X POST /api/v1/discovery/sessions/{id}/advance

# Completar sesión
curl -X POST /api/v1/discovery/sessions/{id}/complete
```

### Generar artefactos desde Discovery
```bash
# Requirements document
curl -X POST /api/v1/discovery/sessions/{id}/generate-requirements
# → 7 requerimientos funcionales, 5 user stories, estimación 600 hrs

# Propuesta comercial
curl -X POST /api/v1/discovery/sessions/{id}/generate-proposal
# → Propuesta con 4 fases, inversión, timeline, T&C
```

### Hallazgos / Issues encontrados
- Las respuestas genéricas ("Respuesta detallada para budget_01...") se filtran al proposal. **TODO:** Validar calidad de respuestas antes de generar propuesta.
- El campo `industry` del session no se persiste correctamente (queda vacío).
- El sistema genera `recommended_plan: "Plan Gratuito"` para un proyecto de USD 150K. **TODO:** Lógica de recomendación de plan necesita ajuste.

---

## Paso 2: Lead + Scoring ICP

**Endpoint:** `POST /api/v1/leads/`

```bash
curl -X POST http://localhost:8000/api/v1/leads/ \
  -d '{
    "company_name": "Banco Patagonia S.A.",
    "contact_name": "Martín Rodriguez",
    "email": "mrodriguez@bancopatagonia.com.ar",
    "region": "LATAM",
    "c_level": true,
    "industry": "Banking",
    "company_size": "enterprise",
    "source": "referral",
    "notes": "Discovery completado. Budget USD 150K."
  }'
```

**Resultado:**
- `score_icp: 61.0` | `afinidad: MEDIUM` | `stage: raw`
- El lead NO captura `email` en `contact_email` (queda null). **TODO:** Mapear campo `email` → `contact_email`.

### Enrichment
```bash
curl -X POST /api/v1/enrichment/2
# → industry: "fintech", confidence: 0.2
```

### Transición de stage
```bash
curl -X PATCH /api/v1/leads/2 -d '{"stage": "qualified"}'
# Nota: /leads/{id}/transition no existe. Se usa PATCH.
```

### Hallazgos
- ICP score 61 para un banco enterprise C-level parece bajo. **TODO:** Revisar pesos del scoring en `sales/scoring.py`.
- No hay endpoint `/leads/{id}/transition`, solo PATCH directo. **TODO:** Crear endpoint de transición con validación de flujo.

---

## Paso 3: Deal + Quote

### Crear Deal
**Endpoint:** `POST /api/v1/deals/` (requiere `tenant_id`)

```bash
curl -X POST http://localhost:8000/api/v1/deals/ \
  -d '{
    "tenant_id": "default",
    "name": "Digitalización Préstamos - Banco Patagonia",
    "amount": 150000,
    "currency": "USD",
    "stage": "proposal",
    "probability": 75,
    "contact_id": "{contact_uuid}",
    "company_id": "{company_uuid}",
    "lead_id": "2",
    "expected_close_date": "2026-05-15"
  }'
```

### Crear Quote con Line Items
**Endpoint:** `POST /api/v1/quotes/` (requiere `client_name`, `client_email`, `line_items`)

```bash
curl -X POST http://localhost:8000/api/v1/quotes/ \
  -d '{
    "tenant_id": "default",
    "deal_id": "{deal_uuid}",
    "title": "Cotización - Plataforma Préstamos Digitales",
    "client_name": "Banco Patagonia S.A.",
    "client_email": "mrodriguez@bancopatagonia.com.ar",
    "currency": "USD",
    "valid_until": "2026-04-22",
    "line_items": [
      {"description": "Fase 1: Discovery y Diseño", "quantity": 1, "unit_price": 12000},
      {"description": "Fase 2: Desarrollo MVP", "quantity": 1, "unit_price": 85000},
      {"description": "Fase 3: Iteración", "quantity": 1, "unit_price": 30000},
      {"description": "Fase 4: QA y Deploy", "quantity": 1, "unit_price": 15000},
      {"description": "Infra AWS (6 meses)", "quantity": 6, "unit_price": 2000}
    ]
  }'
```

**Resultado:** `quote_number: QT-0001` | `total: USD 154,000`

### Pipeline de stages del Deal
```
proposal → negotiation → closed_won
```

```bash
# Avanzar stage
curl -X POST /api/v1/deals/{id}/stage -d '{"new_stage": "negotiation"}'
curl -X POST /api/v1/deals/{id}/stage -d '{"new_stage": "closed_won"}'

# Aceptar quote
curl -X POST /api/v1/quotes/{id}/accept
```

### Hallazgos
- `deals/convert-lead` requiere `tenant_id`, `name`, `amount` — no es un simple convert. **TODO:** Simplificar conversión de lead a deal.
- El forecast después de cerrar deal muestra $0. **TODO:** Revisar lógica de forecast en `deals.py`.
- Stages válidos: NO incluyen "won" (es "closed_won"). Documentar stages válidos.

---

## Paso 4: Propuesta (auto-generada desde Discovery)

Ya documentado en Paso 1. La propuesta se genera automáticamente con:
- Executive summary
- Alcance (7 reqs funcionales + 5 user stories)
- 4 fases de implementación
- Timeline: 19 semanas
- Inversión: USD 47,500 (desarrollo) — **discrepancia con quote de USD 154K**
- Términos y condiciones

**TODO:** La propuesta genera un precio de USD 47,500 pero el quote real es USD 154,000. Alinear la lógica de pricing del proposal generator con quotes reales.

---

## Paso 5: Contrato

**Endpoint:** `POST /api/v1/contracts/`

```bash
curl -X POST http://localhost:8000/api/v1/contracts/ \
  -d '{
    "client_name": "Banco Patagonia S.A.",
    "client_email": "mrodriguez@bancopatagonia.com.ar",
    "project_name": "Plataforma Digital de Préstamos Personales",
    "scope": "Portal web + API scoring ML + integraciones BCRA/Veraz + dashboard",
    "total_amount": 154000,
    "currency": "USD",
    "start_date": "2026-04-01",
    "end_date": "2026-09-15",
    "payment_terms": "50/25/25"
  }'
```

**Resultado:** `CTR-000001` | plan: pro | SLA: 99.5% | soporte: priority

```bash
# Firmar
curl -X POST /api/v1/contracts/CTR-000001/sign
# → status: "signed", signed_at: "2026-03-23T13:07:17"
```

### Hallazgos
- El contrato ignora `total_amount`, `scope`, `payment_terms` del input y genera valores fijos del plan Pro. **TODO:** El contract generator debe usar los datos del deal/quote, no defaults del plan.
- No hay endpoint de markdown para contratos (retorna vacío). **TODO:** Implementar `/contracts/{id}/markdown`.

---

## Paso 6: Proyecto + Tareas

### Crear Proyecto
**Endpoint:** `POST /api/v1/projects/`

```bash
curl -X POST http://localhost:8000/api/v1/projects/ \
  -d '{
    "name": "Plataforma Digital Préstamos - Banco Patagonia",
    "client_name": "Banco Patagonia S.A.",
    "description": "Portal web + API scoring ML + Dashboard + Integraciones",
    "start_date": "2026-04-01",
    "end_date": "2026-09-15",
    "budget": 154000,
    "milestones": [
      {"name": "Kickoff + Discovery", "due_date": "2026-04-14"},
      {"name": "MVP Portal + Scoring", "due_date": "2026-06-23"},
      {"name": "Integraciones BCRA/Veraz", "due_date": "2026-07-20"},
      {"name": "ML Scoring + Analytics", "due_date": "2026-08-17"},
      {"name": "UAT + Go-Live", "due_date": "2026-09-15"}
    ]
  }'
```

**Resultado:** `PROJ-0001` | status: planning | milestones: 0 (no se persistieron)

### Crear Tareas
**Endpoint:** `POST /api/v1/projects/{id}/tasks`

| # | Tarea | Prioridad | Horas Est. |
|---|-------|-----------|-----------|
| 1 | Diseñar arquitectura microservicios | high | 40 |
| 2 | Wireframes portal cliente | high | 24 |
| 3 | Setup CI/CD + infra AWS | high | 32 |
| 4 | API scoring crediticio v1 | high | 60 |
| 5 | Portal web React - solicitud préstamos | high | 80 |
| 6 | Dashboard oficiales de crédito | medium | 60 |
| 7 | Integración BCRA Central de Deudores | high | 40 |
| 8 | Integración Veraz/Nosis | medium | 32 |
| 9 | Modelo ML scoring préstamos | medium | 60 |
| 10 | UAT + deploy producción | high | 40 |

**Total:** 10 tareas | 468 horas estimadas

### Hallazgos
- Los milestones del proyecto NO se persisten (phases: 0). **TODO:** Revisar persistencia de milestones en `project.py`.
- No hay conexión automática entre milestones y tareas. **TODO:** Vincular tareas a milestones.

---

## Paso 7: Sofi (Asistente IA)

### Iniciar conversación
```bash
curl -X POST /api/v1/assistant/start -d '{"user_name": "Fer"}'
# → conversation_id + welcome message con quick actions
```

### Chatear
```bash
curl -X POST /api/v1/assistant/message \
  -d '{"conversation_id": "{id}", "text": "Dame un resumen del estado actual"}'
```

**Respuestas de Sofi:**
- Dashboard: 37 leads, 14 tickets, 17% conversión, CSAT 4.5/5
- Leads: tabla con top 5 leads por score
- Suggestions: "Ver leads hot", "Ver tickets urgentes", "Ver predicciones"
- Visual components: cards, tables con datos estructurados

### Hallazgos
- Sofi devuelve datos de **demo** hardcodeados (37 leads, etc.), no los datos reales de la BD. **TODO:** Conectar Sofi con queries reales a la base de datos.
- El campo para mensajes es `text`, no `message`. Documentar en Swagger.

---

## IDs de Referencia (esta demo)

| Entidad | ID |
|---------|-----|
| Discovery Session | `b3f944c0a6ee4639` |
| Lead | `2` |
| Company | `46aec2af-bf77-4519-bb67-90d44b24a6b5` |
| Contact | `9f7e65b8-a2dc-4af8-80b8-a07241651659` |
| Deal | `14d913e3-099d-4d60-90b8-fe626092a732` |
| Quote | `b953a699-4414-4c0b-85c8-3981b64471a2` (QT-0001) |
| Contract | `CTR-000001` |
| Project | `PROJ-0001` |
| Sofi Conv | `ce40e9d4-885f-4bc8-bfff-7d8258b992fa` |

---

## Backlog de Mejoras Detectadas

### Prioridad Alta
1. **Sofi → datos reales:** Conectar assistant con queries reales, no datos hardcodeados
2. **Contract generator:** Usar datos del deal/quote (monto, scope, payment terms)
3. **Proposal pricing:** Alinear precio generado con quote real
4. **ICP scoring:** Revisar pesos — banco enterprise C-level = 61 puntos es bajo
5. **Lead email mapping:** Campo `email` no se mapea a `contact_email`

### Prioridad Media
6. **Milestones persistencia:** Los milestones del proyecto no se guardan
7. **Lead transition endpoint:** Crear `/leads/{id}/transition` con validación de flujo
8. **Deal convert-lead:** Simplificar — no debería requerir todos los campos del deal
9. **Discovery industry:** El campo industry no se persiste en la sesión
10. **Forecast:** Deal cerrado no aparece en forecast

### Prioridad Baja
11. **Proposal plan recommendation:** Lógica para recomendar plan basado en budget/scope
12. **Contract markdown:** Implementar endpoint de markdown para contratos
13. **Discovery answer validation:** Validar calidad de respuestas antes de generar propuesta
14. **Vincular tareas ↔ milestones** en el módulo de proyectos

---

## Dependencias entre Módulos

```
Discovery ──┐
            ├──→ Requirements ──→ Proposal
            │                       ↓
Lead ───────┼──→ Deal ──→ Quote ──→ Contract
            │     ↓
Company ────┘   Project ──→ Tasks ──→ Milestones
Contact ────┘

Sofi (transversal) ──→ consulta todos los módulos
```

---

## Notas Técnicas

- **Python 3.10 compatible:** El proyecto dice `>=3.11` pero funciona bien en 3.10 (solo necesita `aiosqlite` como dep extra)
- **tenant_id:** Requerido en companies, contacts, deals, quotes. No en leads ni discovery.
- **SQLite en dev:** Usa aiosqlite para desarrollo local (sin PostgreSQL)
- **Swagger docs:** Disponible en `/docs` pero `/openapi.json` puede ser lento

---

*Generado por XcapitSFF pipeline automation — 2026-03-23*
