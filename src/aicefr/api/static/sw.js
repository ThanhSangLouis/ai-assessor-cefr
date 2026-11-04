// SpeakUp's service worker (D088), served at /sw.js so that it covers every
// page. Three jobs, nothing else:
//
// * an installed app that loses the network shows a short "offline" page
//   instead of the browser's error, for a page being opened. Pages and API
//   answers are never cached: a learner must not see an old result;
// * a Web Push message becomes a notification: a title, a sentence and the
//   page to open, nothing more (the server sends no score and no name);
// * a click on it brings an open SpeakUp tab to that page, or opens one.
const ICON = "/static/icons/icon-192.png";
const BADGE = "/static/icons/badge-96.png";

const OFFLINE = `<!doctype html>
<html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>Mất kết nối · SpeakUp</title>
<style>
  :root { --bg: #f5f7fa; --fg: #1b2430; --muted: #5b6676; --brand: #1e3a5f; }
  @media (prefers-color-scheme: dark) {
    :root { --bg: #0e1724; --fg: #e6ecf3; --muted: #a3afbf; --brand: #a9c3e6; }
  }
  body { margin: 0; min-height: 100vh; display: grid; place-items: center;
    background: var(--bg); color: var(--fg);
    font: 16px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
  main { max-width: 32rem; padding: 2rem 1.25rem; text-align: center; }
  h1 { font-size: 1.375rem; margin: 1rem 0 .5rem; }
  p { color: var(--muted); margin: 0 0 1.25rem; }
  a { color: var(--brand); font-weight: 600; }
</style></head>
<body><main>
  <img src="${ICON}" width="72" height="72" alt="">
  <h1>Bạn đang mất kết nối mạng</h1>
  <p>SpeakUp cần mạng để nộp bài và chấm điểm. Khi có mạng lại, tải lại trang này.</p>
  <a href="">Tải lại</a>
</main></body></html>`;

self.addEventListener("install", (e) => {
  // The offline page shows the icon: fetch it while the network is there.
  e.waitUntil(caches.open("speakup-offline-v1").then((c) => c.add(ICON)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method === "GET" && new URL(req.url).pathname === ICON) {
    e.respondWith(caches.match(ICON).then((hit) => hit || fetch(req)));
    return;
  }
  // Only a page being opened, and only by GET: a form sent by POST (and every
  // API call) goes to the network exactly as without a worker.
  if (req.mode !== "navigate" || req.method !== "GET") return;
  e.respondWith(
    fetch(req).catch(
      () => new Response(OFFLINE, { headers: { "Content-Type": "text/html; charset=utf-8" } })
    )
  );
});

// Only pages of this site: a message cannot send the learner elsewhere.
function sameSite(url) {
  try {
    const u = new URL(url || "/", self.location.origin);
    return u.origin === self.location.origin ? u.href : self.location.origin + "/";
  } catch (err) {
    return self.location.origin + "/";
  }
}

self.addEventListener("push", (e) => {
  let d = {};
  try {
    d = e.data ? e.data.json() : {};
  } catch (err) {
    d = {};
  }
  e.waitUntil(
    self.registration.showNotification(d.title || "SpeakUp", {
      body: d.body || "",
      tag: d.tag || undefined,
      icon: ICON,
      badge: BADGE,
      lang: "vi",
      data: { url: sameSite(d.url) },
    })
  );
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const url = sameSite(e.notification.data && e.notification.data.url);
  e.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((tabs) => {
      const tab = tabs.find((t) => new URL(t.url).origin === self.location.origin);
      // navigate() works only on a tab this worker controls; any other way,
      // a new tab.
      if (!tab) return self.clients.openWindow(url);
      return tab
        .navigate(url)
        .then((t) => (t || tab).focus())
        .catch(() => self.clients.openWindow(url));
    })
  );
});
