// Review queue screen. See docs/web/SPEC_WEB.md sections M5 and M6.
//
// Every value below comes from another user: a student chooses their own
// name, and it lands on a teacher's screen. Without escaping, a name
// like `<svg onload=...>` runs script in the teacher's session, with the
// teacher's cookie, and can read every recording and change every score.
//
// Four columns rather than nine: the queue only ever holds responses waiting
// for review, so a status column said the same thing on every row, and the
// action a teacher came for sat in the ninth column, off the edge of a laptop
// screen. "Duyệt bài tiếp theo" opens the oldest response nobody holds.
const escapeHtml = window.escapeHtml;
const listEl = document.getElementById("ds");
const filtersEl = document.getElementById("filters");
const reasonFilterEl = document.getElementById("filter-reason");
const lockFilterEl = document.getElementById("filter-lock");
const filterCountEl = document.getElementById("filter-count");
const queueCountEl = document.getElementById("queue-count");
const nextEl = document.getElementById("next-review");

let rows = [];
let titles = {};
let bands = {};
// The week sheet is the default; the choice is kept per browser.
let view = "week";
try {
  view = localStorage.getItem("su-queue-view") || "week";
} catch (err) {
  /* no storage: the default view */
}

// AC-09.2 again: a rejected or failed response shows no score and no band.
const NO_SCORE_STATUSES = ["REJECTED", "FAILED"];

function resultCell(r) {
  if (NO_SCORE_STATUSES.includes(r.status)) return '<span class="muted">Không áp dụng</span>';
  if (r.overall_0_6 == null) return '<span class="muted">Máy chưa chấm</span>';
  return (
    (r.overall_band ? `<span class="band-chip" data-band="${escapeHtml(r.overall_band)}">${escapeHtml(r.overall_band)}</span> ` : "<b>—</b> ") +
    `<span class="muted">${Number(r.overall_0_6).toFixed(2)}</span>`
  );
}

// How long a response has waited, the number a queue is judged by.
function waited(iso) {
  const ms = Date.now() - new Date(iso).getTime();
  if (!Number.isFinite(ms)) return "";
  const hours = Math.floor(ms / 3600000);
  if (hours < 1) return "vừa nộp";
  if (hours < 24) return `chờ ${hours} giờ`;
  return `chờ ${Math.floor(hours / 24)} ngày`;
}

function reasonCell(r) {
  if (r.reasons === undefined) return '<span class="muted">đang tải…</span>';
  if (!r.reasons || !r.reasons.length) return '<span class="muted">—</span>';
  return r.reasons
    .map((c) => `<span class="badge">${escapeHtml(window.ui.reasonName(c))}</span>`)
    .join(" ");
}

function actionCell(r) {
  const href = `/review/${encodeURIComponent(r.response_id)}`;
  if (r.locked_by) {
    return (
      `<a class="button small secondary" href="${href}">Xem</a>` +
      `<span class="muted lock-note">Đang được ${escapeHtml(r.locked_by)} duyệt</span>`
    );
  }
  return `<a class="button small" href="${href}">Duyệt</a>`;
}

function renderRows(visible) {
  if (!visible.length) {
    return (
      '<div class="empty-state"><div class="empty-mark" aria-hidden="true">⌕</div>' +
      "<h2>Không có bài nào khớp bộ lọc</h2>" +
      "<p>Hãy nới bộ lọc lý do gắn cờ hoặc người đang xem để thấy thêm bài.</p>" +
      '<div class="button-row">' +
      '<button type="button" class="secondary" id="reset-filters">Bỏ mọi bộ lọc</button>' +
      "</div></div>"
    );
  }
  let h =
    '<table class="queue-table"><thead><tr><th>Bài nộp</th><th>Máy chấm</th>' +
    "<th>Lý do gắn cờ</th><th>Xử lý</th></tr></thead><tbody>";
  visible.forEach((r) => {
    const title = escapeHtml(titles[r.task_id] || "Đề");
    h +=
      `<tr${r.locked_by ? ' class="is-locked"' : ""}>` +
      `<td><b>${r.student_name ? escapeHtml(r.student_name) : "Học viên"}</b>` +
      `<span class="cell-sub">${title}</span>` +
      `<span class="cell-sub"><span title="${escapeHtml(window.ui.localTime(r.created_at))}">${waited(r.created_at)}</span> · ` +
      `<a href="/report/${encodeURIComponent(r.response_id)}">Xem báo cáo</a></span></td>` +
      `<td>${resultCell(r)}</td>` +
      `<td>${reasonCell(r)}</td>` +
      `<td class="action-cell">${actionCell(r)}</td></tr>`;
  });
  return h + "</tbody></table>";
}

