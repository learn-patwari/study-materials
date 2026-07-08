# Build pipeline

Turns the Markdown chapters into a single PDF, with Mermaid diagrams
rendered as real images (pandoc has no native Mermaid support).

```bash
# One-time setup
sudo apt-get install -y pandoc weasyprint poppler-utils

# 1. Render every ```mermaid block in every chapter to PNG
bash build/render_diagrams.sh

# 2. Assemble the diagram-substituted chapters into one PDF
bash build/build_pdf.sh
# -> build/output/Senior-Java-Handbook.pdf
```

## How it works

- **`render_diagrams.sh`** reads the chapter file list straight out of
  `../SUMMARY.md` (in link order — that file is the authoritative build
  order), and for each one runs `mermaid-cli` (`mmdc`) in its built-in
  whole-Markdown-transform mode: it finds every ` ```mermaid ` fenced block,
  renders each to a **PNG** next to the output file, and rewrites the copy
  to reference the image instead of the raw fence. Chapters with no
  diagrams are just copied through unchanged. Output lands in
  `build/rendered/` (gitignored — it's a derived artifact).
- **PNG, not SVG**: Mermaid flowchart/class diagrams render node labels via
  an SVG `<foreignObject>`, which weasyprint's SVG rasterizer (CairoSVG)
  does not support — that content silently disappears (confirmed by a
  smoke test: a sequence diagram, which uses plain `<text>`, rendered fine
  as SVG; a flowchart with the same SVG path lost every node label).
  Rendering through the real browser to PNG (`-e png`) sidesteps the
  problem entirely, since weasyprint just embeds the raster image with no
  SVG parsing involved. Don't switch this back to `-e svg` without
  re-verifying flowchart/class diagrams specifically.
- **Chromium for mmdc**: mermaid-cli's own Chromium download can be blocked
  by a sandboxed environment's egress policy (confirmed in this repo's dev
  environment: its default `storage.googleapis.com` fetch returns 403). The
  script instead looks for an already-installed Chromium — first
  `$PLAYWRIGHT_CHROMIUM_PATH`, then anything under
  `$PLAYWRIGHT_BROWSERS_PATH`, then `google-chrome`/`chromium` on `$PATH` —
  and points mmdc at it via a generated `puppeteer-config.generated.json`
  plus `PUPPETEER_SKIP_DOWNLOAD=true`. If none of those exist, install
  Chromium (`npx playwright install chromium` or your distro's package) and
  either add it to `$PATH` or set `PLAYWRIGHT_CHROMIUM_PATH`.
- **`build_pdf.sh`** resolves the same chapter list, assembles the
  `build/rendered/` copies with pandoc using `weasyprint` as the PDF engine
  (HTML→PDF via CSS paged media — see `pandoc.css` for the print
  stylesheet), and writes `build/output/Senior-Java-Handbook.pdf`
  (gitignored).
- **Image path resolution across chapters in different directories**: each
  chapter's rendered PNGs sit next to its own `.md` file (e.g.
  `Part-02-.../chapters/02-04-...-1.png`, referenced as `./02-04-...-1.png`).
  When pandoc hands the assembled HTML to an external `--pdf-engine`, that
  engine resolves relative image paths against its own working directory
  (wherever `build_pdf.sh` itself was invoked from), not against each
  source file's directory — `--resource-path` does **not** fix this for
  the pdf-engine handoff (only for pandoc's own internal AST building).
  With 20 chapters spread across many directories, this silently broke
  every diagram image the first time this pipeline ran against real
  (non-stub) content. The fix: `build_pdf.sh` stages a rewritten copy of
  every chapter under `build/.pdf-staging/` (gitignored) with each
  `](./foo.png)` rewritten to an absolute path before handing the files to
  pandoc, so image resolution no longer depends on invocation directory.
- **weasyprint / python version note**: on Debian/Ubuntu, the apt
  `weasyprint` package can end up depending on native extensions built for
  a different `python3` than `/usr/bin/python3` resolves to if multiple
  Python versions are installed (seen in this repo's dev environment:
  `python3` → 3.11, but weasyprint's compiled `_cffi_backend` was only
  installed for 3.12 — running plain `weasyprint --version` fails with
  `ModuleNotFoundError: No module named '_cffi_backend'`, while
  `python3.12 -m weasyprint --version` works). Pandoc validates
  `--pdf-engine` against a fixed allowlist of binary *names*
  (`weasyprint`, `wkhtmltopdf`, `prince`, ...) and rejects an arbitrary
  interpreter invocation like `python3.12 -m weasyprint` outright. The fix
  `build_pdf.sh` uses: generate a tiny wrapper script literally named
  `weasyprint` (`.weasyprint-wrapper/weasyprint`, gitignored) that execs
  whichever interpreter actually has a working weasyprint, and pass
  pandoc `--pdf-engine=<absolute path to that wrapper>` — pandoc accepts
  any path whose basename matches an allowed engine name. If you hit the
  `_cffi_backend` error yourself, run `python3.12 -m weasyprint --version`
  (or whichever version matches your `python3-cffi-backend` package) to
  find the working interpreter.

## Why weasyprint over LaTeX

Pandoc's default PDF engine needs a full TeX installation
(`texlive-xetex` pulls in ~135 packages on this environment vs.
weasyprint's ~46). weasyprint (HTML+CSS → PDF) produces perfectly good
paginated output for a technical handbook — headings, tables, code blocks,
page breaks per chapter (`h1 { page-break-before: always }` in
`pandoc.css`) — without the LaTeX toolchain weight.

## Verifying a build actually worked

Don't trust "the scripts exited 0" — check the real output:

```bash
pdfinfo build/output/Senior-Java-Handbook.pdf | grep Pages
pdftotext build/output/Senior-Java-Handbook.pdf - | grep -c '```mermaid'   # expect 0 (grep exits 1 on no match) — a match means a diagram leaked through unrendered
pdftoppm -png -r 100 -f 1 -l 1 build/output/Senior-Java-Handbook.pdf /tmp/handbook_page  # then view /tmp/handbook_page-1.png to eyeball a rendered diagram
```

(`pdfinfo`/`pdftotext`/`pdftoppm` are from `poppler-utils`. Avoid `pypdf` for
this check unless you've confirmed it against the same python3 version that
actually has its native deps — see the weasyprint note above; the same
cross-version trap bit a `pip install pypdf` attempt in this repo's dev
environment.)
