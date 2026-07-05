"use strict";
/**
 * Tiny declarative request validator (no external dependency).
 *
 *   validate({ title: { required: true, type: "string", min: 1, max: 200 } })
 *
 * Validates req.body against the schema and attaches the cleaned object to
 * req.valid. Throws a 400 ApiError with field-level details on failure.
 */
const { ApiError } = require("./error");

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function validateValue(field, rules, value) {
  const errors = [];
  const present = value !== undefined && value !== null && value !== "";

  if (rules.required && !present) {
    errors.push(`${field} is required`);
    return { errors, value };
  }
  if (!present) {
    return { errors, value: rules.default !== undefined ? rules.default : undefined };
  }

  if (rules.type === "string" && typeof value !== "string") {
    errors.push(`${field} must be a string`);
  }
  if (rules.type === "number") {
    value = Number(value);
    if (Number.isNaN(value)) errors.push(`${field} must be a number`);
  }
  if (typeof value === "string") {
    if (rules.min !== undefined && value.length < rules.min)
      errors.push(`${field} must be at least ${rules.min} characters`);
    if (rules.max !== undefined && value.length > rules.max)
      errors.push(`${field} must be at most ${rules.max} characters`);
  }
  if (rules.email && !EMAIL_RE.test(value)) errors.push(`${field} must be a valid email`);
  if (rules.enum && !rules.enum.includes(value))
    errors.push(`${field} must be one of: ${rules.enum.join(", ")}`);
  if (rules.isoDate && Number.isNaN(Date.parse(value)))
    errors.push(`${field} must be a valid date`);

  return { errors, value };
}

function validate(schema, source = "body") {
  return (req, res, next) => {
    const data = req[source] || {};
    const cleaned = {};
    const allErrors = [];
    for (const [field, rules] of Object.entries(schema)) {
      const { errors, value } = validateValue(field, rules, data[field]);
      allErrors.push(...errors);
      if (value !== undefined) cleaned[field] = value;
    }
    if (allErrors.length) {
      return next(new ApiError(400, "Validation failed", allErrors));
    }
    req.valid = cleaned;
    next();
  };
}

module.exports = { validate };