// ---------------------------------------------------------------- the week sheet
// Staff work laid out like the faculty timetable: the last seven days as
// columns, the hours of the day ruled down the side, every waiting response a
// block in its prompt's band colour, placed when it arrived and as tall as the
// recording is long. Being reviewed is an outline, waiting over three days is
// hatched: the state is in the form, not only the colour.
const DAY_MS = 86400000;
const FIRST_HOUR = 6;
const HOURS = 18; // 06:00 to 24:00
const HOUR_PX = () => (window.matchMedia("(max-width: 720px)").matches ? 22 : 26);
const WEEKDAYS = ["CN", "T2", "T3", "T4", "T5", "T6", "T7"];

function startOfDay(d) {
  const x = new Date(d);
  x.setHours(0, 0, 0, 0);
  return x;
}

function bandOf(r) {
  return bands[r.task_id] || r.overall_band || "";
}

function blockHtml(r, top, height, now) {
  const band = bandOf(r);
  const late = now - new Date(r.created_at).getTime() > 3 * DAY_MS;
  const cls = ["tt-block", r.locked_by ? "is-held" : "", late ? "is-late" : ""].join(" ").trim();
  const who = r.student_name ? escapeHtml(r.student_name) : "Học viên";
  const len = r.duration_s ? `${Math.floor(r.duration_s / 60)}:${String(Math.round(r.duration_s % 60)).padStart(2, "0")}` : "";
  const first = (r.reasons || [])[0];
  const lines = [
    `<b>${who}</b>`,
    `<span>${escapeHtml(titles[r.task_id] || (band ? `Đề ${band}` : "Đề"))}${len ? ` · ${len}` : ""}</span>`,
    r.locked_by
      ? `<span>${escapeHtml(r.locked_by)} đang xem</span>`
      : first
        ? `<span>${escapeHtml(window.ui.reasonName(first))}</span>`
        : "",
  ].join("");
  const label = `${who}, ${titles[r.task_id] || "đề"}, ${waited(r.created_at)}${r.locked_by ? `, ${r.locked_by} đang xem` : ""}`;
  return (
    `<a class="${cls}" data-band="${escapeHtml(band)}" href="/review/${encodeURIComponent(r.response_id)}"` +
    ` style="top:${top}px;height:${height}px" aria-label="${escapeHtml(label)}">${lines}</a>`
  );
}

