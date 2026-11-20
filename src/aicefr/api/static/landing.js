// The product page's example report (D093). Its words are buttons: pressing one
// shows what the report says about it, which is the one thing a real report
// does that a picture cannot. On arrival the example plays once -- the playhead
// crosses the waveform and each word is "heard" in turn -- then rests with
// every mark showing.
//
// With reduced motion asked for, nothing plays: the page already shows the
// finished report. Without this script the report is the same, minus the notes.
(() => {
  "use strict";

  const demo = document.querySelector("[data-demo]");
  if (!demo) return;
  const words = [...demo.querySelectorAll(".hm-w")];
  const out = demo.querySelector("[data-note-out]");
  const line = demo.querySelector("[data-words]");
  const head = demo.querySelector("[data-head]");
  const clock = demo.querySelector("[data-clock]");
  const bars = [...demo.querySelectorAll(".hm-wave-bars i")];
  const LENGTH_S = 14;

  function pick(word) {
    for (const w of words) w.setAttribute("aria-pressed", String(w === word));
    out.textContent = word.dataset.note;
  }
  for (const w of words) {
    w.setAttribute("aria-pressed", "false");
    w.addEventListener("click", () => pick(w));
  }

  function paint(progress) {
    head.style.setProperty("--p", (progress * 100).toFixed(2) + "%");
    const s = Math.round(progress * LENGTH_S);
    clock.textContent = `0:${String(s).padStart(2, "0")}`;
    bars.forEach((bar, i) => bar.classList.toggle("on", i / bars.length < progress));
    const heard = Math.floor(progress * words.length + 0.15);
    words.forEach((w, i) => w.classList.toggle("is-heard", i < heard));
  }

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
  if (reduced.matches) {
    paint(1);
    bars.forEach((bar) => bar.classList.remove("on"));
    return;
  }

  // Play once, when the report is on screen; any press on a word ends it.
  const PLAY_MS = 4200;
  let frame = 0;
  function finish() {
    cancelAnimationFrame(frame);
    line.classList.remove("is-playing");
    paint(1);
    bars.forEach((bar) => bar.classList.remove("on"));
  }
  function play() {
    const start = performance.now();
    line.classList.add("is-playing");
    const step = (now) => {
      const progress = Math.min(1, (now - start) / PLAY_MS);
      paint(progress);
      if (progress < 1) frame = requestAnimationFrame(step);
      else {
        finish();
        pick(words.find((w) => w.classList.contains("miss")) || words[0]);
      }
    };
    frame = requestAnimationFrame(step);
  }
  line.addEventListener("click", finish, { capture: true });
  paint(0);
  const seen = new IntersectionObserver((entries) => {
    if (entries.some((e) => e.isIntersecting)) {
      seen.disconnect();
      setTimeout(play, 500);
    }
  }, { threshold: 0.4 });
  seen.observe(demo);
})();

// The header bar's tabs are the sections of this page: the one in view is the
// current one (aria-current="location"), so the underline follows the reader
// instead of staying on the first tab.
(() => {
  "use strict";

  const pairs = [...document.querySelectorAll(".site-nav a[data-section]")]
    .map((a) => [a, document.getElementById(a.dataset.section)])
    .filter(([, section]) => section);
  if (!pairs.length) return;

  function mark(current) {
    for (const [a] of pairs) {
      if (a === current) a.setAttribute("aria-current", "location");
      else a.removeAttribute("aria-current");
    }
  }

  // The last section whose top has passed a line a third of the way down the
  // window; above the first one (the hero), none.
  function inView() {
    const line = window.innerHeight / 3;
    let current = null;
    for (const [a, section] of pairs) {
      if (section.getBoundingClientRect().top <= line) current = a;
    }
    return current;
  }

  let queued = false;
  window.addEventListener(
    "scroll",
    () => {
      if (queued) return;
      queued = true;
      requestAnimationFrame(() => {
        queued = false;
        mark(inView());
      });
    },
    { passive: true },
  );
  for (const [a] of pairs) a.addEventListener("click", () => mark(a));
  mark(inView());
})();
