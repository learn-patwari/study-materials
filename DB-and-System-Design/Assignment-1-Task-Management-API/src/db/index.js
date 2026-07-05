"use strict";
/**
 * Database access layer built on Node's built-in `node:sqlite` (no native deps).
 * Exposes a singleton connection plus tiny query helpers.
 */
const fs = require("fs");
const path = require("path");
const { DatabaseSync } = require("node:sqlite");
const config = require("../config");

let db = null;

function connect(dbFile = config.dbFile) {
  if (db) return db;
  if (dbFile !== ":memory:") {
    fs.mkdirSync(path.dirname(dbFile), { recursive: true });
  }
  db = new DatabaseSync(dbFile);
  db.exec("PRAGMA foreign_keys = ON;");
  migrate();
  return db;
}

function migrate() {
  const schema = fs.readFileSync(path.join(__dirname, "schema.sql"), "utf8");
  db.exec(schema);
}

function getDb() {
  if (!db) connect();
  return db;
}

// --- helpers ---------------------------------------------------------------
function run(sql, params = []) {
  return getDb().prepare(sql).run(...params);
}
function get(sql, params = []) {
  return getDb().prepare(sql).get(...params);
}
function all(sql, params = []) {
  return getDb().prepare(sql).all(...params);
}

module.exports = { connect, getDb, migrate, run, get, all };
