# Senior Java Backend, Kubernetes & AI Platform Engineering Handbook

A reference manual for 7+ year Java backend engineers preparing for
Senior/Staff Engineer and Solution Architect roles — Core Java through the
JVM, Spring, databases, microservices, Docker/Kubernetes, security,
observability, AI platform engineering, AWS, system design, and interview
preparation, in one consistently-structured book.

This repository holds the **full roadmap scaffold** plus **7 chapters
written at complete production depth** — proof of the bar every future
chapter is held to, not a placeholder.

---

## Highlights

- **7 complete chapters**, each with all 20 mandatory sections
  (Learning Objectives → Further Reading), real Mermaid diagrams rendered
  and verified through the actual build pipeline, and a backing Maven
  module of **compiling, passing Java 21 code** — not illustrative
  pseudocode:
  - [Chapter 01.01 — Computer Architecture & How Code Becomes Execution](./Part-01-Programming-Fundamentals/chapters/01-01-computer-architecture-execution.md)
  - [Chapter 01.04 — OOP Principles & SOLID in Practice](./Part-01-Programming-Fundamentals/chapters/01-04-oop-solid-principles.md)
  - [Chapter 01.06 — Complexity Analysis & Algorithmic Trade-offs](./Part-01-Programming-Fundamentals/chapters/01-06-complexity-analysis-tradeoffs.md)
  - [Chapter 02.04 — JVM Internals: Memory Management, Garbage Collection & Performance Tuning](./Part-02-Core-Java/chapters/02-04-jvm-internals-memory-gc.md)
  - [Chapter 07.02 — Kubernetes Workloads, Resource Management & Production Deployment Patterns](./Part-07-Kubernetes/chapters/07-02-workloads-resource-mgmt-deployment.md)
  - [Chapter 12.01 — System Design Case Study: Designing a Scalable URL Shortener](./Part-12-System-Design/chapters/12-01-case-study-url-shortener.md)
  - [Chapter 17.01 — Staff/Principal Engineer Interview Playbook](./Part-17-Interview/chapters/17-01-staff-engineer-interview-playbook.md)
- **A working Mermaid → PDF pipeline**, built and verified against this
  repository's real content (not a synthetic smoke test): every diagram
  rendered as an image with zero leaked raw Mermaid syntax, visually
  spot-checked against the rendered PDF pages.
- **Full 19-Part + Appendices roadmap** scaffolded in [`SUMMARY.md`](./SUMMARY.md)
  with representative chapter titles for every unwritten part — this is
  the authoritative build order and completion tracker for future
  sessions.
- **A reusable [`CHAPTER-TEMPLATE.md`](./CHAPTER-TEMPLATE.md)** encoding the
  20-section structure every chapter must follow, so future chapters stay
  consistent with the 7 already written.

## Quick start

**Read a chapter** — every chapter is plain Markdown with GitHub-renderable
Mermaid diagrams; start with any of the 7 links above.

