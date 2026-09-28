import { apiFetch, apiFetchBlob } from "../api-client";
import type { GeneratedFile } from "../types";

export async function listConversationFiles(conversationId: string): Promise<GeneratedFile[]> {
  const data = await apiFetch<{ files: GeneratedFile[] }>(`/chat/conversations/${conversationId}/files`);
  return data.files;
}

export async function downloadConversationFile(conversationId: string, fileId: string): Promise<Blob> {
  const blob = await apiFetchBlob(`/chat/conversations/${conversationId}/files/${fileId}`);
  if (!blob) throw new Error("Datei-Download lieferte keinen Inhalt.");
  return blob;
}

/** Fetches a generated file and triggers a normal browser "Save As" download - shared by the
 * Chat inline link and the Artifact Panel's Download button. Best-effort: a failed fetch here
 * isn't worth its own error UI. */
export async function triggerFileDownload(conversationId: string, fileId: string, filename: string): Promise<void> {
  try {
    const blob = await downloadConversationFile(conversationId, fileId);
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    URL.revokeObjectURL(url);
  } catch {
    // best-effort - see doc comment above
  }
}
