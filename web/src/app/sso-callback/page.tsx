"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";

type Status = "working" | "linked" | "error";

/**
 * The backend's GET /auth/sso/callback (see app/api/sso.py) finishes the OIDC code exchange
 * server-side, then redirects the browser here in one of three shapes:
 *  - login success: tokens in the URL *fragment* (`#access_token=...&refresh_token=...`) - a
 *    fragment is never sent over the network to any server (including this page's own Next.js
 *    server render), only readable by client-side JS, so the tokens never land in a proxy/access
 *    log on this final hop.
 *  - link success (an already-logged-in user linked SSO to their account from Settings): just
 *    `?linked=1`, no tokens - the existing session is untouched.
 *  - either kind of failure: `?error=<code>&message=<text>` (plus `&context=link` for a failed
 *    link attempt) - rendered here instead of the raw JSON body a browser would otherwise show at
 *    the end of the redirect chain.
 */
export default function SsoCallbackPage() {
  const { loginWithTokens } = useAuth();
  const router = useRouter();
  const [status, setStatus] = useState<Status>("working");
  const [error, setError] = useState<string | null>(null);
  const [backHref, setBackHref] = useState("/login");

  useEffect(() => {
    void (async () => {
      const search = new URLSearchParams(window.location.search);

      const errorCode = search.get("error");
      if (errorCode) {
        setError(search.get("message") || "Unbekannter Fehler.");
        setBackHref(search.get("context") === "link" ? "/settings" : "/login");
        setStatus("error");
        return;
      }

      if (search.get("linked") === "1") {
        setStatus("linked");
        return;
      }

      const params = new URLSearchParams(window.location.hash.slice(1));
      const accessToken = params.get("access_token");
      const refreshToken = params.get("refresh_token");

      if (!accessToken || !refreshToken) {
        setError("Anmeldung unvollständig - bitte erneut versuchen.");
        setStatus("error");
        return;
      }

      try {
        await loginWithTokens(accessToken, refreshToken);
        router.replace("/voice");
      } catch {
        setError("Anmeldung fehlgeschlagen - bitte erneut versuchen.");
        setStatus("error");
      }
    })();
    // loginWithTokens/router are stable across this page's single effect run - the query string
    // and fragment are only ever present/meaningful on initial load.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex flex-1 items-center justify-center p-4">
      <div className="animate-scale-in w-full max-w-sm rounded-3xl border border-zinc-200 bg-white p-6 text-center shadow-lg dark:border-zinc-800 dark:bg-zinc-950">
        {status === "error" ? (
          <>
            <p className="mb-4 text-sm text-red-600 dark:text-red-400">{error}</p>
            <a href={backHref} className="text-sm font-medium text-zinc-900 underline dark:text-zinc-100">
              {backHref === "/settings" ? "Zurück zu den Einstellungen" : "Zurück zum Login"}
            </a>
          </>
        ) : status === "linked" ? (
          <>
            <p className="mb-4 text-sm text-zinc-900 dark:text-zinc-100">
              Konto erfolgreich mit SSO verknüpft.
            </p>
            <a href="/settings" className="text-sm font-medium text-zinc-900 underline dark:text-zinc-100">
              Zurück zu den Einstellungen
            </a>
          </>
        ) : (
          <p className="text-sm text-zinc-500">Anmeldung wird abgeschlossen...</p>
        )}
      </div>
    </div>
  );
}
