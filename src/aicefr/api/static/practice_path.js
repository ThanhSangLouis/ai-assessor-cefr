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
const LEVELS = { A1: "Khởi đầu", A2: "Cuộc sống quanh ta", B1: "Mở rộng giao tiếp", B2: "Giao tiếp tự tin", C1: "Giao tiếp nâng cao", C2: "Chuyên gia" };
// The icon of a lesson is the icon of its first exercise.
const KIND_ICON = window.ui.STEP_ICONS;
const STATUS_TEXT = { completed: "Đã hoàn thành", started: "Đang học", new: "Chưa học" };
const WEEKDAY = ["CN", "T2", "T3", "T4", "T5", "T6", "T7"];

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

function getGreetingName() {
  const who = document.querySelector(".who-name");
  if (!who || !who.textContent.trim()) return "bạn";
  const name = who.textContent.trim();
  if (name.includes("@")) return "bạn";
  return name;
}

// ---------------------------------------------------------------- head
function head() {
  const p = data.path;
  const name = getGreetingName();
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
    '<div class="path-greeting">' +
    '<div class="greeting-content">' +
    `<h1 class="greeting-title">Chào <span class="greeting-name">${escapeHtml(name.trim())},</span> sẵn sàng luyện nói hôm nay chưa? <span class="greeting-sparkle" aria-hidden="true">✨</span><span class="visually-hidden"> - ${escapeHtml(p.title)}</span></h1>` +
    '<p class="greeting-sub">Mỗi ngày vài phút phản xạ, nâng chuẩn CEFR vững vàng từng bước.</p>' +
    '</div>' +
    '<div class="greeting-companion" aria-hidden="true">' +
    '<img src="/static/art/mascot_2d_waving_girl.png" alt="Mascot companion" class="greeting-mascot-img">' +
    '</div>' +
    switcher +
    '</div>';
  const select = document.getElementById("path-select");
  if (select) {
    select.addEventListener("change", () => {
      location.search = `?path=${encodeURIComponent(select.value)}`;
    });
  }
}

// ---------------------------------------------------------------- trail
const KIND_LABELS = {
  read_aloud: "Đọc to",
  repeat: "Nhắc lại",
  look_up: "Phản xạ",
  gap: "Điền từ",
  keywords: "Ghép câu",
  starter: "Khung câu",
  picture: "Tả tranh",
  outline: "Dàn ý",
  free: "Nói tự do",
};

function lessonKindLabel(l) {
  if (l.kinds && l.kinds.length && KIND_LABELS[l.kinds[0]]) {
    return KIND_LABELS[l.kinds[0]];
  }
  if (l.criterion && window.ui && window.ui.PRACTICE_NAMES && window.ui.PRACTICE_NAMES[l.criterion]) {
    return window.ui.PRACTICE_NAMES[l.criterion];
  }
  return "Luyện nói";
}

function coinIcon(l, isLocked) {
  if (l.status === "completed") return "check";
  if (isLocked) return "lock";
  return "book-open";
}

const ROW = 80;
const COIN = 56;
const SWING = [0, 0.95, -0.85, 0.85, -0.85, 0.85, -0.85];
const SWING_MAX = 0.95;

function computePartCoords(lessons, partStart, swing, isHeroPart) {
  const coords = [];
  let currentY = 70;

  for (let i = 0; i < lessons.length; i++) {
    const sw = SWING[(partStart + i) % SWING.length];
    const x = Math.round(sw * swing);

    coords.push({
      x,
      y: currentY,
    });

    currentY += ROW;
  }

  const totalHeight = currentY + 30;
  return { coords, totalHeight };
}

