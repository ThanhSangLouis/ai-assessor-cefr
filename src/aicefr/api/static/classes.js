// "Classes" (D054, D071): the classes, one class's teachers, members and
// assignments, and who handed in what -- by the students' names; D074: the
// bands each student studies, grouped by target, and a path for each group. An
// administrator sees every class and assigns its teachers.
const escapeHtml = window.escapeHtml;
const root = document.getElementById("classes-root");
const classId = root.dataset.classId;
const isAdmin = root.dataset.role === "admin";
const teacherNames = (c) => (c.teachers || []).map((t) => escapeHtml(t.name)).join(", ");
const list = (raw) => raw.split(/[,;\s]+/).map((x) => x.trim()).filter(Boolean);

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

// ---------------------------------------------------------------- bands (D074)
// Each learner chooses the bands they study; the class shows them grouped by
// the band they aim for, and a teacher composes a path for a group or assigns
// a published one to it. Assigning replaces each learner's own path.
function bandText(b) {
  if (!b) return '<span class="muted">chưa chọn</span>';
  const range = b.band_from === b.band_to ? escapeHtml(b.band_from) : `${escapeHtml(b.band_from)} → ${escapeHtml(b.band_to)}`;
  return b.assigned_by ? `${range} <span class="muted small">· giảng viên giao</span>` : range;
}

function groupsOf(c) {
  const groups = {};
  c.members.forEach((m) => {
    if (!m.bands || !m.bands.band_to) return;
    const g = (groups[m.bands.band_to] = groups[m.bands.band_to] || { target: m.bands.band_to, from: m.bands.band_from, people: [] });
    if (BAND_ORDER.indexOf(m.bands.band_from) < BAND_ORDER.indexOf(g.from)) g.from = m.bands.band_from;
    g.people.push(m);
  });
  return BAND_ORDER.filter((b) => groups[b]).map((b) => groups[b]);
}

function bandGroups(c) {
  const groups = groupsOf(c);
  const none = c.members.filter((m) => !m.bands).length;
  if (!c.members.length) return "";
  const rows = groups
    .map(
      (g) => `<div class="band-group" data-target="${escapeHtml(g.target)}">
        <span class="band-badge">${escapeHtml(g.target)}</span>
        <div class="who"><b>${g.people.length} sinh viên</b> nhắm tới ${escapeHtml(g.target)}, đang từ ${escapeHtml(g.from)}
          <div class="muted small">${g.people.map((p) => escapeHtml(p.name)).join(", ")}</div></div>
        <a class="button secondary small" href="/teach?compose=1&band_from=${encodeURIComponent(g.from)}&band_to=${encodeURIComponent(g.target)}">Soạn lộ trình cho nhóm</a>
        <label class="visually-hidden" for="assign-${escapeHtml(g.target)}">Lộ trình giao cho nhóm ${escapeHtml(g.target)}</label>
        <select id="assign-${escapeHtml(g.target)}" data-paths><option value="">Chọn lộ trình đã xuất bản…</option></select>
        <button class="button small" data-assign="${escapeHtml(g.target)}">Giao cho nhóm</button>
      </div>`,
    )
    .join("");
  return `<section class="card" aria-labelledby="bands-h">
    <div class="card-head"><h2 id="bands-h">Nhóm theo band mục tiêu</h2></div>
    <p class="muted">Sinh viên tự chọn band trên trang Lộ trình. Giao lộ trình cho một nhóm sẽ thay lộ trình riêng của từng người trong nhóm.</p>
    ${groups.length ? `<div class="band-groups">${rows}</div>` : '<p class="muted">Chưa sinh viên nào chọn band.</p>'}
    ${none ? `<p class="muted small">${none} sinh viên chưa chọn band.</p>` : ""}
  </section>`;
}

async function wireGroups(c) {
  const selects = root.querySelectorAll("select[data-paths]");
  if (!selects.length) return;
  const paths = await window.apiJson("/api/v1/teach/paths");
  const published = (paths || []).filter((p) => p.status === "published");
  const opts = published.map((p) => `<option value="${escapeHtml(p.path_id)}">${escapeHtml(p.title)} (${escapeHtml(p.band_from)}–${escapeHtml(p.band_to)})</option>`).join("");
  selects.forEach((s) => s.insertAdjacentHTML("beforeend", opts));
  const groups = groupsOf(c);
  root.querySelectorAll("button[data-assign]").forEach((b) =>
    b.addEventListener("click", async () => {
      const g = groups.find((x) => x.target === b.dataset.assign);
      const pathId = document.getElementById(`assign-${b.dataset.assign}`).value;
      if (!pathId) {
        window.toast("Hãy chọn một lộ trình đã xuất bản.", "error");
        return;
      }
      if (!window.confirm(`Giao lộ trình này cho ${g.people.length} sinh viên nhóm ${g.target}? Lộ trình riêng của họ sẽ được thay.`)) return;
      const d = await post(`/api/v1/teach/paths/${encodeURIComponent(pathId)}/assign`, { account_ids: g.people.map((p) => p.account_id) });
      if (d) {
        window.toast(`Đã giao “${d.path_title}” cho ${d.assigned} sinh viên.`, "ok");
        detailView();
      }
    }),
  );
}

