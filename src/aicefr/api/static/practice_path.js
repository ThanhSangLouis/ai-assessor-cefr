// The learner's roadmap (D025, M13; a trail since D027, drawn after Thắng's
// mockup in D092).
//
// One part per band, split into visual chapters on an adaptive 2D trail.
// A tick marks completed lessons; a golden coin marks the suggested next one.
// Locked lessons show a padlock and never expose a study action.
// Clicking a coin opens its card without changing the road or scenery. When the learner has chosen
// bands (D074) the roadmap is that plan; otherwise it is the whole path. The
// column beside it: what to study next, today's speaking time, the progress of
// the course and of each band. No score, no band estimate and no ranking.
const escapeHtml = window.escapeHtml;
const icon = (name, cls) => window.ui.icon(name, cls);
const page = document.getElementById("path-page");
const headEl = document.getElementById("path-head");
const unitsEl = document.getElementById("path-units");
const sideEl = document.getElementById("path-side");

const TOPICS = window.ui.TOPICS;
const LEVELS = {
  A1: "Khởi đầu",
  A2: "Cuộc sống quanh ta",
  B1: "Mở rộng giao tiếp",
  B2: "Giao tiếp tự tin",
  C1: "Giao tiếp nâng cao",
  C2: "Thành thạo",
};
const BANDS = ["A1", "A2", "B1", "B2", "C1", "C2"];
const STATUS_TEXT = { completed: "Đã hoàn thành", started: "Đang học", new: "Chưa học", locked: "Chưa mở khóa", unavailable: "Không còn mở" };

const narrow = window.matchMedia("(max-width: 700px)");
let data = null;
// A path chosen by hand is drawn whole, whatever plan is in force.
const chosen = new URLSearchParams(location.search).get("path");
// The plan of D074: undefined until band_plan.js has said, null when none.
let plan;

const topicName = (u) => (u && TOPICS[u.topic] ? TOPICS[u.topic][0] : "");
// A lesson takes about a minute a step, two at least.
const minutes = (l) => `${Math.max(2, Number(l.steps) || 0)} phút`;

// Lessons of the path by id, with their unit: what the plan's lessons are.
let byId = new Map();
function indexPath() {
  byId = new Map();
  for (const u of data.path.units) for (const l of u.lessons) byId.set(l.lesson_id, { lesson: l, unit: u });
}

function findLesson(id) {
  for (const part of parts()) {
    const l = part.lessons.find((x) => x.lesson_id === id);
    if (l) return { lesson: l, unit: l.unit };
  }
  const hit = byId.get(id);
  return hit ? { lesson: hit.lesson, unit: hit.unit } : null;
}

// What the roadmap draws: the plan's lessons when there is a plan, else the
// path's; a run of lessons of one band is one part.
function parts() {
  const out = [];
  const add = (band, lesson) => {
    const last = out[out.length - 1];
    if (last && last.band === band) last.lessons.push(lesson);
    else out.push({ band, lessons: [lesson] });
  };
  if (plan && Array.isArray(plan.units)) {
    for (const u of plan.units) {
      for (const item of u.lessons) {
        const hit = byId.get(item.lesson_id);
        const lesson = { ...(hit ? hit.lesson : {}), ...item, status: item.status };
        lesson.band = item.band || (hit && hit.lesson.band) || u.band;
        lesson.unit = hit ? hit.unit : u;
        add(String(u.band || lesson.band || "").toUpperCase(), lesson);
      }
    }
    return out;
  }
  for (const u of data.path.units) {
    for (const l of u.lessons) add(String(u.band || l.band || "").toUpperCase(), { ...l, unit: u });
  }
  return out;
}

function getGreetingName() {
  const who = document.querySelector(".who-name");
  const name = who ? who.textContent.trim() : "";
  return !name || name.includes("@") ? "bạn" : name;
}

const SPARK =
  '<svg class="rm-spark" viewBox="0 0 32 32" aria-hidden="true" focusable="false">' +
  '<path d="M13 3c1 6 3 8 9 9-6 1-8 3-9 9-1-6-3-8-9-9 6-1 8-3 9-9Z"/>' +
  '<path d="M25 17c.5 3 1.5 4 4.5 4.5-3 .5-4 1.5-4.5 4.5-.5-3-1.5-4-4.5-4.5 3-.5 4-1.5 4.5-4.5Z"/></svg>';
const BOLT =
  '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">' +
  '<path d="M13.5 2 4 13.5h6.5L9.5 22 20 9.5h-6.6L13.5 2Z" fill="currentColor"/></svg>';

