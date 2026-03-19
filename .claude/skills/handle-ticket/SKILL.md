---
name: handle-ticket
description: Gestionar un ticket de soporte. /handle-ticket [ticket_id]
context: fork
disable-model-invocation: false
---
Proceso de gestión de ticket:

1. Leer el ticket completo con todos sus mensajes
2. Invocar ticket-router para clasificar (si no está clasificado)
3. Invocar support-responder para generar respuesta
4. Buscar artículos de knowledge base relevantes
5. Mostrar respuesta propuesta al usuario

Si el ticket es:
- URGENT/HIGH + crypto/billing: FLAG para revisión humana obligatoria
- Involucra fondos: NO auto-responder, solo proponer respuesta
- Bug técnico: generar reporte para equipo dev además de respuesta

Mostrar respuesta propuesta y esperar aprobación antes de enviar.
