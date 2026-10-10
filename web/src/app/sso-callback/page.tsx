"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";

/**
 * The backend's GET /auth/sso/callback (see app/api/sso.py) finishes the OIDC code exchange
 * server-side, then 307-redirects the browser here with the issued OwnAI tokens in the URL
 * *fragment* (`#access_token=...&refresh_token=...`), not the query string - a fragment is
 * never sent over the network to any server (including this page's own Next.js server render),
 * only readable by client-side JS, so the tokens never land in a proxy/access log on this final
 * hop. This page's only job is to read that fragment once and hand it to the same
 * loginWithTokens() that normal password login uses, then get out of the way.
 */
export default function SsoCallbackPage() {
  const { loginWithTokens } = useAuth();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      const params = new URLSearchParams(window.location.hash.slice(1));
      const accessToken = params.get("access_token");
      const refreshToken = params.get("refresh_token");

      if (!accessToken || !refreshToken) {
        setError("Anmeldung unvollständig - bitte erneut versuchen.");
        return;
      }

      try {
        await loginWithTokens(accessToken, refreshToken);
        router.replace("/voice");
      } catch {
        setError("Anmeldung fehlgeschlagen - bitte erneut versuchen.");
      }
    })();
    // loginWithTokens/router are stable across this page's single effect run - the fragment is
    // only ever present/meaningful on initial load.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex flex-1 items-center justify-center p-4">
      <div className="animate-scale-in w-full max-w-sm rounded-3xl border border-zinc-200 bg-white p-6 text-center shadow-lg dark:border-zinc-800 dark:bg-zinc-950">
        {error ? (
          <>
            <p className="mb-4 text-sm text-red-600 dark:text-red-400">{error}</p>
            <a
              href="/login"
              className="text-sm font-medium text-zinc-900 underline dark:text-zinc-100"
            >
              Zurück zum Login
            </a>
          </>
        ) : (
          <p className="text-sm text-zinc-500">Anmeldung wird abgeschlossen...</p>
        )}
      </div>
    </div>
  );
}
