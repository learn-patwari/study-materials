#!/usr/bin/env bash
# Captures real CLI transcripts used to build the demo video.
# Run from anywhere; paths are resolved relative to this script.
set -euo pipefail
DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$DEMO_DIR")"
OUT="$DEMO_DIR/_captured"
mkdir -p "$OUT"

cd "$ROOT"
if [ -f .venv/bin/activate ]; then source .venv/bin/activate; fi

printf '%s\n' \
  "find candidates with React and 3+ years experience" \
  "compare top 3" \
  "why did C001 rank higher than C002" \
  "require Next.js and 5+ years" \
  "screen" \
  "quit" | python cli.py > "$OUT/full_session.txt" 2>&1

python tests/test_scenarios.py > "$OUT/tests.txt" 2>&1

echo "Captured -> $OUT/full_session.txt, $OUT/tests.txt"
