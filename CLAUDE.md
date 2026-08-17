# Claude Code — Project Instructions

## Resume Workflow

- All tailored resumes (`.md` and `.pdf`) must always be committed to this repository.
- Output path: `Resume/Tailored/AkshayPatwari_8years_SLUG.md` and `.pdf`
- Never leave resumes only in scratchpad or `/tmp` — always commit and push after generating.
- PDF builder: `python Resume/build_pdf.py <SLUG>` — matches base resume design exactly.
- The base resume lives at `Resume/Akshay-Patwari-Staff-Engineer.md` — always read it fresh before tailoring.
- Development branch: `claude/apply-for-me-repo-s0jfes`

## PDF Builder Rules

- PDF script lives at scratchpad; use the Volvo/Apple scripts as the canonical template.
- **Critical fix**: Always join continuation lines before rendering. Markdown wraps long bullets
  across multiple indented lines — if each line is rendered as a separate paragraph, text appears
  short with a large gap on the right. Detect continuation lines with `line.startswith("  ") and stripped`,
  and append them to the current buffer (`buf_text`) instead of flushing as a new paragraph.
- Buffer types: `obj` (Objective), `bullet` (list item), `body` (plain text), `subhead` (bold subtitle), `italic` (date line).
- Flush the buffer only on: section headings (`##`), company headings (`###`), `---` dividers, blank lines, or when the block type changes.
- Cover letter PDFs: split markdown on blank lines into logical blocks first, then render each block as one `Paragraph` — never line-by-line.

## Cover Letter Rules

- Email: always `akshaypatwariap@gmail.com` (not `javaclaude1@gmail.com`)
- No date at the top.
- Add a blank line between "Warm regards," and the name.
- 3-4 paragraphs; end with "Resume attached. Warm regards,"
