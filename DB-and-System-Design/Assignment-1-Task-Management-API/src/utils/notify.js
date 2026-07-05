"use strict";
/** Persist a notification and push it in real time over SSE. */
const db = require("../db");
const sse = require("./sse");

function notify(userId, type, message, taskId = null) {
  if (!userId) return;
  const info = db.run(
    "INSERT INTO notifications (user_id, type, message, task_id) VALUES (?, ?, ?, ?)",
    [userId, type, message, taskId]
  );
  const event = {
    id: Number(info.lastInsertRowid),
    type,
    message,
    task_id: taskId,
    created_at: new Date().toISOString(),
  };
  sse.publish(userId, event);
  return event;
}

module.exports = { notify };
