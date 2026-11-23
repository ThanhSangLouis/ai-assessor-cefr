// "Classes" (D054, D071, D075): the classes, one class's teachers and members
// by name; D074: the bands each student studies, grouped by target, and a path
// for each group. Classes set no assessments any more (D075). An
// administrator sees every class and assigns its teachers.
const escapeHtml = window.escapeHtml;
const icon = (name) => window.ui.icon(name);
const root = document.getElementById("classes-root");
const classId = root.dataset.classId;
const isAdmin = root.dataset.role === "admin";
const teacherNames = (c) => (c.teachers || []).map((t) => escapeHtml(t.name)).join(", ");
const list = (raw) => raw.split(/[,;\s]+/).map((x) => x.trim()).filter(Boolean);

const BAND_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"];
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
  const chip = (x) => `<span class="band-chip" data-band="${escapeHtml(x)}">${escapeHtml(x)}</span>`;
  const range = b.band_from === b.band_to ? chip(b.band_from) : `${chip(b.band_from)} → ${chip(b.band_to)}`;
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
        <span class="band-chip" data-band="${escapeHtml(g.target)}">${escapeHtml(g.target)}</span>
        <div class="who"><b>${g.people.length} sinh viên</b> nhắm tới ${escapeHtml(g.target)}, đang từ ${escapeHtml(g.from)}
          <div class="muted small">${g.people.map((p) => escapeHtml(p.name)).join(", ")}</div></div>
        <a class="button secondary small" href="/teach?compose=1&band_from=${encodeURIComponent(g.from)}&band_to=${encodeURIComponent(g.target)}">Soạn lộ trình cho nhóm</a>
        <label class="visually-hidden" for="assign-${escapeHtml(g.target)}">Lộ trình giao cho nhóm ${escapeHtml(g.target)}</label>
        <select id="assign-${escapeHtml(g.target)}" data-paths><option value="">Chọn lộ trình đã xuất bản…</option></select>
        <button type="button" class="small" data-assign="${escapeHtml(g.target)}">Giao cho nhóm</button>
      </div>`,
    )
    .join("");
  return `<section class="card" aria-labelledby="bands-h">
    <div class="card-head"><h2 id="bands-h">${icon("layers")} Nhóm theo band mục tiêu</h2></div>
    <p class="muted">Sinh viên tự chọn band trên trang Lộ trình. Giao lộ trình cho một nhóm sẽ thay lộ trình riêng của từng người trong nhóm.</p>
    ${groups.length ? `<div class="band-groups">${rows}</div>` : '<p class="muted">Chưa sinh viên nào chọn band.</p>'}
    ${none ? `<p class="muted small">${none} sinh viên chưa chọn band.</p>` : ""}
  </section>`;
}

async function wireGroups(c) {
  const selects = root.querySelectorAll("select[data-paths]");
  if (!selects.length) return;
  if (window.enhanceSelects) window.enhanceSelects(root);
  const paths = await window.apiJson("/api/v1/teach/paths");
  const published = (paths || []).filter((p) => p.status === "published");
  const opts = published.map((p) => `<option value="${escapeHtml(p.path_id)}">${escapeHtml(p.title)} (${escapeHtml(p.band_from)}–${escapeHtml(p.band_to)})</option>`).join("");
  selects.forEach((s) => {
    s.insertAdjacentHTML("beforeend", opts);
    s.dispatchEvent(new Event("change"));
  });
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
      <div class="card-head"><h2 id="new-h">${icon("user-plus")} Tạo lớp mới</h2></div>
      <p class="muted">Tạo lớp để quản lý sinh viên và theo dõi bài nói.</p>
      <form id="new-class" class="inline-form one-line" novalidate>
        <div class="field field-name">
          <label for="class-name">Tên lớp</label>
          <input id="class-name" name="name" maxlength="80" required placeholder="Ví dụ: Tiếng Anh 2 · nhóm 03" autocomplete="off">
        </div>
        ${
          isAdmin
            ? `<div class="field field-list">
          <label for="class-teachers">Email giảng viên, cách nhau bằng dấu phẩy</label>
          <input id="class-teachers" name="teachers" placeholder="gv-01@demo.speakup.fit, gv-02@demo.speakup.fit" autocomplete="off">
        </div>`
            : ""
        }
        <div class="button-row">
          <button class="button" type="submit">Tạo lớp</button>
        </div>
      </form>
    </section>
    <section class="card" aria-labelledby="list-h">
      <div class="list-toolbar">
        <h2 id="list-h">${icon("users")} ${isAdmin ? "Tất cả lớp" : "Lớp của tôi"}</h2>
        <span class="muted">${classes.length} lớp</span>
      </div>
      ${
        classes.length
          ? `<div class="table-scroll" tabindex="0" role="region" aria-label="Danh sách lớp"><table class="classes-table"><thead><tr><th scope="col">Lớp</th><th scope="col">Sinh viên</th><th scope="col">Giảng viên</th><th scope="col">Trạng thái</th></tr></thead><tbody>${classes
              .map(
                (c) => `<tr><td><a href="/teach/classes/${encodeURIComponent(c.class_id)}"><b>${escapeHtml(c.name)}</b></a></td>
                  <td>${c.members}</td>
                  <td>${teacherNames(c) || "chưa phân công"}</td>
                  <td>${c.archived ? '<span class="badge">Lưu trữ</span>' : '<span class="badge COMPLETED">Đang dùng</span>'}</td></tr>`,
              )
              .join("")}</tbody></table></div>`
          : '<p class="muted">Chưa có lớp nào.</p>'
      }
    </section>`;
  document.getElementById("new-class").addEventListener("submit", async (e) => {
    e.preventDefault();
    const nameInput = e.target.elements.name;
    const name = nameInput.value.trim();
    if (!name) {
      window.toast("Hãy nhập tên lớp.", "error");
      nameInput.focus();
      return;
    }
    const body = { name };
    if (isAdmin) body.teachers = list(e.target.elements.teachers.value);
    const made = await post("/api/v1/classes", body);
    if (made) window.location.assign(`/teach/classes/${encodeURIComponent(made.class_id)}`);
  });
}

