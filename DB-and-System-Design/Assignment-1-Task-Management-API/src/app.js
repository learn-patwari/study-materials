"use strict";
/** Express application factory (kept separate from server start for testing). */
const express = require("express");
const routes = require("./routes");
const { notFound, errorHandler } = require("./middleware/error");
require("./db").connect(); // ensure DB is connected + migrated

function createApp() {
  const app = express();

  app.use(express.json());
  app.use(express.urlencoded({ extended: true }));

  // Basic request log (skip in test)
  if (process.env.NODE_ENV !== "test") {
    app.use((req, res, next) => {
      const start = Date.now();
      res.on("finish", () => {
        // eslint-disable-next-line no-console
        console.log(`${req.method} ${req.originalUrl} -> ${res.statusCode} ` +
          `(${Date.now() - start}ms)`);
      });
      next();
    });
  }

  app.get("/", (req, res) =>
    res.json({ name: "Task Management API", docs: "/api/health" }));
  app.use("/api", routes);

  app.use(notFound);
  app.use(errorHandler);
  return app;
}

module.exports = { createApp };