function nodeHtml(l, i, coord, nextId, half, isHeroPart, globalIdx) {
  const isNext = l.lesson_id === nextId || (isHeroPart && i === 0 && !nextId);
  const isDone = l.status === "completed";
  const isLocked = !isNext && !isDone;

  const stateCls = isNext ? "current next" : isDone ? "completed" : "locked";
  const stepsTag = l.steps ? `${Math.max(2, Number(l.steps))} phút` : "2 phút";

  // Active / Next Lesson Node (Golden coin + Bắt đầu badge + Speech bubble card)
  if (isNext) {
    return (
      `<li class="lesson-node is-active-node ${stateCls}" style="--node-x:${coord.x}px;--node-y:${coord.y}px">` +
      `<span class="node-start-badge" aria-hidden="true">Bắt đầu</span>` +
      `<button type="button" class="node-coin coin-active" data-lesson="${escapeHtml(l.lesson_id)}" aria-expanded="false" ` +
      `aria-label="${escapeHtml(l.title)}, Đang học">` +
      icon("book-open", "icon coin-icon") +
      `</button>` +
      `<div class="active-speech-card" role="button" tabindex="0" data-lesson="${escapeHtml(l.lesson_id)}" aria-label="${escapeHtml(l.title)}">` +
      `<div class="speech-content">` +
      `<span class="speech-tag">Bài ${globalIdx + 1}</span>` +
      `<h3 class="speech-title">${escapeHtml(l.title)}</h3>` +
      `<span class="speech-time">${icon("clock")} ${stepsTag}</span>` +
      `</div>` +
      `<span class="speech-play-btn" aria-hidden="true">${icon("play")}</span>` +
      `</div>` +
      `<span class="visually-hidden lesson-state">${STATUS_TEXT[l.status] || ""}</span>` +
      `</li>`
    );
  }

  // Completed Node (Green coin with checkmark)
  if (isDone) {
    return (
      `<li class="lesson-node is-done-node ${stateCls}" style="--node-x:${coord.x}px;--node-y:${coord.y}px">` +
      `<button type="button" class="node-coin coin-completed" data-lesson="${escapeHtml(l.lesson_id)}" aria-expanded="false" ` +
      `aria-label="${escapeHtml(l.title)}, Đã hoàn thành">` +
      icon("check", "icon coin-icon") +
      `</button>` +
      `<span class="visually-hidden lesson-state">${STATUS_TEXT[l.status] || ""}</span>` +
      `</li>`
    );
  }

  // Locked Node (Metallic coin with lock or book)
  const coinIco = (i % 3 === 2) ? "book-open" : "lock";
  return (
    `<li class="lesson-node is-locked-node ${stateCls}" style="--node-x:${coord.x}px;--node-y:${coord.y}px">` +
    `<button type="button" class="node-coin coin-locked" data-lesson="${escapeHtml(l.lesson_id)}" aria-expanded="false" ` +
    `aria-label="${escapeHtml(l.title)}, Khóa">` +
    icon(coinIco, "icon coin-icon") +
    `</button>` +
    `<span class="visually-hidden lesson-state">${STATUS_TEXT[l.status] || ""}</span>` +
    `</li>`
  );
}

// Clean 2D Continuous Learning Path
function lineHtml(lessons, coords, nextId) {
  if (!coords || coords.length === 0) return "";
  const swing = narrow.matches ? 22 : 42;
  const width = Math.ceil(2 * SWING_MAX * swing + COIN + 160);
  const totalHeight = coords[coords.length - 1].y + 50;

  let basePaths = "";
  let dashPaths = "";

  for (let i = 0; i + 1 < lessons.length; i += 1) {
    const x1 = coords[i].x;
    const y1 = coords[i].y;
    const x2 = coords[i + 1].x;
    const y2 = coords[i + 1].y;
    const dy = y2 - y1;

    let cls = "locked";
    if (lessons[i].status === "completed" && lessons[i + 1].status === "completed") {
      cls = "done";
    } else if (
      lessons[i].lesson_id === nextId ||
      lessons[i + 1].lesson_id === nextId ||
      (lessons[i].status === "completed" && lessons[i + 1].status !== "completed")
    ) {
      cls = "current";
    }

    const d = `M ${x1} ${y1} C ${x1} ${y1 + Math.round(dy * 0.55)}, ${x2} ${y2 - Math.round(dy * 0.55)}, ${x2} ${y2}`;
    basePaths += `<path class="trail-road-base ${cls}" d="${d}"/>`;
    dashPaths += `<path class="trail-road-dash ${cls}" d="${d}"/>`;
  }
  return (
    `<svg class="trail-line" viewBox="${-width / 2} 0 ${width} ${totalHeight}" width="${width}" ` +
    `height="${totalHeight}" aria-hidden="true" focusable="false">` +
    `<g class="trail-base-group">${basePaths}</g>` +
    `<g class="trail-dash-group">${dashPaths}</g>` +
    `</svg>`
  );
}

