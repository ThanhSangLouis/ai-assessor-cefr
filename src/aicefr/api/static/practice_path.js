// The learner's lesson path (D025, M13), drawn as a trail (D027).
//
// Three levels, each going through units on different topics; each unit is a
// winding trail of lessons. A lesson is a coin on the trail: a tick once
// complete, the icon of its first exercise otherwise. Nothing is locked -- a
// teacher may set any lesson -- lessons not reached yet are only faded. A click
// on a coin opens a card with the lesson and its button; the column beside the
// trail holds what to study next, today's speaking time and the reviews due.
// No score, no band and no ranking here.
const escapeHtml = window.escapeHtml;
const icon = (name, cls) => window.ui.icon(name, cls);
const page = document.getElementById("path-page");
const headEl = document.getElementById("path-head");
const unitsEl = document.getElementById("path-units");
const sideEl = document.getElementById("path-side");

const TOPICS = window.ui.TOPICS;
const LEVELS = { A1: "Khởi đầu", A2: "Cơ bản", B1: "Trung cấp", B2: "Nâng cao", C1: "Thành thạo" };
// The icon of a lesson is the icon of its first exercise.
const KIND_ICON = window.ui.STEP_ICONS;
const STATUS_TEXT = { completed: "Đã hoàn thành", started: "Đang học", new: "Chưa học" };
const WEEKDAY = ["CN", "T2", "T3", "T4", "T5", "T6", "T7"];

// The trail: rows of fixed height, coins swinging left and right of the centre.
const ROW = 124;
const COIN = 64;
const SWING = [0, 1, 1.45, 1, 0, -1, -1.45, -1];
const SWING_MAX = 1.45;
const narrow = window.matchMedia("(max-width: 640px)");
let data = null;

const dmy = (iso) => window.ui.dmy(iso);
const criterionName = window.ui.practiceName;
const topicOf = window.ui.topicOf;
const topicName = (u) => (TOPICS[u.topic] ? TOPICS[u.topic][0] : "");
const topicIcon = (u) => (TOPICS[u.topic] ? TOPICS[u.topic][1] : "path");

function dayLabel(iso) {
  const d = new Date(`${iso}T00:00:00`);
  return Number.isNaN(d.getTime()) ? iso : WEEKDAY[d.getDay()];
}

function findLesson(id) {
  for (const u of data.path.units) {
    const l = u.lessons.find((x) => x.lesson_id === id);
    if (l) return { lesson: l, unit: u };
  }
  return null;
}

// ---------------------------------------------------------------- head
function head() {
  const p = data.path;
  const pct = p.lessons_total ? Math.round((p.lessons_completed / p.lessons_total) * 100) : 0;
  const switcher =
    data.paths.length > 1
      ? '<div class="path-switch"><label for="path-select" class="visually-hidden">Lộ trình</label>' +
        '<select id="path-select">' +
        data.paths
          .map(
            (x) =>
              `<option value="${escapeHtml(x.path_id)}"${x.path_id === p.path_id ? " selected" : ""}>` +
              `${escapeHtml(x.title)}</option>`
          )
          .join("") +
        "</select></div>"
      : "";
  headEl.innerHTML =
    '<div class="path-title">' +
    `<h1>${escapeHtml(p.title)}</h1>` +
    (p.sample ? `<span class="badge sample-badge" title="Nội dung do nhóm phát triển soạn, chờ giảng viên duyệt">Nội dung mẫu</span>` : "") +
    "</div>" +
    '<div class="path-head-row">' +
    `<div class="overall" title="${Number(p.lessons_completed)}/${Number(p.lessons_total)} bài đã hoàn thành">` +
    icon("trophy") +
    `<div class="overall-track"><span style="width:${pct}%"></span></div>` +
    `<span class="muted">${Number(p.lessons_completed)}/${Number(p.lessons_total)} bài đã hoàn thành</span></div>` +
    switcher +
    "</div>";
  const select = document.getElementById("path-select");
  if (select) {
    select.addEventListener("change", () => {
      location.search = `?path=${encodeURIComponent(select.value)}`;
    });
  }
}

// ---------------------------------------------------------------- trail
function coinIcon(l) {
  if (l.status === "completed") return "check";
  return KIND_ICON[l.kinds[0]] || "mic";
}

