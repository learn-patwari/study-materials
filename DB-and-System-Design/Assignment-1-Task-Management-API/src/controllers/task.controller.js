"use strict";
const db = require("../db");
const { ApiError, asyncHandler } = require("../middleware/error");
const { notify } = require("../utils/notify");
const { generateTaskDescription } = require("../utils/ai");

const STATUSES = ["open", "in_progress", "completed"];
const SORTABLE = { created_at: "created_at", due_date: "due_date",
  updated_at: "updated_at", title: "title", priority: "priority" };

function taskWithNames(row) {
  if (!row) return row;
  return {
    ...row,
    creator: row.creator_name ? { id: row.creator_id, name: row.creator_name } : null,
    assignee: row.assignee_id
      ? { id: row.assignee_id, name: row.assignee_name } : null,
  };
}
const TASK_SELECT = `
  SELECT t.*, uc.name AS creator_name, ua.name AS assignee_name
    FROM tasks t
    LEFT JOIN users uc ON uc.id = t.creator_id
    LEFT JOIN users ua ON ua.id = t.assignee_id`;

function loadTask(id) {
  return db.get(`${TASK_SELECT} WHERE t.id = ?`, [id]);
}
function canAccess(task, userId) {
  if (!task) return false;
  if (task.creator_id === userId || task.assignee_id === userId) return true;
  if (task.team_id)
    return !!db.get(
      "SELECT 1 FROM team_members WHERE team_id = ? AND user_id = ?",
      [task.team_id, userId]
    );
  return false;
}