// ---------------------------------------------------------------- head
function head() {
  const p = data.path;
  const switcher =
    data.paths.length > 1
      ? '<div class="rm-path-switch"><label for="path-select">Lộ trình</label><select id="path-select">' +
        data.paths
          .map(
            (x) =>
              `<option value="${escapeHtml(x.path_id)}"${x.path_id === p.path_id ? " selected" : ""}>` +
              `${escapeHtml(x.title)}</option>`,
          )
          .join("") +
        "</select></div>"
      : "";
  headEl.innerHTML =
    '<div class="rm-hero-text">' +
    `<h1>Chào <span class="rm-name">${escapeHtml(getGreetingName())}</span>, cùng luyện nói nhé! ${SPARK}` +
    `<span class="visually-hidden"> - ${escapeHtml(p.title)}</span></h1>` +
    "<p>Luyện nói mỗi ngày, tiến bộ từng bước.</p>" +
    switcher +
    "</div>" +
    '<span class="rm-girl" aria-hidden="true"><img src="/static/art/mascot_girl.png" alt="" width="224" height="150"></span>';
  const select = document.getElementById("path-select");
  if (select) {
    if (window.enhanceSelects) window.enhanceSelects(headEl);
    select.addEventListener("change", () => {
      location.search = `?path=${encodeURIComponent(select.value)}`;
    });
  }
}

// ---------------------------------------------------------------- roadmap
// Geometry in pixels from the centre line of the road: the coins swing left
// and right of it, a row apart; the coin to study next gets room for its flag.
function geometry() {
  return window.rmAdventure.geometry(narrow.matches);
}

function layout(lessons, nextId, g) {
  return window.rmAdventure.layout(lessons, nextId, g);
}

// The road winds: from each coin it leaves straight down and reaches the next
// straight from above, a smooth S between them (cubic Béziers with vertical
// tangents), ending at the last coin so no road protrudes below it. Drawn as a
// translucent guide with small stars; its scale is independent of lesson count.
function roadHtml(points, height) {
  if (points.length < 2) return "";
  const all = points;
  let d = `M${all[0].x} ${all[0].y}`;
  for (let i = 1; i < all.length; i += 1) {
    const a = all[i - 1];
    const z = all[i];
    const k = Math.round((z.y - a.y) * 0.55);
    d += ` C${a.x} ${a.y + k} ${z.x} ${z.y - k} ${z.x} ${z.y}`;
  }
  const stars = all.slice(1).map((point, i) => {
    const x = (all[i].x + point.x) / 2;
    const y = (all[i].y + point.y) / 2;
    return `<path class="rm-road-star" d="M${x} ${y - 4}l1.2 2.8 3.1 1.2-3.1 1.2-1.2 2.8-1.2-2.8-3.1-1.2 3.1-1.2Z"/>`;
  }).join("");
  return (
    `<svg class="rm-road" width="2" height="${height}" viewBox="-1 0 2 ${height}" aria-hidden="true" focusable="false">` +
    `<path class="rm-road-shadow" d="${d}"/><path class="rm-road-side" d="${d}"/>` +
    `<path class="rm-road-edge" d="${d}"/><path class="rm-road-fill" d="${d}"/><path class="rm-road-dash" d="${d}"/>${stars}</svg>`
  );
}

// The coins' marks are solid, as drawn in the mockup; the details take the
// coin's own colour (--glyph-ink).
const GLYPHS = {
  lock:
    '<path d="M7.5 10.5V8a4.5 4.5 0 0 1 9 0v2.5" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"/>' +
    '<rect x="4.5" y="10" width="15" height="11.5" rx="2.8" fill="currentColor"/>' +
    '<circle cx="12" cy="15" r="1.7" fill="var(--glyph-ink)"/><rect x="11.2" y="15.5" width="1.6" height="3.2" rx=".8" fill="var(--glyph-ink)"/>',
  book:
    '<path d="M2.5 5.2c3.1-1.3 6.3-1 8.8.9V20c-2.6-1.7-5.8-2-8.8-.8ZM21.5 5.2c-3.1-1.3-6.3-1-8.8.9V20c2.6-1.7 5.8-2 8.8-.8Z" fill="currentColor"/>' +
    '<path d="M5 9.2h3.8M5 12.2h3.8M5 15.2h3.8M15.2 9.2H19M15.2 12.2H19M15.2 15.2H19" stroke="var(--book-detail, var(--glyph-ink))" stroke-width="1.4" stroke-linecap="round"/>',
  check: '<path d="m5 12.6 4.6 4.6L19.2 7.4" fill="none" stroke="currentColor" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"/>',
};
// A solid triangle, the play mark of the mockup's buttons.
const PLAY =
  '<svg class="icon rm-play-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">' +
  '<path d="M7 4.8c0-1 1.1-1.6 2-1.1l11.2 7.2c.8.5.8 1.7 0 2.2L9 20.3c-.9.5-2-.1-2-1.1Z" fill="currentColor"/></svg>';
const glyph = (name, cls = "rm-coin-icon") =>
  `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${GLYPHS[name]}</svg>`;