function nodeHtml(l, i, swing, nextId, half, start) {
  const x = Math.round(SWING[(start + i) % SWING.length] * swing);
  const ratio = l.steps ? l.passed / l.steps : 0;
  const isNext = l.lesson_id === nextId;
  // The title sits beside the coin, on the side away from the centre line, so
  // the trail (which leaves a coin at its top and bottom) never crosses it.
  // Without room beside the outermost coin (a narrow column), every title of
  // the trail goes under its coin instead, so the trail reads one way.
  const room = Math.min(176, Math.floor(half - Math.abs(x) - COIN / 2 - 14));
  const roomy = half - SWING_MAX * swing - COIN / 2 - 14 >= 110;
  const side = !roomy ? "below" : x < 0 ? "left" : "right";
  const cls = `lesson-node ${escapeHtml(l.status)}${isNext ? " next" : ""} label-${side}`;
  return (
    `<li class="${cls}" style="--i:${i};--x:${x}px;--done:${Math.round(ratio * 100)};--room:${room}px">` +
    (isNext ? `<span class="node-flag" aria-hidden="true">${l.status === "new" ? "Bắt đầu" : "Học tiếp"}</span>` : "") +
    `<button type="button" class="node-coin" data-lesson="${escapeHtml(l.lesson_id)}" aria-expanded="false" ` +
    `aria-label="${escapeHtml(l.title)}, ${STATUS_TEXT[l.status] || ""}">` +
    icon(coinIcon(l), "icon coin-icon") +
    "</button>" +
    `<span class="lesson-title">${escapeHtml(l.title)}</span>` +
    `<span class="visually-hidden lesson-state">${STATUS_TEXT[l.status] || ""}</span>` +
    "</li>"
  );
}

// The line through the coins: one smooth curve per gap, solid once both ends
// are complete, dashed ahead.
function lineHtml(lessons, swing, start) {
  const width = Math.ceil(2 * SWING_MAX * swing + COIN + 24);
  const height = lessons.length * ROW;
  const centre = (i) => [Math.round(SWING[(start + i) % SWING.length] * swing), i * ROW + COIN / 2];
  let paths = "";
  for (let i = 0; i + 1 < lessons.length; i += 1) {
    const [x1, y1] = centre(i);
    const [x2, y2] = centre(i + 1);
    const done = lessons[i].status === "completed" && lessons[i + 1].status === "completed";
    paths +=
      `<path class="${done ? "done" : "ahead"}" d="M ${x1} ${y1 + COIN / 2 - 4} ` +
      `C ${x1} ${y1 + ROW / 2}, ${x2} ${y2 - ROW / 2}, ${x2} ${y2 - COIN / 2 + 4}"/>`;
  }
  return (
    `<svg class="trail-line" viewBox="${-width / 2} 0 ${width} ${height}" width="${width}" ` +
    `height="${height}" aria-hidden="true" focusable="false">${paths}</svg>`
  );
}

function unitHtml(u, swing, nextId, half, start) {
  const done = u.lessons.filter((l) => l.status === "completed").length;
  const name = topicName(u);
  return (
    `<section class="unit topic-${topicOf(u)}" aria-label="${escapeHtml(u.title)}">` +
    '<div class="unit-banner">' +
    `<span class="unit-icon">${icon(topicIcon(u))}</span>` +
    '<div class="unit-text">' +
    (name && name !== u.title ? `<p class="unit-topic">${escapeHtml(name)}</p>` : "") +
    `<h3>${escapeHtml(u.title)}</h3>` +
    (u.function ? `<p class="unit-fn">${escapeHtml(u.function)}</p>` : "") +
    "</div>" +
    `<span class="unit-count" title="${done}/${u.lessons.length} bài đã hoàn thành">${icon("check-circle")}${done}/${u.lessons.length}</span>` +
    "</div>" +
    (u.lessons.length
      ? `<div class="unit-trail" style="--n:${u.lessons.length}">${lineHtml(u.lessons, swing, start)}` +
        `<ol class="trail">${u.lessons.map((l, i) => nodeHtml(l, i, swing, nextId, half, start)).join("")}</ol></div>`
      : '<p class="muted unit-empty">Chặng này chưa có bài học.</p>') +
    "</section>"
  );
}

let drawnWidth = 0;

