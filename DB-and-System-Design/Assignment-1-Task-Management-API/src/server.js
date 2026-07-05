"use strict";
/** HTTP server entry point. */
const { createApp } = require("./app");
const config = require("./config");

const app = createApp();
const server = app.listen(config.port, () => {
  // eslint-disable-next-line no-console
  console.log(`Task Management API listening on http://localhost:${config.port}`);
  console.log(`Health check: http://localhost:${config.port}/api/health`);
});

// Graceful shutdown
for (const sig of ["SIGINT", "SIGTERM"]) {
  process.on(sig, () => server.close(() => process.exit(0)));
}

module.exports = server;
