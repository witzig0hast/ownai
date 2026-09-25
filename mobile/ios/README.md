# OwnAI — iPad Client

A SwiftUI (iOS/iPadOS 17+) client for the OwnAI backend. It's a pure client
surface: chat with the assistant, view/manage a CalDAV-backed calendar, and
review AI-generated suggestions that originate from your Android phone's
notifications. See `../../CONCEPT.md` and `../../DECISIONS.md` for the
overall project background, and `../../API.md` for the API contract this
app implements exactly.

## What's implemented

- **Auth** — Login and Register screens. Access + refresh tokens are stored
  in the **Keychain** (never `UserDefaults`). The networking layer
  transparently refreshes an expired access token on a `401` and retries
  the request once (`Sources/Networking/APIClient.swift`,
  `RefreshCoordinator.swift`); if the refresh token has also expired, the
  app logs the user out back to the login screen.
- **Chat** — `NavigationSplitView` with a conversation-list sidebar and a
  message-thread detail view, per API.md's synchronous (non-streaming)
  `POST /chat/conversations/{id}/messages`: sending a message shows a
  progress indicator ("OwnAI is thinking…") until the full reply (including
  any tool calls) comes back. Tool calls are shown as small badges above
  the assistant's reply.
- **Calendar** — Event list (`GET /calendar/events`, one month back to two
  months forward), a "Connect CalDAV" form (`POST /integrations/caldav`),
  and a "New Event" form (`POST /calendar/events`).
- **Suggestions** — Open suggestions list (`GET
  /notifications/suggestions?status=open`) with **Apply** / **Dismiss**
  actions (`POST /notifications/suggestions/{id}/apply|dismiss`).
- Tab-based navigation between Chat / Calendar / Suggestions, each with a
  **Log Out** action in its toolbar.

## Deliberate scope cuts (not oversights)

- **No notification/SMS listening on this app.** This is a hard platform
  restriction, not a missing feature: iOS sandboxes every app away from
  other apps' notifications and SMS, with no API for reading them — even
  for your own other apps. See `CONCEPT.md` §4. That's why suggestions are
  *generated on the Android phone* and only *reviewed* here.
- **No EventKit / local Calendar app sync.** This pass only talks to the
  backend's own CalDAV integration (`/integrations/caldav`,
  `/calendar/events`); it does not read or write the iPad's native
  Calendar app via EventKit. That's a reasonable, separate future
  enhancement (it would let events also show up in Apple Calendar/widgets),
  but it's out of scope here to keep the surface small: it needs its own
  permission flow, a conflict/merge story against the backend as the source
  of truth, and background-sync handling. Worth doing in a follow-up pass.
