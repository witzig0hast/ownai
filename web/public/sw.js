// OwnAI's Web Push service worker. Kept deliberately tiny - it only shows a notification for
// an incoming push and focuses/opens the app on click. No caching/offline logic here; that's a
// separate concern this project doesn't currently take on.
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
