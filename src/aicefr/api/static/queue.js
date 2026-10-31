// Review queue screen. See docs/web/SPEC_WEB.md sections M5 and M6.
//
// Every value below comes from another user: a student chooses their own
// pseudonym, and it lands on a teacher's screen. Without escaping, a pseudonym
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

// AC-09.2 again: a rejected or failed response shows no score and no band.
const NO_SCORE_STATUSES = ["REJECTED", "FAILED"];

function resultCell(r) {
  if (NO_SCORE_STATUSES.includes(r.status)) return '<span class="muted">Không áp dụng</span>';
  if (r.overall_0_6 == null) return '<span class="muted">Máy chưa chấm</span>';
  return (
    `<b>${escapeHtml(r.overall_band ?? "—")}</b> ` +
    `<span class="muted">${Number(r.overall_0_6).toFixed(2)}</span>`
  );
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
    const title = titles[r.task_id] ? ` · ${escapeHtml(titles[r.task_id])}` : "";
    h +=
      `<tr${r.locked_by ? ' class="is-locked"' : ""}>` +
      `<td><b>${r.student_name ? escapeHtml(r.student_name) : escapeHtml(r.speaker_id)}</b>` +
      `<span class="cell-sub">Đề <code>${escapeHtml(r.task_id)}</code>${title}</span>` +
      `<span class="cell-sub">${escapeHtml(window.ui.localTime(r.created_at))} · ` +
      `<a href="/report/${encodeURIComponent(r.response_id)}">báo cáo ${escapeHtml(r.response_id)}</a></span></td>` +
      `<td>${resultCell(r)}</td>` +
      `<td>${reasonCell(r)}</td>` +
      `<td class="action-cell">${actionCell(r)}</td></tr>`;
  });
  return h + "</tbody></table>";
}

function apply() {
  const reason = reasonFilterEl.value;
  const lock = lockFilterEl.value;
  const visible = rows.filter((r) => {
    if (reason && !(r.reasons || []).includes(reason)) return false;
    if (lock === "free" && r.locked_by) return false;
    return true;
  });
  listEl.innerHTML = renderRows(visible);
  filterCountEl.textContent = `Hiện ${visible.length} / ${rows.length} bài`;
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

// Titles make a row readable at a glance; a failed call keeps the task ids.
function loadTitles() {
  return fetch("/api/v1/tasks")
    .then((r) => (r.ok ? r.json() : []))
    .then((list) => {
      (list || []).forEach((t) => {
        titles[t.task_id] = t.title;
      });
    })
    .catch(() => {});
}

function load() {
  window.showSkeleton(listEl, "table");
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
      rows = data;
      queueCountEl.textContent = `${rows.length} bài`;
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
document.getElementById("queue-refresh").addEventListener("click", load);

load();