function trail() {
  const swing = narrow.matches ? 36 : 64;
  const nextId = data.next ? data.next.lesson_id : null;
  drawnWidth = unitsEl.clientWidth;
  const half = (drawnWidth || 600) / 2;
  // Units grouped into levels: a run of units of one band is one part.
  const parts = [];
  for (const u of data.path.units) {
    const last = parts[parts.length - 1];
    if (last && last.band === u.band) last.units.push(u);
    else parts.push({ band: u.band, units: [u] });
  }
  let start = 0;
  unitsEl.innerHTML = parts
    .map((part, k) => {
      const lessons = part.units.flatMap((u) => u.lessons);
      const done = lessons.filter((l) => l.status === "completed").length;
      return (
        `<section class="path-part band-${escapeHtml((part.band || "x").toLowerCase())}" aria-labelledby="part-h-${k}">` +
        '<header class="part-head">' +
        `<span class="part-badge">${escapeHtml(part.band || "·")}</span>` +
        `<div><p class="eyebrow">Phần ${k + 1}</p><h2 id="part-h-${k}">${escapeHtml(LEVELS[part.band] || part.band || "Lộ trình")}</h2></div>` +
        `<span class="part-count">${done}/${lessons.length} bài</span>` +
        "</header>" +
        part.units
          .map((u) => {
            // The trail keeps winding from one unit to the next.
            const html = unitHtml(u, swing, nextId, half, start);
            start += u.lessons.length;
            return html;
          })
          .join("") +
        "</section>"
      );
    })
    .join("");
}

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
  const action = l.status === "new" ? "Bắt đầu" : l.status === "completed" ? "Học lại" : "Học tiếp";
  const box = coin.closest(".unit-trail");
  const node = coin.closest(".lesson-node");
  const card = document.createElement("div");
  card.id = "node-card";
  card.className = `node-card topic-${topicOf(u)}`;
  card.setAttribute("role", "dialog");
  card.setAttribute("aria-label", l.title);
  card.innerHTML =
    `<p class="unit-topic">${escapeHtml(topicName(u) || u.title)} · ${escapeHtml(l.band)}</p>` +
    `<h3>${escapeHtml(l.title)}</h3>` +
    (l.summary ? `<p class="card-summary">${escapeHtml(l.summary)}</p>` : "") +
    '<ul class="card-facts">' +
    `<li>${icon("layers")}${Number(l.steps)} bước</li>` +
    (l.passed ? `<li>${icon("check-circle")}đạt ${Number(l.passed)}/${Number(l.steps)}</li>` : "") +
    (l.criterion ? `<li>${icon("target")}${escapeHtml(criterionName(l.criterion))}</li>` : "") +
    "</ul>" +
    `<a class="button" href="/practice/lessons/${encodeURIComponent(l.lesson_id)}">${icon("play")}${action}</a>`;
  box.appendChild(card);
  // Under the coin's label, kept inside the trail's box.
  const width = Math.min(300, box.clientWidth - 16);
  const centre = node.offsetLeft + COIN / 2;
  card.style.width = `${width}px`;
  card.style.left = `${Math.max(8, Math.min(box.clientWidth - width - 8, centre - width / 2))}px`;
  card.style.top = `${node.offsetTop + COIN + (node.classList.contains("label-below") ? 46 : 14)}px`;
  card.style.setProperty("--arrow", `${centre - parseFloat(card.style.left)}px`);
  coin.setAttribute("aria-expanded", "true");
  openCoin = coin;
  card.querySelector("a").focus({ preventScroll: true });
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
      '<section class="card side-card next-card" aria-labelledby="next-h">' +
      `<p class="eyebrow">${icon("sparkle")}Nên học tiếp</p>` +
      '<h2 id="next-h">Lộ trình chưa có bài học</h2></section>'
    );
  }
  const found = findLesson(n.lesson_id);
  const l = found && found.lesson;
  const u = found && found.unit;
  const action = !l || l.status === "new" ? "Bắt đầu" : l.status === "completed" ? "Học lại" : "Học tiếp";
  const a = data.assessment;
  const basis =
    n.basis === "weakest_criterion" && a
      ? `<p class="muted">Theo bài đánh giá ngày ${escapeHtml(dmy(a.created_at))}` +
        `${a.teacher_verified ? ", giảng viên đã xác nhận" : ", ước lượng của máy"}.</p>`
      : "";
  return (
    `<section class="card side-card next-card topic-${u ? topicOf(u) : "none"}" aria-labelledby="next-h">` +
    `<p class="eyebrow">${icon("sparkle")}${n.basis === "review_all" ? "Học lại" : "Nên học tiếp"}</p>` +
    '<div class="next-main">' +
    `<span class="unit-icon">${icon(u ? topicIcon(u) : "path")}</span>` +
    `<div><h2 id="next-h">${escapeHtml(n.title)}</h2>` +
    (l ? `<p class="next-meta">${escapeHtml(l.band)} · ${Number(l.steps)} bước${u && topicName(u) ? ` · ${escapeHtml(topicName(u))}` : ""}</p>` : "") +
    "</div></div>" +
    `<p class="next-reason">${escapeHtml(n.reason)}</p>` +
    basis +
    `<a class="button next-go" href="/practice/lessons/${encodeURIComponent(n.lesson_id)}">${icon("play")}${action}</a>` +
    "</section>"
  );
}

