/**
 * Records demo/index.html (built by build_html.py) to a .webm video using
 * Playwright's built-in video capture -- no external screen-recorder needed.
 *
 * Usage:
 *   npm install
 *   node record.js
 *
 * Chromium lookup order: $PLAYWRIGHT_CHROMIUM_PATH, then a version-suffixed
 * install under $PLAYWRIGHT_BROWSERS_PATH (as used by some sandboxed CI
 * images), then Playwright's own default resolution (after a normal
 * `npx playwright install chromium`).
 */
const path = require("path");
const fs = require("fs");
const { chromium } = require("playwright");

const HERE = __dirname;
const VIDEO_DIR = path.join(HERE, "video_out");
const WIDTH = 1280, HEIGHT = 720;

function findChromiumExecutable() {
  if (process.env.PLAYWRIGHT_CHROMIUM_PATH) return process.env.PLAYWRIGHT_CHROMIUM_PATH;
  const browsersPath = process.env.PLAYWRIGHT_BROWSERS_PATH;
  if (browsersPath && fs.existsSync(browsersPath)) {
    const dir = fs.readdirSync(browsersPath).find((d) => /^chromium-\d+$/.test(d));
    if (dir) {
      const p = path.join(browsersPath, dir, "chrome-linux", "chrome");
      if (fs.existsSync(p)) return p;
    }
  }
  return undefined; // let Playwright resolve its default install
}

(async () => {
  fs.rmSync(VIDEO_DIR, { recursive: true, force: true });
  fs.mkdirSync(VIDEO_DIR, { recursive: true });

  const executablePath = findChromiumExecutable();
  const browser = await chromium.launch({
    ...(executablePath ? { executablePath } : {}),
    args: ["--no-sandbox"],
  });
  const context = await browser.newContext({
    viewport: { width: WIDTH, height: HEIGHT },
    recordVideo: { dir: VIDEO_DIR, size: { width: WIDTH, height: HEIGHT } },
  });
  const page = await context.newPage();

  const fileUrl = "file://" + path.join(HERE, "index.html");
  const start = Date.now();
  await page.goto(fileUrl);
  await page.waitForFunction(() => window.__DONE__ === true, null, { timeout: 300000 });
  console.log("Animation finished after", ((Date.now() - start) / 1000).toFixed(1), "s");

  await page.waitForTimeout(600); // avoid cutting the last frame abruptly

  await context.close(); // flushes the video file to disk
  await browser.close();

  const files = fs.readdirSync(VIDEO_DIR).filter((f) => f.endsWith(".webm"));
  if (files.length !== 1) throw new Error("Expected exactly one .webm output, got: " + files);
  const finalPath = path.join(HERE, "resume_matching_agent_demo.webm");
  fs.copyFileSync(path.join(VIDEO_DIR, files[0]), finalPath);
  console.log("Wrote", finalPath);
})().catch((e) => {
  console.error("RECORDING FAILED:", e);
  process.exit(1);
});
