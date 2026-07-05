"use strict";
const db = require("../db");
const { hashPassword, verifyPassword } = require("../utils/password");
const { signToken, revokeToken } = require("../utils/jwt");
const { ApiError, asyncHandler } = require("../middleware/error");

function publicUser(u) {
  return { id: u.id, name: u.name, email: u.email, bio: u.bio, created_at: u.created_at };
}

// POST /api/auth/register
const register = asyncHandler(async (req, res) => {
  const { name, email, password } = req.valid;
  const existing = db.get("SELECT id FROM users WHERE email = ?", [email.toLowerCase()]);
  if (existing) throw new ApiError(409, "Email already registered");

  const password_hash = await hashPassword(password);
  const info = db.run(
    "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
    [name, email.toLowerCase(), password_hash]
  );
  const user = db.get("SELECT * FROM users WHERE id = ?", [info.lastInsertRowid]);
  const token = signToken(user);
  res.status(201).json({ user: publicUser(user), token });
});

// POST /api/auth/login
const login = asyncHandler(async (req, res) => {
  const { email, password } = req.valid;
  const user = db.get("SELECT * FROM users WHERE email = ?", [email.toLowerCase()]);
  if (!user) throw new ApiError(401, "Invalid credentials");

  const ok = await verifyPassword(password, user.password_hash);
  if (!ok) throw new ApiError(401, "Invalid credentials");

  const token = signToken(user);
  res.json({ user: publicUser(user), token });
});

// POST /api/auth/logout  (auth)
const logout = asyncHandler(async (req, res) => {
  revokeToken(req.token.payload);
  res.json({ message: "Logged out successfully" });
});

module.exports = { register, login, logout, publicUser };
