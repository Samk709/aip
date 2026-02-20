#!/usr/bin/env bash
set -euo pipefail

matches=$(rg -n "^(<<<<<<<|=======|>>>>>>>)" . || true)
if [[ -n "$matches" ]]; then
  echo "❌ Merge conflict markers found:"
  echo "$matches"
  exit 1
fi

echo "✅ No merge conflict markers found"
