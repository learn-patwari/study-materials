"use strict";
/**
 * Minimal Server-Sent Events hub for real-time notifications (optional feature).
 * Clients subscribe per user id; `publish(userId, event)` pushes to all of that
 * user's open connections.
 */
const clients = new Map(); // userId -> Set(res)

function subscribe(userId, res) {
  res.set({
    "Content-Type": "text/event-stream",
    "Cache-Control": "no-cache",
    Connection: "keep-alive",
  });
  res.flushHeaders?.();
  res.write(`event: connected\ndata: {"ok":true}\n\n`);

  if (!clients.has(userId)) clients.set(userId, new Set());
  clients.get(userId).add(res);

  const keepAlive = setInterval(() => res.write(": ping\n\n"), 25000);
  res.on("close", () => {
    clearInterval(keepAlive);
    clients.get(userId)?.delete(res);
  });
}

function publish(userId, event) {
  const set = clients.get(userId);
  if (!set) return;
  const payload = `event: notification\ndata: ${JSON.stringify(event)}\n\n`;
  for (const res of set) res.write(payload);
}

module.exports = { subscribe, publish };
