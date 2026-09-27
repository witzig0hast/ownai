"use client";

import type { ReactNode } from "react";
import { NavBar } from "@/components/NavBar";
import { ProtectedRoute } from "@/components/ProtectedRoute";

/** Standard layout for authenticated pages: requires a session, then renders the nav + page
 * content. The Artifact Panel (see lib/artifactPanel.tsx) is provided at the root layout, not
 * here - pages call useArtifactPanel() from their own top-level body, which must be a
 * descendant of the provider, and AppShell (rendered inside the page, not around it) is too
 * low in the tree for that. */
export function AppShell({ children }: { children: ReactNode }) {
  return (
    <ProtectedRoute>
      <div className="flex min-h-full flex-1 flex-col">
        <NavBar />
        <main className="flex flex-1 flex-col overflow-hidden">{children}</main>
      </div>
    </ProtectedRoute>
  );
}
