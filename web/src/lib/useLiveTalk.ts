import { useEffect, useRef, useState } from "react";
import { ApiError } from "./api-client";
import * as chatApi from "./api/chat";
import { transcribeVoice } from "./api/voice";
import { speakAndWait, stopSpeaking } from "./tts";
import { pickMimeType } from "./useVoiceRecorder";

export type LiveTalkState = "idle" | "listening" | "transcribing" | "thinking" | "speaking";

// Energy-based voice activity detection over the mic's time-domain waveform. These
// constants are a reasonable starting point, not something verified against a real
// microphone/room in this environment (no browser with mic access here) - if turns cut
// off too early/late in practice, adjust VOLUME_THRESHOLD first.
const VOLUME_THRESHOLD = 0.045; // RMS amplitude (0..1) above which we consider it speech
const SILENCE_MS = 1200; // how long silence must persist after speech to end a turn
const MIN_SPEECH_MS = 300; // ignore blips shorter than this (clicks, breath noise)

interface EngineCallbacks {
  setState: (state: LiveTalkState) => void;
  setVolume: (volume: number) => void;
  setLastUserText: (text: string | null) => void;
  setLastAssistantText: (text: string | null) => void;
  setError: (message: string | null) => void;
  setMuted: (muted: boolean) => void;
}

/**
 * The hands-free voice loop as a plain class, not hook-body closures: listen -> detect
 * end of turn via silence -> transcribe -> send to the assistant -> speak the reply ->
 * listen again. Kept outside React's render cycle entirely (one instance per component,
 * held in a ref - see useLiveTalk below) so timing-sensitive, side-effecting code (the
 * requestAnimationFrame loop, MediaRecorder callbacks) never has to worry about stale
 * closures across re-renders or React's purity rules for render-body functions.
 */
class LiveTalkEngine {
  private sessionActive = false;
  private stream: MediaStream | null = null;
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private recorder: MediaRecorder | null = null;
  private chunks: BlobPart[] = [];
  private rafId: number | null = null;
  private conversationId: string | null = null;

  private speechStart: number | null = null;
  private silenceStart: number | null = null;
  private hasSpoken = false;
  private frameCount = 0;
  private muted = false;

  constructor(private callbacks: EngineCallbacks) {}

  async start(): Promise<void> {
    this.callbacks.setError(null);
    this.callbacks.setLastUserText(null);
    this.callbacks.setLastAssistantText(null);
    this.muted = false;
    this.callbacks.setMuted(false);

    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      this.callbacks.setError("Live Talk wird von diesem Browser nicht unterstützt.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.stream = stream;

      const audioContext = new AudioContext();
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 2048;
      source.connect(analyser);

      this.audioContext = audioContext;
      this.analyser = analyser;
      this.sessionActive = true;

      this.beginTurn();
    } catch {
      this.callbacks.setError("Mikrofonzugriff nicht möglich. Bitte Berechtigung im Browser erteilen.");
    }
  }

  stop(): void {
    this.sessionActive = false;
    this.conversationId = null;

    if (this.rafId !== null) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
    stopSpeaking();

    if (this.recorder && this.recorder.state !== "inactive") {
      this.recorder.onstop = null; // don't run the "start the next turn" logic on manual stop
      this.recorder.stop();
    }
    this.recorder = null;

    this.stream?.getTracks().forEach((track) => track.stop());
    this.stream = null;

    this.audioContext?.close().catch(() => {});
    this.audioContext = null;
    this.analyser = null;

    this.callbacks.setVolume(0);
    this.callbacks.setState("idle");
  }

  /** Mutes/unmutes the mic without ending the session - the audio track is simply disabled,
   * so voice-activity detection just sees silence and never ends a turn while muted, rather
   * than needing to pause/resume the whole recording+VAD state machine. */
  toggleMute(): void {
    this.muted = !this.muted;
    this.stream?.getAudioTracks().forEach((track) => {
      track.enabled = !this.muted;
    });
    this.callbacks.setMuted(this.muted);
  }

  /** Cuts off the assistant mid-reply and goes straight back to listening, instead of the
   * only previous option (end the whole session). speakAndWait's promise resolves on either
   * onend or onerror, and cancelling speech synthesis fires one of those either way, so
   * handleTurnRecorded's awaited speakAndWait call unblocks on its own and its `finally`
   * naturally starts the next turn - no extra state juggling needed here. */
  interrupt(): void {
    stopSpeaking();
  }

