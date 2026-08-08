# Relay Demo — Verbal Script

> Read this aloud while running `record-demo.ps1` on screen.
> Each section is timed to match a step in the script.
> Pause naturally at `[PAUSE]` markers.

---

## Opening (before running the script)

"Hi, I'm going to walk you through Relay — an AI workflow orchestrator
I built as a capstone project.

Relay lets you define multi-step workflows that mix regular logic —
HTTP calls, conditions, delays — with AI steps powered by an LLM.
What makes it production-grade is that it guarantees correctness:
runs survive crashes, side effects never fire twice, and humans can
approve sensitive actions before they execute.

Let me show you how it works."

[PAUSE — start the script now]

---

## Step 1 — Create & Publish a Workflow

"First, let's create a workflow called 'order-pipeline'.

[PAUSE — watch workflow creation]

A workflow is just a JSON definition — a graph of nodes. This one has
four nodes: a condition that checks the order amount, an HTTP charge
node marked as sensitive, and two notify nodes for success and rejection.

[PAUSE — watch definition save]

I'm publishing version 1. Publishing freezes this definition — it
can never change mid-run. That's intentional: you can edit drafts,
but a running workflow always executes the exact version it started with."

[PAUSE — watch publish]

---

## Step 2 — Trigger Runs

"Now let's trigger some runs.

Run number one has an amount of 500 — that's above the threshold,
so it will pass the condition and hit the charge node.
But charge is marked sensitive, so Relay will pause and wait
for a human to approve it before doing anything.

[PAUSE — watch run #1 status: WAITING_APPROVAL]

Run number two has an amount of 50 — below the threshold.
The condition routes it straight to the reject node.
No approval needed, it completes immediately.

[PAUSE — watch run #2 status: SUCCEEDED]"

---

## Step 3 — Execution Trace

"Every run produces a full trace — every node that executed,
when it ran, what the inputs and outputs were.

Here's the trace for run number two. You can see the condition
evaluated, branched to reject, and the notify fired.
This is how you debug a workflow — no guessing, full history."

[PAUSE — watch trace print]

---

## Step 4 — Human Approval Gate

"Back to run number one. It's been sitting at WAITING_APPROVAL
because the charge node is sensitive.

[PAUSE — watch pending approvals list]

In a real system a human would review this in the console UI.
I'm approving it now via API — but you can also do it with
one click in the web console.

[PAUSE — watch approve call]

Watch what happens — Relay resumes exactly where it left off.
The charge fires, the notify sends, the run completes.

[PAUSE — watch status: SUCCEEDED]

That's the approval gate. A run can sit paused for hours or days —
it doesn't matter. When approved, it picks up from the exact node
it was waiting at."

---

## Step 5 — Exactly-Once Side Effects

"Here's something subtle but critical.

What if the worker crashed right after calling the charge API,
but before recording that it did? Without protection, the next
worker would charge the customer twice.

Relay prevents this with an idempotency ledger — a database table
with a unique key per run, per node, per attempt. The first worker
wins the insert and performs the effect. Any retry finds the existing
row and replays the stored result instead of re-calling.

[PAUSE — watch trace showing charge fired once]

One entry for the charge node. Not two. That guarantee holds
even through a hard process crash."

---

## Step 6 — AI Node

"Now let's look at the AI node.

I'm creating a triage workflow — it takes a support ticket,
sends it to an LLM, and asks it to classify it as bug, feature,
or question.

[PAUSE — watch workflow creation]

The key detail here is the output schema. I define exactly what
shape the LLM must return — in this case an object with a
'category' field restricted to three values. If the model returns
anything else, Relay rejects it before it reaches the next node.

The engine never trusts raw LLM output. It validates, then routes.

[PAUSE — watch run trigger and completion]

Run completed — the ticket was classified and the notification sent."

---

## Step 7 — Web Console

"Let me show you the console.

[PAUSE — browser opens to localhost:8080]

This is the Relay Console. On the left you have all the runs —
you can see their status, current node, and step count.
On the right is the trace panel for the selected run.
At the bottom are pending approvals you can approve or reject
with one click.

It auto-refreshes every two seconds — no need to reload."

[PAUSE — let the console sit on screen for a moment]

---

## Closing

"So to summarise what Relay does:

You define a workflow as a versioned graph of nodes.
You publish it, then trigger it via API or webhook.
Relay executes it step by step, persisting state after every node.
If it crashes, it resumes from where it left off.
Sensitive nodes pause for human approval.
AI nodes validate their output before the workflow continues.
And every side effect is guaranteed to fire exactly once.

The tech stack is Java 21, Spring Boot, and PostgreSQL — with
a DB-backed outbox queue that can be swapped for Kafka if needed.

That's Relay. Thanks for watching."

---

## Quick Reference — timings

| Script step | Approx time | What to say |
|---|---|---|
| Health check | 5s | Start opening line |
| Step 1 — create + publish | 15s | Workflow authoring section |
| Step 2 — trigger runs | 20s | Trigger runs section |
| Step 3 — trace | 10s | Trace section |
| Step 4 — approval | 20s | Approval gate section |
| Step 5 — exactly-once | 10s | Exactly-once section |
| Step 6 — AI node | 20s | AI node section |
| Step 7 — console | 15s | Console section |
| Summary print | 10s | Closing |
| **Total** | **~2 min** | |
