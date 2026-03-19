---
name: context-refresh
description: Reconstruir FACTORY_STATE.md desde el estado actual del repo. /context-refresh
disable-model-invocation: true
---
Reconstruir FACTORY_STATE.md con:
1. Branch actual y último commit
2. Archivos modificados vs. main/master
3. Specs en .claude/specs/ y su estado
4. Tareas completadas (desde log del hook TaskCompleted)
5. Stacks activos (desde .claude/factory/stack.json)
