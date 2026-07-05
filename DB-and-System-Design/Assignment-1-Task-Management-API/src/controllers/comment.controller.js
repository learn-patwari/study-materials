"use strict";
const db = require("../db");
const { ApiError, asyncHandler } = require("../middleware/error");
const { canAccess, loadTask } = require("./task.controller");
const { notify } = require("../utils/notify");

function requireTaskAccess(req) {
  const task = loadTask(Number(req.params.id));
  if (!task) throw new ApiError(404, "Task not found");
  if (!canAccess(task, req.user.id)) throw new ApiError(403, "Access denied");
  return task;
}

// GET /api/tasks/:id/comments
const listComments = asyncHandler(async (req, res) => {
  requireTaskAccess(req);
  const comments = db.all(
    `SELECT c.id, c.body, c.created_at, u.id AS user_id, u.name AS user_name
       FROM comments c JOIN users u ON u.id = c.user_id
      WHERE c.task_id = ? ORDER BY c.created_at`,
    [Number(req.params.id)]
  );
  res.json({ comments });
});

// POST /api/tasks/:id/comments
const addComment = asyncHandler(async (req, res) => {
  const task = requireTaskAccess(req);
  const info = db.run(
    "INSERT INTO comments (task_id, user_id, body) VALUES (?, ?, ?)",
    [task.id, req.user.id, req.valid.body]
  );
  // notify the other party (assignee or creator)
  const notifyTarget =
    req.user.id === task.creator_id ? task.assignee_id : task.creator_id;
  if (notifyTarget) {
    notify(notifyTarget, "task_comment",
      `${req.user.name} commented on "${task.title}"`, task.id);
  }
  const comment = db.get(
    `SELECT c.id, c.body, c.created_at, u.id AS user_id, u.name AS user_name
       FROM comments c JOIN users u ON u.id = c.user_id WHERE c.id = ?`,
    [info.lastInsertRowid]
  );
  res.status(201).json({ comment });
});

module.exports = { listComments, addComment };
