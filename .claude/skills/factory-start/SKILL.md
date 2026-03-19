---
name: factory-start
description: Iniciar el pipeline completo de la Software Factory para un feature. Invocar con /factory-start "descripción del feature"
context: fork
disable-model-invocation: false
---
Pipeline de la Software Factory:

1. SPECIFY: Invocar planner con el feature recibido como argumento.
   Mostrar el plan al usuario. PAUSAR y esperar aprobación explícita.

2. PLAN: Para cada tarea aprobada, invocar spec-writer.
   Mostrar specs generadas. PAUSAR y esperar aprobación de specs.

3. TASK: Las tareas sin dependencias pueden ejecutarse en paralelo.
   Las tareas con dependencias deben esperar a que sus dependencias completen.

4. IMPLEMENT: Para cada tarea aprobada, en orden de dependencias:
   - Invocar implementer con el TASK-ID
   - Al terminar implementer: invocar test-runner
   - Si tests pasan: invocar code-reviewer
   - Si code-reviewer APPROVE: invocar security-reviewer (si aplica)
   - Si security-reviewer APPROVE o no aplica: invocar doc-updater
   - PAUSAR antes de avanzar si cualquier reviewer da BLOCKED/REQUEST_CHANGES

5. VERIFY: Correr suite completa de tests con test-runner

6. CLOSE: doc-updater actualiza DECISIONS.md y FACTORY_STATE.md
   Mostrar resumen final al usuario.
