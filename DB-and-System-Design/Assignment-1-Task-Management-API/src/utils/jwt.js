"use strict";
/**
 * JWT helpers. Tokens carry a `jti` (unique id) so we can revoke individual
 * tokens on logout via the `revoked_tokens` table — real logout for otherwise
 * stateless JWTs.
 */
const crypto = require("crypto");
const jwt = require("jsonwebtoken");
const config = require("../config");
const db = require("../db");

function signToken(user) {
  const jti = crypto.randomUUID();
  const token = jwt.sign(
    { sub: user.id, email: user.email, jti },
    config.jwtSecret,
    { expiresIn: config.jwtExpiresIn }
  );
  return token;
}

function verifyToken(token) {
  return jwt.verify(token, config.jwtSecret); // throws on invalid/expired
}

function revokeToken(payload) {
  if (!payload || !payload.jti) return;
  db.run(
    "INSERT OR REPLACE INTO revoked_tokens (jti, expires_at) VALUES (?, ?)",
    [payload.jti, payload.exp || 0]
  );
}

function isRevoked(jti) {
  if (!jti) return false;
  return !!db.get("SELECT jti FROM revoked_tokens WHERE jti = ?", [jti]);
}

module.exports = { signToken, verifyToken, revokeToken, isRevoked };
