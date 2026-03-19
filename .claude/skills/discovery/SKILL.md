---
name: discovery
description: Iniciar una sesión de product discovery con un cliente nuevo. /discovery "nombre de la empresa"
context: fork
disable-model-invocation: false
---
Flujo completo de Product Discovery:

1. Invocar **product-manager** agent con el nombre de la empresa
2. El PM guía al usuario a través de las 10 fases de discovery
3. En cada fase, hacer las preguntas correspondientes y esperar respuestas
4. Al completar el discovery, generar un resumen estructurado

5. Invocar **business-analyst** agent con el resumen del discovery
6. El BA genera:
   - Documento de Requerimientos (PRD)
   - User Stories con criterios de aceptación
   - Backlog priorizado

7. Invocar **proposal-writer** agent con los requerimientos
8. El PW genera la propuesta comercial completa

9. Mostrar al usuario:
   - Resumen del discovery
   - PRD generado
   - Propuesta comercial
   - Próximos pasos

PAUSAR después de cada fase para permitir feedback del usuario.
Guardar todo en .claude/specs/DISCOVERY-{empresa}.md
