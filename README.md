# Study Materials

A personal knowledge base spanning **cloud & AWS**, **interview preparation**, **resumes**, a
from-scratch **capstone project (Relay)**, and assorted **engineering assignments**. Everything is
Markdown-first and self-contained; the one runnable app (Relay) has its own build.

---

## 📚 Contents

### Cloud & AWS
| Path | What it is |
|------|-----------|
| [`Cloud-Book/`](Cloud-Book/) | A beginner-friendly, book-style course — pain points → intro → building blocks → examples → **free AWS setup** → hands-on labs → glossary (10 chapters) |
| [`Cloud-Computing-Study-Guide.md`](Cloud-Computing-Study-Guide.md) | Concept-first, scenario-driven study guide with 8 real-world architecture case studies |
| [`AWS-IAM-Interview-Prep.md`](AWS-IAM-Interview-Prep.md) | Deep dive on IAM (policy evaluation, roles, boundaries, SCPs, STS, federation) + AWS breadth, for senior interviews |

### Interview Preparation
| Path | What it is |
|------|-----------|
| [`Interview-Preparation/Zscaler/`](Interview-Preparation/Zscaler/) | Company + product deep-dive (Zero Trust, SASE, ZIA/ZPA/ZDX), a technical architecture doc, a reverse-interview guide, and a full **5-round role prep** (Sr Staff SDE, Unified API Platform) incl. reported DSA experiences |

### Resumes
| Path | What it is |
|------|-----------|
| [`Resume/`](Resume/) | Base resume (PDF + editable Markdown) and **JD-tailored variants** in [`Resume/Tailored/`](Resume/Tailored/) named `AkshayPatwari_8years_<company>` — skills kept identical, only relevant fields tuned per JD |

### Capstone Project — Relay
| Path | What it is |
|------|-----------|
| [`Relay-Capstone-Project/`](Relay-Capstone-Project/) | **Relay — an AI Workflow Orchestrator.** A full design (11 docs) *and* a runnable **Java 21 / Spring Boot 3** implementation (Phases 0–10): durable outbox engine, deterministic + AI nodes, exactly-once idempotency, approval gates, retry/backoff, tracing, a web console, and a kill-and-resume demo |

### Engineering Assignments
| Path | What it is |
|------|-----------|
| [`AI-Assignments/`](AI-Assignments/) | LLM file-tools, a Resume-RAG job matcher, and a resume-matching agent (Python) |
| [`DB-and-System-Design/`](DB-and-System-Design/) | A Task Management REST API (Node.js) with schema + tests |

---

## 🚀 Quick starts

- **Learn cloud from zero:** open [`Cloud-Book/README.md`](Cloud-Book/README.md) and read in order.
- **Run the Relay app:** see [`Relay-Capstone-Project/relay/README.md`](Relay-Capstone-Project/relay/README.md)
  — `docker compose up --build`, then the console at `http://localhost:8080/`.
- **See Relay's guarantees proven:** `Relay-Capstone-Project/relay/demo/kill-and-resume.sh`.
- **Tailor a resume to a JD:** copy a file in [`Resume/Tailored/`](Resume/Tailored/) and tune the
  objective + bullet emphasis (never the skills list) — see [`Resume/README.md`](Resume/README.md).

---

## 🗂️ Repository layout

```
study-materials/
├── AWS-IAM-Interview-Prep.md          # AWS/IAM interview deep-dive
├── Cloud-Computing-Study-Guide.md     # concept + scenarios study guide
├── Cloud-Book/                        # beginner cloud course (10 chapters)
├── Interview-Preparation/
│   └── Zscaler/                       # company prep + Sr Staff SDE 5-round loop
├── Resume/
│   ├── Akshay-Patwari-Staff-Engineer.(md|pdf)
│   └── Tailored/                      # per-company tailored resumes (.md + .pdf)
├── Relay-Capstone-Project/            # design docs + Spring Boot app (relay/)
├── AI-Assignments/                    # Python LLM/RAG/agent assignments
└── DB-and-System-Design/              # Node.js task-management API
```

---

## 🛠️ Tech across the repo

Markdown docs · **Java 21 / Spring Boot 3 / PostgreSQL** (Relay) · Python (AI assignments) ·
Node.js (task API) · Docker + GitHub Actions (Relay CI).
