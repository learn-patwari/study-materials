"use strict";
const express = require("express");
const multer = require("multer");
const path = require("path");
const crypto = require("crypto");
const config = require("../config");

const { authenticate } = require("../middleware/auth");
const { validate } = require("../middleware/validate");

const auth = require("../controllers/auth.controller");
const users = require("../controllers/user.controller");
const teams = require("../controllers/team.controller");
const tasks = require("../controllers/task.controller");
const comments = require("../controllers/comment.controller");
const attachments = require("../controllers/attachment.controller");
const misc = require("../controllers/misc.controller");

// --- multer (disk storage for attachments) ---------------------------------
const fs = require("fs");
fs.mkdirSync(config.uploadDir, { recursive: true });
const storage = multer.diskStorage({
  destination: (req, file, cb) => cb(null, config.uploadDir),
  filename: (req, file, cb) => {
    const ext = path.extname(file.originalname);
    cb(null, `${Date.now()}-${crypto.randomBytes(6).toString("hex")}${ext}`);
  },
});
const upload = multer({ storage, limits: { fileSize: config.maxUploadBytes } });

const router = express.Router();

// Health
router.get("/health", (req, res) => res.json({ status: "ok", time: new Date().toISOString() }));

// --- Auth ---
router.post("/auth/register", validate({
  name: { required: true, type: "string", min: 1, max: 100 },
  email: { required: true, type: "string", email: true },
  password: { required: true, type: "string", min: 8, max: 200 },
}), auth.register);
router.post("/auth/login", validate({
  email: { required: true, type: "string", email: true },
  password: { required: true, type: "string" },
}), auth.login);
router.post("/auth/logout", authenticate, auth.logout);

// --- Users ---
router.get("/users/me", authenticate, users.getMe);
router.patch("/users/me", authenticate, validate({
  name: { type: "string", min: 1, max: 100 },
  bio: { type: "string", max: 500 },
}), users.updateMe);
router.get("/users", authenticate, users.listUsers);

// --- Teams ---
router.post("/teams", authenticate, validate({
  name: { required: true, type: "string", min: 1, max: 100 },
  description: { type: "string", max: 500 },
}), teams.createTeam);
router.get("/teams", authenticate, teams.listMyTeams);
router.get("/teams/:id", authenticate, teams.getTeam);
router.post("/teams/:id/members", authenticate, teams.addMember);
router.post("/teams/:id/join", authenticate, teams.joinTeam);

// --- Tasks ---
router.post("/tasks", authenticate, validate({
  title: { required: true, type: "string", min: 1, max: 200 },
  description: { type: "string", max: 5000 },
  notes: { type: "string", max: 2000 },
  status: { type: "string", enum: tasks.STATUSES },
  priority: { type: "string", enum: ["low", "medium", "high"] },
  due_date: { type: "string", isoDate: true },
  team_id: { type: "number" },
  assignee_id: { type: "number" },
}), tasks.createTask);
router.get("/tasks", authenticate, tasks.listTasks);
router.get("/tasks/:id", authenticate, tasks.getTask);
router.patch("/tasks/:id", authenticate, validate({
  title: { type: "string", min: 1, max: 200 },
  description: { type: "string", max: 5000 },
  status: { type: "string", enum: tasks.STATUSES },
  priority: { type: "string", enum: ["low", "medium", "high"] },
  due_date: { type: "string", isoDate: true },
  assignee_id: { type: "number" },
}), tasks.updateTask);
router.post("/tasks/:id/complete", authenticate, tasks.completeTask);
router.post("/tasks/:id/assign", authenticate, tasks.assignTask);
router.delete("/tasks/:id", authenticate, tasks.deleteTask);

// --- Comments (nested under a task) ---
router.get("/tasks/:id/comments", authenticate, comments.listComments);
router.post("/tasks/:id/comments", authenticate, validate({
  body: { required: true, type: "string", min: 1, max: 2000 },
}), comments.addComment);

// --- Attachments ---
router.get("/tasks/:id/attachments", authenticate, attachments.listAttachments);
router.post("/tasks/:id/attachments", authenticate, upload.single("file"),
  attachments.uploadAttachment);
router.get("/attachments/:attId/download", authenticate, attachments.downloadAttachment);

// --- Notifications (optional real-time) ---
router.get("/notifications", authenticate, misc.listNotifications);
router.post("/notifications/:id/read", authenticate, misc.markRead);
router.get("/notifications/stream", authenticate, misc.stream);

// --- Generative AI (optional) ---
router.post("/ai/task-description", authenticate, validate({
  title: { required: true, type: "string", min: 1, max: 200 },
  notes: { type: "string", max: 2000 },
}), misc.aiTaskDescription);

module.exports = router;
