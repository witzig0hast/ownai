// Talks to public/pyodide-worker.js - see that file for the sandboxing rationale (Code
// Interpreter feature). One worker is reused across runs within a tab (loading the Pyodide
// runtime takes a few seconds, so we don't want to repeat it per execution).

export interface PythonRunResult {
  ok: boolean;
  stdout: string;
  stderr: string;
  result?: string | null;
  error?: string;
}

let worker: Worker | null = null;
let nextId = 0;
const pending = new Map<number, (result: PythonRunResult) => void>();

function getWorker(): Worker {
  if (!worker) {
    // type: "module" is required - pyodide-worker.js imports pyodide.mjs via ES import,
    // which classic (non-module) workers can't do.
    worker = new Worker("/pyodide-worker.js", { type: "module" });
    worker.onmessage = (event: MessageEvent<PythonRunResult & { id: number }>) => {
      const { id, ...result } = event.data;
      const resolve = pending.get(id);
      if (resolve) {
        pending.delete(id);
        resolve(result);
      }
    };
  }
  return worker;
}

export function isPyodideSupported(): boolean {
  return typeof window !== "undefined" && typeof Worker !== "undefined";
}

export function runPython(code: string): Promise<PythonRunResult> {
  return new Promise((resolve) => {
    const id = nextId;
    nextId += 1;
    pending.set(id, resolve);
    getWorker().postMessage({ id, code });
  });
}
