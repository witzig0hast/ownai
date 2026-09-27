// Copies the Pyodide WASM runtime (JS glue, .wasm binary, stdlib.zip) from node_modules into
// public/, so it's served self-hosted from this app rather than fetched from a CDN at runtime -
// keeps the "fully self-hosted, private" project goal intact for the Code Interpreter feature
// (see src/lib/pyodideRunner.ts). Runs on `npm install` (postinstall) and again explicitly in
// the Docker build, since the builder stage's `COPY . .` happens after `npm ci`'s postinstall
// and would otherwise overwrite public/ with a copy that lacks these generated files.
import { cpSync, existsSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const sourceDir = join(__dirname, "..", "node_modules", "pyodide");
const targetDir = join(__dirname, "..", "public", "pyodide");

const FILES = [
  "pyodide.js",
  "pyodide.mjs",
  "pyodide.asm.mjs",
  "pyodide.asm.wasm",
  "pyodide-lock.json",
  "python_stdlib.zip",
];

if (!existsSync(sourceDir)) {
  console.warn("pyodide package not found in node_modules, skipping asset copy.");
  process.exit(0);
}

mkdirSync(targetDir, { recursive: true });
for (const file of FILES) {
  const from = join(sourceDir, file);
  if (!existsSync(from)) {
    console.warn(`Expected pyodide asset missing, skipping: ${file}`);
    continue;
  }
  cpSync(from, join(targetDir, file));
}
console.log(`Copied Pyodide runtime assets to ${targetDir}`);