function lessonCardContent(l, number, detail = false) {
  const action = l.status === "completed" ? "Học lại" : l.status === "started" ? "Học tiếp" : "Học bài";
  const meta = `${minutes(l)} · ${Number(l.steps) || 0} bước`;
  const label = `<span class="rm-lesson-action">${action}${icon("arrow-right")}</span>`;
  return `<small class="rm-node-card-eyebrow">Bài ${number}${l.band ? ` · ${escapeHtml(l.band)}` : ""}</small>` +
    `<strong class="rm-lesson-title">${escapeHtml(l.title)}</strong>` +
    (l.summary ? `<p class="rm-node-card-summary">${escapeHtml(l.summary)}</p>` : "") +
    `<span class="rm-bubble-time">${icon("clock")}${escapeHtml(meta)}</span>` +
    (["locked", "unavailable"].includes(l.status) ? `<p class="muted">${l.status === "locked" ? "Hoàn thành bài trước để mở khóa." : "Bài này không còn mở."}</p>` :
      detail ? `<a class="rm-lesson-link" href="/practice/lessons/${encodeURIComponent(l.lesson_id)}">${label}</a>` : label);
}

// A compact reward emblem shares the lesson coin footprint.
function victoryEmblem() {
  const center = '<path fill="var(--reward-center)" d="m24 13 1.8 3.6 4 .6-2.9 2.8.7 4-3.6-1.9-3.6 1.9.7-4-2.9-2.8 4-.6Z"/>';
  return `<svg class="rm-reward-emblem" viewBox="0 0 48 48" aria-hidden="true" focusable="false">
    <path d="M14 12H8v5c0 5 4 8 9 8M34 12h6v5c0 5-4 8-9 8" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round"/>
    <path fill="currentColor" d="M14 9h20v10a10 10 0 0 1-8 9.8V34h6v5H16v-5h6v-5.2A10 10 0 0 1 14 19Z"/>
    ${center}
  </svg>`;
}

function nodeHtml(l, i, point, nextId, isFinish = false) {
  const isNext = l.lesson_id === nextId && !["locked", "unavailable"].includes(l.status);
  const isDone = l.status === "completed";
  const isUnavailable = ["locked", "unavailable"].includes(l.status);
  const state = isUnavailable ? "locked" : isNext ? "current next" : isDone ? "complete" : "available";
  const mark = isFinish
    ? victoryEmblem()
    : isUnavailable ? glyph("lock") : glyph("book");
  const said = isNext ? (l.status === "started" ? "Đang học" : "Học tiếp theo") : STATUS_TEXT[l.status] || "Chưa học";
  const id = escapeHtml(l.lesson_id);
  let html =
    `<li class="lesson-node ${state}${isFinish ? " rm-victory" : ""} ${escapeHtml(l.status || "new")}" style="--dx:${point.x}px;--y:${point.y}px">` +
    `<button type="button" class="node-coin rm-coin" data-lesson="${id}" aria-expanded="false" ` +
    `aria-label="${escapeHtml(l.title)}${isFinish ? ", Bài cuối phần" : ""}, ${said}">${mark}</button>` +
    `<span class="visually-hidden lesson-state">${STATUS_TEXT[l.status] || ""}</span>`;
  if (isNext) {
    html += `<span class="node-flag rm-flag" aria-hidden="true">${l.status === "started" ? "Học tiếp" : "Bắt đầu"}</span>`;
  }
  return `${html}</li>`;
}

// The themed companion of a part, with its tip.
// Each companion sits halfway down its band’s lesson area.
function mascotHtml(band, k) {
  const cast = window.rmMascots && window.rmMascots.CAST[band];
  if (!cast) return "";
  const side = k % 2 ? "right" : "left";
  const art = window.rmMascots.ART[cast.name];
  return (
    `<span class="rm-deco rm-mascot rm-mascot-${side} rm-mascot-${cast.name}" aria-hidden="true">` +
    `<span class="rm-say">${escapeHtml(cast.tip)}</span><span class="rm-mascot-art">${art}</span></span>`
  );
}

let drawnNarrow = null;

