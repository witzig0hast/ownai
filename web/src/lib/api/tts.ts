import { apiFetch, apiFetchBlob } from "../api-client";

export async function listServerVoices(): Promise<string[]> {
  const data = await apiFetch<{ voices: string[] }>("/tts/voices");
  return data.voices;
}

/** Null when there's nothing to synthesize (empty text) - never actually returned in practice
 * since callers already skip empty text, kept for type-honesty with the 204 the backend can send. */
export function synthesizeSpeech(text: string, voice?: string): Promise<Blob | null> {
  return apiFetchBlob("/tts/speak", { text, voice });
}
