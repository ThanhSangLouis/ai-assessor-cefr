// "Classes" (D054): a teacher's classes, one class's members and assignments,
// and who handed in what. Pseudonyms only, as on every staff screen.
const escapeHtml = window.escapeHtml;
const root = document.getElementById("classes-root");
const classId = root.dataset.classId;

const BAND_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"];
const STATE_CLASS = { on_time: "state-on", late: "state-warn", open: "state-off", missing: "state-warn" };
const STATE = { open: "Chưa nộp", missing: "Chưa nộp (quá hạn)", on_time: "Đúng hạn", late: "Muộn" };
const dmy = (iso) => window.ui.dmy(iso, "—");
const post = (url, body) =>
  window.apiJson(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

async function listView() {
  const classes = await window.apiJson("/api/v1/classes");
  if (!classes) return;
  root.innerHTML = `
    <section class="card" aria-labelledby="new-h">
      <div class="card-head"><h2 id="new-h">Tạo lớp mới</h2></div>
      <form id="new-class" class="inline-form">
        <label class="field"><span>Tên lớp</span><input name="name" maxlength="80" required placeholder="Ví dụ: Tiếng Anh 2 · nhóm 03"></label>
        <button class="button" type="submit">Tạo lớp</button>
      </form>
    </section>
    <section class="card" aria-labelledby="list-h">
      <div class="card-head"><h2 id="list-h">Lớp của tôi</h2></div>
      ${
        classes.length
          ? `<ul class="plain-list">${classes
              .map(
                (c) => `<li class="assign-row"><div><a href="/teach/classes/${encodeURIComponent(c.class_id)}"><b>${escapeHtml(c.name)}</b></a>
                  <div class="muted small">Mã lớp <code>${escapeHtml(c.code)}</code> · ${c.members} sinh viên · ${c.assignments} bài đã giao${c.archived ? " · đã lưu trữ" : ""}</div></div></li>`,
              )
              .join("")}</ul>`
          : '<p class="muted">Chưa có lớp nào.</p>'
      }
    </section>`;
  document.getElementById("new-class").addEventListener("submit", async (e) => {
    e.preventDefault();
    const made = await post("/api/v1/classes", { name: e.target.name.value });
    if (made) window.location.assign(`/teach/classes/${encodeURIComponent(made.class_id)}`);
  });
}

function bandBar(bands) {
  const total = BAND_ORDER.reduce((n, b) => n + (bands[b] || 0), 0);
  if (!total) return '<span class="muted small">chưa có band</span>';
  return `<span class="band-spread">${BAND_ORDER.map(
    (b) => `<span class="band-chip">${b}: <b>${bands[b] || 0}</b></span>`,
  ).join("")}</span>`;
}

async function detailView() {
  const [c, tasks] = await Promise.all([
    window.apiJson(`/api/v1/classes/${encodeURIComponent(classId)}`),
    window.apiJson("/api/v1/tasks"),
  ]);
  if (!c) return;
  document.getElementById("page-title").textContent = c.name;
  document.getElementById("page-lede").innerHTML =
    `Mã lớp <code class="join-code">${escapeHtml(c.code)}</code>: sinh viên vào trang <b>Bài được giao</b> và nhập mã này để tự tham gia. <a href="/teach/classes">Tất cả lớp</a>`;
  const today = new Date().toISOString().slice(0, 10);
  root.innerHTML = `
    <section class="card" aria-labelledby="assign-h">
      <div class="card-head"><h2 id="assign-h">Bài đã giao</h2></div>
      ${
        c.assignments.length
          ? `<ul class="plain-list">${c.assignments
              .map(
                (a) => `<li class="assign-row"><div><b>${escapeHtml(a.task_title)}</b> · hạn ${dmy(a.due_on)}
                  <div class="muted small">${a.on_time} đúng hạn · ${a.late} muộn · ${a.open + a.missing} chưa nộp / ${a.members} sinh viên · ${a.verified} bài đã duyệt</div>
                  <div class="small">${bandBar(a.bands)}</div></div>
                  <button class="button secondary small" data-detail="${escapeHtml(a.assignment_id)}">Xem từng sinh viên</button></li>
                  <li id="detail-${escapeHtml(a.assignment_id)}" hidden></li>`,
              )
              .join("")}</ul>`
          : '<p class="muted">Chưa giao bài nào.</p>'
      }
      ${
        c.archived
          ? '<p class="muted">Lớp đã lưu trữ.</p>'
          : `<form id="assign-form" class="inline-form">
        <label class="field"><span>Đề</span><select name="task_id">${(tasks || [])
          .map((t) => `<option value="${escapeHtml(t.task_id)}">${escapeHtml(t.task_id)} · ${escapeHtml(t.title)}</option>`)
          .join("")}</select></label>
        <label class="field"><span>Hạn nộp</span><input type="date" name="due_on" min="${today}" value="${today}" required></label>
        <label class="field"><span>Ghi chú cho lớp</span><input name="note" maxlength="300"></label>
        <button class="button" type="submit">Giao bài</button>
      </form>`
      }
    </section>
    <section class="card" aria-labelledby="members-h">
      <div class="card-head"><h2 id="members-h">Sinh viên (${c.members.length})</h2></div>
      <p class="small">${c.members.map(escapeHtml).join(", ") || '<span class="muted">Chưa có ai.</span>'}</p>
      <form id="members-form" class="inline-form">
        <label class="field"><span>Thêm theo mã giả danh, cách nhau bằng dấu phẩy</span><input name="list" placeholder="SV-001, SV-002"></label>
        <button class="button secondary" type="submit">Thêm</button>
      </form>
    </section>`;
  root.querySelectorAll("button[data-detail]").forEach((b) =>
    b.addEventListener("click", () => showStudents(b.dataset.detail)),
  );
  const assignForm = document.getElementById("assign-form");
  if (assignForm)
    assignForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const f = e.target;
      const made = await post(`/api/v1/classes/${encodeURIComponent(classId)}/assignments`, {
        task_id: f.task_id.value,
        due_on: f.due_on.value,
        note: f.note.value,
      });
      if (made) {
        window.toast("Đã giao bài.", "ok");
        detailView();
      }
    });
  document.getElementById("members-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const pseudonyms = e.target.list.value.split(/[,\s]+/).filter(Boolean);
    if (!pseudonyms.length) return;
    const d = await post(`/api/v1/classes/${encodeURIComponent(classId)}/members`, { pseudonyms });
    if (!d) return;
    const parts = [`Đã thêm ${d.added.length}`];
    if (d.already.length) parts.push(`${d.already.length} đã ở trong lớp`);
    if (d.unknown.length) parts.push(`không tìm thấy: ${d.unknown.join(", ")}`);
    window.toast(parts.join(" · "), d.unknown.length ? "warn" : "ok");
    detailView();
  });
}