function trail() {
  const g = geometry();
  drawnNarrow = narrow.matches;
  const all = parts();
  if (!all.length) {
    unitsEl.innerHTML = '<p class="muted rm-empty">Lộ trình này chưa có bài học.</p>';
    return;
  }
  unitsEl.innerHTML = all
    .map((part, k) => {
      const nextId = part.lessons.find(l => ["new", "started"].includes(l.status))?.lesson_id || null;
      const done = part.lessons.filter((l) => l.status === "completed").length;
      const total = part.lessons.length;
      const pct = total ? Math.round((done / total) * 100) : 0;
      const isLast = k === all.length - 1;
      const points = layout(part.lessons, nextId, g);
      const height = window.rmAdventure.height(points, g);
      const band = part.band || "A1";
      const theme = window.rmAdventure.THEMES[band] || window.rmAdventure.THEMES.A1;
      const chapterLabels = window.rmAdventure.chapters(points).map((chapter) =>
        `<span class="rm-chapter-label" style="top:${chapter.y}px">Chặng ${chapter.number}<span>${chapter.start + 1}–${chapter.end}</span></span>`
      ).join("");
      return (
        `<section class="path-part rm-level band-${escapeHtml(band.toLowerCase())}" aria-labelledby="part-h-${k}">` +
        '<header class="rm-level-head">' +
        `<span class="rm-pill" aria-hidden="true">${escapeHtml(band)}</span>` +
        `<h2 class="rm-level-name" id="part-h-${k}"><span class="visually-hidden">${escapeHtml(band)}: </span>` +
        `<span class="rm-adventure-title">${escapeHtml(theme.title)}</span><span class="rm-band-description">${escapeHtml(LEVELS[band] || band)}</span></h2>` +
        `<div class="rm-level-stat"><span><b>${done}/${total}</b> bài</span>` +
        `<span class="rm-bar" role="progressbar" aria-label="Tiến độ ${escapeHtml(band)}" aria-valuemin="0" aria-valuemax="100" ` +
        `aria-valuenow="${pct}"><span style="width:${pct}%"></span></span></div>` +
        "</header>" +
        `<div class="rm-path rm-adventure-path${isLast ? " is-last" : ""}" style="--h:${height}px">` +
        window.rmAdventure.sceneryHtml() + chapterLabels +
        mascotHtml(band, k) +
        roadHtml(points, height) +
        `<ol class="rm-nodes">${part.lessons.map((l, i) => nodeHtml(l, i, points[i], nextId, i === part.lessons.length - 1)).join("")}</ol>` +
        "</div></section>"
      );
    })
    .join("");
  positionCompanions();
  wakeMascots();
}

// Place companions in the clearing beside nearby lessons, rather than at the border.
// Observe path width so sidebar and viewport changes use the same collision rules.
let companionObserver = null;
function positionCompanions() {
  if (companionObserver) companionObserver.disconnect();
  const place = (path) => {
    const scenery = path.querySelector(".rm-adventure-scenery");
    const ratio = Number(getComputedStyle(path).getPropertyValue("--scene-ratio")) || 3;
    const tiles = window.rmAdventure.terrainTiles(path.clientHeight, path.clientWidth, ratio);
    if (scenery && scenery.childElementCount !== tiles.length) {
      scenery.innerHTML = tiles.map(tile =>
        `<span class="rm-terrain-tile" style="--tile-index:${tile.index}"></span>`).join("");
    }
    const mascot = path.querySelector(".rm-mascot");
    if (!mascot) return;
    const bounds = path.getBoundingClientRect();
    const size = mascot.getBoundingClientRect().width;
    const bubbleWidth = Math.min(bounds.width <= 400 ? 112 : 180, size + 30);
    const footprint = Math.max(size, bubbleWidth);
    const nodes = [...path.querySelectorAll(".node-coin")].map(node => {
      const r = node.getBoundingClientRect();
      return { left: r.left - bounds.left - 10, right: r.right - bounds.left + 10,
        top: r.top - bounds.top - 32, bottom: r.bottom - bounds.top + 12 };
    });
    const middle = bounds.height / 2;
    let best = null;
    const reach = Math.max(220, size);
    const start = Math.max(64 + size / 2, middle - reach);
    const end = Math.min(bounds.height - size / 2 - 8, middle + reach);
    for (let y = start; y <= end; y += 8) {
      for (let x = footprint / 2 + 12; x <= bounds.width - footprint / 2 - 12; x += 8) {
        const box = { left: x - footprint / 2, right: x + footprint / 2,
          top: y - size / 2 - 60, bottom: y + size / 2 + 6 };
        const overlap = nodes.reduce((sum, n) => sum +
          Math.max(0, Math.min(box.right, n.right) - Math.max(box.left, n.left)) *
          Math.max(0, Math.min(box.bottom, n.bottom) - Math.max(box.top, n.top)), 0);
        const preferredLeft = mascot.classList.contains("rm-mascot-left");
        const wrongSide = preferredLeft ? x > bounds.width / 2 : x < bounds.width / 2;
        const artOverlap = nodes.reduce((sum, n) => sum +
          Math.max(0, Math.min(x + size / 2, n.right) - Math.max(x - size / 2, n.left)) *
          Math.max(0, Math.min(y + size / 2, n.bottom) - Math.max(y - size / 2, n.top + 32)), 0);
        const score = artOverlap * 1000000 + overlap * 10000 + Math.abs(x - bounds.width / 2) +
          Math.abs(y - middle) * .45 + (wrongSide ? 24 : 0);
        if (!best || score < best.score) best = { x, y, score };
      }
    }
    if (!best) return;
    mascot.style.left = `${best.x - size / 2}px`;
    mascot.style.right = "auto";
    mascot.style.top = `${best.y}px`;
    mascot.style.setProperty("--companion-bubble-width", `${bubbleWidth}px`);
  };
  companionObserver = new ResizeObserver(entries => entries.forEach(entry => place(entry.target)));
  unitsEl.querySelectorAll(".rm-adventure-path").forEach(path => {
    place(path);
    companionObserver.observe(path);
  });
}

