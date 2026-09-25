# OwnAI – Android client

Kotlin + Jetpack Compose client for OwnAI (see the repo root `CONCEPT.md`, `DECISIONS.md`
and the binding `API.md` contract). This is the one client that is Android-only by
platform necessity: it is the device that reads incoming notifications/SMS and forwards
them to the backend (iOS does not allow any app to read other apps' notifications).

## ⚠️ This code has not been compiled

The container this was written in has **no Android SDK** (see the repo root
`DECISIONS.md`). Every file was written and re-read carefully, but nothing here has
actually gone through `javac`/`kotlinc`/AAPT. **Open this folder in Android Studio and
build it once (`Build > Make Project` or `./gradlew assembleDebug`) before relying on
it.** See "Things I'm not 100% sure about" at the end of this file for the specific
spots most worth a second look if the build fails.

## What's implemented

- **Auth** (`ui/auth/`): Login and Register screens against `POST /auth/login` /
  `POST /auth/register`. Access + refresh tokens are stored in
  `EncryptedSharedPreferences` (`data/local/SecurePrefs.kt`). `data/remote/AuthInterceptor.kt`
  attaches `Authorization: Bearer <token>` to every request except `/auth/*` and
  `/notifications/ingest`; `data/remote/TokenAuthenticator.kt` is an OkHttp
  `Authenticator` that transparently calls `POST /auth/refresh` on a 401 and retries,
  logging the user out (clearing tokens, flipping `SessionManager`) if the refresh
  token itself is rejected or missing.
- **Device registration** (`data/repository/DeviceRepository.kt`): on the first
  successful login, calls `POST /devices/register` with `platform: "android"` and
  persists the returned `device_api_key` into `EncryptedSharedPreferences` immediately
  (it is only ever returned once by the API). Registration only runs once - if it fails,
  it's retried on the next fresh login (see "Known limitations" below).
- **Chat** (`ui/chat/`): conversation list, a message thread with a text input, and a
  loading indicator while a message is in flight. `POST /chat/conversations/{id}/messages`
  is synchronous per `API.md` (no streaming in v1), so the screen just shows a spinner
  until the reply comes back. The user's own message is shown immediately (added
  locally); the response only contains the assistant's reply, per the API contract.
- **Calendar** (`ui/calendar/`): a 30-day event list (`GET /calendar/events`), a
  "Connect CalDAV" dialog (`POST /integrations/caldav`), and a "New event" dialog
  (`POST /calendar/events`). Start/end times are entered as raw ISO-8601 strings
  (e.g. `2026-09-25T19:00:00Z`) - there's no native date/time picker UI yet, see
  "Known limitations".
- **Notification suggestions** (`ui/suggestions/`): lists open suggestions
  (`GET /notifications/suggestions?status=open`) with Apply/Dismiss actions
  (`POST /notifications/suggestions/{id}/apply` / `/dismiss`), matching `API.md`.
- **Notification listener** (`notification/NotificationForwardingService.kt`) - the
  core Android-specific feature, see below.
- Bottom navigation across the four screens (Chat / Calendar / Suggestions /
  Notification access), with a logout action in each screen's top bar.

## The notification listener

`NotificationForwardingService` extends `NotificationListenerService`. When any app
posts a notification, `onNotificationPosted` extracts the package name, the source
app's label, the notification's title/text, and its posted timestamp, then forwards it
to `POST /notifications/ingest` using the **device API key** (`X-Device-Key` header) -
never the user's JWT, matching the deliberate decoupling described in `API.md` ("Geräte"
section): a leaked device key can't grant full account access, and the listener keeps
working even if nobody is logged into the UI (logout intentionally does not clear the
device key - see `SecurePrefs.clearSession()`).

### Filtering (documented in code, `NotificationForwardingService`'s class doc)

Kept deliberately simple:
- OwnAI's own notifications are always skipped.
- A small denylist of system packages (`android`, `com.android.systemui`) is skipped.
- Ongoing notifications (`StatusBarNotification.isOngoing`) are skipped - this covers
  foreground-service notifications and media transport controls (play/pause etc.),
  which are never something the assistant should act on.
- Group-summary notifications (`Notification.FLAG_GROUP_SUMMARY`) are skipped, since the
  individual notifications in the group already carry the real content.