function renderWeek(visible) {
  if (!visible.length) return renderRows(visible);
  const now = Date.now();
  const today = startOfDay(now);
  const hour = HOUR_PX();
  const days = Array.from({ length: 7 }, (_, i) => new Date(today.getTime() - (6 - i) * DAY_MS));
  const older = visible.filter((r) => new Date(r.created_at) < days[0]);
  const cols = (older.length ? [{ older: true, items: older }] : []).concat(
    days.map((d) => ({
      day: d,
      items: visible.filter((r) => startOfDay(new Date(r.created_at)).getTime() === d.getTime()),
    }))
  );
  const sheetH = HOURS * hour;
  let tallest = sheetH;
  // Blocks are placed by arrival time and pushed down when they would overlap.
  const bodies = cols.map((c) => {
    const items = c.items.slice().sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
    let floor = 4;
    const html = items
      .map((r) => {
        const at = new Date(r.created_at);
        const h = Math.min(Math.max(40, 16 + (r.duration_s || 30) * 1.1), 150);
        const want = c.older ? floor : ((at.getHours() + at.getMinutes() / 60 - FIRST_HOUR) / HOURS) * sheetH;
        const top = Math.max(Math.round(want), floor);
        floor = top + h + 4;
        tallest = Math.max(tallest, floor + 4);
        return blockHtml(r, top, h, now);
      })
      .join("");
    return html;
  });
  const heads = cols
    .map((c) => {
      if (c.older) return `<div class="tt-dayhead is-older">Cũ hơn <small>${c.items.length}</small></div>`;
      const isToday = c.day.getTime() === today.getTime();
      return (
        `<div class="tt-dayhead${isToday ? " is-today" : ""}">${WEEKDAYS[c.day.getDay()]}` +
        ` <small>${c.day.getDate()}/${c.day.getMonth() + 1}${isToday ? " · hôm nay" : ""}</small></div>`
      );
    })
    .join("");
  const hourMarks = Array.from({ length: HOURS / 2 + 1 }, (_, i) => FIRST_HOUR + i * 2)
    .filter((hh) => hh < 24)
    .map((hh) => `<span style="top:${(hh - FIRST_HOUR) * hour}px">${hh}:00</span>`)
    .join("");
  const nowD = new Date(now);
  const nowTop = ((nowD.getHours() + nowD.getMinutes() / 60 - FIRST_HOUR) / HOURS) * sheetH;
  const nowLine =
    nowTop > 0 && nowTop < sheetH
      ? `<div class="tt-now" style="top:${Math.round(nowTop)}px"></div>`
      : "";
  const columns = cols
    .map((c, i) => {
      const isToday = !c.older && c.day.getTime() === today.getTime();
      return `<div class="tt-day${c.older ? " is-older" : ""}${isToday ? " is-today" : ""}">${bodies[i]}${isToday ? nowLine.replace(/<span>.*<\/span>/, "") : ""}</div>`;
    })
    .join("");
  const used = Array.from(new Set(visible.map(bandOf).filter(Boolean))).sort();
  const legend =
    '<div class="tt-legend">' +
    used.map((b) => `<span><span class="band-chip" data-band="${escapeHtml(b)}">${escapeHtml(b)}</span></span>`).join("") +
    '<span class="tt-forms"><span><i class="tt-key"></i>chờ</span>' +
    '<span><i class="tt-key is-held"></i>có người đang xem</span>' +
    '<span><i class="tt-key is-late"></i>chờ quá 3 ngày</span>' +
    "<span>cao theo độ dài bản ghi</span></span></div>";
  return (
    legend +
    '<div class="tt-scroll" tabindex="0" role="region" aria-label="Bài chờ theo ngày nộp">' +
    `<div class="tt" style="--days:${cols.length};--hour:${hour}px;grid-template-rows:auto ${tallest}px">` +
    `<div class="tt-corner"></div>${heads}<div class="tt-hours">${hourMarks}${nowTop > 0 && nowTop < sheetH ? `<b class="tt-now-label" style="top:${Math.round(nowTop)}px">${String(nowD.getHours()).padStart(2, "0")}:${String(nowD.getMinutes()).padStart(2, "0")}</b>` : ""}</div>${columns}</div></div>` +
    (older.length ? `<p class="tt-foot">${older.length} bài nộp trước ${days[0].getDate()}/${days[0].getMonth() + 1} xếp ở cột "Cũ hơn", cũ nhất ở trên.</p>` : "")
  );
}

function setView(next) {
  view = next;
  try {
    localStorage.setItem("su-queue-view", view);
  } catch (err) {
    /* kept for this page only */
  }
  document.querySelectorAll(".view-switch [data-view]").forEach((b) => {
    b.setAttribute("aria-pressed", String(b.dataset.view === view));
  });
  if (rows.length) apply();
}
document.querySelectorAll(".view-switch [data-view]").forEach((b) => {
  b.setAttribute("aria-pressed", String(b.dataset.view === view));
  b.addEventListener("click", () => setView(b.dataset.view));
});

function apply() {
  const reason = reasonFilterEl.value;
  const lock = lockFilterEl.value;
  const visible = rows.filter((r) => {
    if (reason && !(r.reasons || []).includes(reason)) return false;
    if (lock === "free" && r.locked_by) return false;
    return true;
  });
  listEl.innerHTML = view === "week" ? renderWeek(visible) : renderRows(visible);
  // Today is the last column: when the sheet has to scroll, start at today.
  const sheet = listEl.querySelector(".tt-scroll");
  if (sheet) sheet.scrollLeft = sheet.scrollWidth;
  // The total is in the heading; this line only speaks when a filter hides rows.
  filterCountEl.textContent = visible.length < rows.length ? `Hiện ${visible.length} / ${rows.length} bài` : "";
  const reset = document.getElementById("reset-filters");
  if (reset) {
    reset.addEventListener("click", () => {
      reasonFilterEl.value = "";
      lockFilterEl.value = "";
      apply();
    });
  }
}

// The oldest response nobody holds. The queue is ordered oldest first.
function paintNext() {
  const free = rows.find((r) => !r.locked_by);
  if (free) {
    nextEl.href = `/review/${encodeURIComponent(free.response_id)}`;
    nextEl.removeAttribute("aria-disabled");
  } else {
    nextEl.href = "/review";
    nextEl.setAttribute("aria-disabled", "true");
  }
}

nextEl.addEventListener("click", (e) => {
  if (nextEl.getAttribute("aria-disabled") === "true") {
    e.preventDefault();
    window.toast("Không còn bài nào chưa có người duyệt.", "info");
  }
});