async function detailView() {
  const c = await window.apiJson(`/api/v1/classes/${encodeURIComponent(classId)}`);
  if (!c) return;
  document.getElementById("page-title").textContent = c.name;
  document.getElementById("page-lede").innerHTML =
    `${c.archived ? "Lớp đã lưu trữ. " : ""}<a href="/teach/classes">Tất cả lớp</a>`;
  root.innerHTML = `
    <section class="card" aria-labelledby="members-h">
      <div class="card-head"><h2 id="members-h">${icon("users")} Sinh viên (${c.members.length})</h2></div>
      <form id="members-form" class="inline-form one-line" novalidate>
        <div class="field field-list">
          <label for="member-list">Thêm sinh viên theo email, cách nhau bằng dấu phẩy</label>
          <input id="member-list" name="list" placeholder="sv-001@demo.speakup.fit, sv-002@demo.speakup.fit" autocomplete="off">
        </div>
        <div class="button-row">
          <button class="button secondary" type="submit">Thêm</button>
        </div>
      </form>
      ${
        c.members.length
          ? `<div class="table-scroll" tabindex="0" role="region" aria-label="Danh sách sinh viên"><table class="members-table"><thead><tr><th scope="col">Sinh viên</th><th scope="col">Học theo band</th><th scope="col"><span class="visually-hidden">Thao tác</span></th></tr></thead><tbody>${c.members
              .map(
                (m) => `<tr><td>${escapeHtml(m.name)}${m.email && m.email !== m.name ? `<span class="cell-sub">${escapeHtml(m.email)}</span>` : ""}</td>
                  <td>${bandText(m.bands)}</td>
                  <td><div class="row-actions"><button type="button" class="danger small" data-remove="${escapeHtml(m.account_id)}" data-name="${escapeHtml(m.name)}" aria-label="Xoá ${escapeHtml(m.name)} khỏi lớp">Xoá khỏi lớp</button></div></td></tr>`,
              )
              .join("")}</tbody></table></div>`
          : '<p class="muted">Chưa có ai.</p>'
      }
    </section>
    <section class="card" aria-labelledby="teachers-h">
      <div class="card-head"><h2 id="teachers-h">${icon("user")} Giảng viên (${c.teachers.length})</h2></div>
      <ul class="plain-list">${
        c.teachers
          .map(
            (t) => `<li class="assign-row"><span>${escapeHtml(t.name)}${t.email && t.email !== t.name ? `<span class="cell-sub">${escapeHtml(t.email)}</span>` : ""}</span>${
              isAdmin
                ? `<div class="row-actions"><button type="button" class="danger small" data-unteach="${escapeHtml(t.account_id)}" data-name="${escapeHtml(t.name)}" aria-label="Bỏ phân công ${escapeHtml(t.name)}">Bỏ phân công</button></div>`
                : ""
            }</li>`,
          )
          .join("") || '<li class="muted">Chưa phân công giảng viên: chỉ quản trị viên chấm bài của lớp này.</li>'
      }</ul>
      ${
        isAdmin
          ? `<form id="teachers-form" class="inline-form one-line" novalidate>
        <div class="field field-list">
          <label for="teacher-email">Phân công giảng viên theo email</label>
          <input id="teacher-email" name="email" type="email" placeholder="gv-01@demo.speakup.fit" required autocomplete="off">
        </div>
        <div class="button-row">
          <button class="button secondary" type="submit">Phân công</button>
        </div>
      </form>`
          : ""
      }
    </section>
    ${bandGroups(c)}
`;
  wireGroups(c);
  root.querySelectorAll("button[data-remove]").forEach((b) =>
    b.addEventListener("click", async () => {
      const name = b.dataset.name || b.dataset.remove;
      if (!window.confirm(`Xoá ${name} khỏi lớp?`)) return;
      const r = await window.apiJson(
        `/api/v1/classes/${encodeURIComponent(classId)}/members/${encodeURIComponent(b.dataset.remove)}`,
        { method: "DELETE" },
      );
      if (r) detailView();
    }),
  );
  root.querySelectorAll("button[data-unteach]").forEach((b) =>
    b.addEventListener("click", async () => {
      const name = b.dataset.name || b.dataset.unteach;
      if (!window.confirm(`Bỏ phân công ${name} khỏi lớp này?`)) return;
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
      const emailInput = e.target.elements.email;
      const email = emailInput.value.trim();
      if (!email) {
        window.toast("Hãy nhập email giảng viên.", "error");
        emailInput.focus();
        return;
      }
      const d = await post(`/api/v1/classes/${encodeURIComponent(classId)}/teachers`, {
        email,
      });
      if (d) {
        window.toast(d.added ? "Đã phân công giảng viên." : "Giảng viên này đã dạy lớp.", "ok");
        detailView();
      }
    });
  document.getElementById("members-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const listInput = e.target.elements.list;
    const people = list(listInput.value);
    if (!people.length) {
      window.toast("Hãy nhập ít nhất một email sinh viên.", "error");
      listInput.focus();
      return;
    }
    const d = await post(`/api/v1/classes/${encodeURIComponent(classId)}/members`, { people });
    if (!d) return;
    const parts = [`Đã thêm ${d.added.length}`];
    if (d.already.length) parts.push(`${d.already.length} đã ở trong lớp`);
    if (d.unknown.length) parts.push(`không tìm thấy: ${d.unknown.join(", ")}`);
    window.toast(parts.join(" · "), d.unknown.length ? "warn" : "ok");
    detailView();
  });
}

if (classId) detailView();
else listView();
