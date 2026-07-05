"use strict";
const db = require("../db");
const { asyncHandler } = require("../middleware/error");
const sse = require("../utils/sse");
const { generateTaskDescription } = require("../utils/ai");

// GET /api/notifications
const listNotifications = asyncHandler(async (req, res) => {
  const rows = db.all(
    "SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 100",
    [req.user.id]
  );
  res.json({ notifications: rows });
});

// POST /api/notifications/:id/read
const markRead = asyncHandler(async (req, res) => {
  db.run("UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?",
    [Number(req.params.id), req.user.id]);
  res.json({ message: "Marked as read" });
});

// GET /api/notifications/stream  (SSE)
const stream = (req, res) => {
  sse.subscribe(req.user.id, res);
};

// POST /api/ai/task-description  { title, notes? }
const aiTaskDescription = asyncHandler(async (req, res) => {
  const { title, notes = "" } = req.valid;
  const result = await generateTaskDescription({ title, notes });
  res.json(result);
});

module.exports = { listNotifications, markRead, stream, aiTaskDescription };
