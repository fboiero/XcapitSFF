---
name: draft-outreach
description: Componer mensaje de outreach para un lead. /draft-outreach [lead_id] [canal:email|linkedin|whatsapp]
context: fork
disable-model-invocation: false
---
Proceso de composición de outreach:

1. Leer datos del lead (ID proporcionado)
2. Determinar canal (email por defecto)
3. Invocar outreach-composer agent con contexto del lead
4. Generar mensaje personalizado + variante A/B
5. Guardar como draft en outreach_messages

El mensaje debe adaptarse a:
- Region del lead (LATAM vs Iberia → idioma y tono)
- Si es C-Level (enfoque estratégico vs operativo)
- Afinidad (HIGH: directo, MEDIUM: educativo, LOW: nurturing)
- Stage actual (no enviar outreach agresivo a leads cold)

Mostrar el draft al usuario para aprobación antes de guardar.
