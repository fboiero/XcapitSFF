---
name: security-scan
description: Ejecutar revisión de seguridad sobre archivos modificados en el branch actual. Invocar con /security-scan
disable-model-invocation: true
---
1. Ejecutar: git diff --name-only main...HEAD (o master si no hay main)
2. Filtrar archivos de código fuente (excluir docs, configs)
3. Invocar security-reviewer con la lista de archivos
4. Mostrar resultado completo al usuario
