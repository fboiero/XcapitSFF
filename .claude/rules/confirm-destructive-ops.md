---
name: confirm-destructive-ops
description: Aplica antes de deploy, DB migrations, contract deployment, o cualquier operación irreversible
---
SIEMPRE pausar y pedir confirmación explícita al usuario antes de:
- Deploy a cualquier ambiente
- Ejecutar migraciones de base de datos
- Deployar contratos a blockchain
- Borrar archivos o ramas
- Modificar CI/CD pipelines
- Force push
