// The learner's roadmap (D025, M13; a trail since D027, drawn after Thắng's
// mockup in D092).
//
// One part per band, each a zigzag of lessons on a grey road: a tick once a
// lesson is complete, the golden coin with its "Bắt đầu" flag and its card for
// the lesson to study next, a padlock for the others. The padlock only says
// "not reached yet": nothing is locked -- a teacher may set any lesson -- so a
// click on any coin opens its card and its button. When the learner has chosen
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
const STATUS_TEXT = { completed: "Đã hoàn thành", started: "Đang học", new: "Chưa học", unavailable: "Không còn mở" };

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
  if (plan && plan.units && plan.units.length) {
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
    `<h1>Chào <span class="rm-name">${escapeHtml(getGreetingName())}</span>, sẵn sàng luyện nói hôm nay chưa? ${SPARK}` +
    `<span class="visually-hidden"> - ${escapeHtml(p.title)}</span></h1>` +
    "<p>Mỗi ngày vài phút phản xạ, nâng chuẩn CEFR vững vàng từng bước.</p>" +
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
  return narrow.matches
    ? { row: 46, top: 30, flag: 46, tail: 40, swing: [-26, 26], finale: 170 }
    : { row: 90, top: 50, flag: 62, tail: 74, swing: [-44, 40], finale: 250 };
}

function layout(lessons, nextId, g) {
  let y = g.top;
  return lessons.map((l, i) => {
    if (l.lesson_id === nextId) y += g.flag;
    const point = { x: g.swing[i % 2], y };
    y += g.row;
    return point;
  });
}

