"use client";

import type { ReactNode } from "react";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { NavBar } from "@/components/NavBar";

/** Standard layout for authenticated pages: requires a session, then renders the nav + page content. */
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
