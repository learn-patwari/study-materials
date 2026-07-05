"use strict";
/**
 * Central configuration, sourced from environment variables with sane defaults
 * so the app runs out of the box in development.
 */
const path = require("path");

const ROOT = path.resolve(__dirname, "..");

module.exports = {
  env: process.env.NODE_ENV || "development",
  port: parseInt(process.env.PORT || "3000", 10),

  // JWT
  jwtSecret: process.env.JWT_SECRET || "dev-insecure-secret-change-me",
  jwtExpiresIn: process.env.JWT_EXPIRES_IN || "2h",

  // Database file (":memory:" for tests)
  dbFile: process.env.DB_FILE || path.join(ROOT, "data", "app.db"),

  // Uploads
  uploadDir: process.env.UPLOAD_DIR || path.join(ROOT, "uploads"),
  maxUploadBytes: parseInt(process.env.MAX_UPLOAD_BYTES || "5242880", 10), // 5 MB

  // Generative AI (optional)
  anthropicModel: process.env.ANTHROPIC_MODEL || "claude-opus-4-8",

  ROOT,
};
