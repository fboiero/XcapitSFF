---
name: import-leads
description: Importar leads desde archivo CSV/TSV. /import-leads [ruta_archivo]
context: fork
disable-model-invocation: false
---
Proceso de importación:

1. Leer el archivo proporcionado (CSV o TSV)
2. Parsear con src/xcapitsff/sales/importer.py
3. Validar datos: regiones válidas, scores en rango, afinidad válida
4. Mostrar preview de primeros 10 registros al usuario
5. Calcular ICP scores para leads sin score
6. PAUSAR y pedir confirmación antes de importar

Reportar:
- Total registros parseados
- Registros válidos vs inválidos
- Distribución por región/afinidad/c-level
- Registros sin score (se calculará automáticamente)

Esperar confirmación explícita antes de ejecutar la importación.
