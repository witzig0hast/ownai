"use client";

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

export type Artifact =
  | { type: "file"; conversationId: string; fileId: string; filename: string; sizeBytes?: number }
  | { type: "code"; language: string; code: string };

interface ArtifactPanelContextValue {
  artifact: Artifact | null;
  isOpen: boolean;
  openArtifact: (artifact: Artifact) => void;
  close: () => void;
}

const ArtifactPanelContext = createContext<ArtifactPanelContextValue | null>(null);

/** Claude-style side panel state, shared across Chat and Voice: a generated file or a code
 * block "opens" here (right-side drawer, see components/ArtifactPanel.tsx) instead of being
 * dumped as raw text/links into the conversation - one provider at the AppShell level so both
 * screens can drive the same panel without prop-drilling. */
export function ArtifactPanelProvider({ children }: { children: ReactNode }) {
  const [artifact, setArtifact] = useState<Artifact | null>(null);
  const [isOpen, setIsOpen] = useState(false);

  const openArtifact = useCallback((next: Artifact) => {
    setArtifact(next);
    setIsOpen(true);
  }, []);

  const close = useCallback(() => setIsOpen(false), []);

  const value = useMemo(() => ({ artifact, isOpen, openArtifact, close }), [artifact, isOpen, openArtifact, close]);

  return <ArtifactPanelContext.Provider value={value}>{children}</ArtifactPanelContext.Provider>;
}

export function useArtifactPanel(): ArtifactPanelContextValue {
  const ctx = useContext(ArtifactPanelContext);
  if (!ctx) throw new Error("useArtifactPanel must be used within ArtifactPanelProvider");
  return ctx;
}