**Build the PDF** (requires `pandoc`, `weasyprint`, and Node/`npx` for
`@mermaid-js/mermaid-cli`; see [`build/README.md`](./build/README.md) for
the full toolchain explanation, including two nonobvious fixes this
pipeline needed — a Chromium-download workaround and a `weasyprint`
wrapper script pandoc's engine-name allowlist requires):

```bash
cd Interview-Handbook/Senior-Java-Handbook
bash build/render_diagrams.sh   # renders every Mermaid block to PNG per SUMMARY.md order
bash build/build_pdf.sh         # assembles build/output/Senior-Java-Handbook.pdf
```

**Compile and test a chapter's code sample:**

```bash
cd Part-01-Programming-Fundamentals/code-samples/cache-and-execution && mvn -q test  # 6 tests
cd Part-01-Programming-Fundamentals/code-samples/solid-principles    && mvn -q test  # 7 tests
cd Part-01-Programming-Fundamentals/code-samples/complexity-tradeoffs && mvn -q test # 10 tests
cd Part-02-Core-Java/code-samples/jvm-internals   && mvn -q test   # 3 tests
cd Part-07-Kubernetes/code-samples/workload-patterns && ./validate.sh  # 4 manifests
cd Part-12-System-Design/code-samples/url-shortener && mvn -q test  # 24 tests
cd Part-17-Interview/code-samples/coding-drills    && mvn -q test   # 12 tests
```

## Project layout

```
Senior-Java-Handbook/
├── README.md                 # this file
├── SUMMARY.md                 # ★ authoritative roadmap + PDF build order
├── CHAPTER-TEMPLATE.md         # the 20-section skeleton every chapter follows
├── build/                      # Mermaid -> PDF pipeline (see build/README.md)
├── Part-01-Programming-Fundamentals/
│   ├── chapters/01-01-computer-architecture-execution.md   ✅
│   ├── chapters/01-04-oop-solid-principles.md               ✅
│   ├── chapters/01-06-complexity-analysis-tradeoffs.md      ✅
│   └── code-samples/cache-and-execution/, solid-principles/, complexity-tradeoffs/  (Maven, JUnit 5)
├── Part-02-Core-Java/
│   ├── chapters/02-04-jvm-internals-memory-gc.md          ✅
│   └── code-samples/jvm-internals/                         (Maven, JUnit 5)
├── Part-07-Kubernetes/
│   ├── chapters/07-02-workloads-resource-mgmt-deployment.md ✅
│   └── code-samples/workload-patterns/                      (K8s YAML)
├── Part-12-System-Design/
│   ├── chapters/12-01-case-study-url-shortener.md          ✅
│   └── code-samples/url-shortener/                          (Spring Boot 3.2)
├── Part-17-Interview/
│   ├── chapters/17-01-staff-engineer-interview-playbook.md ✅
│   └── code-samples/coding-drills/                          (Maven, JUnit 5)
└── Part-03-06, 08-11, 13-16, 18-19, Appendices/             (roadmap stubs, 📝)
```

## Completion status

103 chapters/case-studies/guides are scoped across 19 Parts + Appendices; 7
are written at full production depth. See [`SUMMARY.md`](./SUMMARY.md) for
the authoritative, part-by-part breakdown — it is kept in sync with this
repository's actual content and is what the PDF build pipeline parses for
chapter order.

## Design notes

**Why a handful of complete chapters, not partial coverage of many.** A
2,500+ page, 19-part handbook is a multi-week authoring project. Writing
chapters at genuine full depth (all 20 sections, real diagrams, compiling
code, 4 labs) in small, deliberately-scoped batches — and scaffolding the
rest as an honest, explicit roadmap — is a deliberate trade-off against
silently producing 100 chapters of shallow, under-verified content — the
scaffold-first approach this repository follows throughout. Each batch is
its own small planning round (see git history for the specific chapters
each round added), not one all-at-once push.

**Why a fixed 20-section chapter template.** Consistency across a
book this size is what makes it usable as a reference rather than a
loose pile of notes — every chapter answers the same questions in the
same order (theory → internals → production examples → troubleshooting →
interview prep), so a reader builds a stable mental map of where to look
for anything.

**Why weasyprint, not wkhtmltopdf or texlive-xetex.** All three integrate
with pandoc's `--pdf-engine`; weasyprint required the fewest new apt
packages (46, vs. 82 for wkhtmltopdf and 135 for texlive-xetex) for
equivalent output quality on this content.

**Why PNG diagrams, not SVG.** Mermaid flowchart/class diagrams use
`<foreignObject>` for node labels, which weasyprint's SVG rasterizer
(CairoSVG) silently fails to render — labels disappeared entirely in an
early test. Switching mermaid-cli's export format to PNG rasterizes
diagrams through a real headless Chromium first, which handles
`foreignObject` correctly, before weasyprint ever touches an SVG.

**Why these 7 chapters specifically.** JVM Internals anchors Core Java
with the material Staff loops probe hardest (memory/GC troubleshooting);
Kubernetes Workloads covers the production-deployment patterns every
backend engineer at this level is expected to own; the URL Shortener case
study is the most tractable of the 10 planned system-design case studies
to execute at full depth in one pass, while still exercising the complete
6-step design framework; the Interview Playbook ties those three together
into the book's actual purpose — passing the loop, not just knowing the
material. The 3 Part-01 chapters (Computer Architecture, OOP/SOLID,
Complexity Analysis) were added in a second round to start the book's
actual reading-order foundation, each anchored in real, measured
benchmark numbers (not textbook estimates) run directly in this
repository's own environment.

## Submission checklist

- [x] Full 19-Part + Appendices folder scaffold with root docs (README,
      SUMMARY, CHAPTER-TEMPLATE)
- [x] 7 chapters written, each with all 20 required sections in order
- [x] Every written chapter's Mermaid diagrams render cleanly through
      `build/render_diagrams.sh` (verified, not assumed)
- [x] Every written chapter's code sample compiles and its tests pass
      (`mvn test` / `./validate.sh`, run and confirmed for all 7)
- [x] Full PDF pipeline built and verified against real content:
      diagrams visually confirmed rendering correctly, zero leaked raw
      Mermaid syntax
- [x] `SUMMARY.md` accurately reflects real completion status and doubles
      as the PDF build's chapter order
- [ ] Remaining ~96 chapters, 9 system-design case studies, and 10 project
      guides — explicitly deferred to future sessions (see `SUMMARY.md`)
