#!/usr/bin/env bash
# PreToolUse hook (Bash matcher): blocks commands that delete protected files.
set -euo pipefail

input=$(cat)
command=$(jq -r '.tool_input.command // empty' <<<"$input")

[[ -z "$command" ]] && exit 0

# Delete-like commands only — grep/cat/echo of these files is fine.
if ! grep -qE '\b(rm|unlink|shred|rmdir)\b|git[[:space:]]+rm\b' <<<"$command"; then
  exit 0
fi

declare -A protected=(
  ["expense_tracker\.db"]="expense_tracker.db"
  ["(^|[/[:space:]])\.env([/[:space:]]|$)"]=".env"
  ["\.gitignore"]=".gitignore"
)

for pattern in "${!protected[@]}"; do
  if grep -qE "$pattern" <<<"$command"; then
    name="${protected[$pattern]}"
    jq -nc --arg reason "Blocked: \"$command\" attempts to delete $name, a protected file. This file can't be deleted." '{
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        permissionDecision: "deny",
        permissionDecisionReason: $reason
      }
    }'
    exit 0
  fi
done

exit 0