async function listView() {
  const classes = await window.apiJson("/api/v1/classes");
  if (!classes) return;
  root.innerHTML = `
    <section class="card" aria-labelledby="new-h">
      <div class="card-head"><h2 id="new-h">Tạo lớp mới</h2></div>
      <form id="new-class" class="inline-form">
        <label class="field"><span>Tên lớp</span><input name="name" maxlength="80" required placeholder="Ví dụ: Tiếng Anh 2 · nhóm 03"></label>
        ${
          isAdmin
            ? '<label class="field"><span>Email giảng viên, cách nhau bằng dấu phẩy</span><input name="teachers" placeholder="gv.an@truong.edu.vn"></label>'
            : ""
        }
        <button class="button" type="submit">Tạo lớp</button>
      </form>
    </section>
    <section class="card" aria-labelledby="list-h">
      <div class="card-head"><h2 id="list-h">${isAdmin ? "Tất cả lớp" : "Lớp của tôi"}</h2></div>
      ${
        classes.length
          ? `<ul class="plain-list">${classes
              .map(
                (c) => `<li class="assign-row"><div><a href="/teach/classes/${encodeURIComponent(c.class_id)}"><b>${escapeHtml(c.name)}</b></a>
                  <div class="muted small">Mã lớp <code>${escapeHtml(c.code)}</code> · ${c.members} sinh viên · ${c.assignments} bài đã giao${c.archived ? " · đã lưu trữ" : ""}</div>
                  <div class="muted small">Giảng viên: ${teacherNames(c) || "chưa phân công"}</div></div></li>`,
              )
              .join("")}</ul>`
          : '<p class="muted">Chưa có lớp nào.</p>'
      }
    </section>`;
  document.getElementById("new-class").addEventListener("submit", async (e) => {
    e.preventDefault();
    const body = { name: e.target.name.value };
    if (isAdmin) body.teachers = list(e.target.teachers.value);
    const made = await post("/api/v1/classes", body);
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
    <section class="card" aria-labelledby="teachers-h">
      <div class="card-head"><h2 id="teachers-h">Giảng viên (${c.teachers.length})</h2></div>
      <ul class="plain-list">${
        c.teachers
          .map(
            (t) => `<li class="assign-row"><span>${escapeHtml(t.name)}</span>${
              isAdmin
                ? `<button class="button secondary small" data-unteach="${escapeHtml(t.account_id)}">Bỏ phân công</button>`
                : ""
            }</li>`,
          )
          .join("") || '<li class="muted">Chưa phân công giảng viên: chỉ quản trị viên chấm bài của lớp này.</li>'
      }</ul>
      ${
        isAdmin
          ? `<form id="teachers-form" class="inline-form">
        <label class="field"><span>Phân công giảng viên theo email</span><input name="email" type="email" placeholder="gv.an@truong.edu.vn" required></label>
        <button class="button secondary" type="submit">Phân công</button>
      </form>`
          : ""
      }
    </section>
    ${bandGroups(c)}
    <section class="card" aria-labelledby="members-h">
      <div class="card-head"><h2 id="members-h">Sinh viên (${c.members.length})</h2></div>
      ${
        c.members.length
          ? `<div class="table-scroll" tabindex="0" role="region" aria-label="Danh sách sinh viên"><table><thead><tr><th>Họ và tên</th><th>Email</th><th>Học theo band</th><th></th></tr></thead><tbody>${c.members
              .map(
                (m) => `<tr><td>${escapeHtml(m.name)}</td><td>${m.email ? escapeHtml(m.email) : '<span class="muted">chưa có</span>'}</td>
                  <td>${bandText(m.bands)}</td>
                  <td><button class="button secondary small" data-remove="${escapeHtml(m.account_id)}">Xoá khỏi lớp</button></td></tr>`,
              )
              .join("")}</tbody></table></div>`
          : '<p class="muted">Chưa có ai.</p>'
      }
      <form id="members-form" class="inline-form">
        <label class="field"><span>Thêm sinh viên theo email, cách nhau bằng dấu phẩy</span><input name="list" placeholder="an.nguyen@truong.edu.vn, binh.tran@truong.edu.vn"></label>
        <button class="button secondary" type="submit">Thêm</button>
      </form>
    </section>`;
  wireGroups(c);
  root.querySelectorAll("button[data-remove]").forEach((b) =>
    b.addEventListener("click", async () => {
      const r = await window.apiJson(
        `/api/v1/classes/${encodeURIComponent(classId)}/members/${encodeURIComponent(b.dataset.remove)}`,
        { method: "DELETE" },
      );
      if (r) detailView();
    }),
  );
  root.querySelectorAll("button[data-unteach]").forEach((b) =>
    b.addEventListener("click", async () => {
      const r = await window.apiJson(
        `/api/v1/classes/${encodeURIComponent(classId)}/teachers/${encodeURIComponent(b.dataset.unteach)}`,
        { method: "DELETE" },
      );
      if (r) detailView();
    }),
  );
  const teachersForm = document.getElementById("teachers-form");
  if (teachersForm)
    teachersForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const d = await post(`/api/v1/classes/${encodeURIComponent(classId)}/teachers`, {
        email: e.target.email.value.trim(),
      });
      if (d) {
        window.toast(d.added ? "Đã phân công giảng viên." : "Giảng viên này đã dạy lớp.", "ok");
        detailView();
      }
    });
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
    const people = list(e.target.list.value);
    if (!people.length) return;
    const d = await post(`/api/v1/classes/${encodeURIComponent(classId)}/members`, { people });
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
      (s) => `<tr><td>${escapeHtml(s.name)}</td><td><span class="badge ${STATE_CLASS[s.state] || ""}">${STATE[s.state] || s.state}</span></td>
        <td>${s.submitted_at ? new Date(s.submitted_at).toLocaleString("vi-VN") : "—"}</td>
        <td>${s.band ? escapeHtml(s.band) + (s.teacher_verified ? " ✓" : "") : "—"}</td>
        <td>${s.response_id ? `<a href="/review/${encodeURIComponent(s.response_id)}">Mở bài</a>` : ""}</td></tr>`,
    )
    .join("")}</tbody></table></div>`;
}

if (classId) detailView();
else listView();
