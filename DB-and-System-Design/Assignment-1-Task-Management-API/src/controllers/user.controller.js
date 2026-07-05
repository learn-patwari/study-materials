"use strict";
const db = require("../db");
const { asyncHandler } = require("../middleware/error");
const { publicUser } = require("./auth.controller");

// GET /api/users/me
const getMe = asyncHandler(async (req, res) => {
  res.json({ user: publicUser(req.user) });
});

// PATCH /api/users/me
const updateMe = asyncHandler(async (req, res) => {
  const { name, bio } = req.valid;
  const updates = [];
  const params = [];
  if (name !== undefined) { updates.push("name = ?"); params.push(name); }
  if (bio !== undefined) { updates.push("bio = ?"); params.push(bio); }
  if (updates.length) {
    params.push(req.user.id);
    db.run(`UPDATE users SET ${updates.join(", ")} WHERE id = ?`, params);
  }
  const user = db.get("SELECT * FROM users WHERE id = ?", [req.user.id]);
  res.json({ user: publicUser(user) });
});

// GET /api/users  (for assignment / invitations)
const listUsers = asyncHandler(async (req, res) => {
  const q = (req.query.q || "").toLowerCase();
  const rows = q
    ? db.all(
        "SELECT id, name, email, bio, created_at FROM users " +
          "WHERE lower(name) LIKE ? OR lower(email) LIKE ? ORDER BY name LIMIT 50",
        [`%${q}%`, `%${q}%`]
      )
    : db.all("SELECT id, name, email, bio, created_at FROM users ORDER BY name LIMIT 50");
  res.json({ users: rows });
});

module.exports = { getMe, updateMe, listUsers };
