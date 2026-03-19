#!/bin/bash
# Hook: TaskCompleted
# Loguea completion y actualiza estado

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
TASK_ID=$(echo "$CLAUDE_HOOK_INPUT" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(d.get('task_id','unknown'))
" 2>/dev/null)

STATE_FILE="FACTORY_STATE.md"
[ ! -f "$STATE_FILE" ] && printf "# Factory State\n" > "$STATE_FILE"

echo "- [$TIMESTAMP] Task completada: $TASK_ID" >> "$STATE_FILE"
exit 0