async function showStudents(assignmentId) {
  const el = document.getElementById(`detail-${assignmentId}`);
  if (!el.hidden) {
    el.hidden = true;
    return;
  }
  const d = await window.apiJson(`/api/v1/assignments/${encodeURIComponent(assignmentId)}`);
  if (!d) return;
  el.hidden = false;
  el.innerHTML = `<div class="table-scroll" tabindex="0" role="region" aria-label="Bảng sinh viên"><table><thead><tr><th>Sinh viên</th><th>Trạng thái</th><th>Nộp lúc</th><th>Band</th><th></th></tr></thead><tbody>${d.students
    .map(
      (s) => `<tr><td>${escapeHtml(s.pseudonym)}</td><td><span class="badge ${STATE_CLASS[s.state] || ""}">${STATE[s.state] || s.state}</span></td>
        <td>${s.submitted_at ? new Date(s.submitted_at).toLocaleString("vi-VN") : "—"}</td>
        <td>${s.band ? escapeHtml(s.band) + (s.teacher_verified ? " ✓" : "") : "—"}</td>
        <td>${s.response_id ? `<a href="/review/${encodeURIComponent(s.response_id)}">Mở bài</a>` : ""}</td></tr>`,
    )
    .join("")}</tbody></table></div>`;
}

if (classId) detailView();
else listView();
