"use strict";
const fs = require("fs");
const path = require("path");
const db = require("../db");
const config = require("../config");
const { ApiError, asyncHandler } = require("../middleware/error");
const { canAccess, loadTask } = require("./task.controller");

function requireTaskAccess(req) {
  const task = loadTask(Number(req.params.id));
  if (!task) throw new ApiError(404, "Task not found");
  if (!canAccess(task, req.user.id)) throw new ApiError(403, "Access denied");
  return task;
}

// GET /api/tasks/:id/attachments
const listAttachments = asyncHandler(async (req, res) => {
  requireTaskAccess(req);
  const rows = db.all(
    `SELECT a.id, a.original_name, a.mime_type, a.size_bytes, a.created_at,
            u.id AS user_id, u.name AS user_name
       FROM attachments a JOIN users u ON u.id = a.user_id
      WHERE a.task_id = ? ORDER BY a.created_at`,
    [Number(req.params.id)]
  );
  res.json({ attachments: rows });
});

// POST /api/tasks/:id/attachments  (multipart form field: "file")
const uploadAttachment = asyncHandler(async (req, res) => {
  const task = requireTaskAccess(req);
  if (!req.file) throw new ApiError(400, "No file uploaded (field name: 'file')");
  const info = db.run(
    `INSERT INTO attachments
       (task_id, user_id, stored_name, original_name, mime_type, size_bytes)
     VALUES (?, ?, ?, ?, ?, ?)`,
    [task.id, req.user.id, req.file.filename, req.file.originalname,
     req.file.mimetype, req.file.size]
  );
  const attachment = db.get(
    `SELECT id, original_name, mime_type, size_bytes, created_at
       FROM attachments WHERE id = ?`,
    [info.lastInsertRowid]
  );
  res.status(201).json({ attachment });
});

// GET /api/attachments/:attId/download
const downloadAttachment = asyncHandler(async (req, res) => {
  const att = db.get("SELECT * FROM attachments WHERE id = ?", [Number(req.params.attId)]);
  if (!att) throw new ApiError(404, "Attachment not found");
  const task = loadTask(att.task_id);
  if (!canAccess(task, req.user.id)) throw new ApiError(403, "Access denied");

  const filePath = path.join(config.uploadDir, att.stored_name);
  if (!fs.existsSync(filePath)) throw new ApiError(404, "File missing on server");
  res.setHeader("Content-Type", att.mime_type);
  res.setHeader("Content-Disposition",
    `attachment; filename="${att.original_name.replace(/"/g, "")}"`);
  fs.createReadStream(filePath).pipe(res);
});

module.exports = { listAttachments, uploadAttachment, downloadAttachment };
