#!/usr/bin/env bash
# Assembles all diagram-rendered chapters (build/rendered/, produced by
# render_diagrams.sh) into a single PDF via pandoc + weasyprint, in
# SUMMARY.md's link order.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
RENDERED="$HERE/rendered"
OUT_DIR="$HERE/output"
OUT_PDF="$OUT_DIR/Senior-Java-Handbook.pdf"

mkdir -p "$OUT_DIR"

if [ ! -d "$RENDERED" ]; then
  echo "ERROR: $RENDERED does not exist — run render_diagrams.sh first." >&2
  exit 1
fi

# Resolve a working weasyprint. pandoc validates --pdf-engine against a
# fixed allowlist of binary *names* (wkhtmltopdf, weasyprint, prince, ...) --
# it will reject "python3.12" outright even though that's what actually
# works here. See build/README.md: apt's weasyprint can end up depending on
# native extensions built for a different python3 than /usr/bin/python3
# resolves to (confirmed: python3 -> 3.11, but weasyprint's _cffi_backend
# was only installed for 3.12). Fix: generate a tiny wrapper script literally
# named "weasyprint" that execs the interpreter that actually has it, and
# point pandoc at that (pandoc accepts any path whose basename matches an
# allowed engine name).
WRAPPER_DIR="$HERE/.weasyprint-wrapper"
mkdir -p "$WRAPPER_DIR"
WRAPPER="$WRAPPER_DIR/weasyprint"
if python3.12 -c "import weasyprint" >/dev/null 2>&1; then
  printf '#!/bin/sh\nexec python3.12 -m weasyprint "$@"\n' > "$WRAPPER"
elif python3 -c "import weasyprint" >/dev/null 2>&1; then
  printf '#!/bin/sh\nexec python3 -m weasyprint "$@"\n' > "$WRAPPER"
elif command -v weasyprint >/dev/null 2>&1; then
  printf '#!/bin/sh\nexec %s "$@"\n' "$(command -v weasyprint)" > "$WRAPPER"
else
  echo "ERROR: no working weasyprint found (tried python3.12/python3 -m weasyprint and \$PATH)." >&2
  exit 1
fi
chmod +x "$WRAPPER"
PANDOC_PDF_ENGINE_OPTS=(--pdf-engine="$WRAPPER")

mapfile -t CHAPTER_FILES < <(
  grep -oE '\]\(\./[A-Za-z0-9_./-]+\.md\)' "$ROOT/SUMMARY.md" \
    | sed -E 's/^\]\((.*)\)$/\1/' \
    | sort -u
)

# Each chapter's Mermaid diagrams are rendered as PNGs sitting NEXT TO that
# chapter's .md file (e.g. Part-02-.../chapters/02-04-...-1.png), referenced
# from the Markdown with a relative path like `./02-04-...-1.png`. When
# pandoc hands off to an external --pdf-engine (weasyprint here), the
# intermediate HTML's relative image paths get resolved against the
# ENGINE's working directory (effectively wherever this script itself was
# invoked from), not against each source .md file's own directory --
# --resource-path does not fix this for the pdf-engine handoff, only for
# pandoc's own internal AST-building. With chapters spread across many
# different directories, that silently breaks every diagram image unless
# each file's image references are rewritten to absolute paths first.
STAGING="$HERE/.pdf-staging"
rm -rf "$STAGING"
mkdir -p "$STAGING"

FILES=()
for rel in "${CHAPTER_FILES[@]}"; do
  f="$RENDERED/$rel"
  if [ -f "$f" ]; then
    dir="$(dirname "$f")"
    # Preserve the relative path under STAGING (not just the basename --
    # many stub chapters are literally all named README.md, so flattening
    # to basename alone would silently collide and overwrite them).
    staged="$STAGING/$rel"
    mkdir -p "$(dirname "$staged")"
    # Rewrite `](./whatever.png)` -> `](<absolute-dir>/whatever.png)` so the
    # image resolves correctly regardless of the pdf-engine's own cwd.
    sed -E "s|\]\(\./([A-Za-z0-9_.-]+\.png)\)|](${dir}/\1)|g" "$f" > "$staged"
    FILES+=("$staged")
  fi
done
echo "Assembling ${#FILES[@]} rendered chapter files into $OUT_PDF"

pandoc \
  --metadata title="Senior Java Handbook" \
  --metadata subtitle="Java Backend, Kubernetes & AI Platform Engineering" \
  --toc --toc-depth=2 \
  --css "$HERE/pandoc.css" \
  "${PANDOC_PDF_ENGINE_OPTS[@]}" \
  -o "$OUT_PDF" \
  "${FILES[@]}"

echo "Wrote $OUT_PDF"