// "4 phút 10 giây", "50 giây".
function spoken(s) {
  const total = Math.round(Number(s) || 0);
  const m = Math.floor(total / 60);
  const sec = total % 60;
  if (!m) return `${sec} giây`;
  return sec ? `${m} phút ${sec} giây` : `${m} phút`;
}

// The streak with its record, the week with its rest days (a day off the rule
// lets the streak keep, D023), and the week against the one before: the only
// yardstick here is the learner's own past (D032).
function todayCard(t) {
  const seconds = Math.round(t.seconds);
  const goal = Number(t.goal_seconds);
  const pct = Math.min(100, Math.round((seconds / Math.max(1, goal)) * 100));
  const rest = new Set(t.rest_days || []);
  const dots = t.week
    .map((w) => {
      const kind = w.seconds > 0 ? "on" : rest.has(w.date) ? "rest" : "";
      const said = kind === "rest" ? "nghỉ, chuỗi vẫn giữ" : `${Math.round(w.seconds)} giây`;
      return (
        `<li class="${kind}" title="${escapeHtml(dmy(w.date))}: ${said}">` +
        `<span class="dot" aria-hidden="true"></span>${dayLabel(w.date)}</li>`
      );
    })
    .join("");
  const days = t.week.filter((w) => w.seconds > 0).length;
  const streak = Number(t.streak) || 0;
  const best = Number(t.best_streak) || 0;
  let record = "";
  if (best > streak) record = `<p class="streak-best">Kỷ lục của bạn: <b>${best}</b> ngày</p>`;
  else if (streak >= 2) record = '<p class="streak-best">Đang là kỷ lục của bạn</p>';
  const before = Number(t.last_week_seconds) || 0;
  return (
    '<section class="card side-card today-card" aria-labelledby="today-h">' +
    `<h2 id="today-h">${icon("target")}Hôm nay</h2>` +
    '<div class="today-row">' +
    `<div class="goal-ring" style="--pct:${pct}" role="img" aria-label="Đã nói ${seconds} trên ${goal} giây hôm nay">` +
    `<span><b>${seconds}</b>/${goal} giây</span></div>` +
    '<div class="today-facts">' +
    `<p class="streak">${icon("flame", "icon flame")}<b>${streak}</b> ngày liên tiếp</p>` +
    record +
    `<p class="goal-text">${t.goal_met ? "Đã đạt mục tiêu hôm nay." : `Nói thêm ${goal - seconds} giây.`}</p>` +
    "</div></div>" +
    `<ol class="week-dots" aria-label="Bảy ngày gần nhất, ${days} ngày có luyện">${dots}</ol>` +
    `<p class="week-sum">7 ngày qua: <b>${spoken(t.week_seconds)}</b>` +
    (before > 0 ? ` <span>· 7 ngày trước đó: ${spoken(before)}</span>` : "") +
    "</p>" +
    "</section>"
  );
}

