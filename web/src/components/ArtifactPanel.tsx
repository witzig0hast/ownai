"use client";

import { useState } from "react";
import * as filesApi from "@/lib/api/files";
import { useArtifactPanel } from "@/lib/artifactPanel";
import { isPyodideSupported, runPython, type PythonRunResult } from "@/lib/pyodideRunner";

const PYTHON_LANGUAGES = new Set(["python", "py", "python3"]);

function CloseIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" aria-hidden="true">
      <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth={2} strokeLinecap="round" />
    </svg>
  );
}

function FileIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-10 w-10 text-zinc-400" aria-hidden="true">
      <path
        d="M6 3h9l3 3v15a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z"
        stroke="currentColor"
        strokeWidth={1.5}
        strokeLinejoin="round"
      />
      <path d="M14 3v4a1 1 0 0 0 1 1h4" stroke="currentColor" strokeWidth={1.5} strokeLinejoin="round" />
    </svg>
  );
}

function formatBytes(bytes?: number): string | null {
  if (bytes === undefined) return null;
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function FileArtifactView({
  conversationId,
  fileId,
  filename,
  sizeBytes,
}: {
  conversationId: string;
  fileId: string;
  filename: string;
  sizeBytes?: number;
}) {
  const [downloading, setDownloading] = useState(false);

  async function handleDownload() {
    setDownloading(true);
    try {
      await filesApi.triggerFileDownload(conversationId, fileId, filename);
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="flex flex-col items-center gap-4 p-8 text-center">
      <div className="flex h-20 w-20 items-center justify-center rounded-xl bg-zinc-100 dark:bg-zinc-800">
        <FileIcon />
      </div>
      <div>
        <p className="font-medium break-all text-zinc-900 dark:text-zinc-100">{filename}</p>
        {formatBytes(sizeBytes) ? (
          <p className="mt-1 text-xs text-zinc-500">{formatBytes(sizeBytes)}</p>
        ) : null}
      </div>
      <button
        type="button"
        onClick={handleDownload}
        disabled={downloading}
        className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-700 disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
      >
        {downloading ? "Lade herunter..." : "Herunterladen"}
      </button>
    </div>
  );
}

function CodeArtifactView({ language, code }: { language: string; code: string }) {
  const [running, setRunning] = useState(false);
  const [output, setOutput] = useState<PythonRunResult | null>(null);
  const canRun = PYTHON_LANGUAGES.has(language) && isPyodideSupported();

  async function handleRun() {
    setRunning(true);
    setOutput(null);
    try {
      setOutput(await runPython(code));
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="flex flex-col">
      <div className="flex items-center justify-between border-b border-zinc-200 px-4 py-2 dark:border-zinc-800">
        <span className="font-mono text-xs text-zinc-500">{language || "code"}</span>
        {canRun ? (
          <button
            type="button"
            onClick={handleRun}
            disabled={running}
            className="rounded bg-zinc-900 px-2.5 py-1 text-xs font-medium text-white transition-colors hover:bg-zinc-700 disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
          >
            {running ? "Läuft..." : "Ausführen"}
          </button>
        ) : null}
      </div>
      <pre className="overflow-x-auto bg-zinc-950 p-4 text-xs text-zinc-100">
        <code>{code}</code>
      </pre>
      {output ? (
        <div className="border-t border-zinc-200 p-4 font-mono text-xs dark:border-zinc-800">
          {output.stdout ? (
            <pre className="whitespace-pre-wrap text-zinc-700 dark:text-zinc-300">{output.stdout}</pre>
          ) : null}
          {output.stderr || output.error ? (
            <pre className="whitespace-pre-wrap text-red-600 dark:text-red-400">
              {output.stderr || output.error}
            </pre>
          ) : null}
          {output.result ? <pre className="whitespace-pre-wrap text-zinc-500">→ {output.result}</pre> : null}
          {!output.stdout && !output.stderr && !output.error && !output.result ? (
            <span className="text-zinc-400">Kein Output.</span>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

/** Claude-style right-side drawer for "results" (a generated file, a code block) - opened via
 * useArtifactPanel().openArtifact() from Chat/Voice instead of dumping a raw link/URL into the
 * conversation text. Mounted once in AppShell so it's available from every authenticated page. */
export function ArtifactPanel() {
  const { artifact, isOpen, close } = useArtifactPanel();

  const title = artifact?.type === "file" ? artifact.filename : artifact?.type === "code" ? "Code" : "";

  return (
    <>
      {/* Backdrop - only really needed on narrow screens where the panel covers the content,
          but harmless (transparent-ish, click-to-close) on wide screens too. */}
      <div
        className={`fixed inset-0 z-30 bg-black/20 transition-opacity duration-200 ${
          isOpen ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
        onClick={close}
        aria-hidden="true"
      />
      <aside
        role="dialog"
        aria-label={title || "Artefakt"}
        className={`fixed top-0 right-0 z-40 flex h-full w-full max-w-md transform flex-col border-l border-zinc-200 bg-white shadow-xl transition-transform duration-300 ease-out dark:border-zinc-800 dark:bg-zinc-950 ${
          isOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between border-b border-zinc-200 px-4 py-3 dark:border-zinc-800">
          <h2 className="truncate text-sm font-semibold text-zinc-700 dark:text-zinc-300">{title}</h2>
          <button
            type="button"
            onClick={close}
            aria-label="Schließen"
            className="rounded-md p-1 text-zinc-400 transition-colors hover:bg-zinc-100 hover:text-zinc-600 dark:hover:bg-zinc-800 dark:hover:text-zinc-300"
          >
            <CloseIcon />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto">
          {artifact?.type === "file" ? (
            <FileArtifactView
              conversationId={artifact.conversationId}
              fileId={artifact.fileId}
              filename={artifact.filename}
              sizeBytes={artifact.sizeBytes}
            />
          ) : artifact?.type === "code" ? (
            <CodeArtifactView language={artifact.language} code={artifact.code} />
          ) : null}
        </div>
      </aside>
    </>
  );
}
