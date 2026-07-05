"use strict";
const db = require("../db");
const { ApiError, asyncHandler } = require("../middleware/error");
const { notify } = require("../utils/notify");

function isMember(teamId, userId) {
  return !!db.get(
    "SELECT 1 FROM team_members WHERE team_id = ? AND user_id = ?",
    [teamId, userId]
  );
}
function isOwner(teamId, userId) {
  const t = db.get("SELECT owner_id FROM teams WHERE id = ?", [teamId]);
  return t && t.owner_id === userId;
}

// POST /api/teams
const createTeam = asyncHandler(async (req, res) => {
  const { name, description = "" } = req.valid;
  const info = db.run(
    "INSERT INTO teams (name, description, owner_id) VALUES (?, ?, ?)",
    [name, description, req.user.id]
  );
  const teamId = info.lastInsertRowid;
  db.run(
    "INSERT INTO team_members (team_id, user_id, role) VALUES (?, ?, 'owner')",
    [teamId, req.user.id]
  );
  res.status(201).json({ team: db.get("SELECT * FROM teams WHERE id = ?", [teamId]) });
});

// GET /api/teams  (teams I belong to)
const listMyTeams = asyncHandler(async (req, res) => {
  const teams = db.all(
    `SELECT t.*, tm.role FROM teams t
       JOIN team_members tm ON tm.team_id = t.id
      WHERE tm.user_id = ? ORDER BY t.created_at DESC`,
    [req.user.id]
  );
  res.json({ teams });
});

// GET /api/teams/:id
const getTeam = asyncHandler(async (req, res) => {
  const teamId = Number(req.params.id);
  if (!isMember(teamId, req.user.id))
    throw new ApiError(403, "You are not a member of this team");
  const team = db.get("SELECT * FROM teams WHERE id = ?", [teamId]);
  if (!team) throw new ApiError(404, "Team not found");
  const members = db.all(
    `SELECT u.id, u.name, u.email, tm.role, tm.joined_at
       FROM team_members tm JOIN users u ON u.id = tm.user_id
      WHERE tm.team_id = ? ORDER BY tm.joined_at`,
    [teamId]
  );
  res.json({ team, members });
});

// POST /api/teams/:id/members   (owner invites/adds by email or userId)
const addMember = asyncHandler(async (req, res) => {
  const teamId = Number(req.params.id);
  if (!isOwner(teamId, req.user.id))
    throw new ApiError(403, "Only the team owner can add members");

  const { email, userId } = req.body;
  const target = userId
    ? db.get("SELECT * FROM users WHERE id = ?", [userId])
    : db.get("SELECT * FROM users WHERE email = ?", [String(email || "").toLowerCase()]);
  if (!target) throw new ApiError(404, "User not found");
  if (isMember(teamId, target.id))
    throw new ApiError(409, "User is already a member");

  db.run(
    "INSERT INTO team_members (team_id, user_id, role) VALUES (?, ?, 'member')",
    [teamId, target.id]
  );
  const team = db.get("SELECT name FROM teams WHERE id = ?", [teamId]);
  notify(target.id, "team_invite", `You were added to team "${team.name}"`);
  res.status(201).json({ message: "Member added", user_id: target.id });
});

// POST /api/teams/:id/join   (self-join)
const joinTeam = asyncHandler(async (req, res) => {
  const teamId = Number(req.params.id);
  const team = db.get("SELECT * FROM teams WHERE id = ?", [teamId]);
  if (!team) throw new ApiError(404, "Team not found");
  if (isMember(teamId, req.user.id))
    throw new ApiError(409, "You are already a member");
  db.run(
    "INSERT INTO team_members (team_id, user_id, role) VALUES (?, ?, 'member')",
    [teamId, req.user.id]
  );
  res.status(201).json({ message: "Joined team", team_id: teamId });
});

module.exports = { createTeam, listMyTeams, getTeam, addMember, joinTeam, isMember };