// A companion says its tip once its part scrolls into view, and hops when
// clicked; both only decoration.
let watcher = null;
function wakeMascots() {
  if (watcher) watcher.disconnect();
  const all = unitsEl.querySelectorAll(".rm-mascot");
  if (!("IntersectionObserver" in window)) return;
  watcher = new IntersectionObserver(
    (entries) => {
      for (const e of entries) {
        if (!e.isIntersecting) continue;
        const m = e.target;
        watcher.unobserve(m);
        m.classList.add("is-saying");
        setTimeout(() => m.classList.remove("is-saying"), 4200);
      }
    },
    { threshold: 0.7 },
  );
  all.forEach((m) => watcher.observe(m));
}
unitsEl.addEventListener("click", (e) => {
  const m = e.target.closest(".rm-mascot");
  if (!m) return;
  m.classList.remove("is-hopping");
  void m.offsetWidth;
  m.classList.add("is-hopping", "is-saying");
  setTimeout(() => m.classList.remove("is-saying"), 3000);
});
unitsEl.addEventListener("animationend", (e) => {
  if (e.animationName === "rm-hop") e.target.closest(".rm-mascot")?.classList.remove("is-hopping");
});

// ---------------------------------------------------------------- lesson card
let openCoin = null;

function closeCard() {
  const card = document.getElementById("node-card");
  if (card) card.remove();
  if (openCoin) {
    openCoin.setAttribute("aria-expanded", "false");
    openCoin = null;
  }
}

function openCard(coin) {
  const found = findLesson(coin.dataset.lesson);
  if (!found) return;
  closeCard();
  const { lesson: l } = found;
  const node = coin.closest(".lesson-node");
  const box = coin.closest(".rm-path");
  const card = document.createElement("div");
  card.id = "node-card";
  card.className = "rm-node-card";
  card.setAttribute("role", "dialog");
  card.setAttribute("aria-label", l.title);
  card.innerHTML = lessonCardContent(l, orderOf(l.lesson_id), true);
  box.appendChild(card);
  // Under the coin, kept inside the roadmap's box.
  const points = [...box.querySelectorAll(".lesson-node")];
  const rightEdge = Math.max(...points.map((item) => item.offsetLeft)) + 60;
  const leftEdge = Math.min(...points.map((item) => item.offsetLeft)) - 60;
  const bounds = box.getBoundingClientRect();
  const obstacles = [...box.querySelectorAll(".rm-mascot, .rm-bubble, .node-coin")];
  let placed = false;
  for (const side of ["right", "left"]) {
    const space = side === "right" ? box.clientWidth - rightEdge - 12 : leftEdge - 12;
    if (space < 230) continue;
    const width = Math.min(270, space);
    card.style.width = `${width}px`;
    const left = side === "right" ? rightEdge : leftEdge - width;
    const top = Math.max(8, Math.min(node.offsetTop - card.offsetHeight / 2, box.clientHeight - card.offsetHeight - 12));
    const rect = { left: bounds.left + left, right: bounds.left + left + width,
      top: bounds.top + top, bottom: bounds.top + top + card.offsetHeight };
    const collides = obstacles.some((item) => {
      const r = item.getBoundingClientRect();
      return rect.left < r.right + 12 && rect.right > r.left - 12 && rect.top < r.bottom + 12 && rect.bottom > r.top - 12;
    });
    if (collides || card.offsetHeight > box.clientHeight - 20) continue;
    card.style.left = `${left}px`;
    card.style.top = `${top}px`;
    card.classList.add("rm-node-card-side");
    placed = true;
    break;
  }
  if (!placed) {
    const width = Math.min(270, box.clientWidth - 24);
    card.style.width = `${width}px`;
    card.style.left = `${Math.max(12, Math.min(box.clientWidth - width - 12, node.offsetLeft - width / 2))}px`;
    card.style.top = `${node.offsetTop + coin.offsetHeight / 2 + 20}px`;
    // Float the card over the page; opening a lesson never changes the trail.
    const below = node.offsetTop + coin.offsetHeight / 2 + 20;
    const top = below + card.offsetHeight <= box.clientHeight
      ? below : Math.max(8, node.offsetTop - coin.offsetHeight / 2 - card.offsetHeight - 20);
    card.style.top = `${top}px`;
    card.classList.add("rm-node-card-floating");
  }
  coin.setAttribute("aria-expanded", "true");
  openCoin = coin;
  const go = card.querySelector("a");
  if (go) go.focus({ preventScroll: true });
}

