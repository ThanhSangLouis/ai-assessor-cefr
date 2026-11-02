// "My responses" screen: submission history (FR-04) and profile export (FR-38).
//
// A list rather than a seven-column table: on a phone the table scrolled
// sideways and its first column was a twelve-character id. Each row now leads
// with what the student recognises -- the task -- and reads as one sentence:
// when, what state, what result.
const escapeHtml = window.escapeHtml;
const listEl = document.getElementById("list");
const listCountEl = document.getElementById("list-count");
const exportBtn = document.getElementById("export");
const exportNoteEl = document.getElementById("export-note");

// Statuses where the response has not been scored yet, so the link must go to
// the progress screen instead of the report screen.
const PENDING_STATUSES = ["QUEUED", "RUNNING"];
// AC-09.2: for these statuses no score and no band may be shown, in any form.
const NO_SCORE_STATUSES = ["REJECTED", "FAILED"];

let allRows = [];
let titles = {};
// When the student last opened this list (D028). A teacher decision after it
// is marked "new" on its row; opening the list then moves the mark forward.
let seenAt = null;
const isNewDecision = (r) => !!r.reviewed_at && (!seenAt || r.reviewed_at > seenAt);

// Task titles make the list readable; the task id alone means nothing to a
// student. If the call fails we simply keep showing the id.
function loadTaskTitles() {
  return fetch("/api/v1/tasks")
    .then((r) => (r.ok ? r.json() : []))
    .then((rows) => {
      const byId = {};
      (rows || []).forEach((t) => {
        byId[t.task_id] = t.title;
      });
      return byId;
    })
    .catch(() => ({}));
}

function badgeFor(r) {
  return window.ui.statusBadge(r.status);
}

// The result part of a row. Two rules meet here:
//   - AC-09.2: a rejected or failed response shows no number at all.
//   - FR-21: a band the teacher has not verified carries the "estimate" label,
//     so it is never read as a final result.
function resultText(r) {
  if (NO_SCORE_STATUSES.includes(r.status)) return '<span class="muted">Chưa có kết quả</span>';
  if (r.overall_band == null && r.overall_0_6 == null) return "";
  let h = "";
  if (r.overall_band != null) h += `Band <b>${escapeHtml(r.overall_band)}</b>`;
  if (r.overall_0_6 != null) h += ` <span class="muted">${Number(r.overall_0_6).toFixed(2)}/6</span>`;
  h += r.teacher_verified
    ? ' <span class="success">· Giảng viên đã xác nhận</span>'
    : ' <span class="muted">· ước lượng, chưa xác nhận</span>';
  return h;
}

function hrefFor(r) {
  const id = encodeURIComponent(r.response_id);
  if (PENDING_STATUSES.includes(r.status)) return `/progress/${id}`;
  return `/report/${id}`;
}

function item(r) {
  const title = titles[r.task_id] || r.task_id;
  const result = resultText(r);
  return `
    <li class="response-item">
      <div class="response-main">
        <a class="response-title" href="${hrefFor(r)}">${escapeHtml(title)}</a>
        <p class="response-meta">
          <span>${escapeHtml(window.ui.localTime(r.created_at))}</span>
          ${isNewDecision(r) ? '<span class="new-chip">Mới xác nhận</span>' : ""}
          ${badgeFor(r)}
          ${result ? `<span>${result}</span>` : ""}
        </p>
        <p class="response-id muted">Mã bài <code>${escapeHtml(r.response_id)}</code></p>
      </div>
    </li>`;
}

function emptyState() {
  return (
    '<div class="empty-state"><div class="empty-mark" aria-hidden="true">♪</div>' +
    "<h2>Bạn chưa nộp bài nói nào</h2>" +
    "<p>Ghi âm khoảng một phút trả lời một đề bài, hệ thống sẽ trả về một ước lượng " +
    "tổng thể kèm bằng chứng cụ thể để bạn biết nên luyện tiếp phần nào.</p>" +
    '<div class="button-row"><a class="button" href="/">Nộp bài đầu tiên</a>' +
    '<a class="button secondary" href="/practice">Học theo lộ trình trước</a></div></div>'
  );
}

function render() {
  listCountEl.textContent = allRows.length ? `${allRows.length} bài` : "";
  if (!allRows.length) {
    listEl.innerHTML = emptyState();
    return;
  }
  listEl.innerHTML = `<ul class="response-list">${allRows.map(item).join("")}</ul>`;
}

// Read the mark first, show the list against it, then move it to now: the
// rows stay marked for this visit and the sidebar count clears.
function loadSeen() {
  return fetch("/api/v1/me/badges")
    .then((r) => (r.ok ? r.json() : {}))
    .then((b) => b.results_seen_at || null)
    .catch(() => null);
}

// The body is read even though only the status matters: Chromium keeps a
// response whose body nobody reads open, and the page never goes idle.
function markSeen() {
  fetch("/api/v1/me/badges/results/seen", { method: "POST" })
    .then((r) => (r.ok ? r.json() : null))
    .then((d) => {
      if (d) window.ui.setBadge("results", 0);
    })
    .catch(() => {});
}

let firstLoad = true;

function load() {
  Promise.all([
    fetch("/api/v1/me/responses").then((r) => {
      if (window.redirectToLoginIfExpired(r)) return null;
      return r.json();
    }),
    loadTaskTitles(),
    firstLoad ? loadSeen() : Promise.resolve(seenAt),
  ])
    .then(([rows, taskTitles, seen]) => {
      if (rows === null) return;
      window.clearBusy(listEl);
      if (!Array.isArray(rows)) {
        listEl.innerHTML = '<p class="error">Không đọc được danh sách bài.</p>';
        return;
      }
      allRows = rows;
      titles = taskTitles;
      seenAt = seen;
      render();
      if (firstLoad) markSeen();
      firstLoad = false;
    })
    .catch(() => {
      window.clearBusy(listEl);
      listEl.innerHTML = '<p class="error">Không kết nối được máy chủ.</p>';
      window.toast("Không kết nối được máy chủ.", "error");
    });
}

// FR-38. The endpoint already sets Content-Disposition, so the browser saves the
// file; going through fetch first lets an expired session send the user to the
// login page instead of downloading an error page.
function exportProfile() {
  exportNoteEl.innerHTML = "";
  exportBtn.disabled = true;
  fetch("/api/v1/me/profile.json")
    .then((r) => {
      if (window.redirectToLoginIfExpired(r)) return null;
      if (!r.ok) throw new Error("export failed");
      return r.blob();
    })
    .then((blob) => {
      if (blob === null) return;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "speaking_profile.json";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      exportNoteEl.innerHTML =
        '<p class="success">Đã tải tệp <code>speaking_profile.json</code>. ' +
        "Tệp chỉ gồm những kết quả giảng viên đã xác nhận.</p>";
      window.toast("Đã tải tệp speaking_profile.json.", "ok");
    })
    .catch(() => {
      exportNoteEl.innerHTML = '<p class="error">Không xuất được hồ sơ. Hãy thử lại sau.</p>';
      window.toast("Không xuất được hồ sơ. Hãy thử lại sau.", "error");
    })
    .finally(() => {
      exportBtn.disabled = false;
    });
}

exportBtn.addEventListener("click", exportProfile);
load();
