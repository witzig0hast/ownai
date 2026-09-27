"use client";

import { useState } from "react";
import { useArtifactPanel } from "@/lib/artifactPanel";
import { isPyodideSupported, runPython, type PythonRunResult } from "@/lib/pyodideRunner";

const PYTHON_LANGUAGES = new Set(["python", "py", "python3"]);

function ExpandIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-3.5 w-3.5" aria-hidden="true">
      <path
        d="M9 4H4v5M15 4h5v5M4 15v5h5M20 15v5h-5"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function CodeBlock({ language, code }: { language: string; code: string }) {
  const [running, setRunning] = useState(false);
  const [output, setOutput] = useState<PythonRunResult | null>(null);
  const canRun = PYTHON_LANGUAGES.has(language) && isPyodideSupported();
  const { openArtifact } = useArtifactPanel();

  async function handleRun() {
    setRunning(true);
    setOutput(null);
    try {
      const result = await runPython(code);
      setOutput(result);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="my-2 overflow-hidden rounded-md border border-zinc-200 dark:border-zinc-700">
      <div className="flex items-center justify-between bg-zinc-100 px-3 py-1.5 dark:bg-zinc-800">
        <span className="font-mono text-xs text-zinc-500">{language || "code"}</span>
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => openArtifact({ type: "code", language, code })}
            title="Im Panel öffnen"
            className="rounded p-1 text-zinc-500 transition-colors hover:bg-zinc-200 hover:text-zinc-700 dark:text-zinc-400 dark:hover:bg-zinc-700 dark:hover:text-zinc-200"
          >
            <ExpandIcon />
          </button>
          {canRun ? (
            <button
              type="button"
              onClick={handleRun}
              disabled={running}
              title="Im Browser ausführen (Pyodide/WASM) - läuft komplett lokal, nichts erreicht den Server"
              className="rounded bg-zinc-900 px-2 py-0.5 text-xs font-medium text-white transition-colors hover:bg-zinc-700 disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
            >
              {running ? "Läuft..." : "Ausführen"}
            </button>
          ) : null}
        </div>
      </div>
      <pre className="overflow-x-auto bg-zinc-950 p-3 text-xs text-zinc-100">
        <code>{code}</code>
      </pre>
      {output ? (
        <div className="border-t border-zinc-200 bg-zinc-50 p-3 font-mono text-xs dark:border-zinc-700 dark:bg-zinc-900">
          {output.stdout ? (
            <pre className="whitespace-pre-wrap text-zinc-700 dark:text-zinc-300">{output.stdout}</pre>
          ) : null}
          {output.stderr || output.error ? (
            <pre className="whitespace-pre-wrap text-red-600 dark:text-red-400">
              {output.stderr || output.error}
            </pre>
          ) : null}
          {output.result ? (
            <pre className="whitespace-pre-wrap text-zinc-500">→ {output.result}</pre>
          ) : null}
          {!output.stdout && !output.stderr && !output.error && !output.result ? (
            <span className="text-zinc-400">Kein Output.</span>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