unitsEl.addEventListener("click", (e) => {
  const coin = e.target.closest(".node-coin");
  if (!coin) return;
  if (coin === openCoin) closeCard();
  else openCard(coin);
});
document.addEventListener("click", (e) => {
  if (openCoin && !e.target.closest("#node-card") && !e.target.closest(".node-coin")) closeCard();
});
document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape" || !openCoin) return;
  const coin = openCoin;
  closeCard();
  coin.focus();
});

// ---------------------------------------------------------------- side column
function nextCard() {
  const n = data.next;
  if (!n) {
    return (
      '<section class="rm-card rm-next next-card" aria-labelledby="next-h">' +
      `<div class="rm-card-head"><p class="rm-card-title">${BOLT}Nên học tiếp</p></div>` +
      '<h2 id="next-h" class="rm-next-empty">Lộ trình chưa có bài học</h2></section>'
    );
  }
  const found = findLesson(n.lesson_id);
  const l = found && found.lesson;
  const u = found && found.unit;
  const order = l ? orderOf(n.lesson_id) : 0;
  const action = l && l.status === "completed" ? "Luyện lại" : l && l.status === "started" ? "Tiếp tục học" : "Bắt đầu học";
  const meta = l ? [minutes(l), topicName(u)].filter(Boolean).join(" · ") : "";
  return (
    `<section class="rm-card rm-next next-card" aria-labelledby="next-h"${n.reason ? ` title="${escapeHtml(n.reason)}"` : ""}>` +
    `<div class="rm-card-head"><p class="rm-card-title">${BOLT}${n.basis === "review_all" ? "Học lại" : "Nên học tiếp"}</p>` +
    (l && l.band ? `<span class="rm-chip">${escapeHtml(l.band)}</span>` : "") +
    "</div>" +
    '<div class="rm-next-info">' +
    `<span class="rm-next-icon" aria-hidden="true">${glyph("book", "rm-book")}</span>` +
    `<div class="rm-next-text"><div class="rm-next-name">${order ? `<span>Bài ${order}: </span>` : ""}` +
    `<h2 id="next-h">${escapeHtml(n.title)}</h2></div>` +
    (meta ? `<p class="rm-next-meta">${escapeHtml(meta)}</p>` : "") +
    "</div></div>" +
    `<a class="rm-btn rm-btn-green next-go" href="/practice/lessons/${encodeURIComponent(n.lesson_id)}">${PLAY}${action}</a>` +
    "</section>"
  );
}

// Where a lesson stands in its part, counted from one.
function orderOf(id) {
  for (const part of parts()) {
    const i = part.lessons.findIndex((x) => x.lesson_id === id);
    if (i >= 0) return i + 1;
  }
  return 0;
}

function getCalendarWeek(t) {
  const todayIso = t.week && t.week.length ? t.week[t.week.length - 1].date : "";
  const todayDate = todayIso ? new Date(`${todayIso}T00:00:00`) : new Date();
  const dayOfWeek = todayDate.getDay(); // 0: Sun, 1: Mon, ..., 6: Sat
  const mondayOffset = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;

  const weekMap = new Map();
  if (t.week) {
    for (const w of t.week) {
      weekMap.set(w.date, w);
    }
  }

  const days = [];
  const LABELS = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"];
  for (let i = 0; i < 7; i++) {
    const d = new Date(todayDate);
    d.setDate(todayDate.getDate() + mondayOffset + i);
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    const iso = `${y}-${m}-${day}`;
    const isToday = iso === todayIso;
    const isFuture = d.getTime() > todayDate.getTime();
    const w = weekMap.get(iso);
    const seconds = w ? w.seconds : 0;
    days.push({
      date: iso,
      dayName: LABELS[i],
      isToday,
      isFuture,
      seconds,
    });
  }
  return days;
}

