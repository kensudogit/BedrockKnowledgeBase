/**
 * Run vitest with NODE_ENV=test so React.act() works inside Docker
 * (Railway image sets NODE_ENV=production by default).
 */
process.env.NODE_ENV = "test";
process.env.CI = process.env.CI || "1";

const { spawnSync } = require("child_process");
const path = require("path");

const vitestCli = path.join(__dirname, "..", "node_modules", "vitest", "vitest.mjs");
const result = spawnSync(
  process.execPath,
  [vitestCli, "run", "--reporter=json", "--outputFile=.test-results.json"],
  { stdio: "inherit", env: process.env, cwd: path.join(__dirname, "..") },
);
process.exit(result.status == null ? 1 : result.status);
