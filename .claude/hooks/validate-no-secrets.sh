#!/bin/bash
# Hook: PostToolUse (matcher: Write|Edit)
# Bloquea escritura de secrets en código

FILE=$(echo "$CLAUDE_HOOK_INPUT" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(d.get('tool_input',{}).get('file_path',''))
" 2>/dev/null)

[ -z "$FILE" ] && exit 0

# Patrones a detectar
PATTERNS=(
  'sk-[a-zA-Z0-9]{20,}'
  'PRIVATE KEY'
  '0x[a-fA-F0-9]{64}'
  'password\s*=\s*["'"'"'][^"'"'"']+["'"'"']'
  'secret\s*=\s*["'"'"'][^"'"'"']+["'"'"']'
  'Bearer [a-zA-Z0-9._-]{20,}'
  'AKIA[0-9A-Z]{16}'
)

for pattern in "${PATTERNS[@]}"; do
  if grep -qiP "$pattern" "$FILE" 2>/dev/null; then
    echo "BLOQUEADO: Posible secret detectado en $FILE" >&2
    echo "   Patron: $pattern" >&2
    echo "   Usa variables de entorno o un secret manager." >&2
    exit 2
  fi
done

exit 0