function todayCard(t) {
  const seconds = Math.round(t.seconds);
  const goal = Number(t.goal_seconds);
  const shown = seconds === 0 ? "0" : seconds >= 60 ? String(Math.round((seconds / 60) * 10) / 10) : `${seconds}s`;
  const pct = Math.min(100, Math.round((seconds / Math.max(1, goal)) * 100));
  const rest = new Set(t.rest_days || []);
  const streak = Number(t.streak) || 0;
  const days = t.week.filter((w) => w.seconds > 0).length;
  const calendarDays = getCalendarWeek(t);
  const calendarIsos = new Set(calendarDays.map((d) => d.date));
  const dots = calendarDays
    .map((cd) => {
      const isDone = cd.seconds > 0;
      const isRest = !isDone && !cd.isFuture && rest.has(cd.date);
      const kind = isDone ? "on" : isRest ? "rest" : cd.isFuture ? "future" : "";
      const said = isDone
        ? `${Math.round(cd.seconds)} giây`
        : isRest
          ? "nghỉ, chuỗi vẫn giữ"
          : cd.isToday
            ? "hôm nay"
            : cd.isFuture
              ? "sắp tới"
              : "chưa luyện";
      const mark = isDone ? icon("check") : isRest ? "z" : "";
      return (
        `<li class="${kind}${cd.isToday ? " is-today" : ""}" title="${escapeHtml(window.ui.dmy(cd.date))}: ${said}">` +
        `<span class="rm-day" aria-hidden="true">${mark}</span>${cd.dayName}</li>`
      );
    })
    .join("");
  // Rest days of the last seven that fall before this week still count.
  let extraHiddenRest = "";
  for (const w of t.week || []) {
    if (!calendarIsos.has(w.date) && rest.has(w.date) && w.seconds <= 0) {
      extraHiddenRest += `<li class="rest visually-hidden" title="${escapeHtml(window.ui.dmy(w.date))}: nghỉ, chuỗi vẫn giữ"></li>`;
    }
  }
  return (
    '<section class="rm-card today-card" aria-labelledby="today-h">' +
    '<div class="rm-card-head">' +
    `<h2 class="rm-card-title" id="today-h">${icon("target", "icon rm-orange")}Mục tiêu hôm nay</h2>` +
    `<span class="rm-chip rm-chip-orange${t.goal_met ? " met" : ""}">${t.goal_met ? "Đạt" : `${pct}%`}</span>` +
    "</div>" +
    `<p class="rm-today-num"><b>${shown}</b> / ${Math.round(goal / 60)} phút luyện tập</p>` +
    `<div class="goal-ring visually-hidden"><span>${seconds}/${goal} giây</span></div>` +
    `<span class="rm-bar rm-bar-lg"><span style="width:${pct}%"></span></span>` +
    `<p class="rm-streak">${icon("flame", "icon rm-flame")}<b>${streak}</b> ngày liên tiếp</p>` +
    `<ol class="week-dots rm-week" aria-label="Tuần này, ${days} ngày có luyện">${dots}${extraHiddenRest}</ol>` +
    `<div class="rm-today-foot"><span>Mục tiêu mỗi ngày</span>${goalPicker(goal)}</div>` +
    "</section>"
  );
}

function progressCard(all) {
  const lessons = all.flatMap((p) => p.lessons);
  const done = lessons.filter((l) => l.status === "completed").length;
  const total = lessons.length;
  const pct = total ? Math.round((done / total) * 100) : 0;
  return (
    '<section class="rm-card rm-progress" aria-labelledby="overall-h">' +
    '<div class="rm-card-head">' +
    `<h2 class="rm-card-title" id="overall-h">${icon("trophy", "icon rm-gold")}Tiến độ khóa học</h2>` +
    `</div>` +
    `<p class="rm-row"><span>Bài học hoàn thành</span><b>${done} / ${total} bài</b></p>` +
    `<span class="rm-bar rm-bar-lg overall"><span style="width:${pct}%"></span>` +
    `<span class="visually-hidden">${done}/${total} bài đã hoàn thành</span></span>` +
    "</section>"
  );
}

function levelCard(all) {
  const rows = BANDS.map((band) => {
    const lessons = all.filter((p) => p.band === band).flatMap((p) => p.lessons);
    if (!lessons.length) return "";
    const done = lessons.filter((l) => l.status === "completed").length;
    const pct = Math.round((done / lessons.length) * 100);
    return (
      `<li><span class="rm-band-chip">${band}</span>` +
      `<span class="rm-bar"><span style="width:${pct}%"></span></span><span class="rm-pct">${pct}%</span></li>`
    );
  }).join("");
  if (!rows) return "";
  return (
    '<section class="rm-card rm-levels" aria-labelledby="levels-h">' +
    `<div class="rm-card-head"><h2 class="rm-card-title" id="levels-h">${icon("chart", "icon rm-orange")}Tổng quan cấp độ</h2></div>` +
    `<ul class="rm-level-list">${rows}</ul></section>`
  );
}

// Reviews due (D034), phrases due (D070) and the achievements (D032): a card
// only when something waits, so the page stays the mockup's on most days.
function reviewCard() {
  const reviews = Number(data.reviews_due) || 0;
  const due = phrases && phrases.total ? Math.min(Number(phrases.due_count) || 0, phrases.per_day) : 0;
  if (!reviews && !due) return "";
  const ach = data.achievements;
  const row = (href, name, label, value, id) =>
    `<a class="rm-link-row" href="${href}"${id ? ` id="${id}"` : ""}>${icon(name, "icon rm-orange")}<span>${label}</span>` +
    `<b>${value}</b>${icon("chevron-right")}</a>`;
  return (
    '<section class="rm-card review-card" aria-labelledby="review-h">' +
    `<div class="rm-card-head"><h2 class="rm-card-title" id="review-h">${icon("refresh", "icon rm-orange")}Ôn tập hôm nay</h2></div>` +
    (reviews ? row("/practice/review", "refresh", "Từ cần nói lại", `<span class="review-count">${reviews}</span>`) : "") +
    (due ? row("/phrases", "book-open", "Sổ cụm từ", `${due} cụm`) : "") +
    (ach ? row("/my-progress#achievements", "trophy", "Thành tựu", `${Number(ach.unlocked) || 0}/${Number(ach.total) || 0}`) : "") +
    "</section>"
  );
}