- Notifications with neither a title nor body text are skipped.
- Notifications posted at `Notification.PRIORITY_MIN` are skipped as a best-effort
  "silent" signal. This intentionally uses the legacy `Notification.priority` field
  (still populated by the platform for compatibility) instead of looking up the source
  app's `NotificationChannel` importance, which would need an extra lookup per
  notification for a fairly marginal gain - a reasonable place to start for v1.

`category` (`"msg" | "sms" | "other"`) is derived without needing any SMS permission:
`Telephony.Sms.getDefaultSmsPackage()` names the phone's current default SMS app (a
lightweight, permission-free lookup); a notification from that package is tagged `"sms"`,
anything else tagged `Notification.CATEGORY_MESSAGE` by its source app is `"msg"`,
everything else is `"other"`.

### The permission the user has to grant, and why

Reading other apps' notifications requires the special **"Notification access"**
permission. Unlike normal runtime permissions (camera, location, ...), Android does not
let an app request this through the standard in-app permission dialog - it can only be
granted from system Settings. `ui/notifications/NotificationAccessScreen.kt` explains
this to the user, shows whether it's currently granted
(`NotificationManagerCompat.getEnabledListenerPackages`), and deep-links straight to the
right settings page via:

```kotlin
context.startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
```

The same screen also requests the (separate, ordinary runtime) `POST_NOTIFICATIONS`
permission on Android 13+, needed for OwnAI to post its own notifications - not used by
anything yet, reserved for a future "suggestion ready" style notification.

### SMS nuance (out of scope for v1, by design)

What's implemented here reads the **notification** the default SMS app posts for an
incoming text - the same banner/heads-up notification the user sees - not the raw SMS
message via `RECEIVE_SMS`/`READ_SMS`. For the common case (SMS notifications enabled,
which is the Android default) this already gets the message content to OwnAI.

Capturing the *raw* SMS content directly (e.g. so it still reaches OwnAI even if the
user has muted notifications for their messaging app) would require:
1. `RECEIVE_SMS` and `READ_SMS` permissions, **and**
2. This app becoming the phone's **default SMS handler** - Google Play policy restricts
   these permissions to whichever single app is registered as the default SMS app, and
   qualifying for that requires implementing a full SMS app (compose/view/receive UI,
   not just background capture).

That's a meaningfully bigger scope than "a personal assistant client" for a sideloaded
v1 app, so it's deliberately left out - flagged here as a documented future option
rather than silently ignored, per the product brief. If this becomes a priority later,
it's its own small project: a minimal SMS-handler UI plus `SmsReceiver`
(`RECEIVE_SMS`) forwarding straight to `/notifications/ingest` with `category: "sms"`.

## Pointing the app at a different backend

The base URL is a `BuildConfig` field (`BuildConfig.API_BASE_URL`), set in
`app/build.gradle.kts`:

```kotlin
val apiBaseUrl = (project.findProperty("ownaiApiBaseUrl") as String?)
    ?: "http://10.0.2.2:8000/api/v1/"
buildConfigField("String", "API_BASE_URL", "\"$apiBaseUrl\"")
```

`10.0.2.2` is the Android emulator's alias for the host machine's `localhost`, so the
default works out of the box against a backend run locally on the same machine as
Android Studio (`docker compose up backend` et al., see the repo root `README.md`).

To point at a real server (e.g. over Tailscale, or a public domain with TLS), either:

```bash
./gradlew assembleDebug -PownaiApiBaseUrl="https://ownai.example.internal/api/v1/"
```

or add a line to your local (git-ignored) `~/.gradle/gradle.properties` or a
project-local `gradle.properties` you don't commit:

```properties
ownaiApiBaseUrl=https://ownai.example.internal/api/v1/
```

**The trailing slash matters** - Retrofit resolves every endpoint path (e.g.
`"auth/login"`, no leading slash - see `data/remote/OwnAiApi.kt`) relative to this base
URL, so a missing trailing slash silently drops the last path segment.

## Architecture / libraries

No DI framework (Hilt/Dagger) - the app is small enough that a hand-rolled container
(`data/AppContainer.kt`, built once in `OwnAiApplication.onCreate()`) plus a small
`ViewModelFactory` (`ui/ViewModelFactory.kt`) is simpler to read and reason about.

- **Networking**: Retrofit 2 + OkHttp 4, with **kotlinx.serialization** (not Moshi/Gson)
  for JSON, via `com.jakewharton.retrofit:retrofit2-kotlinx-serialization-converter`.
  Chosen for consistency with the rest of the Kotlin toolchain (no reflection, no
  annotation-processor codegen).
