#!/usr/bin/env bash
# Renders every ```mermaid fenced block in every chapter (in SUMMARY.md's
# link order) to SVG via mermaid-cli, writing the diagram-substituted copy
# to build/rendered/. Run before build_pdf.sh.
#
# Portability: mermaid-cli's own Chromium download can be blocked by
# sandboxed egress policies. This script reuses an already-installed
# Chromium (Playwright's, if present) instead of relying on mmdc's default
# postinstall download.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
RENDERED="$HERE/rendered"
PUPPETEER_CFG="$HERE/puppeteer-config.generated.json"

mkdir -p "$RENDERED"

# --- Resolve a usable Chromium binary (portable across environments) -------
CHROME_BIN="${PLAYWRIGHT_CHROMIUM_PATH:-}"
if [ -z "$CHROME_BIN" ] && [ -n "${PLAYWRIGHT_BROWSERS_PATH:-}" ] && [ -d "$PLAYWRIGHT_BROWSERS_PATH" ]; then
  CHROME_BIN="$(find "$PLAYWRIGHT_BROWSERS_PATH" -maxdepth 3 -type f -name chrome 2>/dev/null | head -1)"
fi
if [ -z "$CHROME_BIN" ]; then
  CHROME_BIN="$(command -v google-chrome || command -v chromium || command -v chromium-browser || true)"
fi
if [ -z "$CHROME_BIN" ] || [ ! -x "$CHROME_BIN" ]; then
  echo "ERROR: no usable Chromium binary found. Set PLAYWRIGHT_CHROMIUM_PATH or install Chromium." >&2
  exit 1
fi
echo "Using Chromium: $CHROME_BIN"

cat > "$PUPPETEER_CFG" <<EOF
{
  "executablePath": "$CHROME_BIN",
  "args": ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
}
EOF

# --- Build the ordered chapter file list from SUMMARY.md -------------------
# Extract markdown links of the form [Title](./Part-XX/.../file.md) or
# (./Part-XX/.../README.md), in file order.
mapfile -t CHAPTER_FILES < <(
  grep -oE '\]\(\./[A-Za-z0-9_./-]+\.md\)' "$ROOT/SUMMARY.md" \
    | sed -E 's/^\]\((.*)\)$/\1/' \
    | sort -u
)
echo "Found ${#CHAPTER_FILES[@]} referenced files in SUMMARY.md"

render_one() {
  local rel="$1"
  local src="$ROOT/$rel"
  local dst="$RENDERED/$rel"
  mkdir -p "$(dirname "$dst")"
  if [ ! -f "$src" ]; then
    echo "  SKIP (missing): $rel"
    return
  fi
  if ! grep -q '```mermaid' "$src" 2>/dev/null; then
    cp "$src" "$dst"
    echo "  copy (no diagrams): $rel"
    return
  fi
  echo "  render: $rel"
  # PNG, not SVG: Mermaid flowchart/class diagrams render node labels via
  # SVG <foreignObject>, which weasyprint's SVG rasterizer (CairoSVG) does
  # not support -- that content silently disappears in the PDF. Rendering
  # through the real browser to PNG sidesteps the issue entirely (confirmed
  # via a smoke test: the SVG path dropped flowchart labels, PNG did not).
  # Default scale (no -s/--scale): -s 2 was observed to trigger a puppeteer
  # CDP screenshot protocol error against this Chromium build.
  PUPPETEER_SKIP_DOWNLOAD=true npx --yes @mermaid-js/mermaid-cli@11.16.0 \
    -i "$src" -o "$dst" \
    --puppeteerConfigFile "$PUPPETEER_CFG" \
    -e png -b white >/tmp/mmdc.log 2>&1 \
    || { echo "  FAILED to render $rel — see /tmp/mmdc.log"; tail -20 /tmp/mmdc.log; return 1; }
}

for rel in "${CHAPTER_FILES[@]}"; do
  render_one "$rel"
done

# Also copy root docs (README/SUMMARY are not chapters but nice to have if
# ever included in the PDF; harmless to skip otherwise).
echo "Diagram rendering complete -> $RENDERED"
