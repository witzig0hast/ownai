"use client";

import { useEffect, type ReactNode } from "react";
import { NavBar } from "@/components/NavBar";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { warmupOnce } from "@/lib/warmup";

/** Standard layout for authenticated pages: requires a session, then renders the nav + page
 * content. The Artifact Panel (see lib/artifactPanel.tsx) is provided at the root layout, not
 * here - pages call useArtifactPanel() from their own top-level body, which must be a
 * descendant of the provider, and AppShell (rendered inside the page, not around it) is too
 * low in the tree for that. */
export function AppShell({ children }: { children: ReactNode }) {
  // Fires on every authenticated page, not just Chat/Voice - this way the LLM starts loading
  // the moment the user lands anywhere in the app (e.g. Settings), giving it a head start
  // before they actually reach Voice/Chat and expect a fast first reply. Deduped internally,
  // so navigating around doesn't spam Ollama with repeat warmup calls.
  useEffect(() => {
    warmupOnce().catch(() => {});
  }, []);

  return (
    <ProtectedRoute>
      <div className="flex min-h-full flex-1 flex-col">
        <NavBar />
        <main className="flex flex-1 flex-col overflow-hidden">{children}</main>
      </div>
    </ProtectedRoute>
  );
}
