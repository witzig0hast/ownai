import { apiFetch, apiFetchBlob } from "../api-client";
import type { GeneratedFile } from "../types";

export async function listConversationFiles(conversationId: string): Promise<GeneratedFile[]> {
  const data = await apiFetch<{ files: GeneratedFile[] }>(`/chat/conversations/${conversationId}/files`);
  return data.files;
}

export function downloadConversationFile(conversationId: string, fileId: string): Promise<Blob> {
  return apiFetchBlob(`/chat/conversations/${conversationId}/files/${fileId}`);
}
