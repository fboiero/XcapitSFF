---
name: analytics
description: Generar reportes de analytics de ventas y soporte. /analytics [sales|support|executive]
context: fork
disable-model-invocation: false
---
Generar reporte según tipo solicitado:

**sales**: Pipeline de ventas
- Total leads por stage (funnel)
- Distribución por región y afinidad
- Score ICP promedio por segmento
- Leads hot que necesitan acción inmediata
- Conversion rate

**support**: Performance de soporte
- Tickets abiertos vs resueltos
- Tiempo promedio de resolución
- Distribución por categoría y prioridad
- Tickets que excedieron SLA
- Top temas de consulta

**executive** (default): Resumen ejecutivo
- KPIs principales de ambos módulos
- Alertas y recomendaciones accionables

Invocar analytics-reporter agent con los datos del sistema.
Usar las rutas /api/v1/leads/stats y /api/v1/tickets/stats para datos reales.