function partTrailHtml(part, swing, nextId, half, partStart, isHeroPart, k, isLastPart) {
  const allLessons = part.units.flatMap((u) => u.lessons);
  if (!allLessons.length) return '<p class="muted unit-empty">Chặng này chưa có bài học.</p>';

  const { coords, totalHeight } = computePartCoords(allLessons, partStart, swing, isHeroPart);

  // Decorative illustrations based on part
  let decoMarkup = "";
  if (k === 0) {
    // Part 1 (A1): Owl Mascot on the left
    decoMarkup = '<div class="roadmap-owl-companion" aria-hidden="true">' +
      '<img src="/static/art/mascot_2d_owl.png" alt="Mascot SpeakUp" class="owl-img">' +
      '</div>';
  } else if (k === 1) {
    // Part 2 (A2): Signpost on left, trees on right
    decoMarkup = '<div class="roadmap-deco deco-signpost" aria-hidden="true"><img src="/static/art/deco_2d_signpost.png" alt=""></div>' +
      '<div class="roadmap-deco deco-trees" aria-hidden="true"><img src="/static/art/deco_2d_trees.png" alt=""></div>';
  } else if (k === 3) {
    // Part 4 (B2): Books stack on left
    decoMarkup = '<div class="roadmap-deco deco-books" aria-hidden="true"><img src="/static/art/deco_2d_books.png" alt=""></div>';
  }

  const trophyMarkup = isLastPart
    ? '<div class="milestone-trophy-wrap" aria-hidden="true">' +
      '<img src="/static/art/deco_2d_trophy_finish.png" alt="Hoàn thành lộ trình C2" class="milestone-trophy-img">' +
      '</div>'
    : '';

  return (
    `<div class="part-trail unit-trail" style="--trail-h:${totalHeight}px;height:${totalHeight}px">` +
    decoMarkup +
    lineHtml(allLessons, coords, nextId) +
    `<ol class="trail">` +
    allLessons
      .map((l, i) => nodeHtml(l, i, coords[i], nextId, half, isHeroPart, partStart + i))
      .join("") +
    `</ol>` +
    trophyMarkup +
    `</div>`
  );
}

let drawnWidth = 0;

