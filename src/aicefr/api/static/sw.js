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
<meta name="color-scheme" content="light">
<title>Mất kết nối · SpeakUp</title>
<style>
  * { box-sizing: border-box; }
  body { margin: 0; min-height: 100vh; min-height: 100dvh; display: flex; flex-direction: column;
    background: #fafbfc; color: #192033; font: 15px/1.6 system-ui, -apple-system, "Segoe UI", sans-serif; }
  header { padding: 26px 36px; }
  .brand { display: inline-flex; align-items: center; gap: 9px; font-size: 21px; font-weight: 750; letter-spacing: -.6px; }
  .brand svg { width: 30px; height: 30px; color: #ff7b17; }
  main { flex: 1; display: grid; place-items: center; padding: 24px 20px 60px; }
  .card { width: 100%; max-width: 460px; padding: 36px 32px; text-align: center; background: #fff;
    border: 1px solid #eceef2; border-radius: 24px; box-shadow: 0 8px 32px #1e293b06; }
  .illustration { display: block; width: 148px; height: 122px; margin: 0 auto 22px; }
  h1 { margin: 0 0 10px; font-size: 25px; line-height: 1.35; font-weight: 700; letter-spacing: -.5px; }
  p { margin: 0 auto; max-width: 330px; color: #657086; }
  .retry { display: inline-flex; align-items: center; justify-content: center; gap: 8px; min-height: 44px;
    margin-top: 26px; padding: 10px 28px; border: 1px solid #f47715; border-radius: 11px;
    background: #ff7b17; color: white; text-decoration: none; font-weight: 650; }
  .retry:hover { background: #eb6b0a; }
  .retry:focus-visible { outline: 3px solid #ffc897; outline-offset: 4px; }
  .retry svg { width: 18px; height: 18px; }
  .hint { margin-top: 20px; font-size: 12px; color: #7c8596; }
  footer { padding: 16px 20px 24px; color: #7c8596; text-align: center; font-size: 12px; }
  @media (max-width: 480px) { header { padding: 20px; } .card { padding: 28px 20px; } h1 { font-size: 23px; } }
</style></head>
<body>
<header><span class="brand"><svg viewBox="0 0 32 32" fill="none" aria-hidden="true"><path d="M7 4h18a4 4 0 0 1 4 4v13a4 4 0 0 1-4 4H14l-7 5v-5a4 4 0 0 1-4-4V8a4 4 0 0 1 4-4Z" fill="currentColor"/><path d="M10 16v3m6-8v8m6-11v11" stroke="white" stroke-width="3" stroke-linecap="round"/></svg>SpeakUp</span></header>
<main><section class="card" aria-labelledby="offline-title">
  <svg class="illustration" viewBox="0 0 148 122" fill="none" aria-hidden="true">
    <circle cx="74" cy="59" r="54" fill="#fff3e8"/>
    <circle cx="127" cy="29" r="5" fill="#ffe0c4"/><circle cx="20" cy="94" r="3" fill="#ffd1a8"/>
    <rect x="40" y="80" width="68" height="25" rx="9" fill="white" stroke="#ffc28f" stroke-width="2"/>
    <path d="M54 91h18m7 0h3" stroke="#ff9b4d" stroke-width="3" stroke-linecap="round"/>
    <path d="M100 80V66" stroke="#ffc28f" stroke-width="3" stroke-linecap="round"/>
    <path d="M43 43a48 48 0 0 1 62 0M53 56a32 32 0 0 1 42 0M65 68a14 14 0 0 1 18 0" stroke="#ff8b32" stroke-width="5" stroke-linecap="round"/>
    <path d="m48 28 54 49" stroke="#fff3e8" stroke-width="10" stroke-linecap="round"/>
    <path d="m48 28 54 49" stroke="#dc8b53" stroke-width="4" stroke-linecap="round"/>
    <circle cx="74" cy="78" r="3" fill="#ff8b32"/>
  </svg>
  <h1 id="offline-title">Kết nối bị gián đoạn</h1>
  <p>Chưa thể kết nối với SpeakUp.<br>Kiểm tra mạng rồi thử lại nhé.</p>
  <a class="retry" href=""><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 7v5h-5M4 17v-5h5"/><path d="M6 7a7 7 0 0 1 12-1l2 6M4 12l2 6a7 7 0 0 0 12-1"/></svg>Thử lại</a>
  <p class="hint">Cần kết nối để nộp bài và chấm điểm.</p>
</section></main>
<footer>SpeakUp · Luyện nói mỗi ngày, tiến bộ từng bước.</footer>
</body></html>`;

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
