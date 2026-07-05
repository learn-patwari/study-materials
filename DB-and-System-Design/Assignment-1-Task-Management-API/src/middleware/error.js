"use strict";
/** Central error handling + a typed ApiError + async wrapper. */

class ApiError extends Error {
  constructor(status, message, details = undefined) {
    super(message);
    this.status = status;
    this.details = details;
  }
}

// Wrap async route handlers so thrown errors reach the error middleware.
const asyncHandler = (fn) => (req, res, next) =>
  Promise.resolve(fn(req, res, next)).catch(next);

function notFound(req, res) {
  res.status(404).json({ error: "Not found", path: req.originalUrl });
}

// eslint-disable-next-line no-unused-vars
function errorHandler(err, req, res, next) {
  // multer file-size errors
  if (err && err.code === "LIMIT_FILE_SIZE") {
    return res.status(413).json({ error: "File too large" });
  }
  // SQLite unique-constraint => 409 conflict
  if (err && /UNIQUE constraint failed/i.test(err.message || "")) {
    return res.status(409).json({ error: "Resource already exists" });
  }
  // JWT errors => 401
  if (err && (err.name === "JsonWebTokenError" || err.name === "TokenExpiredError")) {
    return res.status(401).json({ error: "Invalid or expired token" });
  }
  const status = err.status || 500;
  const body = { error: err.message || "Internal server error" };
  if (err.details) body.details = err.details;
  if (status >= 500) {
    // eslint-disable-next-line no-console
    console.error(err);
    body.error = process.env.NODE_ENV === "production"
      ? "Internal server error" : body.error;
  }
  res.status(status).json(body);
}

module.exports = { ApiError, asyncHandler, notFound, errorHandler };
