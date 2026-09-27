# OwnAI Web

Next.js (App Router, TypeScript, Tailwind CSS) client for OwnAI — the PC-facing
surface for chat, calendar and Android-notification suggestions. See the root
[`CONCEPT.md`](../CONCEPT.md), [`DECISIONS.md`](../DECISIONS.md) and, most
importantly, [`API.md`](../API.md) (the binding contract this app was built
against).

## Running locally

```bash
cd web
npm install
cp .env.example .env.local   # adjust NEXT_PUBLIC_API_BASE_URL if needed
npm run dev
```

Opens on `http://localhost:3000`. It expects the backend at
`NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000/api/v1`) to be
reachable; without it, every page will show its "failed to load" error state
after login (auth pages still render, but requests will fail).

## Environment variables

| Variable | Default | Notes |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000/api/v1` | Backend base URL, **including** the `/api/v1` prefix. Read from `.env.local` in dev. |

`NEXT_PUBLIC_*` variables are inlined into the client JS bundle by Next.js
**at build time**, not read at container start. This matters for Docker: see
"Docker & the `NEXT_PUBLIC_API_BASE_URL` gotcha" below.

## Scripts

- `npm run dev` — dev server (Turbopack, hot reload)
- `npm run build` — production build (`output: "standalone"`, see `next.config.ts`)
- `npm run start` — run the production build (`next start`)
- `npm run lint` — ESLint (flat config; `next lint` was removed in Next.js 16)

Verified in this environment: `npm install`, `npm run build` and
`npm run lint` all pass cleanly. There is no backend running here, so no live
end-to-end requests were made — the networking code was written and reviewed
directly against `API.md` (method, path, request/response field names, and
the `{"error":{"code","message"}}` envelope).

## What's implemented

- **Auth**: `/login`, `/register`. `POST /auth/register` then `/auth/login`,
  tokens stored client-side, `GET /users/me` to hydrate the profile.
- **Fetch wrapper** (`src/lib/api-client.ts`): attaches
  `Authorization: Bearer <token>`, and on a `401` calls `POST /auth/refresh`
  once (de-duplicated across concurrent requests) and retries the original
  request; if refresh also fails, clears the session and hard-redirects to
  `/login`. Throws `ApiError` (`code`, `message`, `status`) parsed from the
  backend's error envelope.
- **Live Talk / Voice** (`/voice`, the landing page after login): a fully hands-free
  voice conversation loop — `src/lib/useLiveTalk.ts` (`LiveTalkEngine`, a plain class
  held in a ref, not hook-body closures — see the file's comment for why: React's
  compiler-era `react-hooks/purity` lint rule flags timing-sensitive code like a
  `requestAnimationFrame` loop when it's written as plain functions inside a hook body,
  since it can't prove they never run during render). Tap once to start; the loop is
  listen → detect end-of-turn via energy-based voice-activity detection (silence after
  speech, ~1.2s) → `POST /voice/transcribe` → `POST /chat/conversations/{id}/messages`
  → speak the reply (`speakAndWait` in `src/lib/tts.ts`) → listen again, with no buttons
  in between. A big animated circle (`src/app/voice/page.tsx`) shows the current phase
  (listening/transcribing/thinking/speaking) and pulses with live mic volume while
  listening; the last exchange is shown as text below it for confirmation, not a
  scrolling message list — this is the "helpful agent" surface, deliberately not styled
  as a chat thread. Auto-creates its own conversation per session
  (`POST /chat/conversations`) so it doesn't interleave with regular `/chat` history.
  **Not verified against a real microphone/room** in this environment (no browser with
  mic access here) — the VAD silence/volume thresholds in `useLiveTalk.ts` are a
  reasonable starting point, not tuned; if turns cut off too early or drag on, that's
  the first thing to adjust.
- **Chat** (`/chat`): conversation sidebar (`GET /chat/conversations`,
  create via `POST /chat/conversations`), message thread
  (`GET .../messages`), and a synchronous send flow (`POST .../messages`)
  with a "Thinking..." loading state, since v1 has no streaming. The user's
  own message is rendered optimistically (the API only returns the new
  assistant message, per `API.md`).
- **Calendar** (`/calendar`): upcoming events for a date range
  (`GET /calendar/events?start&end`), a "Connect CalDAV" form
  (`POST /integrations/caldav`), and a "New event" form
  (`POST /calendar/events`).
- **Suggestions** (`/suggestions`): open suggestions
  (`GET /notifications/suggestions?status=open`), with Apply/Dismiss buttons
  (`POST .../{id}/apply` / `.../dismiss`) that remove the item from the list
  on success.
- Shared nav (Voice / Chat / Calendar / Suggestions) + logout, route protection via
  a client-side `ProtectedRoute` guard that redirects unauthenticated users
  to `/login`.
- **Push-to-talk in Chat** (`/chat`, separate from the Live Talk screen above): a mic
  button (`src/lib/useVoiceRecorder.ts`, browser
  `MediaRecorder` API) records a clip, uploads it to `POST /voice/transcribe`
  (multipart — see `API.md`), and fills the message input with the
  transcript for you to review/edit before sending (never auto-sent, in case
  the transcription is off). Only shown when the browser supports
  `getUserMedia` — iPad/Windows/Android browsers all do; needs an HTTPS or
  `localhost` origin (browsers block mic access on plain HTTP otherwise).
  Text-to-speech (`src/lib/tts.ts`) reads assistant replies aloud via the
  browser's native `speechSynthesis` — a speaker icon on each reply for a
  one-off read, or a persistent "auto-read replies" checkbox (per-viewer
  preference, stored in `localStorage`). Both run entirely client-side/
  on-device: STT goes to your own self-hosted Whisper (see root
  `DECISIONS.md`), TTS never leaves the browser at all.

## Installing as an app (PWA)

This is the primary client for iPad and Windows PC (see root `DECISIONS.md`,
decisions #3/#7/#8: no Mac available for a native iPad build, no
publication/App Store wanted). `public/manifest.webmanifest` plus the
`metadata`/`viewport` exports in `src/app/layout.tsx` make it installable as
a standalone app instead of a browser tab:

- **iPad (Safari)**: open the site, tap Share → "Add to Home Screen". Launches
  full-screen with the OwnAI icon, no address bar.
- **Windows (Edge or Chrome)**: open the site, click the install icon in the
  address bar (or menu → "Apps" / "Install OwnAI"). Runs in its own window
  with a taskbar icon, like a native app.

Icons are placeholder art generated for this pass
(`public/icon-192.png`, `public/icon-512.png`, `public/apple-touch-icon.png`,
`public/favicon-32.png`) — swap them for real branding whenever you want,
same filenames.

## Auth storage: localStorage vs. httpOnly-cookie proxy

**Chosen: localStorage**, for both the access and refresh token
(`src/lib/auth-storage.ts`).

- **Why**: OwnAI is a single-user, self-hosted personal tool, not a
  multi-tenant SaaS product. A plain SPA reading/writing tokens directly is
  simple, has no extra moving parts, and matches the "keep it simple and
  correct" brief. The alternative — httpOnly cookies — requires routing
  *every* backend call through Next.js API routes (or middleware) acting as
  a proxy, so the browser never sees the token. That's meaningfully more
  code (a proxy route per backend endpoint, or a generic passthrough proxy
  that still has to special-case the refresh flow) for a project whose
  server is already reached only over a private VPN mesh or a hardened
  reverse proxy (see `CONCEPT.md`/`DECISIONS.md`), which is the primary
  defense for this deployment.
- **Trade-off accepted**: tokens in `localStorage` are readable by any JS
  that runs on the page, so a successful XSS against this app can exfiltrate
  the session (15 min access token + 30 day refresh token). There is no
  first-party or third-party script inclusion in this app to make that a
  live risk today, but it's the honest cost of this choice.
- **If this ever becomes multi-user or internet-facing**, switch to httpOnly
  cookies set by a Next.js Route Handler that proxies `/auth/*` and stamps
  the cookie, plus a `proxy.ts` (Next 16's renamed `middleware.ts`) that
  forwards the cookie as a bearer header to the backend for all other
  routes. That removes token-in-JS exposure at the cost of the extra proxy
  layer described above.

## Docker

`Dockerfile` is a 3-stage build (`deps` → `builder` → `runner`) using
`output: "standalone"` (set in `next.config.ts`) so the final image only
ships the traced runtime files, not the full `node_modules`. It runs as a
non-root user and starts with `node server.js` on port 3000, matching what
the root `docker-compose.yml`'s `web` service (`build: context: ./web`)
expects.

**Not verified with a live `docker build`** in this session — there is no
Docker daemon available in this sandbox (see `DECISIONS.md`'s note on
container limitations for this pass). The image follows Next.js's official
`output: "standalone"` Docker pattern; please run `docker compose build web`
once on your own machine to confirm.

### `NEXT_PUBLIC_API_BASE_URL` gotcha

`NEXT_PUBLIC_*` values are baked into the client bundle at `next build` time,
not read from the environment at container start. The root
`docker-compose.yml` currently sets `NEXT_PUBLIC_API_BASE_URL` under the
`web` service's `environment:`, which only affects the **running container's
process env** — it has **no effect on the already-built client bundle**.

The `Dockerfile` accepts the same variable as a **build arg** with a working
default:

```bash
docker compose build --build-arg NEXT_PUBLIC_API_BASE_URL=https://your-domain/api/v1 web
```

If you don't override it, the image builds with the default
`http://localhost:8000/api/v1`, which is wrong for anything but local dev
against a backend on the same machine. Either:

- pass `--build-arg` as above when building for your real domain, or
- (better, if you want `docker compose up` alone to be correct) wire
  `NEXT_PUBLIC_API_BASE_URL` as a build arg in the root `docker-compose.yml`
  (`build.args`) instead of (or in addition to) `environment` — left as-is
  here since editing files outside `web/` was out of scope for this pass.

## Known gaps / TODOs

- **Live Talk's VAD thresholds are untuned** (see the "Live Talk / Voice" bullet
  above) — needs a real microphone/room to dial in.
- Live Talk has no interrupt-while-speaking (tap the orb to cut off a reply early) —
  you wait for the full reply to finish playing before the next turn starts listening.
- No Android equivalent of Live Talk yet — Android has push-to-talk + TTS (see
  `mobile/android/README.md`), not the hands-free loop.
- No streaming chat (matches `API.md` v1 — `stream=true` is a documented
  future extension that currently 501s).
- No token-expiry countdown/UI warning; refresh is fully transparent unless
  the refresh token itself is invalid/expired, in which case the user is
  bounced to `/login`.
- Calendar event editing/deleting isn't in `API.md` yet, so it isn't in the
  UI either (only list + create).
- No CalDAV connection status indicator beyond a one-time "Connected."
  message after a successful `POST /integrations/caldav` — the API doesn't
  expose a "get current connection status" endpoint to check.
- No pagination for conversations/messages/events/suggestions lists — the
  API responses aren't documented as paginated, so none was added.
- **Mic button needs a secure context.** `getUserMedia` is blocked by
  browsers on plain `http://` origins other than `localhost` — on
  `http://<server-ip>:<port>` (no Caddy/HTTPS yet) the mic button won't
  appear at all (the code detects this and hides it rather than showing a
  broken button, but the feature is simply unavailable until the app is
  served over HTTPS or accessed as `localhost`). See root
  `GETTING_STARTED.md` step 6 for the Caddy+HTTPS option.
- Not tested end-to-end against a live backend (none was running in this
  environment); verified via `npm run build` + `npm run lint` plus a careful
  read of `API.md` for every request/response shape.
