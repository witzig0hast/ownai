# OwnAI Web

Next.js (App Router, TypeScript, Tailwind CSS) client for OwnAI — the PC-facing
surface for chat, voice, calendar, Home Assistant and Android-notification
suggestions. See the root
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
  the first thing to adjust. `useLiveTalk` also exposes `lastToolCalls`/`conversationId`
  now (not just `lastAssistantText`) so Voice can show a file/code Artifact Panel button
  for a `create_file` result or a fenced code block in the reply instead of leaving a raw
  technical path in the displayed/spoken text — a real bug a user hit in practice (the
  reply mentioned an internal `/api/v1/...` download URL out loud). The backend now also
  strips such paths from the reply as a hard guarantee (see backend/README.md's
  `_strip_internal_urls`), so this is defense in depth, not the only fix.
- **Artifact Panel** (`src/lib/artifactPanel.tsx` + `src/components/ArtifactPanel.tsx`): a
  Claude-style right-side drawer, provided once at the root layout (`src/app/layout.tsx`), not
  in `AppShell` — a page-level component that calls `useArtifactPanel()` in its own top-level
  body (Voice does) must have the provider as an ANCESTOR of the whole page, and `AppShell` is
  rendered *inside* the page's returned JSX, not around it, so putting the provider there was a
  real bug caught by `next build`'s prerender step (`useArtifactPanel must be used within
  ArtifactPanelProvider`) before it ever reached a browser. Generated files (`create_file` tool
  results) and code blocks now "open" here — a file shows an icon/name/size + Download button,
  code shows the language + Ausführen button + output — instead of a raw link/URL dumped into
  the conversation text. Used from both Chat (file chip buttons on tool_calls, an expand icon on
  `CodeBlock`) and Voice (see below). Verified live: seeded a message with both a file and a
  code block, opened each in the panel, downloaded the file via a real browser download event.
- **Chat** (`/chat`): conversation sidebar (`GET /chat/conversations`,
  create via `POST /chat/conversations`), message thread
  (`GET .../messages`), and a synchronous send flow (`POST .../messages`)
  with an animated three-dot "thinking" indicator (`.animate-typing-dot` in
  `globals.css`), since v1 has no streaming. The user's own message is
  rendered optimistically (the API only returns the new assistant message,
  per `API.md`). Visual pass (user asked for something closer to Claude's
  look): assistant messages get a small circular avatar, bubbles are
  `rounded-2xl` with a shadow instead of flat `rounded-lg`, each message has
  a subtle fade/slide-in (`.animate-message-in`) and a timestamp underneath,
  and the composer is a single pill-shaped container (image/mic/send buttons
  as circular icons inside it, not separate boxed buttons) with a textarea
  that auto-grows with content up to `max-h-40` instead of a fixed 2-row box.
  - **Code Interpreter**: a message's content is split into text/code segments
    (`src/lib/parseMessageContent.ts`, looks for ```` ```lang\n...\n``` ```` fences) and a
    Python code block gets an "Ausführen" button (`src/components/CodeBlock.tsx`). Execution
    runs entirely in-browser via Pyodide (WASM Python) inside a dedicated module Web Worker
    (`public/pyodide-worker.js` + `src/lib/pyodideRunner.ts`) — no server round-trip, no
    filesystem/network access beyond the WASM sandbox itself, so nothing the code does can
    touch the host in any way. The Pyodide runtime is vendored into `public/pyodide/` at
    install/build time (`scripts/copy-pyodide-assets.mjs`, from the pinned `pyodide` npm
    package) rather than fetched from a CDN, keeping this fully self-hosted. **Must be loaded
    as a module worker** (`new Worker(url, { type: "module" })`) — newer Pyodide releases
    dropped classic-worker/`importScripts` support, which was a real bug found and fixed
    while verifying this live (a classic worker threw `"Classic web workers are not
    supported"`). Verified live end-to-end: seeded an assistant message with a
    ```` ```python ```` block, clicked "Ausführen", got the correct `stdout` back.
- **Calendar** — no longer a standalone top-level page. Moved into Settings →
  Kalender (`src/components/settings/CalendarTab.tsx`) per user request, with an
  on/off toggle (`ownai.calendarEnabled` in localStorage, per-viewer preference,
  defaults on) above the same event list/create form the old `/calendar` page had
  (`GET/POST /calendar/events`). Turning it off just hides the view - the CalDAV
  connection itself is untouched.
- **Suggestions** (`/suggestions`): open suggestions
  (`GET /notifications/suggestions?status=open`), with Apply/Dismiss buttons
  (`POST .../{id}/apply` / `.../dismiss`) that remove the item from the list
  on success. Only useful with the Android app (it's the sole source of
  suggestions), so both the NavBar link and the page's real content are gated
  on `GET /devices` returning at least one `platform: "android"` device — a
  web-only account sees neither the nav link nor a confusing "always empty"
  page, just a short explanation instead.
- **Settings** (`/settings`): a tabbed page (`src/app/settings/page.tsx`) — room to grow
  as more per-user configuration gets added (the user explicitly asked for "alles
  einstellen können" in one place). Currently five tabs (Integrations, Kalender, E-Mail, Agent
  Bus, Konto) - the tab bar scrolls horizontally on narrow screens rather than wrapping, since
  more tabs keep getting added:
  - **Integrations** tab (`src/components/settings/IntegrationsTab.tsx`, the former
    `/integrations` page): a small grid of tiles (icon, name, status dot), one per
    connectable service — Calendar (CalDAV, `POST /integrations/caldav`) and Home
    Assistant (`POST /integrations/home-assistant`) — matching the "Add Integration" card
    style of tools like Home Assistant itself, rather than always-expanded forms. Tapping a
    tile opens its connect form in a popup (`src/components/Modal.tsx`). Status (Verbunden /
    Nicht verbunden / Fehler) is inferred by probing the corresponding list endpoint and
    checking for the `..._not_connected` error code, since neither integration has a
    dedicated status endpoint — see `API.md`. Home Assistant devices themselves aren't
    managed here beyond connecting: controlling them (lights, switches, ...) happens
    conversationally through Chat/Voice via the backend's LLM tools. Also has a floating
    chat button that opens `SetupHelperChat` (`src/components/SetupHelperChat.tsx`) in a
    popup — a small chat scoped to its own dedicated conversation ("Integrations-Hilfe")
    that answers setup questions ("wo finde ich meine CalDAV-URL?") using the same OwnAI
    assistant as regular chat, just kept out of the normal history.
  - **Kalender** tab (`src/components/settings/CalendarTab.tsx`): the former `/calendar` page,
    moved here per user request with an on/off toggle above it (see the Calendar bullet above).
  - **E-Mail** tab (`src/components/settings/EmailTab.tsx`): connect a personal SMTP account
    (`POST /integrations/email`) for the `send_email` tool to use instead of the system-wide
    default — same form/status-probe pattern as the Integrations tab.
  - **Agent Bus** tab (`src/components/settings/AgentBusTab.tsx`): register/remove external
    agents (`GET/POST/DELETE /agent-bus/agents`) — the API key is shown exactly once right
    after registration, in a dismissable callout, then never again (only its hash is stored
    server-side). Below that, a full message log (`GET /agent-bus/messages`) shows every
    exchange (from/to/kind/content/status/time) across all of the account's agents. Verified
    live: registered an agent, sent a real message through its API key via `curl`, confirmed
    it showed up in the log table.
  - **Konto** tab (`src/components/settings/AccountTab.tsx`): read-only account info (name,
    email, admin badge) plus a Push-Benachrichtigungen enable/disable toggle
    (`src/lib/push.ts`) — requests notification permission, registers the Service Worker
    (`public/sw.js`), subscribes via the Push API and registers the subscription with the
    backend (`POST /push/subscribe`). States the iOS "must be installed to Home Screen"
    caveat directly in the UI.
- **Admin** (`/admin`, only shown/reachable for `user.is_admin`): the first user ever to
  register becomes admin automatically (see `API.md`'s Admin section) and gets a toggle
  for open registration (`PATCH /admin/settings`), a global "pause the system" switch with
  an optional reason shown to users (blocks only `POST .../messages`, i.e. actual LLM
  traffic — login, calendar, Home Assistant, timers etc. stay usable, including for the
  admin themself, so a paused system can never lock out its own admin), and a read-only
  user list (`GET /admin/users`). Client-side redirects a logged-in non-admin straight to
  `/voice` if they somehow land on the URL — the backend's `require_admin` dependency is
  the actual enforcement, this is just UX.
- **Timers** (`src/components/TimerBadge.tsx`, shown in the nav bar on every page — "oben
  rechts in der Ecke"): timers themselves are set/cancelled by the LLM through chat/voice
  (`set_timer`/`cancel_timer` tool calls, see `API.md`) — this badge's job is just to show
  them. Polls `GET /timers` every 20s (picks up a timer set from any device/conversation)
  and ticks the nearest one down locally every second; on expiry, a short synthesized beep,
  a browser `Notification` if permitted, and a visible alert state with a dismiss button
  (`POST /timers/{id}/cancel`). Hidden entirely when there are no active timers. Client-only
  by design — only fires while the tab is open; see `mobile/android/README.md`'s
  `alarm/` section for how Android covers the "app isn't open" case via a local
  `AlarmManager` alarm instead.
- Shared nav (Voice / Chat / Calendar / Suggestions / Settings, plus Admin for admins) +
  logout, route protection via a client-side `ProtectedRoute` guard that redirects
  unauthenticated users to `/login`.
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
- **Voice picker** (`src/components/VoicePicker.tsx`, shown on `/voice` and in
  `/chat`'s toolbar): the browser/OS often ships several `speechSynthesis`
  voices of wildly different quality (e.g. a low-quality offline
  espeak/Piper-style voice alongside better ones) — this enumerates every
  voice the platform reports (`src/lib/tts.ts`'s `getVoices()`, handling the
  async `voiceschanged` event some browsers need), lets the user pick one,
  persists the choice in `localStorage`, and plays a short sample on
  selection. Applied automatically everywhere replies are read aloud
  (`speak`/`speakAndWait`), including the Live Talk loop.

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
- Integration status badges on `/settings`'s Integrations tab are inferred by probing the
  corresponding list endpoint rather than a dedicated status endpoint (see
  the "Settings" bullet above) — accurate, but means an extra request on
  page load.
- No way to disconnect/remove a Home Assistant or CalDAV connection from the
  UI once set — only connect/reconnect. Neither `API.md` nor the backend
  currently expose a delete endpoint for either.
- Home Assistant device control has no dedicated UI beyond the connect form
  on `/integrations` — using it (turning lights on/off, etc.) happens
  conversationally through Chat/Voice via the backend's LLM tools, not
  through a device list/toggle screen.
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