// The road winds: from each coin it leaves straight down and reaches the next
// straight from above, a smooth S between them (cubic Béziers with vertical
// tangents), then runs on past the last coin towards the next part. Drawn as a
// slab: a soft shadow and a darker side under the surface give it depth.
function roadHtml(points, height) {
  if (!points.length) return "";
  const last = points[points.length - 1];
  const all = [...points, { x: last.x + (last.x < 0 ? 26 : -26), y: height }];
  let d = `M${all[0].x} ${all[0].y}`;
  for (let i = 1; i < all.length; i += 1) {
    const a = all[i - 1];
    const z = all[i];
    const k = Math.round((z.y - a.y) * 0.55);
    d += ` C${a.x} ${a.y + k} ${z.x} ${z.y - k} ${z.x} ${z.y}`;
  }
  return (
    `<svg class="rm-road" width="2" height="${height}" viewBox="-1 0 2 ${height}" aria-hidden="true" focusable="false">` +
    `<path class="rm-road-shadow" d="${d}"/><path class="rm-road-side" d="${d}"/>` +
    `<path class="rm-road-edge" d="${d}"/><path class="rm-road-fill" d="${d}"/><path class="rm-road-dash" d="${d}"/></svg>`
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
    '<path d="M5 9.2h3.8M5 12.2h3.8M5 15.2h3.8M15.2 9.2H19M15.2 12.2H19M15.2 15.2H19" stroke="var(--glyph-ink)" stroke-width="1.4" stroke-linecap="round"/>',
  check: '<path d="m5 12.6 4.6 4.6L19.2 7.4" fill="none" stroke="currentColor" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"/>',
};
// A solid triangle, the play mark of the mockup's buttons.
const PLAY =
  '<svg class="icon rm-play-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">' +
  '<path d="M7 4.8c0-1 1.1-1.6 2-1.1l11.2 7.2c.8.5.8 1.7 0 2.2L9 20.3c-.9.5-2-.1-2-1.1Z" fill="currentColor"/></svg>';
const glyph = (name, cls = "rm-coin-icon") =>
  `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${GLYPHS[name]}</svg>`;

function nodeHtml(l, i, point, nextId) {
  const isNext = l.lesson_id === nextId;
  const isDone = l.status === "completed";
  const state = isNext ? "current next" : isDone ? "complete" : "locked";
  const mark = isNext ? "book" : isDone ? "check" : i % 3 === 2 ? "book" : "lock";
  const said = isNext ? (l.status === "started" ? "Đang học" : "Học tiếp theo") : STATUS_TEXT[l.status] || "Chưa học";
  const id = escapeHtml(l.lesson_id);
  let html =
    `<li class="lesson-node ${state} ${escapeHtml(l.status || "new")}" style="--dx:${point.x}px;--y:${point.y}px">` +
    `<button type="button" class="node-coin rm-coin" data-lesson="${id}" aria-expanded="false" ` +
    `aria-label="${escapeHtml(l.title)}, ${said}">${glyph(mark)}</button>` +
    `<span class="visually-hidden lesson-state">${STATUS_TEXT[l.status] || ""}</span>`;
  if (isNext) {
    html +=
      `<span class="node-flag rm-flag" aria-hidden="true">${l.status === "started" ? "Học tiếp" : "Bắt đầu"}</span>` +
      `<a class="rm-bubble" href="/practice/lessons/${encodeURIComponent(l.lesson_id)}">` +
      `<span class="rm-bubble-text"><small>Bài <b>${i + 1}</b></small><strong>${escapeHtml(l.title)}</strong>` +
      `<span class="rm-bubble-time">${icon("clock")}${minutes(l)}</span></span>` +
      `<span class="rm-play" aria-hidden="true">${PLAY}</span></a>`;
  }
  return `${html}</li>`;
}

// Scenery, as in the mockup: clouds, hills, a signpost, books, a mountain;
// the trophy at the end of the last part.
const HILL =
  '<svg class="rm-hill" viewBox="0 0 170 70" aria-hidden="true" focusable="false">' +
  '<path class="rm-hill-ground" d="M0 70C20 40 60 30 92 34s62 14 78 36Z"/>' +
  '<rect class="rm-trunk" x="104" y="34" width="4" height="18" rx="2"/><rect class="rm-trunk" x="124" y="40" width="3" height="14" rx="1.5"/>' +
  '<ellipse class="rm-leaf" cx="106" cy="24" rx="12" ry="16"/><ellipse class="rm-leaf-2" cx="125.5" cy="33" rx="9" ry="11"/></svg>';
const SIGN =
  '<svg class="rm-sign" viewBox="0 0 120 84" aria-hidden="true" focusable="false">' +
  '<path class="rm-hill-ground" d="M0 84c14-18 40-26 62-24s44 10 58 24Z"/>' +
  '<rect x="44" y="18" width="7" height="56" rx="3" fill="#b8742f"/>' +
  '<path d="M30 14h44l12 9-12 9H30Z" fill="#f2a24b"/><path d="M30 14h44l12 9H30Z" fill="#f7b866"/>' +
  '<ellipse class="rm-leaf-2" cx="22" cy="70" rx="12" ry="8"/><ellipse class="rm-leaf" cx="98" cy="68" rx="10" ry="7"/></svg>';
const BOOKS =
  '<svg class="rm-books" viewBox="0 0 130 70" aria-hidden="true" focusable="false">' +
  '<ellipse class="rm-hill-ground" cx="65" cy="62" rx="64" ry="8"/>' +
  '<rect x="30" y="44" width="70" height="14" rx="3" fill="#2eb6a5"/><rect x="32" y="47" width="58" height="8" rx="2" fill="#e9f7f4"/>' +
  '<rect x="26" y="30" width="72" height="14" rx="3" fill="#7bc74d"/><rect x="28" y="33" width="60" height="8" rx="2" fill="#f2f9ea"/>' +
  '<rect x="34" y="16" width="66" height="14" rx="3" fill="#ff8a2b"/><rect x="36" y="19" width="54" height="8" rx="2" fill="#fff4e8"/></svg>';
const MOUNTAIN =
  '<svg class="rm-mountain" viewBox="0 0 170 80" aria-hidden="true" focusable="false">' +
  '<path class="rm-hill-ground" d="M0 80 58 22l26 22 24-30 62 66Z"/>' +
  '<path class="rm-leaf-2" d="M108 14 92 34l10-4 6 6 6-6 12 4Z" opacity=".55"/>' +
  '<rect class="rm-trunk" x="122" y="56" width="3" height="12" rx="1.5"/><ellipse class="rm-leaf" cx="123.5" cy="50" rx="7" ry="10"/></svg>';
const TROPHY =
  '<svg class="rm-cup" viewBox="0 0 120 120" aria-hidden="true" focusable="false">' +
  '<circle cx="60" cy="60" r="56" class="rm-cup-glow"/>' +
  '<path d="M38 30h44v14c0 15-9 26-22 26S38 59 38 44Z" fill="#ffc21a"/>' +
  '<path d="M38 34H26c0 14 8 22 18 22M82 34h12c0 14-8 22-18 22" fill="none" stroke="#ffb000" stroke-width="5" stroke-linecap="round"/>' +
  '<rect x="55" y="68" width="10" height="12" fill="#f0a500"/><rect x="44" y="80" width="32" height="10" rx="3" fill="#e28c00"/>' +
  '<path d="m60 38 3.6 7.4 8 1.1-5.8 5.6 1.4 8-7.2-3.8-7.2 3.8 1.4-8-5.8-5.6 8-1.1Z" fill="#fff6d6"/></svg>';

// The meadow at the end of the road: two rolling hills, bushes, a few flowers.
const FLOWER = (x, y) =>
  `<g transform="translate(${x} ${y})"><path d="M0 0v12" stroke="#7cc561" stroke-width="1.6"/>` +
  '<circle cx="0" cy="-3" r="3.4" fill="#fff"/><circle cx="-3.4" cy="0" r="3.4" fill="#fff"/><circle cx="3.4" cy="0" r="3.4" fill="#fff"/>' +
  '<circle cx="0" cy="3" r="3.4" fill="#fff"/><circle cx="0" cy="0" r="2.4" fill="#ffc21a"/></g>';
const MEADOW =
  '<svg class="rm-meadow" viewBox="0 0 800 130" preserveAspectRatio="none" aria-hidden="true" focusable="false">' +
  '<path class="rm-hill-ground" d="M0 52C120 18 240 22 360 46s250 34 440 4V130H0Z"/>' +
  '<path class="rm-meadow-front" d="M0 84c140-30 280-26 420-6s260 24 380-2V130H0Z"/></svg>' +
  '<svg class="rm-bushes rm-bushes-l" viewBox="0 0 140 70" aria-hidden="true" focusable="false">' +
  '<circle class="rm-leaf-2" cx="40" cy="44" r="26"/><circle class="rm-leaf" cx="74" cy="40" r="30"/><circle class="rm-leaf-2" cx="106" cy="50" r="20"/>' +
  `${FLOWER(52, 58)}${FLOWER(84, 62)}</svg>` +
  '<svg class="rm-bushes rm-bushes-r" viewBox="0 0 140 70" aria-hidden="true" focusable="false">' +
  '<circle class="rm-leaf-2" cx="36" cy="50" r="20"/><circle class="rm-leaf" cx="70" cy="40" r="30"/><circle class="rm-leaf-2" cx="102" cy="46" r="24"/>' +
  `${FLOWER(48, 60)}${FLOWER(96, 62)}</svg>`;

function cloud(cls) {
  return `<span class="rm-deco rm-cloud ${cls}" aria-hidden="true"></span>`;
}

// The companion of a part: the owl's picture or a drawn one, with its tip.
// It stands beside a coin the card of the next lesson does not cover.
function mascotHtml(band, k, points, lessons, nextId) {
  const cast = window.rmMascots && window.rmMascots.CAST[band];
  if (!cast) return "";
  const n = points.length;
  const at = k === 0 ? Math.min(2, n - 1) : Math.max(0, Math.min(n - 1, Math.floor((n - 1) / 2)));
  const next = lessons.findIndex((l) => l.lesson_id === nextId);
  let side = k % 2 ? "right" : "left";
  if (side === "right" && next >= 0 && Math.abs(next - at) <= 1) side = "left";
  const art =
    cast.name === "owl"
      ? '<img src="/static/art/mascot_owl.png" alt="" width="178" height="153">'
      : window.rmMascots.ART[cast.name];
  return (
    `<span class="rm-deco rm-mascot rm-mascot-${side} rm-mascot-${cast.name}" style="--m-y:${points[at].y}px" aria-hidden="true">` +
    `<span class="rm-say">${escapeHtml(cast.tip)}</span><span class="rm-mascot-art">${art}</span></span>`
  );
}

function sceneryHtml(k, isLast, band) {
  if (k === 0) return "";
  const scenes = [
    "",
    cloud("rm-cloud-a") + `<span class="rm-deco rm-at-bl">${SIGN}</span><span class="rm-deco rm-at-br">${HILL}</span>`,
    cloud("rm-cloud-b") + `<span class="rm-deco rm-at-br">${HILL}</span>`,
    cloud("rm-cloud-a") + cloud("rm-cloud-c") + `<span class="rm-deco rm-at-bl">${BOOKS}</span>`,
    cloud("rm-cloud-a") + `<span class="rm-deco rm-at-r">${MOUNTAIN}</span>`,
    cloud("rm-cloud-b") + cloud("rm-cloud-c"),
  ];
  let html = scenes[k % scenes.length] || scenes[1];
  if (isLast) {
    html +=
      '<div class="rm-finale" aria-hidden="true">' +
      MEADOW +
      '<span class="rm-rays"></span>' +
      TROPHY +
      `<span class="rm-ribbon">Hoàn thành lộ trình ${escapeHtml(band)}</span></div>`;
  }
  return html;
}

let drawnNarrow = null;

function trail() {
  const g = geometry();
  drawnNarrow = narrow.matches;
  const nextId = data.next ? data.next.lesson_id : null;
  const all = parts();
  if (!all.length) {
    unitsEl.innerHTML = '<p class="muted rm-empty">Lộ trình này chưa có bài học.</p>';
    return;
  }
  unitsEl.innerHTML = all
    .map((part, k) => {
      const done = part.lessons.filter((l) => l.status === "completed").length;
      const total = part.lessons.length;
      const pct = total ? Math.round((done / total) * 100) : 0;
      const isLast = k === all.length - 1;
      const points = layout(part.lessons, nextId, g);
      const height = points[points.length - 1].y + g.tail;
      const band = part.band || "A1";
      return (
        `<section class="path-part rm-level band-${escapeHtml(band.toLowerCase())}" aria-labelledby="part-h-${k}">` +
        '<header class="rm-level-head">' +
        `<span class="rm-pill" aria-hidden="true">${escapeHtml(band)}</span>` +
        `<h2 class="rm-level-name" id="part-h-${k}"><span class="visually-hidden">${escapeHtml(band)}: </span>` +
        `Phần ${k + 1} · ${escapeHtml(LEVELS[band] || band)}</h2>` +
        `<div class="rm-level-stat"><span><b>${done}/${total}</b> bài hoàn thành</span>` +
        `<span class="rm-bar" role="progressbar" aria-label="Tiến độ ${escapeHtml(band)}" aria-valuemin="0" aria-valuemax="100" ` +
        `aria-valuenow="${pct}"><span style="width:${pct}%"></span></span></div>` +
        "</header>" +
        `<div class="rm-path${isLast ? " is-last" : ""}" style="--h:${height}px">` +
        sceneryHtml(k, isLast, band) +
        mascotHtml(band, k, points, part.lessons, nextId) +
        roadHtml(points, height) +
        `<ol class="rm-nodes">${part.lessons.map((l, i) => nodeHtml(l, i, points[i], nextId)).join("")}</ol>` +
        "</div></section>"
      );
    })
    .join("");
  wakeMascots();
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
  const { lesson: l, unit: u } = found;
  const action = l.status === "completed" ? "Học lại" : l.status === "started" ? "Học tiếp" : "Bắt đầu";
  const node = coin.closest(".lesson-node");
  const box = coin.closest(".rm-path");
  const card = document.createElement("div");
  card.id = "node-card";
  card.className = "rm-node-card";
  card.setAttribute("role", "dialog");
  card.setAttribute("aria-label", l.title);
  const facts = [
    `<li>${icon("layers")}${Number(l.steps) || 0} bước</li>`,
    l.passed ? `<li>${icon("check-circle")}đạt ${Number(l.passed)}/${Number(l.steps)}</li>` : "",
    l.criterion ? `<li>${icon("target")}${escapeHtml(window.ui.practiceName(l.criterion))}</li>` : "",
  ].join("");
  card.innerHTML =
    `<p class="rm-node-card-eyebrow">${escapeHtml(topicName(u) || (u && u.title) || "")}${l.band ? ` · ${escapeHtml(l.band)}` : ""}</p>` +
    `<h3>${escapeHtml(l.title)}</h3>` +
    (l.summary ? `<p class="rm-node-card-summary">${escapeHtml(l.summary)}</p>` : "") +
    `<ul class="rm-node-card-facts">${facts}</ul>` +
    (l.status === "unavailable"
      ? '<p class="muted">Bài này không còn mở. Hãy tạo lại lộ trình để thay bài khác.</p>'
      : `<a class="rm-btn rm-btn-orange" href="/practice/lessons/${encodeURIComponent(l.lesson_id)}">${PLAY}${action}</a>`);
  box.appendChild(card);
  // Under the coin, kept inside the roadmap's box.
  const width = Math.min(300, box.clientWidth - 16);
  const centre = node.offsetLeft;
  const left = Math.max(8, Math.min(box.clientWidth - width - 8, centre - width / 2));
  card.style.width = `${width}px`;
  card.style.left = `${left}px`;
  card.style.top = `${node.offsetTop + coin.offsetHeight / 2 + 14}px`;
  card.style.setProperty("--arrow", `${centre - left}px`);
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
  const action = l && l.status === "completed" ? "Luyện lại" : "Tiếp tục học";
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
    `<span class="rm-chip rm-chip-orange">${pct}%</span></div>` +
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
