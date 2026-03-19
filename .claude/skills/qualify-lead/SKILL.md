---
name: qualify-lead
description: Calificar un lead o batch de leads usando ICP scoring. /qualify-lead [lead_id | "all" | filtro]
context: fork
disable-model-invocation: false
---
Proceso de calificación de leads:

1. Si se recibe un lead_id específico: leer ese lead de la DB vía API
2. Si se recibe "all": obtener todos los leads en stage "raw"
3. Si se recibe un filtro (ej: "region:LATAM afinidad:HIGH"): filtrar

Para cada lead:
- Invocar sales-qualifier agent con los datos del lead
- Calcular/verificar ICP score usando src/xcapitsff/sales/scoring.py
- Clasificar como hot/warm/cool/cold
- Recomendar acción: contactar, nutrir, o descartar
- Si es hot + c_level: auto-avanzar a stage "qualified"

Mostrar resultado como tabla con acción recomendada para cada lead.
PAUSAR antes de hacer cambios masivos de stage.