- **No voice (STT/TTS).** Explicitly deferred to a later phase per
  `DECISIONS.md` (#5).
- **No streaming chat.** `API.md` is explicit that v1 is synchronous only;
  streaming is a planned, backwards-compatible v2 addition (`stream=true`
  query param). The UI already isolates this behind `APIClient.sendMessage`,
  so adding streaming later is a localized change.

## Project structure

This project is generated with **[XcodeGen](https://github.com/yonaskolb/XcodeGen)**
from `project.yml` — there is no hand-written `.xcodeproj`/`project.pbxproj`
in this repo (that file format is an opaque, UUID-cross-referenced plist
that's very easy to corrupt by hand). `project.yml` is the source of truth;
the generated `.xcodeproj` and `Generated/Info.plist` are build artifacts
and are gitignored.

```
mobile/ios/
├── project.yml              # XcodeGen project spec (target, sources, Info.plist)
├── Sources/
│   ├── OwnAIApp.swift        # @main App entry point
│   ├── Config.swift          # API base URL configuration
│   ├── Networking/           # URLSession API client, Keychain, Codable models glue
│   ├── Models/                # Domain models (User, Conversation, ChatMessage, …)
│   ├── State/
│   │   └── AuthSession.swift # App-wide auth/session state (ObservableObject)
│   └── Features/
│       ├── Auth/              # Login / Register
│       ├── Root/               # Tab navigation + shared logout button
│       ├── Chat/                # Conversation list, thread, message bubble
│       ├── Calendar/            # Event list, connect-CalDAV form, new-event form
│       └── Suggestions/          # Suggestions list + apply/dismiss
└── Resources/
    └── Assets.xcassets/       # App icon + accent color placeholders
```

## Setup

One-time setup:

```bash
brew install xcodegen
cd mobile/ios
xcodegen generate
open OwnAI.xcodeproj
```

Re-run `xcodegen generate` any time `project.yml` changes (new source
files are picked up automatically by folder reference, so you generally
only need to re-run it when target settings or Info.plist keys change —
though re-running it is always safe).

Then build & run the `OwnAI` scheme on an iPad (or iPhone) Simulator, or a
device with Xcode's automatic signing.

### Pointing at a backend

By default the app targets `http://localhost:8000/api/v1`
(`Sources/Config.swift`), which works out of the box against a Simulator
if your backend is reachable at `localhost:8000` on your Mac (e.g. running
`docker compose up` from the repo root, or an SSH port-forward to the real
server).

To point at a real server instead:

1. **No code changes**: in Xcode, *Product ▸ Scheme ▸ Edit Scheme… ▸ Run ▸
   Arguments ▸ Environment Variables*, add `OWNAI_API_BASE_URL` set to the
   full base URL including `/api/v1`, e.g.
   `https://ownai.example.com/api/v1` or `http://192.168.1.50:8000/api/v1`.
2. **Or** edit `AppConfig.fallbackBaseURL` in `Sources/Config.swift`
   directly.

### HTTP during local development

iOS's App Transport Security (ATS) blocks plaintext HTTP by default.
`project.yml` configures two narrow exceptions for local development only:

- `NSExceptionDomains.localhost` — allows insecure HTTP to `localhost`
  (covers the Simulator-against-a-forwarded-backend default above).
- `NSAllowsLocalNetworking: true` — allows insecure HTTP to devices on
  your private/local network (e.g. `http://192.168.1.50:8000`), which is
  the supported mechanism for testing against a real server's LAN/Tailscale
  IP without setting up TLS.

Neither of these enables `NSAllowsArbitraryLoads` (which would allow HTTP
to *any* host). For anything beyond local development — and especially
before this ever leaves your own devices — put the backend behind HTTPS
(the repo's `docker-compose.yml`/Caddy setup) and these exceptions won't be
needed at all.

### Requirements

- Xcode 15+ (iOS/iPadOS 17 SDK)
- [XcodeGen](https://github.com/yonaskolb/XcodeGen) (`brew install xcodegen`)
- No third-party Swift packages are used — networking is plain
  `URLSession`/`async`-`await`, persistence is the Keychain via `Security`.

## Known limitations / things to double check on first build

This code was written and reviewed carefully but **could not be compiled**
in the environment it was written in (no macOS/Xcode toolchain available).
Everything has been re-read for syntax and API correctness, but if Xcode's
first build turns up an issue, these are the most likely spots:

- The exact date format the backend expects for the `start`/`end` **query
  parameters** on `GET /calendar/events` — `API.md` labels them `{date}`
  but the rest of the contract uses full ISO-8601 datetimes throughout, so
  `APIClient.events(start:end:)` sends full datetimes (e.g.
  `2026-09-25T00:00:00Z`) for consistency. If the backend expects a plain
  `yyyy-MM-dd` there instead, that's a one-line change in
  `Sources/Networking/APIClient.swift` (`events(start:end:)`).
- Minor SwiftUI API surface drift between Xcode versions (e.g.
  `ContentUnavailableView`, the zero-argument `onChange(of:)` overload) —
  all APIs used target iOS 17 and should be stable, but this is the kind of
  thing only a real compiler catches.