// POST /api/tasks
const createTask = asyncHandler(async (req, res) => {
  const v = req.valid;
  // team membership check if a team is specified
  if (v.team_id) {
    const member = db.get(
      "SELECT 1 FROM team_members WHERE team_id = ? AND user_id = ?",
      [v.team_id, req.user.id]
    );
    if (!member) throw new ApiError(403, "You are not a member of that team");
  }
  let description = v.description || "";
  if (!description && req.body.generate_description) {
    const gen = await generateTaskDescription({ title: v.title, notes: v.notes });
    description = gen.description;
  }
  const info = db.run(
    `INSERT INTO tasks (title, description, status, priority, due_date, team_id,
                        creator_id, assignee_id)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
    [v.title, description, v.status || "open", v.priority || "medium",
     v.due_date || null, v.team_id || null, req.user.id, v.assignee_id || null]
  );
  const task = loadTask(info.lastInsertRowid);
  if (task.assignee_id && task.assignee_id !== req.user.id) {
    notify(task.assignee_id, "task_assigned",
      `You were assigned task "${task.title}"`, task.id);
  }
  res.status(201).json({ task: taskWithNames(task) });
});

// GET /api/tasks  — filter, sort, search, paginate
const listTasks = asyncHandler(async (req, res) => {
  const { status, team_id, priority, q, sort, order, assignee } = req.query;
  const where = [];
  const params = [];

  // visibility: tasks I created, am assigned, or in my teams
  where.push(`(t.creator_id = ? OR t.assignee_id = ? OR t.team_id IN
    (SELECT team_id FROM team_members WHERE user_id = ?))`);
  params.push(req.user.id, req.user.id, req.user.id);

  if (assignee === "me") { where.push("t.assignee_id = ?"); params.push(req.user.id); }
  else if (assignee) { where.push("t.assignee_id = ?"); params.push(Number(assignee)); }
  if (status) {
    if (!STATUSES.includes(status)) throw new ApiError(400, "Invalid status filter");
    where.push("t.status = ?"); params.push(status);
  }
  if (priority) { where.push("t.priority = ?"); params.push(priority); }
  if (team_id) { where.push("t.team_id = ?"); params.push(Number(team_id)); }
  if (q) {
    where.push("(lower(t.title) LIKE ? OR lower(t.description) LIKE ?)");
    params.push(`%${q.toLowerCase()}%`, `%${q.toLowerCase()}%`);
  }

  const sortCol = SORTABLE[sort] || "created_at";
  const sortDir = String(order).toLowerCase() === "asc" ? "ASC" : "DESC";
  const limit = Math.min(parseInt(req.query.limit || "50", 10), 100);
  const offset = Math.max(parseInt(req.query.offset || "0", 10), 0);

  const rows = db.all(
    `${TASK_SELECT} WHERE ${where.join(" AND ")}
       ORDER BY ${sortCol} ${sortDir} LIMIT ? OFFSET ?`,
    [...params, limit, offset]
  );
  res.json({ count: rows.length, tasks: rows.map(taskWithNames) });
});

// GET /api/tasks/:id
const getTask = asyncHandler(async (req, res) => {
  const task = loadTask(Number(req.params.id));
  if (!task) throw new ApiError(404, "Task not found");
  if (!canAccess(task, req.user.id)) throw new ApiError(403, "Access denied");
  res.json({ task: taskWithNames(task) });
});

// PATCH /api/tasks/:id
const updateTask = asyncHandler(async (req, res) => {
  const task = loadTask(Number(req.params.id));
  if (!task) throw new ApiError(404, "Task not found");
  if (!canAccess(task, req.user.id)) throw new ApiError(403, "Access denied");

  const v = req.valid;
  const fields = [];
  const params = [];
  for (const key of ["title", "description", "status", "priority", "due_date"]) {
    if (v[key] !== undefined) { fields.push(`${key} = ?`); params.push(v[key]); }
  }
  let newAssignee;
  if (v.assignee_id !== undefined) {
    newAssignee = v.assignee_id === null ? null : Number(v.assignee_id);
    fields.push("assignee_id = ?"); params.push(newAssignee);
  }
  if (!fields.length) throw new ApiError(400, "No valid fields to update");
  fields.push("updated_at = datetime('now')");
  params.push(task.id);
  db.run(`UPDATE tasks SET ${fields.join(", ")} WHERE id = ?`, params);

  const updated = loadTask(task.id);
  if (newAssignee && newAssignee !== task.assignee_id && newAssignee !== req.user.id) {
    notify(newAssignee, "task_assigned",
      `You were assigned task "${updated.title}"`, updated.id);
  }
  if (v.status && v.status !== task.status && updated.creator_id !== req.user.id) {
    notify(updated.creator_id, "task_updated",
      `Task "${updated.title}" is now ${v.status}`, updated.id);
  }
  res.json({ task: taskWithNames(updated) });
});

// POST /api/tasks/:id/complete  (convenience)
const completeTask = asyncHandler(async (req, res) => {
  req.valid = { status: "completed" };
  return updateTask(req, res);
});

// POST /api/tasks/:id/assign  { assignee_id }
const assignTask = asyncHandler(async (req, res) => {
  const task = loadTask(Number(req.params.id));
  if (!task) throw new ApiError(404, "Task not found");
  if (!canAccess(task, req.user.id)) throw new ApiError(403, "Access denied");

  const assigneeId = Number(req.body.assignee_id);
  if (!assigneeId) throw new ApiError(400, "assignee_id is required");
  const assignee = db.get("SELECT id, name FROM users WHERE id = ?", [assigneeId]);
  if (!assignee) throw new ApiError(404, "Assignee not found");
  if (task.team_id) {
    const member = db.get(
      "SELECT 1 FROM team_members WHERE team_id = ? AND user_id = ?",
      [task.team_id, assigneeId]
    );
    if (!member) throw new ApiError(400, "Assignee must be a member of the task's team");
  }
  db.run("UPDATE tasks SET assignee_id = ?, updated_at = datetime('now') WHERE id = ?",
    [assigneeId, task.id]);
  if (assigneeId !== req.user.id) {
    notify(assigneeId, "task_assigned",
      `You were assigned task "${task.title}"`, task.id);
  }
  res.json({ task: taskWithNames(loadTask(task.id)) });
});

// DELETE /api/tasks/:id
const deleteTask = asyncHandler(async (req, res) => {
  const task = loadTask(Number(req.params.id));
  if (!task) throw new ApiError(404, "Task not found");
  const teamOwner = task.team_id &&
    db.get("SELECT 1 FROM teams WHERE id = ? AND owner_id = ?", [task.team_id, req.user.id]);
  if (task.creator_id !== req.user.id && !teamOwner)
    throw new ApiError(403, "Only the creator or team owner can delete this task");
  db.run("DELETE FROM tasks WHERE id = ?", [task.id]);
  res.json({ message: "Task deleted", id: task.id });
});

module.exports = {
  createTask, listTasks, getTask, updateTask, completeTask, assignTask, deleteTask,
  canAccess, loadTask, STATUSES,
};