- **UI**: Jetpack Compose + Material 3, `androidx.navigation:navigation-compose` for a
  single `NavHost` behind the bottom navigation bar (`ui/navigation/MainScreen.kt`), and
  a separate `NavHost` for the logged-out Login/Register flow (`ui/navigation/AuthNavHost.kt`).
- **Secure storage**: `androidx.security:security-crypto` (`EncryptedSharedPreferences`
  backed by an Android Keystore `MasterKey`) for tokens and the device API key.
- **State**: plain `ViewModel` + `StateFlow`, no third-party state library.

## Known limitations (v1, by design)

- No offline queue for the notification listener: if `POST /notifications/ingest` fails
  (no network, backend down), that one notification is just logged and dropped - it is
  not retried or persisted. Worth a `WorkManager`-backed queue if this turns out to
  matter in practice.
- If device registration fails right after login (network blip, server error), there is
  no dedicated retry UI - it will be attempted again automatically on the next fresh
  login (see `AuthViewModel.onLoggedIn()`), since login itself already succeeded and the
  user is not blocked by it.
- Calendar event start/end times are plain ISO-8601 text fields, not a native date/time
  picker.
- Chat has no message editing/deletion, and no streaming (matching `API.md` v1 - the
  backend's send-message call is synchronous by design; SSE streaming is called out
  there as a planned, non-breaking v2 addition).

## Things I'm not 100% sure about

Flagged honestly, per the brief, since nothing here has been compiled:

- **Library versions**: AGP `8.7.2`, Kotlin `2.0.21`, Compose BOM `2024.12.01`,
  Gradle `8.9` (the actual wrapper jar/scripts checked into `gradle/wrapper/` and
  `gradlew`/`gradlew.bat` are the real Gradle 8.9 release, not placeholders - fetched
  directly from the Gradle project's `v8.9.0` tag). These are all real, mutually
  compatible releases as of when this was written, but if some time has passed, Android
  Studio may prompt an AGP/Gradle upgrade on first open - that's expected and fine to
  accept.
- **`androidx.security:security-crypto:1.1.0-alpha06`**: this is the version that
  introduced the `MasterKey.Builder` API used in `SecurePrefs.kt` (as opposed to the
  older, now-deprecated `MasterKeys.getOrCreate(...)` from `1.0.0`). It's been the
  de-facto standard version for this exact API for a long time, but it is still an
  alpha artifact - if a newer stable release of `security-crypto` is available by the
  time you build this, bumping `gradle/libs.versions.toml`'s `securityCrypto` version is
  worth doing (the `MasterKey.Builder` call site shouldn't need to change).
- **`Json.asConverterFactory(...)`** (from `retrofit2-kotlinx-serialization-converter`)
  is annotated `@ExperimentalSerializationApi`; this is opted into project-wide via
  `freeCompilerArgs` in `app/build.gradle.kts` rather than per call site - double-check
  that still resolves if you bump the converter library version.
- The OkHttp `Authenticator` (`TokenAuthenticator.kt`) calls the suspend `refresh()` API
  with `runBlocking` inside a `synchronized` block, since `Authenticator.authenticate()`
  is a synchronous callback on OkHttp's own dispatcher thread. This is a known,
  reasonably common pattern for coroutines + OkHttp token refresh, but it's worth
  exercising the "access token expires mid-session" path by hand once (e.g. temporarily
  shortening the backend's access-token TTL) to confirm the refresh-and-retry flow
  behaves as expected under this app's real event loop.
- Icons: everything is drawn from `androidx.compose.material:material-icons-extended`
  (e.g. `Icons.Filled.Chat`, `Icons.Filled.CalendarMonth`, `Icons.Filled.Lightbulb`,
  `Icons.AutoMirrored.Filled.ArrowBack`/`Send`). These are standard, long-established
  icon names, but this is the one area where a typo would only surface as an unresolved
  reference at build time rather than a logic bug - if the build complains about a
  specific icon, swapping it for any other icon in the same package is a trivial fix.
- The app icon (`res/mipmap-anydpi-v26/ic_launcher.xml` + `drawable/ic_launcher_foreground.xml`)
  is a plain adaptive icon built from vector paths (a simple two-circle mark), not a
  designed asset - purely functional placeholder art.