  private beginTurn(): void {
    if (!this.sessionActive || !this.stream) return;

    this.hasSpoken = false;
    this.speechStart = null;
    this.silenceStart = null;
    this.chunks = [];
    this.callbacks.setVolume(0);

    const mimeType = pickMimeType();
    const recorder = mimeType ? new MediaRecorder(this.stream, { mimeType }) : new MediaRecorder(this.stream);
    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) this.chunks.push(e.data);
    };
    recorder.onstop = () => {
      void this.handleTurnRecorded(recorder.mimeType || "audio/webm");
    };
    this.recorder = recorder;
    recorder.start();

    this.callbacks.setState("listening");
    this.rafId = requestAnimationFrame(this.tick);
  }

  /** Arrow property (not a method) so `this` stays bound when passed to requestAnimationFrame. */
  private tick = (): void => {
    if (!this.sessionActive || !this.analyser) return;
    const analyser = this.analyser;
    const data = new Uint8Array(analyser.fftSize);
    analyser.getByteTimeDomainData(data);

    let sumSquares = 0;
    for (let i = 0; i < data.length; i++) {
      const normalized = (data[i] - 128) / 128;
      sumSquares += normalized * normalized;
    }
    const rms = Math.sqrt(sumSquares / data.length);

    this.frameCount += 1;
    if (this.frameCount % 4 === 0) {
      this.callbacks.setVolume(Math.min(1, rms / 0.3));
    }

    const now = performance.now();
    if (rms > VOLUME_THRESHOLD) {
      if (this.speechStart === null) this.speechStart = now;
      this.silenceStart = null;
      if (!this.hasSpoken && now - this.speechStart > MIN_SPEECH_MS) {
        this.hasSpoken = true;
      }
    } else if (this.hasSpoken) {
      if (this.silenceStart === null) {
        this.silenceStart = now;
      } else if (now - this.silenceStart > SILENCE_MS) {
        this.callbacks.setState("transcribing");
        this.recorder?.stop(); // -> onstop -> handleTurnRecorded
        return; // don't schedule another frame; the next turn schedules its own
      }
    }

    this.rafId = requestAnimationFrame(this.tick);
  };

  private async ensureConversation(): Promise<string> {
    if (this.conversationId) return this.conversationId;
    // No title here (unlike earlier versions of this code): leaving it null lets the backend's
    // auto-titling generate a real title from the first exchange, same as typed chats, instead
    // of every Live Talk conversation being stuck showing the boring, identical "Live Talk".
    const conversation = await chatApi.createConversation(null);
    this.conversationId = conversation.id;
    return conversation.id;
  }

  private async handleTurnRecorded(mimeType: string): Promise<void> {
    const blob = new Blob(this.chunks, { type: mimeType });
    this.chunks = [];

    if (blob.size === 0 || !this.hasSpoken) {
      if (this.sessionActive) this.beginTurn();
      return;
    }

    try {
      const text = await transcribeVoice(blob);
      if (!text.trim()) {
        if (this.sessionActive) this.beginTurn();
        return;
      }
      this.callbacks.setLastUserText(text);
      this.callbacks.setState("thinking");

      const conversationId = await this.ensureConversation();
      const reply = await chatApi.sendMessage(conversationId, text);
      this.callbacks.setLastAssistantText(reply.content);

      if (!this.sessionActive) return; // stopped while we were waiting for the reply
      this.callbacks.setState("speaking");
      await speakAndWait(reply.content);
    } catch (err) {
      this.callbacks.setError(err instanceof ApiError ? err.message : "Etwas ist schiefgelaufen.");
    } finally {
      if (this.sessionActive) this.beginTurn();
      else this.callbacks.setState("idle");
    }
  }
}

interface UseLiveTalkResult {
  state: LiveTalkState;
  volume: number; // 0..1, smoothed mic level while listening - drives the UI animation
  lastUserText: string | null;
  lastAssistantText: string | null;
  error: string | null;
  isSupported: boolean;
  muted: boolean;
  start: () => Promise<void>;
  stop: () => void;
  toggleMute: () => void;
  interrupt: () => void;
}

/** React-facing wrapper around {@link LiveTalkEngine} - see the /voice screen for the UI this drives. */
export function useLiveTalk(): UseLiveTalkResult {
  const [state, setState] = useState<LiveTalkState>("idle");
  const [volume, setVolume] = useState(0);
  const [lastUserText, setLastUserText] = useState<string | null>(null);
  const [lastAssistantText, setLastAssistantText] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [muted, setMuted] = useState(false);

  const engineRef = useRef<LiveTalkEngine | null>(null);
  if (engineRef.current === null) {
    engineRef.current = new LiveTalkEngine({
      setState,
      setVolume,
      setLastUserText,
      setLastAssistantText,
      setError,
      setMuted,
    });
  }

  useEffect(() => {
    const engine = engineRef.current;
    return () => engine?.stop();
  }, []);

  const isSupported =
    typeof window !== "undefined" &&
    typeof navigator !== "undefined" &&
    typeof navigator.mediaDevices?.getUserMedia === "function" &&
    typeof window.AudioContext === "function";

  return {
    state,
    volume,
    lastUserText,
    lastAssistantText,
    error,
    isSupported,
    muted,
    start: () => engineRef.current!.start(),
    stop: () => engineRef.current!.stop(),
    toggleMute: () => engineRef.current!.toggleMute(),
    interrupt: () => engineRef.current!.interrupt(),
  };
}
