#!/bin/bash
# Hook: Stop
# Al cerrar sesion, verifica si DECISIONS.md necesita actualizacion

DECISIONS_MODIFIED=$(git diff --name-only HEAD 2>/dev/null | grep "DECISIONS.md")
CODE_MODIFIED=$(git diff --name-only HEAD 2>/dev/null | grep -v "DECISIONS\|FACTORY_STATE\|CLAUDE.md")

if [ -n "$CODE_MODIFIED" ] && [ -z "$DECISIONS_MODIFIED" ]; then
  echo "Codigo modificado pero DECISIONS.md no actualizado."
  echo "   Si tomaste decisiones arquitecturales, documentalas antes de cerrar."
fi

exit 0
