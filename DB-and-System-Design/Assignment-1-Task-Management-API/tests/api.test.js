"use strict";
/**
 * Integration tests covering the assignment's user stories.
 * Runs against an in-memory database — no external services.
 *
 *   npm test
 */
process.env.NODE_ENV = "test";
process.env.DB_FILE = ":memory:";
process.env.JWT_SECRET = "test-secret";

const test = require("node:test");
const assert = require("node:assert");
const { createApp } = require("../src/app");

const app = createApp();
let server, base;

function url(p) { return base + p; }
function headers(token) {
  return { "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}) };
}
async function api(method, path, body, token) {
  const res = await fetch(url(path), {
    method,
    headers: headers(token),
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  const json = await res.json().catch(() => ({}));
  return { status: res.status, body: json };
}

test.before(async () => {
  await new Promise((resolve) => {
    server = app.listen(0, () => {
      base = `http://localhost:${server.address().port}`;
      resolve();
    });
  });
});
test.after(() => server && server.close());

// Shared state across ordered tests.
const ctx = {};

test("register creates an account and returns a token", async () => {
  const r = await api("POST", "/api/auth/register",
    { name: "Alice", email: "alice@example.com", password: "password123" });
  assert.equal(r.status, 201);
  assert.ok(r.body.token);
  assert.equal(r.body.user.email, "alice@example.com");
  assert.ok(!("password_hash" in r.body.user), "must not leak password hash");
  ctx.alice = r.body.token;
  ctx.aliceId = r.body.user.id;
});

test("duplicate registration is rejected (409)", async () => {
  const r = await api("POST", "/api/auth/register",
    { name: "Alice2", email: "alice@example.com", password: "password123" });
  assert.equal(r.status, 409);
});

test("registration validation rejects short passwords (400)", async () => {
  const r = await api("POST", "/api/auth/register",
    { name: "Bob", email: "bob@example.com", password: "short" });
  assert.equal(r.status, 400);
  assert.ok(Array.isArray(r.body.details));
});

test("login with correct credentials succeeds", async () => {
  await api("POST", "/api/auth/register",
    { name: "Bob", email: "bob@example.com", password: "password123" });
  const r = await api("POST", "/api/auth/login",
    { email: "bob@example.com", password: "password123" });
  assert.equal(r.status, 200);
  assert.ok(r.body.token);
  ctx.bob = r.body.token;
  ctx.bobId = r.body.user.id;
});

test("login with wrong password fails (401)", async () => {
  const r = await api("POST", "/api/auth/login",
    { email: "bob@example.com", password: "wrongpass1" });
  assert.equal(r.status, 401);
});

test("protected route requires auth (401)", async () => {
  const r = await api("GET", "/api/users/me");
  assert.equal(r.status, 401);
});

test("view and update profile", async () => {
  let r = await api("GET", "/api/users/me", undefined, ctx.alice);
  assert.equal(r.status, 200);
  r = await api("PATCH", "/api/users/me", { bio: "Team lead" }, ctx.alice);
  assert.equal(r.status, 200);
  assert.equal(r.body.user.bio, "Team lead");
});

test("create a team and add a member", async () => {
  let r = await api("POST", "/api/teams",
    { name: "Engineering", description: "Core team" }, ctx.alice);
  assert.equal(r.status, 201);
  ctx.teamId = r.body.team.id;

  r = await api("POST", `/api/teams/${ctx.teamId}/members`,
    { email: "bob@example.com" }, ctx.alice);
  assert.equal(r.status, 201);

  r = await api("GET", `/api/teams/${ctx.teamId}`, undefined, ctx.alice);
  assert.equal(r.status, 200);
  assert.equal(r.body.members.length, 2);
});

test("non-owner cannot add members (403)", async () => {
  const r = await api("POST", `/api/teams/${ctx.teamId}/members`,
    { email: "alice@example.com" }, ctx.bob);
  assert.equal(r.status, 403);
});

test("create a task with title, description, due date", async () => {
  const r = await api("POST", "/api/tasks", {
    title: "Design schema", description: "ERD for the app",
    due_date: "2026-09-01", priority: "high", team_id: ctx.teamId,
  }, ctx.alice);
  assert.equal(r.status, 201);
  assert.equal(r.body.task.status, "open");
  ctx.taskId = r.body.task.id;
});

test("assign a task to a team member (notifies them)", async () => {
  const r = await api("POST", `/api/tasks/${ctx.taskId}/assign`,
    { assignee_id: ctx.bobId }, ctx.alice);
  assert.equal(r.status, 200);
  assert.equal(r.body.task.assignee.id, ctx.bobId);

  const notif = await api("GET", "/api/notifications", undefined, ctx.bob);
  assert.ok(notif.body.notifications.some((n) => n.type === "task_assigned"));
});

test("assignee sees the task in 'assigned to me'", async () => {
  const r = await api("GET", "/api/tasks?assignee=me", undefined, ctx.bob);
  assert.equal(r.status, 200);
  assert.ok(r.body.tasks.some((t) => t.id === ctx.taskId));
});

test("filter by status, and search by title/description", async () => {
  let r = await api("GET", "/api/tasks?status=open", undefined, ctx.alice);
  assert.ok(r.body.tasks.every((t) => t.status === "open"));

  r = await api("GET", "/api/tasks?q=schema", undefined, ctx.alice);
  assert.ok(r.body.tasks.some((t) => t.id === ctx.taskId));

  r = await api("GET", "/api/tasks?q=nonexistentzzz", undefined, ctx.alice);
  assert.equal(r.body.count, 0);
});

test("mark a task completed", async () => {
  const r = await api("POST", `/api/tasks/${ctx.taskId}/complete`, {}, ctx.bob);
  assert.equal(r.status, 200);
  assert.equal(r.body.task.status, "completed");

  const done = await api("GET", "/api/tasks?status=completed", undefined, ctx.bob);
  assert.ok(done.body.tasks.some((t) => t.id === ctx.taskId));
});

test("comment on a task", async () => {
  let r = await api("POST", `/api/tasks/${ctx.taskId}/comments`,
    { body: "Looks good!" }, ctx.bob);
  assert.equal(r.status, 201);
  r = await api("GET", `/api/tasks/${ctx.taskId}/comments`, undefined, ctx.alice);
  assert.equal(r.body.comments.length, 1);
  assert.equal(r.body.comments[0].user_name, "Bob");
});

test("outsider cannot access a task they're unrelated to (403)", async () => {
  const outsider = await api("POST", "/api/auth/register",
    { name: "Eve", email: "eve@example.com", password: "password123" });
  const r = await api("GET", `/api/tasks/${ctx.taskId}`, undefined, outsider.body.token);
  assert.equal(r.status, 403);
});

test("AI task-description endpoint returns a description (template fallback)", async () => {
  const r = await api("POST", "/api/ai/task-description",
    { title: "Add caching layer", notes: "Redis for sessions" }, ctx.alice);
  assert.equal(r.status, 200);
  assert.ok(r.body.description.length > 0);
  assert.ok(["template", "claude"].includes(r.body.source));
});

test("logout revokes the token (subsequent calls 401)", async () => {
  let r = await api("POST", "/api/auth/logout", {}, ctx.bob);
  assert.equal(r.status, 200);
  r = await api("GET", "/api/users/me", undefined, ctx.bob);
  assert.equal(r.status, 401);
});
