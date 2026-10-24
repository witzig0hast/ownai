// OwnAI's service worker. Kept deliberately tiny: it shows Web Push notifications, focuses/opens
// the app on click, and receives things shared to the installed app (manifest "share_target").
// No caching/offline logic here; that's a separate concern this project doesn't currently take on.
//
// iOS Safari note: Web Push only fires here at all if this site was added to the Home Screen
// ("Zum Home-Bildschirm hinzufügen") - a background tab in Safari itself never receives push,
// regardless of what this file does. That's an iOS platform restriction, not something fixable
// from the web app's side.

self.addEventListener("push", (event) => {
  let data = { title: "OwnAI", body: "" };
  try {
    if (event.data) data = { ...data, ...event.data.json() };
  } catch {
    // Non-JSON payload - fall back to the default title/empty body above.
  }

  event.waitUntil(
    self.registration.showNotification(data.title || "OwnAI", {
      body: data.body || "",
      icon: "/icon-192.png",
      badge: "/icon-192.png",
      data: { url: data.url || "/" },
    }),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const targetUrl = event.notification.data?.url || "/";

  event.waitUntil(
    (async () => {
      const allClients = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
      const existing = allClients.find((c) => new URL(c.url).origin === self.location.origin);
      if (existing) {
        await existing.focus();
        if ("navigate" in existing) await existing.navigate(targetUrl);
        return;
      }
      await self.clients.openWindow(targetUrl);
    })(),
  );
});

// Share target: the OS share sheet POSTs title/text/url and optionally an image here. A page
// can't read a POST body, so the worker parks the payload in Cache Storage and redirects to
// /share, which picks it up once and deletes it. (web/src/app/share-target/route.ts handles
// the same POST server-side, minus the image, for the rare case this worker isn't active yet.)
const SHARE_CACHE = "ownai-share";

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== "POST" || url.pathname !== "/share-target") return;

  event.respondWith(
    (async () => {
      const form = await event.request.formData();
      const cache = await caches.open(SHARE_CACHE);
      const meta = {
        title: form.get("title") || "",
        text: form.get("text") || "",
        url: form.get("url") || "",
        hasFile: false,
      };
      const file = form.getAll("files").find((f) => typeof f !== "string");
      if (file) {
        meta.hasFile = true;
        await cache.put("/__share/file", new Response(file, { headers: { "Content-Type": file.type || "image/jpeg" } }));
      }
      await cache.put("/__share/meta", new Response(JSON.stringify(meta), { headers: { "Content-Type": "application/json" } }));
      return Response.redirect("/share", 303);
    })(),
  );
});

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));
