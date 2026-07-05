"use strict";
/**
 * Generative task descriptions (optional feature).
 *
 * If `@anthropic-ai/sdk` is installed and `ANTHROPIC_API_KEY` is set, Claude
 * (claude-opus-4-8) expands a title + notes into a clear task description.
 * Otherwise a deterministic template is used, so the endpoint always works.
 */
const config = require("../config");

async function generateTaskDescription({ title, notes = "" }) {
  const viaLlm = await tryClaude({ title, notes });
  if (viaLlm) return { description: viaLlm, source: "claude" };
  return { description: templateDescription({ title, notes }), source: "template" };
}

async function tryClaude({ title, notes }) {
  if (!process.env.ANTHROPIC_API_KEY) return null;
  let Anthropic;
  try {
    Anthropic = require("@anthropic-ai/sdk");
  } catch {
    return null;
  }
  try {
    const client = new Anthropic();
    const resp = await client.messages.create({
      model: config.anthropicModel,
      max_tokens: 400,
      system:
        "You write concise, actionable software task descriptions. " +
        "Given a title and optional notes, return 2-4 sentences describing the " +
        "task and its acceptance criteria. No preamble.",
      messages: [
        { role: "user", content: `Title: ${title}\nNotes: ${notes || "(none)"}` },
      ],
    });
    const text = (resp.content || [])
      .filter((b) => b.type === "text")
      .map((b) => b.text)
      .join("\n")
      .trim();
    return text || null;
  } catch {
    return null; // network/quota/etc. — fall back to template
  }
}

function templateDescription({ title, notes }) {
  const base =
    `Complete the task "${title}". ` +
    (notes ? `Context: ${notes}. ` : "") +
    "Define clear acceptance criteria, implement the change, and verify it " +
    "works before marking the task complete.";
  return base;
}

module.exports = { generateTaskDescription };
