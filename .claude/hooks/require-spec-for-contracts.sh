#!/bin/bash
# Hook: PreToolUse (matcher: Write)
# Bloquea escritura de .sol sin spec aprobada

FILE=$(echo "$CLAUDE_HOOK_INPUT" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(d.get('tool_input',{}).get('file_path',''))
" 2>/dev/null)

[[ "$FILE" != *.sol ]] && exit 0

# Buscar spec para este archivo
BASENAME=$(basename "$FILE" .sol)
SPEC_DIR=".claude/specs"

if ! ls "$SPEC_DIR"/TASK-*.md 2>/dev/null | xargs grep -l "$BASENAME" &>/dev/null; then
  echo "BLOQUEADO: No hay spec aprobada para el contrato $BASENAME" >&2
  echo "   Crear spec en .claude/specs/TASK-N.md antes de implementar." >&2
  exit 2
fi

exit 0
