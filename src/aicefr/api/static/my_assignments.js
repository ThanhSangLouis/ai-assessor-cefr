// "Assignments" (D054): what my classes set me, and joining a class by its code.
const escapeHtml = window.escapeHtml;
const todoEl = document.getElementById("todo");
const doneEl = document.getElementById("done");

const STATE_CLASS = { on_time: "state-on", late: "state-warn", open: "state-off", missing: "state-warn" };
const STATE = {
  open: "Chưa nộp",
  missing: "Quá hạn, chưa nộp",
  on_time: "Đã nộp đúng hạn",
  late: "Nộp muộn",
};
const dmy = (iso) => window.ui.dmy(iso, "—");

function row(a, todo) {
  const tag = `<span class="badge ${STATE_CLASS[a.state] || ""}">${STATE[a.state] || a.state}</span>`;
  const band = a.band ? ` · band <b>${escapeHtml(a.band)}</b>${a.teacher_verified ? " (giảng viên đã duyệt)" : " (chờ duyệt)"}` : "";
  const action = todo
    ? `<a class="button small" href="/?task=${encodeURIComponent(a.task_id)}">Làm bài</a>`
    : `<a class="button secondary small" href="/report/${encodeURIComponent(a.response_id)}">Xem kết quả</a>`;
  return `<li class="assign-row">
    <div><b>${escapeHtml(a.task_title)}</b> · ${escapeHtml(a.class_name)}
      <div class="muted small">Hạn ${dmy(a.due_on)} · ${tag}${band}</div>
      ${a.note ? `<div class="small">${escapeHtml(a.note)}</div>` : ""}</div>
    ${action}</li>`;
}

async function load() {
  const d = await window.apiJson("/api/v1/me/assignments");
  window.clearBusy(todoEl);
  if (!d) return;
  todoEl.innerHTML = d.todo.length
    ? `<ul class="plain-list">${d.todo.map((a) => row(a, true)).join("")}</ul>`
    : '<p class="muted">Không có bài nào đang chờ bạn.</p>';
  doneEl.innerHTML = d.done.length
    ? `<ul class="plain-list">${d.done.map((a) => row(a, false)).join("")}</ul>`
    : '<p class="muted">Chưa nộp bài nào được giao.</p>';
  document.getElementById("my-classes").textContent = d.classes.length
    ? `Bạn đang ở lớp: ${d.classes.join(", ")}.`
    : "Bạn chưa ở lớp nào. Hỏi giảng viên mã lớp.";
}

document.getElementById("join-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const code = document.getElementById("join-code").value;
  const d = await window.apiJson("/api/v1/me/classes/join", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code }),
  });
  if (!d) return;
  window.toast(d.joined ? `Đã vào lớp ${d.class_name}.` : `Bạn đã ở lớp ${d.class_name}.`, "ok");
  e.target.reset();
  load();
});

load();
