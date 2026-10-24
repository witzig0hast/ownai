"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { ErrorMessage } from "@/components/ErrorMessage";
import { ApiError } from "@/lib/api-client";
import * as chatApi from "@/lib/api/chat";
import * as visionApi from "@/lib/api/vision";

interface SharedPayload {
  title: string;
  text: string;
  url: string;
  image: Blob | null;
}

const SHARE_CACHE = "ownai-share"; // must match public/sw.js

/** Reads what the OS share sheet handed the installed app: from Cache Storage when the service
 * worker caught the POST (text + image), else from the query string (share-target/route.ts
 * fallback, text only). The cached copy is deleted once read, so a reload doesn't re-share. */
async function readSharedPayload(): Promise<SharedPayload | null> {
  const search = new URLSearchParams(window.location.search);
  const fromQuery = {
    title: search.get("title") ?? "",
    text: search.get("text") ?? "",
    url: search.get("url") ?? "",
    image: null,
  };
  if (typeof caches === "undefined") return fromQuery.title || fromQuery.text || fromQuery.url ? fromQuery : null;

  const cache = await caches.open(SHARE_CACHE);
  const metaResponse = await cache.match("/__share/meta");
  if (!metaResponse) return fromQuery.title || fromQuery.text || fromQuery.url ? fromQuery : null;
  const meta = (await metaResponse.json()) as { title: string; text: string; url: string; hasFile: boolean };
  const fileResponse = meta.hasFile ? await cache.match("/__share/file") : undefined;
  const image = fileResponse ? await fileResponse.blob() : null;
  await cache.delete("/__share/meta");
  await cache.delete("/__share/file");
  return { title: meta.title, text: meta.text, url: meta.url, image };
}

// Android often puts the link into `text` instead of `url` (e.g. "Schau mal https://...").
function extractUrl(payload: SharedPayload): string {
  if (payload.url) return payload.url;
  return payload.text.match(/https?:\/\/\S+/)?.[0] ?? "";
}

type Action = "discuss" | "summarize" | "expense";

export default function SharePage() {
  const router = useRouter();
  const [payload, setPayload] = useState<SharedPayload | null | undefined>(undefined);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let objectUrl: string | null = null;
    void (async () => {
      try {
        const p = await readSharedPayload();
        setPayload(p);
        if (p?.image) {
          objectUrl = URL.createObjectURL(p.image);
          setPreviewUrl(objectUrl);
        }
      } catch {
        setPayload(null);
      }
    })();
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, []);

  async function run(action: Action) {
    if (!payload) return;
    setError(null);
    try {
      const parts: string[] = [];
      if (payload.image) {
        setBusy("Bild wird gelesen...");
        const vision = await visionApi.describeImage(payload.image);
        if (vision.description) parts.push(`Bildbeschreibung: ${vision.description}`);
        if (vision.ocr_text) parts.push(`Text im Bild: "${vision.ocr_text}"`);
      }
      const url = extractUrl(payload);
      const shared = [payload.title, payload.text && payload.text !== url ? payload.text : "", url]
        .filter(Boolean)
        .join("\n");

      const intro =
        action === "expense"
          ? "Das ist ein Kassenbon/eine Rechnung. Erfasse den Gesamtbetrag als Ausgabe (mit passender Kategorie) und sag mir kurz, was du eingetragen hast."
          : action === "summarize"
            ? `Fasse diese Webseite für mich zusammen: ${url}`
            : "Ich habe dir etwas geteilt:";
      const message = [intro, action === "summarize" ? "" : shared, ...parts, note.trim() ? `Dazu: ${note.trim()}` : ""]
        .filter(Boolean)
        .join("\n\n");

      setBusy("OwnAI denkt nach...");
      const conversation = await chatApi.createConversation(null);
      await chatApi.sendMessage(conversation.id, message);
      router.replace(`/chat?c=${conversation.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Das hat nicht geklappt.");
      setBusy(null);
    }
  }

  const url = payload ? extractUrl(payload) : "";
  const buttonClass =
    "rounded-full px-4 py-2 text-sm font-medium transition-all hover:scale-105 active:scale-95 disabled:opacity-50 disabled:hover:scale-100";

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto p-4 sm:p-6">
        <div className="mx-auto w-full max-w-lg">
          <h1 className="mb-4 text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">Mit OwnAI teilen</h1>
          {payload === undefined ? (
            <p className="text-sm text-zinc-500">Lade...</p>
          ) : payload === null ? (
            <p className="text-sm text-zinc-500">
              Hier landet, was du aus einer anderen App mit „Teilen → OwnAI“ schickst (Android und
              Chrome/Edge am PC, wenn OwnAI als App installiert ist). Gerade wurde nichts geteilt.
            </p>
          ) : (
            <div className="flex flex-col gap-4">
              <div className="rounded-2xl border border-zinc-200 bg-white p-4 text-sm shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
                {previewUrl ? (
                  // eslint-disable-next-line @next/next/no-img-element -- local blob: preview, nothing to optimize
                  <img src={previewUrl} alt="Geteiltes Bild" className="mb-3 max-h-64 w-full rounded-xl object-contain" />
                ) : null}
                {payload.title ? <p className="font-medium text-zinc-900 dark:text-zinc-100">{payload.title}</p> : null}
                {payload.text && payload.text !== url ? (
                  <p className="whitespace-pre-wrap text-zinc-700 dark:text-zinc-300">{payload.text}</p>
                ) : null}
                {url ? <p className="mt-1 truncate text-indigo-600 dark:text-indigo-400">{url}</p> : null}
              </div>

              <textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                rows={2}
                placeholder="Optional: was soll OwnAI damit machen?"
                className="rounded-xl border border-zinc-300 px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900"
              />

              <ErrorMessage message={error} />

              <div className="flex flex-wrap gap-2">
                <button type="button" disabled={!!busy} onClick={() => run("discuss")} className={`${buttonClass} bg-indigo-500 text-white`}>
                  Im Chat besprechen
                </button>
                {url ? (
                  <button type="button" disabled={!!busy} onClick={() => run("summarize")} className={`${buttonClass} border border-zinc-300 text-zinc-700 dark:border-zinc-700 dark:text-zinc-300`}>
                    Webseite zusammenfassen
                  </button>
                ) : null}
                {payload.image ? (
                  <button type="button" disabled={!!busy} onClick={() => run("expense")} className={`${buttonClass} border border-zinc-300 text-zinc-700 dark:border-zinc-700 dark:text-zinc-300`}>
                    Als Ausgabe erfassen
                  </button>
                ) : null}
              </div>
              {busy ? <p className="text-sm text-zinc-500">{busy}</p> : null}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