// Achievements (D032): how many, which are new, the last few, the nearest.
// Effort only and private; the full list is on the progress page.
function achievementsCard(a) {
  if (!a) return "";
  const n = Number(a.unlocked) || 0;
  const fresh = Number(a.new) || 0;
  const medals = (a.recent || [])
    .map(
      (x) =>
        `<li title="${escapeHtml(x.title)}">${icon(x.icon)}` +
        `<span class="visually-hidden">${escapeHtml(x.title)}</span></li>`
    )
    .join("");
  const next = a.next;
  let ahead = "";
  if (next) {
    const value = Number(next.value);
    const target = Math.max(1, Number(next.target));
    ahead =
      `<p class="ach-next">Sắp đạt: <b>${escapeHtml(next.title)}</b>` +
      ` <span>${value}/${target} ${escapeHtml(next.unit)}</span></p>` +
      `<div class="bar" role="progressbar" aria-label="${escapeHtml(next.title)}" aria-valuemin="0"` +
      ` aria-valuemax="${target}" aria-valuenow="${value}"><span style="width:${Math.round((value / target) * 100)}%"></span></div>`;
  } else if (!n) {
    ahead = '<p class="muted">Ghi lượt nói đầu tiên để mở thành tựu đầu tiên.</p>';
  }
  return (
    '<section class="card side-card ach-card" aria-labelledby="ach-h">' +
    `<h2 id="ach-h">${icon("trophy")}Thành tựu` +
    `<span class="ach-tally"><b>${n}</b>/${Number(a.total)}</span></h2>` +
    (medals || fresh
      ? '<div class="ach-row">' +
        (medals ? `<ul class="ach-medals" aria-label="Đạt gần đây">${medals}</ul>` : "") +
        (fresh ? `<span class="ach-fresh">${fresh} mới</span>` : "") +
        "</div>"
      : "") +
    ahead +
    `<a class="ach-all" href="/my-progress#achievements">Xem tất cả${icon("chevron-right")}</a>` +
    "</section>"
  );
}

function reviewCard(due) {
  const n = Number(due) || 0;
  return (
    '<section class="card side-card review-card" aria-labelledby="review-h">' +
    `<h2 id="review-h">${icon("refresh")}Ôn tập</h2>` +
    `<p class="review-count">${n} <small>mục đến hạn</small></p>` +
    (n
      ? `<a class="button" href="/practice/review">${icon("play")}Ôn ngay</a>`
      : '<p class="muted">Từ máy chưa nghe ra sẽ quay lại đây sau 1, 3 rồi 7 ngày.</p>') +
    "</section>"
  );
}

// ---------------------------------------------------------------- render
function render() {
  window.clearBusy(page);
  if (!data.path) {
    headEl.innerHTML = "<h1>Lộ trình luyện nói</h1>";
    sideEl.hidden = true;
    unitsEl.innerHTML =
      '<div class="card"><div class="empty-state"><div class="empty-mark" aria-hidden="true">◇</div>' +
      "<h2>Chưa có lộ trình nào được xuất bản</h2>" +
      "<p>Giảng viên của bạn sẽ xuất bản lộ trình học. Trong lúc chờ, bạn vẫn làm được bài đánh giá ở trang Nộp bài.</p>" +
      "</div></div>";
    return;
  }
  head();
  sideEl.innerHTML =
    nextCard() + todayCard(data.today) + reviewCard(data.reviews_due) + achievementsCard(data.achievements);
  trail();
  fitSide();
}

// The side column follows the page down while it fits in the window. Taller
// than the window, a sticky column keeps its last cards out of sight until
// the end of the trail, so it then scrolls with the page instead.
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

// The swing of the trail and the room for titles follow the column's width;
// redraw when it changes enough to matter.
let redraw = null;
new ResizeObserver(() => {
  if (!data || !data.path || Math.abs(unitsEl.clientWidth - drawnWidth) < 24) return;
  clearTimeout(redraw);
  redraw = setTimeout(() => {
    closeCard();
    trail();
  }, 150);
}).observe(unitsEl);

const chosen = new URLSearchParams(location.search).get("path");
fetch(`/api/v1/learn${chosen ? `?path_id=${encodeURIComponent(chosen)}` : ""}`)
  .then((r) => {
    if (window.redirectToLoginIfExpired(r)) return null;
    if (!r.ok) throw new Error(String(r.status));
    return r.json();
  })
  .then((d) => {
    if (!d) return;
    data = d;
    render();
  })
  .catch(() => {
    window.clearBusy(page);
    sideEl.hidden = true;
    unitsEl.innerHTML = '<p class="error">Không tải được lộ trình. Hãy tải lại trang.</p>';
  });