// D068: the daily goal is set on the card that measures it, saved when picked.
const GOALS = (page.dataset.goals || "").split(",").filter(Boolean).map(Number);

function goalPicker(goal) {
  if (!GOALS.length) return "";
  const options = GOALS.map((s) => `<option value="${s}"${s === goal ? " selected" : ""}>${s / 60} phút</option>`).join("");
  return `<div class="goal-pick"><select id="goal-select" aria-label="Mục tiêu mỗi ngày">${options}</select></div>`;
}

sideEl.addEventListener("change", async (e) => {
  if (e.target.id !== "goal-select") return;
  const r = await fetch("/api/v1/me/profile", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ daily_goal_s: Number(e.target.value) }),
  });
  if (window.redirectToLoginIfExpired(r)) return;
  const d = await r.json().catch(() => ({}));
  if (!r.ok) {
    window.toast("Không lưu được mục tiêu.", "error");
    return;
  }
  data.today.goal_seconds = d.daily_goal_s;
  data.today.goal_met = data.today.seconds >= d.daily_goal_s;
  side();
  window.toast(`Mục tiêu mới: ${Math.round(d.daily_goal_s / 60)} phút nói mỗi ngày.`, "ok");
});

// D070: the phrase book, loaded beside the path and painted when it arrives;
// a failure leaves it out, nothing else.
let phrases = null;
fetch("/api/v1/me/phrases")
  .then((r) => (r.ok ? r.json() : null))
  .then((d) => {
    phrases = d;
    if (data && data.path && plan !== undefined) side();
  })
  .catch(() => {});

function side() {
  const all = parts();
  sideEl.hidden = false;
  sideEl.innerHTML = nextCard() + todayCard(data.today) + progressCard(all) + levelCard(all) + reviewCard();
  if (window.enhanceSelects) window.enhanceSelects(sideEl);
  fitSide();
}

// ---------------------------------------------------------------- render
function render() {
  window.clearBusy(page);
  if (!data.path) {
    headEl.innerHTML = "<h1>Lộ trình học</h1>";
    sideEl.hidden = true;
    unitsEl.innerHTML =
      '<div class="rm-card"><div class="empty-state"><div class="empty-mark" aria-hidden="true">◇</div>' +
      "<h2>Chưa có lộ trình nào được xuất bản</h2>" +
      "<p>Giảng viên của bạn sẽ xuất bản lộ trình học. Trong lúc chờ, bạn vẫn làm được bài đánh giá ở trang Nộp bài.</p>" +
      "</div></div>";
    return;
  }
  indexPath();
  head();
  closeCard();
  trail();
  side();
}

// The side column follows the page down while it fits in the window; taller
// than the window it scrolls with the page, or its last cards stay hidden.
function fitSide() {
  sideEl.classList.remove("is-tall");
  const style = getComputedStyle(sideEl);
  if (style.position !== "sticky") return;
  const top = parseFloat(style.top) || 0;
  sideEl.classList.toggle("is-tall", sideEl.offsetHeight + top > window.innerHeight);
}
let refit = null;
window.addEventListener("resize", () => {
  closeCard();
  if (!data || !data.path) return;
  clearTimeout(refit);
  refit = setTimeout(fitSide, 150);
});
// Phones draw the road tighter: redraw when the width crosses that line.
narrow.addEventListener("change", () => {
  if (!data || !data.path || plan === undefined || drawnNarrow === narrow.matches) return;
  closeCard();
  trail();
});

function ready() {
  if (data && plan !== undefined) render();
}

function load() {
  return fetch(`/api/v1/learn${chosen ? `?path_id=${encodeURIComponent(chosen)}` : ""}`)
    .then((r) => {
      if (window.redirectToLoginIfExpired(r)) return null;
      if (!r.ok) throw new Error(String(r.status));
      return r.json();
    })
    .then((d) => {
      if (!d) return;
      data = d;
      ready();
    })
    .catch(() => {
      window.clearBusy(page);
      sideEl.hidden = true;
      unitsEl.innerHTML = '<p class="error">Không tải được lộ trình. Hãy tải lại trang.</p>';
    });
}

// The first word from band_plan.js comes with the page; a later one means the
// plan was made or dropped, and with it what to study next: ask again.
document.addEventListener("bandplan", (e) => {
  const changed = plan !== undefined;
  plan = chosen ? null : e.detail;
  if (changed && data) load();
  else ready();
});

load();
