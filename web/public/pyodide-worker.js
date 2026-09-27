// Runs assistant-written Python in a dedicated Web Worker via Pyodide (WASM) - this is
// OwnAI's Code Interpreter. It never touches the host machine in any way: no filesystem, no
// network the app controls, no server round-trip at all. Whatever the code does stays inside
// this worker's in-browser WASM sandbox and is thrown away when the worker/tab closes. The
// runtime itself is served from /pyodide/ (see scripts/copy-pyodide-assets.mjs), not a CDN, so
// this stays fully self-hosted.
//
// Must be loaded as a module worker (new Worker(url, { type: "module" }), see
// lib/pyodideRunner.ts) - newer Pyodide releases dropped classic-worker/importScripts support
// ("Classic web workers are not supported"), so this imports pyodide.mjs directly instead.
import { loadPyodide } from "/pyodide/pyodide.mjs";

let pyodideReadyPromise = null;

async function loadPyodideRuntime() {
  return loadPyodide({ indexURL: "/pyodide/" });
}

self.onmessage = async (event) => {
  const { id, code } = event.data;

  if (!pyodideReadyPromise) {
    pyodideReadyPromise = loadPyodideRuntime();
  }

  let stdout = "";
  let stderr = "";

  try {
    const pyodide = await pyodideReadyPromise;
    pyodide.setStdout({ batched: (s) => { stdout += s + "\n"; } });
    pyodide.setStderr({ batched: (s) => { stderr += s + "\n"; } });

    const result = await pyodide.runPythonAsync(code);
    self.postMessage({
      id,
      ok: true,
      stdout,
      stderr,
      result: result === undefined || result === null ? null : String(result),
    });
  } catch (err) {
    self.postMessage({ id, ok: false, stdout, stderr, error: String(err) });
  }
};
