<!--
CHAPTER TEMPLATE — Senior Java Handbook
========================================
Copy this file to Part-XX-.../chapters/XX-NN-kebab-title.md and fill every
section. Do not delete, rename, or reorder sections — the build pipeline and
readers both rely on the 20-section order being identical across chapters.
If a section is genuinely inapplicable to a topic, keep the header and write
one line: "N/A — because <reason>." Never delete it silently.

Target length: 1,500-3,000 lines for a flagship/complete chapter. Stub
placeholders (not yet written) do not use this file at all — they're just a
row in the Part's README.md and SUMMARY.md until someone writes them.

Naming: XX-NN-kebab-title.md, where XX = zero-padded Part number (matches
the folder, e.g. 02 for Part-02-Core-Java) and NN = chapter number within
that part. This keeps a stable sort order without extra front-matter.
-->

# Chapter XX.NN — <Title>

> <One-paragraph hook: a concrete scenario or question that shows why a
> Staff Engineer / Solution Architect candidate is expected to know this
> cold — not a generic "in this chapter we will learn about X.">

**Part:** <Part name> · **Level:** Beginner / Intermediate / Advanced / Production
**Estimated study time:** <N> hours · **Status:** ✅ Complete

---

## Learning Objectives

<!--
5-8 bullets, each starting with a testable action verb (Explain / Diagnose /
Implement / Compare / Tune / Design). Avoid "Understand X" — say what the
reader will be able to DO.
-->

## Prerequisites

<!--
A small table: | Concept | Where it's covered | Required? |
Link to other chapters where possible (even if they're still 📝 planned —
note that explicitly so the cross-reference isn't silently broken).
-->

## Introduction

<!--
Motivating real-world scenario. Frame the business/engineering problem
before any theory. This is where you justify "why does a staff engineer
get asked this in an interview AND need it in production."
-->

## Theory

<!--
First-principles / formal model. Define terminology precisely. This section
answers "what is the mental model," not yet "how does the JVM/framework
actually implement it."
-->

## Internal Working

<!--
How the runtime/framework/system actually does this under the hood —
bytecode, algorithms, data structures, wire protocol, whatever is the
actual mechanism. This is the "why it works" section, the most commonly
shallow section in AI-generated material — go deep here.
-->

## Architecture

<!--
Component/deployment-level view of how this fits into a real system.
Prose description backing the diagrams below.
-->

## Sequence Diagrams (Mermaid)

<!--
At least one ```mermaid sequenceDiagram``` block showing a real
request/operation flow through the components described above.
-->

## Flow Charts (Mermaid)

<!--
At least one ```mermaid flowchart``` block showing a decision/algorithm
flow (e.g. a tuning decision tree, a troubleshooting decision flow).
-->

## Class Diagrams (Mermaid)

<!--
At least one ```mermaid classDiagram``` block showing the key
types/interfaces/relationships relevant to this chapter.
-->

## Production Examples

<!--
A real (or realistic, clearly-labeled-as-illustrative) production
scenario: a config snippet, a metrics dashboard excerpt, an incident
timeline. Grounds the chapter in practice, not just theory.
-->

## Code Examples

<!--
Java 21 + Spring Boot 3.x + Maven unless the chapter topic is explicitly
Kubernetes YAML / Helm / Bash / SQL, in which case use that instead. Must
actually compile/run — back it with a code-samples/<slug>/ Maven module
where applicable, and say so here with a relative link.
-->

## Best Practices

<!-- A Do / Don't table, each row justified with the WHY, not just the WHAT. -->

## Common Mistakes

<!-- | Mistake | Why it happens | How to fix it | -->

## Performance Considerations

<!-- Complexity, benchmarks, latency/throughput/memory trade-offs, with numbers where credible. -->

## Security Considerations

<!-- OWASP-relevant risks for this topic, and concrete hardening steps. -->

## Production Troubleshooting

<!--
A runbook table: | Symptom | Root Cause | Diagnosis Commands | Fix |
This is the section interviewers probe hardest for staff-level candidates —
don't skimp here.
-->

## Interview Questions

<!--
8-15 questions, mixing conceptual, scenario-based, and "explain like you're
debugging this at 3am" framings. Include model answers, not just the
question — a question bank without answers isn't a study aid.
-->

## Hands-on Exercises

### Lab 1 (Beginner)
<!-- Goal / Setup / Task / Verification -->

### Lab 2 (Intermediate)
<!-- Goal / Setup / Task / Verification -->

### Lab 3 (Advanced)
<!-- Goal / Setup / Task / Verification -->

### Lab 4 (Production)
<!-- Goal / Setup / Task / Verification — should resemble an actual on-call scenario. -->

## Summary

<!-- 5-8 bullets recapping the chapter — should be useful as flash-card material. -->

## Further Reading

<!-- Books / RFCs / official docs / talks, each with one line on why it's worth the reader's time. -->

---

### Chapter checklist (for the author, not the reader — delete this section once verified)

- [ ] All 20 sections present, in this exact order
- [ ] Every Mermaid block renders cleanly through `build/render_diagrams.sh` (no mmdc errors)
- [ ] Every Java/Maven code sample compiles: `mvn -q -f code-samples/<slug>/pom.xml compile`
- [ ] All 4 labs present and independently completable
- [ ] Every cross-reference in Prerequisites/Further Reading resolves to a real file or is explicitly marked as a future chapter
