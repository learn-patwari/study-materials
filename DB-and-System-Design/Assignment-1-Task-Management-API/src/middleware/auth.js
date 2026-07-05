"use strict";
/** Authentication middleware: verifies the Bearer JWT and loads req.user. */
const { verifyToken, isRevoked } = require("../utils/jwt");
const { ApiError } = require("./error");
const db = require("../db");

function extractToken(req) {
  const header = req.headers.authorization || "";
  if (header.startsWith("Bearer ")) return header.slice(7).trim();
  // Allow token via query for SSE (EventSource can't set headers).
  if (req.query && req.query.token) return String(req.query.token);
  return null;
}

function authenticate(req, res, next) {
  const token = extractToken(req);
  if (!token) return next(new ApiError(401, "Authentication required"));

  let payload;
  try {
    payload = verifyToken(token);
  } catch (err) {
    return next(err); // handled as 401 in error middleware
  }
  if (isRevoked(payload.jti)) {
    return next(new ApiError(401, "Token has been revoked"));
  }
  const user = db.get(
    "SELECT id, name, email, bio, created_at FROM users WHERE id = ?",
    [payload.sub]
  );
  if (!user) return next(new ApiError(401, "User no longer exists"));

  req.user = user;
  req.token = { raw: token, payload };
  next();
}

module.exports = { authenticate };
