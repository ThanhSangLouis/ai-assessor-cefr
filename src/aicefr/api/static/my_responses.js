// "My responses" screen: submission history (FR-04) and profile export (FR-38).
//
// A list rather than a seven-column table: on a phone the table scrolled
// sideways and its first column was a twelve-character id. Each row now leads
// with what the student recognises -- the task -- and reads as one sentence:
// when, what state, what result.
const escapeHtml = window.escapeHtml;
const listEl = document.getElementById("list");
const listCountEl = document.getElementById("list-count");
const filterEl = document.getElementById("list-filter");
const exportBtn = document.getElementById("export");
const exportNoteEl = document.getElementById("export-note");

// Statuses where the response has not been scored yet, so the link must go to
// the progress screen instead of the report screen.
const PENDING_STATUSES = ["QUEUED", "RUNNING"];
// AC-09.2: for these statuses no score and no band may be shown, in any form.
const NO_SCORE_STATUSES = ["REJECTED", "FAILED"];

// D023. A practice attempt has no band and no teacher review. Its title is built
// from the task id (PR-FLU-A2 -> "Luyện tập · Độ trôi chảy A2") because
// /api/v1/tasks returns assessment tasks only.
const PRACTICE_SKILL = {
  FLU: "Độ trôi chảy",
  COH: "Mạch lạc",
  RAN: "Vốn từ",
  ACC: "Ngữ pháp",
  PHO: "Phát âm dễ nghe",
};
const isPractice = (r) => r.purpose === "practice";

function practiceTitle(taskId) {
  const [, skill, band] = String(taskId).split("-");
  return `Luyện tập · ${PRACTICE_SKILL[skill] || taskId} ${band || ""}`.trim();
}

let allRows = [];
let titles = {};
let kind = "all";
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
  if (isPractice(r) && r.status === "COMPLETED") {
    return '<span class="badge COMPLETED">Đã luyện xong</span>';
  }
  return window.ui.statusBadge(r.status);
}

// The result part of a row. Two rules meet here:
//   - AC-09.2: a rejected or failed response shows no number at all.
//   - FR-21: a band the teacher has not verified carries the "estimate" label,
//     so it is never read as a final result.
function resultText(r) {
  if (isPractice(r)) return '<span class="muted">Không chấm</span>';
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
  return isPractice(r) ? `/practice/results/${id}` : `/report/${id}`;
}

// FR-35, the learner's side. A response a teacher has verified cannot be deleted
// by its owner, and the row says so on the spot instead of offering a button
// that only leads to a 409.
function deleteControl(r) {
  const id = escapeHtml(r.response_id);
  if (r.teacher_verified) {
    return '<span class="muted small-note" title="Bài đã được giảng viên xác nhận">Không xoá được</span>';
  }
  // One visible word, but a full accessible name: "Xoá" alone is clear to
  // someone who sees the whole row and vague to someone hearing one button.
  return (
    `<button type="button" class="link-button danger" data-delete="${id}"` +
    ` aria-label="Xoá bài ${id} và bản ghi âm của nó">Xoá</button>`
  );
}

function item(r) {
  const title = isPractice(r) ? practiceTitle(r.task_id) : titles[r.task_id] || r.task_id;
  const result = resultText(r);
  return `
    <li class="response-item${isPractice(r) ? " is-practice" : ""}">
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
      <div class="response-side">${deleteControl(r)}</div>
    </li>`;
}

function emptyState() {
  return (
    '<div class="empty-state"><div class="empty-mark" aria-hidden="true">♪</div>' +
    "<h2>Bạn chưa nộp bài nói nào</h2>" +
    "<p>Ghi âm khoảng một phút trả lời một đề bài, hệ thống sẽ trả về một ước lượng " +
    "tổng thể kèm bằng chứng cụ thể để bạn biết nên luyện tiếp phần nào.</p>" +
    '<div class="button-row"><a class="button" href="/">Nộp bài đầu tiên</a>' +
    '<a class="button secondary" href="/practice">Luyện tập trước</a></div></div>'
  );
}

function render() {
  const rows = allRows.filter(
    (r) => kind === "all" || (kind === "practice") === isPractice(r)
  );
  const practiced = allRows.filter(isPractice).length;
  const counts = { all: allRows.length, assessment: allRows.length - practiced, practice: practiced };
  filterEl.querySelectorAll("button").forEach((b) => {
    const k = b.getAttribute("data-kind");
    b.setAttribute("aria-pressed", String(k === kind));
    b.textContent = `${{ all: "Tất cả", assessment: "Đánh giá", practice: "Luyện tập" }[k]} (${counts[k]})`;
  });
  filterEl.hidden = !allRows.length || !practiced || practiced === allRows.length;
  listCountEl.textContent = allRows.length ? `${allRows.length} bài` : "";
  if (!allRows.length) {
    listEl.innerHTML = emptyState();
    return;
  }
  listEl.innerHTML = rows.length
    ? `<ul class="response-list">${rows.map(item).join("")}</ul>`
    : '<p class="muted">Không có bài nào thuộc loại này.</p>';
  wireDeletes();
}

filterEl.addEventListener("click", (e) => {
  const b = e.target.closest("button[data-kind]");
  if (!b) return;
  kind = b.getAttribute("data-kind");
  render();
});

// Deleting cannot be undone, so it asks once more. `confirm` rather than a
// home-made dialog: the browser's own handles focus, Escape and screen readers,
// and getting any of those wrong is worse than its plain look.
function wireDeletes() {
  listEl.querySelectorAll("[data-delete]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.dataset.delete;
      if (!window.confirm(`Xoá vĩnh viễn bài ${id}? Cả bản ghi âm cũng bị xoá.`)) return;

      btn.disabled = true;
      const r = await fetch(`/api/v1/responses/${encodeURIComponent(id)}`, {
        method: "DELETE",
      });
      if (window.redirectToLoginIfExpired(r)) return;
      if (!r.ok) {
        btn.disabled = false;
        const d = await r.json().catch(() => ({}));
        window.toast(d.detail || "Không xoá được bài này.", "error");
        return;
      }
      window.toast(`Đã xoá bài ${id} và bản ghi âm của nó.`, "ok");
      load();
    });
  });
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
