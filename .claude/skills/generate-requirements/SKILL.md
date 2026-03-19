---
name: generate-requirements
description: Generar documento de requerimientos desde un discovery completado. /generate-requirements [session_id]
context: fork
disable-model-invocation: false
---
1. Leer la sesión de discovery (por session_id o la más reciente)
2. Invocar business-analyst agent con todos los datos del discovery
3. Generar:
   - PRD completo con requerimientos funcionales y no funcionales
   - User stories en formato estándar
   - Backlog priorizado con MoSCoW
   - Mapa de módulos XcapitSFF recomendados
   - Estimación de effort

4. Guardar el PRD en .claude/specs/PRD-{empresa}.md
5. Mostrar resumen al usuario
