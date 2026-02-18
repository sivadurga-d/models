#!/usr/bin/env bash
# Make a minimal dummy change to every pricing/*.json so a PR will trigger
# the sync-pricing-to-general workflow and you can verify missing models.
# Change: ensure each file ends with exactly one newline (normalize trailing newline).

set -e
cd "$(dirname "$0")/.."
PRICING_DIR="${PRICING_DIR:-pricing}"

count=0
for f in "$PRICING_DIR"/*.json; do
  [ -f "$f" ] || continue
  content=$(cat "$f")
  # Ensure exactly one trailing newline
  normalized=$(printf '%s\n' "$content" | sed -e :a -e '/^\n*$/{$d;N;ba' -e '}')
  # Remove all trailing newlines then add one
  trimmed=${content%%$'\n'}
  while [[ "$trimmed" != "$content" ]]; do content="$trimmed"; trimmed=${content%%$'\n'}; done
  printf '%s\n' "$content" > "$f"
  count=$((count + 1))
done

echo "Touched $count pricing file(s). Run: git diff pricing/"