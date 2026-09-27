import { apiFetch } from "../api-client";

/** POST /voice/transcribe (multipart) — returns the transcribed text for a recorded audio clip. */
export async function transcribeVoice(audioBlob: Blob): Promise<string> {
  const formData = new FormData();
  const extension = audioBlob.type.includes("webm") ? "webm" : "audio";
  formData.append("audio", audioBlob, `clip.${extension}`);

  const data = await apiFetch<{ text: string }>("/voice/transcribe", {
    method: "POST",
    body: formData,
  });
  return data.text;
}