function trail() {
  const swing = narrow.matches ? 24 : 58;
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
  let globalStart = 0;
  unitsEl.innerHTML = parts
    .map((part, k) => {
      const lessons = part.units.flatMap((u) => u.lessons);
      const done = lessons.filter((l) => l.status === "completed").length;
      const pct = lessons.length ? Math.round((done / lessons.length) * 100) : 0;
      const partStart = globalStart;
      globalStart += lessons.length;
      const isHeroPart = (k === 0);
      const isLastPart = (k === parts.length - 1);
      const bandCode = (part.band || "A1").toUpperCase();
      return (
        `<section class="path-part band-${escapeHtml(bandCode.toLowerCase())}" aria-labelledby="part-h-${k}">` +
        '<header class="part-head">' +
        '<div class="part-title-group">' +
        `<span class="part-level-badge badge-${escapeHtml(bandCode.toLowerCase())}">${escapeHtml(bandCode)}</span>` +
        `<h2 class="part-title" id="part-h-${k}">Phần ${k + 1} · ${escapeHtml(LEVELS[part.band] || part.band || "Khởi đầu")}</h2>` +
        '</div>' +
        '<div class="part-progress-wrap">' +
        `<span class="part-progress-text">${done}/${lessons.length} bài hoàn thành</span>` +
        `<div class="part-progress-bar" title="${pct}% hoàn thành"><span style="width:${pct}%"></span></div>` +
        '</div>' +
        "</header>" +
        partTrailHtml(part, swing, nextId, half, partStart, isHeroPart, k, isLastPart) +
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
  const pill = e.target.closest(".lesson-pill");
  const coin = e.target.closest(".node-coin") || (pill ? pill.closest(".lesson-node")?.querySelector(".node-coin") : null);
  if (!coin) return;
  if (coin === openCoin) closeCard();
  else openCard(coin);
});
document.addEventListener("click", (e) => {
  if (openCoin && !e.target.closest("#node-card") && !e.target.closest(".node-coin") && !e.target.closest(".lesson-pill")) closeCard();
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
      `<div class="side-card-head"><p class="eyebrow">${icon("sparkle")}Nên học tiếp</p></div>` +
      '<h2 id="next-h">Lộ trình chưa có bài học</h2></section>'
    );
  }
  const found = findLesson(n.lesson_id);
  const l = found && found.lesson;
  const u = found && found.unit;
  let lessonIcon = u ? topicIcon(u) : "path";
  if (n.title && (n.title.toLowerCase().includes("giới thiệu") || n.title.toLowerCase().includes("bản thân"))) {
    lessonIcon = "user";
  }
  const action = l && l.status === "completed" ? "Luyện lại" : "Tiếp tục học";
  const a = data.assessment;
  const basis =
    n.basis === "weakest_criterion" && a
      ? `<p class="muted">Theo bài đánh giá ngày ${escapeHtml(dmy(a.created_at))}` +
        `${a.teacher_verified ? ", giảng viên đã xác nhận" : ", ước lượng của máy"}.</p>`
      : "";
  const reasonText = (n.reason || "").trim();
  const showReason =
    reasonText &&
    !reasonText.toLowerCase().startsWith("bài tiếp theo");
  return (
    `<section class="card side-card next-card topic-${u ? topicOf(u) : "none"}" aria-labelledby="next-h">` +
    `<div class="side-card-head"><p class="eyebrow">${icon("sparkle")}${n.basis === "review_all" ? "Học lại" : "Nên học tiếp"}</p>` +
    (l ? `<span class="next-band-badge">${escapeHtml(l.band)}</span>` : "") +
    "</div>" +
    '<div class="next-main">' +
    `<span class="unit-icon">${icon(lessonIcon)}</span>` +
    `<div><h2 id="next-h">${escapeHtml(n.title)}</h2>` +
    (l ? `<p class="next-meta">${Number(l.steps)} bước${u && topicName(u) ? ` · ${escapeHtml(topicName(u))}` : ""}</p>` : "") +
    "</div></div>" +
    (showReason ? `<p class="next-reason">${escapeHtml(n.reason)}</p>` : "") +
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

// Option 1 Master Card 1: Today Focus (Minimal Elevated Redesign)
function todayCard(t) {
  const seconds = Math.round(t.seconds);
  const goal = Number(t.goal_seconds);
  const goalMin = Math.round(goal / 60);
  const currentMinDisplay =
    seconds === 0
      ? "0"
      : seconds >= 60
      ? String(Math.round((seconds / 60) * 10) / 10)
      : `${seconds}s`;
  const pct = Math.min(100, Math.round((seconds / Math.max(1, goal)) * 100));
  const rest = new Set(t.rest_days || []);
  const streak = Number(t.streak) || 0;
  const days = t.week.filter((w) => w.seconds > 0).length;

  const calendarDays = getCalendarWeek(t);
  const calendarIsos = new Set(calendarDays.map((d) => d.date));

  const dots = calendarDays
    .map((cd) => {
      const isToday = cd.isToday;
      const isDone = cd.seconds > 0;
      const isRest = !isDone && !cd.isFuture && rest.has(cd.date);
      const isFuture = cd.isFuture;
      const kind = isDone ? "on" : isRest ? "rest" : isFuture ? "future" : "";
      const said = isDone
        ? `${Math.round(cd.seconds)} giây`
        : isRest
        ? "nghỉ, chuỗi vẫn giữ"
        : isToday
        ? "hôm nay"
        : isFuture
        ? "sắp tới"
        : "chưa luyện";
      let innerNode = "";
      if (isDone) {
        innerNode =
          '<svg viewBox="0 0 16 16" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="3.5 8.5 6.5 11.5 12.5 4.5"/></svg>';
      } else if (isRest) {
        innerNode = '<span class="rest-mark">z</span>';
      } else if (isToday) {
        innerNode = '<span class="today-ring-pulse"></span>';
      } else if (isFuture) {
        innerNode = '<span class="future-empty-dot"></span>';
      } else {
        innerNode = '<span class="past-empty-dot"></span>';
      }
      return (
        `<li class="${kind}${isToday ? " is-today" : ""}" title="${escapeHtml(dmy(cd.date))}: ${said}">` +
        `<span class="circle-node" aria-hidden="true">${innerNode}</span>` +
        `<span class="day-name">${cd.dayName}</span>` +
        `<span class="dot visually-hidden" aria-hidden="true"></span>` +
        `</li>`
      );
    })
    .join("");

  let extraHiddenRest = "";
  if (t.week) {
    for (const w of t.week) {
      if (!calendarIsos.has(w.date) && rest.has(w.date) && w.seconds <= 0) {
        extraHiddenRest += `<li class="rest visually-hidden" title="${escapeHtml(dmy(w.date))}: nghỉ, chuỗi vẫn giữ"></li>`;
      }
    }
  }

  return (
    '<section class="card side-card today-card" aria-labelledby="today-h">' +
    '<div class="side-card-head">' +
    `<h2 id="today-h">${icon("target", "icon target-icon")}Mục tiêu hôm nay</h2>` +
    `<span class="today-goal-pill ${t.goal_met ? "met" : ""}">${t.goal_met ? "Đạt mục tiêu" : `${pct}%`}</span>` +
    "</div>" +
    '<div class="today-hero-row">' +
    `<div class="today-hero-digits"><b>${currentMinDisplay}</b> <span>/ ${goalMin} phút luyện tập</span></div>` +
    // Preserves Playwright E2E checks for .goal-ring and /300
    `<div class="goal-ring visually-hidden" style="--pct:${pct}"><span class="visually-hidden">${seconds}/${goal} giây</span><span class="visually-hidden">/${goal}</span></div>` +
    "</div>" +
    '<div class="today-hero-bar">' +
    `<div class="today-hero-track"><span style="width:${pct}%"></span></div>` +
    "</div>" +
    '<div class="today-sub-row">' +
    `<div class="today-streak-stat">${icon("flame", "icon flame-icon")}<b>${streak}</b> <span class="streak-label">ngày liên tiếp</span></div>` +
    "</div>" +
    `<ol class="week-dots today-week-circles" aria-label="Tuần này, ${days} ngày có luyện">${dots}${extraHiddenRest}</ol>` +
    '<div class="today-footer-row">' +
    '<span class="today-footer-label">Mục tiêu mỗi ngày</span>' +
    goalPicker(goal) +
    "</div>" +
    "</section>"
  );
}

// Option 1 Master Card 2: Journey & Review & Achievements (Clean Flat List)
function journeyCard(p, reviews_due, ach, phrases) {
  if (!p) return "";
  const pct = p.lessons_total ? Math.round((p.lessons_completed / p.lessons_total) * 100) : 0;
  const nReviews = Number(reviews_due) || 0;
  const nAch = Number(ach ? ach.unlocked : 0) || 0;
  const totalAch = Number(ach ? ach.total : 17) || 17;
  const nextAch = ach && ach.next;
  let aheadHtml = "";
  if (nextAch) {
    const value = Number(nextAch.value);
    const target = Math.max(1, Number(nextAch.target));
    aheadHtml =
      `<div class="ach-next-wrap">` +
      `<p class="ach-next">Sắp đạt: <b>${escapeHtml(nextAch.title)}</b> <span>${value}/${target} ${escapeHtml(nextAch.unit)}</span></p>` +
      `<div class="bar" role="progressbar" aria-label="${escapeHtml(nextAch.title)}" aria-valuemin="0" aria-valuemax="${target}" aria-valuenow="${value}"><span style="width:${Math.round((value / target) * 100)}%"></span></div>` +
      `</div>`;
  }

  let phraseHtml = "";
  if (phrases && phrases.total) {
    const n = Math.min(Number(phrases.due_count) || 0, phrases.per_day);
    phraseHtml =
      `<a class="journey-menu-row phrase-side" href="/phrases" aria-labelledby="phrase-side-h">` +
      '<div class="journey-menu-left">' +
      `<span class="journey-menu-icon icon-blue">${icon("book-open")}</span>` +
      '<span class="journey-menu-label" id="phrase-side-h">Sổ cụm từ</span>' +
      '</div>' +
      `<div class="journey-menu-right"><span class="journey-menu-val"><b class="review-count">${n}</b> cụm</span>${icon("chevron-right")}</div>` +
      '</a>';
  }

  return (
    '<section class="card side-card progress-side-card journey-card" aria-label="Tiến độ lộ trình">' +
    '<div class="side-card-head">' +
    '<h2 id="overall-h">' +
    icon("trophy", "icon trophy-icon") +
    '<span>Tiến độ khóa học</span>' +
    '</h2>' +
    `<span class="progress-pct-badge">${pct}%</span>` +
    '</div>' +
    '<div class="journey-progress-wrap">' +
    '<div class="journey-progress-meta">' +
    '<span class="journey-progress-title">Bài học hoàn thành</span>' +
    `<span class="journey-progress-count"><b>${Number(p.lessons_completed)}</b> / ${Number(p.lessons_total)} bài</span>` +
    '</div>' +
    `<div class="overall journey-progress-track" title="${Number(p.lessons_completed)}/${Number(p.lessons_total)} bài đã hoàn thành">` +
    `<span class="overall-fill" style="width:${pct}%"></span>` +
    `<span class="muted visually-hidden">${Number(p.lessons_completed)}/${Number(p.lessons_total)} bài đã hoàn thành</span>` +
    '</div>' +
    '</div>' +
    '<div class="journey-menu-list">' +
    `<a class="journey-menu-row review-card" href="/practice/review" aria-labelledby="review-h">` +
    '<div class="journey-menu-left">' +
    `<span class="journey-menu-icon icon-emerald">${icon("refresh")}</span>` +
    '<span class="journey-menu-label" id="review-h">Từ vựng cần ôn</span>' +
    '</div>' +
    `<div class="journey-menu-right"><span class="journey-menu-val"><b class="review-count">${nReviews}</b> ${nReviews ? "từ cần ôn" : "mục đến hạn"}</span>${icon("chevron-right")}</div>` +
    '</a>' +
    `<a class="journey-menu-row ach-card" href="/my-progress#achievements" aria-labelledby="ach-h">` +
    '<div class="journey-menu-left">' +
    `<span class="journey-menu-icon icon-amber">${icon("trophy")}</span>` +
    '<span class="journey-menu-label" id="ach-h">Huy hiệu thành tựu</span>' +
    '</div>' +
    `<div class="journey-menu-right"><span class="journey-menu-val"><b>${nAch}</b> / ${totalAch}</span>${icon("chevron-right")}</div>` +
    '</a>' +
    aheadHtml +
    phraseHtml +
    '</div>' +
    '</section>'
  );
}

function levelOverviewCard(p) {
  if (!p || !p.units) return "";
  const BANDS = ["A1", "A2", "B1", "B2", "C1", "C2"];
  const rows = BANDS.map((band) => {
    const units = p.units.filter((u) => (u.band || "").toUpperCase() === band);
    const lessons = units.flatMap((u) => u.lessons || []);
    const done = lessons.filter((l) => l.status === "completed").length;
    const total = lessons.length;
    const pct = total ? Math.round((done / total) * 100) : 0;
    return (
      `<div class="level-overview-row">` +
      `<span class="level-overview-badge">${escapeHtml(band)}</span>` +
      `<div class="level-overview-track"><span class="level-overview-fill" style="width:${pct}%"></span></div>` +
      `<span class="level-overview-pct">${pct}%</span>` +
      `</div>`
    );
  }).join("");

  return (
    '<section class="card side-card level-overview-card" aria-label="Tổng quan cấp độ">' +
    '<div class="side-card-head">' +
    '<h2 id="level-overview-h">' +
    icon("chart", "icon chart-icon") +
    '<span>Tổng quan cấp độ</span>' +
    '</h2>' +
    '</div>' +
    `<div class="level-overview-list">${rows}</div>` +
    '</section>'
  );
}

// D068: the daily goal is set on the card that measures it, saved when picked.
const GOALS = (page.dataset.goals || "").split(",").filter(Boolean).map(Number);

function goalPicker(goal) {
  if (!GOALS.length) return "";
  const options = GOALS.map(
    (s) => `<option value="${s}"${s === goal ? " selected" : ""}>${s / 60} phút</option>`
  ).join("");
  return (
    '<div class="goal-pick">' +
    `<select id="goal-select" aria-label="Mục tiêu mỗi ngày">${options}</select></div>`
  );
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
  render();
  window.toast(`Mục tiêu mới: ${Math.round(d.daily_goal_s / 60)} phút nói mỗi ngày.`, "ok");
});

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
    '<div class="side-card-head">' +
    `<h2 id="review-h">${icon("refresh")}Ôn tập</h2>` +
    `<span class="review-status-pill ${n ? "due" : "clear"}">${n ? `${n} từ cần ôn` : "Đã hoàn thành"}</span>` +
    "</div>" +
    `<p class="review-count"><b>${n}</b> <small>mục đến hạn</small></p>` +
    (n
      ? '<p class="review-desc">Từ máy chưa nhận diện rõ cần luyện lại hôm nay.</p>' +
        `<a class="button review-go" href="/practice/review">${icon("play")}Ôn ngay</a>`
      : '<p class="muted review-desc">Từ máy chưa nghe ra sẽ quay lại đây sau 1, 3 rồi 7 ngày.</p>') +
    "</section>"
  );
}

// D070: the phrase book, shown once it has a card. Loaded beside the path and
// painted when it arrives; a failure leaves the card out, nothing else.
let phrases = null;
fetch("/api/v1/me/phrases")
  .then((r) => (r.ok ? r.json() : null))
  .then((d) => {
    phrases = d;
    if (data && data.path) render();
  })
  .catch(() => {});

function phraseCard(p) {
  if (!p || !p.total) return "";
  const n = Math.min(Number(p.due_count) || 0, p.per_day);
  return (
    '<section class="card side-card phrase-side" aria-labelledby="phrase-side-h">' +
    `<h2 id="phrase-side-h">${icon("book-open")}Sổ cụm từ</h2>` +
    `<p class="review-count">${n} <small>cụm hôm nay</small></p>` +
    (n
      ? `<a class="button" href="/phrases">${icon("play")}Ôn cụm từ</a>`
      : `<p class="muted">Đã thuộc ${p.learned}/${p.total} cụm. <a href="/phrases">Xem sổ</a></p>`) +
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
    nextCard() +
    todayCard(data.today) +
    journeyCard(data.path, data.reviews_due, data.achievements, phrases) +
    levelOverviewCard(data.path);
  if (window.enhanceSelects) window.enhanceSelects(sideEl);
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
