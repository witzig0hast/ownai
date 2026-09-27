import { useCallback, useRef, useState } from "react";
import { ApiError } from "./api-client";
import { transcribeVoice } from "./api/voice";

function pickMimeType(): string | undefined {
  if (typeof MediaRecorder === "undefined") return undefined;
  const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg"];
  return candidates.find((type) => MediaRecorder.isTypeSupported(type));
}

/**
 * Records a short voice clip via the browser's MediaRecorder API and sends it to
 * POST /voice/transcribe. Recording format depends on what the browser supports
 * (webm/opus on Chrome/Edge, mp4/aac on Safari) — the backend decodes whatever
 * arrives via ffmpeg, so no specific format is required here.
 */
export function useVoiceRecorder() {
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const streamRef = useRef<MediaStream | null>(null);

  const startRecording = useCallback(async () => {
    setError(null);
    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      setError("Sprachaufnahme wird von diesem Browser nicht unterstützt.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mimeType = pickMimeType();
      const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      mediaRecorderRef.current = recorder;
      recorder.start();
      setIsRecording(true);
    } catch {
      setError("Mikrofonzugriff nicht möglich. Bitte Berechtigung im Browser erteilen.");
    }
  }, []);

  /** Stops recording, uploads the clip, and resolves with the transcribed text (or null on failure). */
  const stopRecording = useCallback((): Promise<string | null> => {
    return new Promise((resolve) => {
      const recorder = mediaRecorderRef.current;
      if (!recorder) {
        resolve(null);
        return;
      }

      recorder.onstop = async () => {
        setIsRecording(false);
        streamRef.current?.getTracks().forEach((track) => track.stop());
        streamRef.current = null;

        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        chunksRef.current = [];
        mediaRecorderRef.current = null;

        if (blob.size === 0) {
          resolve(null);
          return;
        }

        setIsTranscribing(true);
        try {
          const text = await transcribeVoice(blob);
          resolve(text);
        } catch (err) {
          setError(err instanceof ApiError ? err.message : "Transkription fehlgeschlagen.");
          resolve(null);
        } finally {
          setIsTranscribing(false);
        }
      };

      recorder.stop();
    });
  }, []);

  const cancelRecording = useCallback(() => {
    const recorder = mediaRecorderRef.current;
    if (recorder) {
      recorder.onstop = null;
      recorder.stop();
    }
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    mediaRecorderRef.current = null;
    chunksRef.current = [];
    setIsRecording(false);
  }, []);

  return { isRecording, isTranscribing, error, startRecording, stopRecording, cancelRecording };
}
