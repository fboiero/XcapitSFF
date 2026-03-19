---
name: generate-proposal
description: Generar propuesta comercial para un cliente. /generate-proposal [session_id]
context: fork
disable-model-invocation: false
---
1. Leer la sesión de discovery y el PRD generado
2. Invocar proposal-writer agent
3. Generar propuesta comercial completa con:
   - Resumen ejecutivo
   - Solución propuesta (módulos + features)
   - Plan de implementación (fases + timeline)
   - Inversión (plan recomendado + pricing)
   - ROI esperado
   - Próximos pasos
   - Términos y condiciones

4. Guardar en .claude/specs/PROPOSAL-{empresa}.md
5. También generar versión markdown limpia para enviar al cliente