function fillOptions(select, values, nameOf) {
  const keep = select.value;
  const first = select.options[0];
  select.innerHTML = "";
  select.appendChild(first);
  Array.from(values)
    .sort()
    .forEach((v) => {
      const o = document.createElement("option");
      o.value = v;
      o.textContent = nameOf(v);
      select.appendChild(o);
    });
  select.value = keep;
}

// The queue endpoint does not carry the flag reasons, so they are fetched from
// each response's own detail endpoint. The queue only ever holds flagged
// responses, so this is a short list; the fetches are still capped so a large
// backlog cannot fire hundreds of requests at once.
const MAX_ENRICH = 60;
const BATCH = 6;

async function loadReasons() {
  const targets = rows.slice(0, MAX_ENRICH);
  if (targets.length < rows.length) {
    rows.slice(MAX_ENRICH).forEach((r) => {
      r.reasons = [];
    });
  }
  for (let i = 0; i < targets.length; i += BATCH) {
    const slice = targets.slice(i, i + BATCH);
    await Promise.all(
      slice.map(async (r) => {
        try {
          const res = await fetch(`/api/v1/responses/${encodeURIComponent(r.response_id)}`);
          const d = res.ok ? await res.json() : {};
          r.reasons = Array.isArray(d.reasons) ? d.reasons : [];
        } catch (err) {
          r.reasons = [];
        }
      })
    );
    const seen = new Set();
    rows.forEach((r) => (r.reasons || []).forEach((c) => seen.add(c)));
    fillOptions(reasonFilterEl, seen, window.ui.reasonName);
    apply();
  }
}

// The prompt's band ("Đề B1") makes a row readable at a glance (D078).
function loadTitles() {
  return fetch("/api/v1/tasks")
    .then((r) => (r.ok ? r.json() : []))
    .then((list) => {
      (list || []).forEach((t) => {
        titles[t.task_id] = t.title;
        bands[t.task_id] = t.band;
      });
    })
    .catch(() => {});
}

// `quiet`: a refresh the teacher did not ask for (D086) keeps the list on screen
// until the new one is in, instead of flashing a placeholder.
function load(quiet = false) {
  if (!quiet) window.showSkeleton(listEl, "table");
  Promise.all([
    fetch("/api/v1/review/queue").then((r) => {
      if (window.redirectToLoginIfExpired(r)) return null;
      if (r.status === 403) {
        window.clearBusy(listEl);
        listEl.innerHTML =
          '<p class="error">Tài khoản này không có quyền duyệt bài. ' +
          "Chỉ giảng viên và quản trị viên xem được hàng đợi.</p>";
        return null;
      }
      return r.json();
    }),
    loadTitles(),
  ])
    .then(([data]) => {
      if (data === null) return;
      window.clearBusy(listEl);
      // Reasons already fetched stay shown while they are fetched again.
      const known = new Map(rows.map((r) => [r.response_id, r.reasons]));
      data.forEach((r) => {
        if (known.has(r.response_id)) r.reasons = known.get(r.response_id);
      });
      rows = data;
      queueCountEl.textContent = String(rows.length);
      const lede = document.getElementById("queue-lede");
      if (lede && rows.length) {
        lede.textContent = `${rows.length} bài chờ · lâu nhất ${waited(rows[0].created_at).replace("chờ ", "")}. Mọi lần sửa được ghi lại kèm lý do.`;
      }
      paintNext();
      if (!rows.length) {
        filtersEl.hidden = true;
        listEl.innerHTML =
          '<div class="empty-state"><div class="empty-mark" aria-hidden="true">✓</div>' +
          "<h2>Hàng đợi trống</h2>" +
          "<p>Không có bài nào chờ duyệt. Bài mới sẽ tự xuất hiện ở đây khi hệ thống " +
          "gắn cờ vì không đủ chắc chắn.</p>" +
          '<div class="button-row"><a class="button secondary" href="/review/stats">Xem thống kê lớp</a></div></div>';
        return;
      }
      filtersEl.hidden = false;
      apply();
      loadReasons();
    })
    .catch(() => {
      window.clearBusy(listEl);
      listEl.innerHTML = '<p class="error">Không kết nối được máy chủ.</p>';
      window.toast("Không kết nối được máy chủ.", "error");
    });
}

[reasonFilterEl, lockFilterEl].forEach((el) => el.addEventListener("change", apply));
document.getElementById("queue-refresh").addEventListener("click", () => load());

// D086: a response flagged, locked, decided or closed by anyone changes this
// queue. Several changes in a row (a teacher saving and moving on) make one
// refresh.
let liveRefresh = null;
document.addEventListener("live:queue.changed", () => {
  clearTimeout(liveRefresh);
  liveRefresh = setTimeout(() => load(true), 800);
});

load();
