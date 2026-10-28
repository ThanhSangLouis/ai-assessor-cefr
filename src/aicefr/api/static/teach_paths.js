// Teachers author paths, units and lessons (D025, M16).
//
// A path is visible to students only once published, and a lesson only in its
// last published version; this screen says which is which on every row, so a
// teacher never wonders what the class is seeing.
const escapeHtml = window.escapeHtml;
const root = document.getElementById("teach-paths");
let paths = [];

const STAGE_OF = window.ui.STEP_STAGES;
const criterionName = window.ui.practiceName;
const $ = (id) => document.getElementById(id);
const icon = (name, cls) => window.ui.icon(name, cls);
const TOPICS = window.ui.TOPICS;
const topicOf = window.ui.topicOf;
const NO_RIGHTS =
  '<p class="error">Tài khoản này không có quyền soạn bài. <a href="/">Về trang của bạn</a>.</p>';

// One place for the request, the session check and the error message.
async function api(method, url, body) {
  const r = await fetch(url, {
    method,
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : typeof body === "string" ? body : JSON.stringify(body),
  });
  if (window.redirectToLoginIfExpired(r)) throw new Error("expired");
  const d = await r.json().catch(() => ({}));
  if (!r.ok) {
    const msg = typeof d.detail === "string" ? d.detail : "Không lưu được. Kiểm tra lại các ô đã nhập.";
    const err = new Error(msg);
    err.status = r.status;
    // A 403 on reading means no rights (the page says so); on writing it is
    // the plan (D034), and its message says which plan includes it.
    if (r.status !== 403 || method !== "GET") window.toast(msg.charAt(0).toUpperCase() + msg.slice(1), "error");
    throw err;
  }
  return d;
}

function ladder(kinds) {
  return (
    '<span class="mini-ladder" aria-hidden="true">' +
    kinds.map((k) => `<i class="${escapeHtml(STAGE_OF[k] || "model")}"></i>`).join("") +
    "</span>"
  );
}

function lessonRow(l) {
  const id = encodeURIComponent(l.lesson_id);
  const state = l.published_version
    ? `<span class="badge state-on">Đã xuất bản v${Number(l.published_version)}</span>` +
      (l.draft_changed ? ' <span class="badge state-warn">Có sửa đổi chưa xuất bản</span>' : "")
    : '<span class="badge state-off">Chưa xuất bản</span>';
  const name = escapeHtml(l.title);
  return (
    "<tr>" +
    `<td><a class="t-lesson-link" href="/teach/lessons/${id}">${escapeHtml(l.title)}</a>` +
    (l.sample ? ' <span class="badge sample-badge">Mẫu</span>' : "") +
    `<div class="muted">${escapeHtml(l.band)}${l.criterion ? ` · ${escapeHtml(criterionName(l.criterion))}` : ""}</div></td>` +
    `<td class="t-steps">${ladder(l.kinds)} <span class="muted">${Number(l.steps)} bước</span></td>` +
    `<td>${state}</td>` +
    '<td><div class="t-row-actions">' +
    `<a class="button small" href="/teach/lessons/${id}">${icon("pencil")}Soạn</a>` +
    `<a class="button small secondary" href="/practice/lessons/${id}?preview=1">${icon("eye")}Xem thử</a>` +
    `<button type="button" class="small secondary icon-only" data-action="lesson-up" data-id="${escapeHtml(l.lesson_id)}" aria-label="Đưa bài ${name} lên trên">${icon("arrow-up")}</button>` +
    `<button type="button" class="small secondary icon-only" data-action="lesson-down" data-id="${escapeHtml(l.lesson_id)}" aria-label="Đưa bài ${name} xuống dưới">${icon("arrow-down")}</button>` +
    `<button type="button" class="small secondary icon-only" data-action="archive-lesson" data-id="${escapeHtml(l.lesson_id)}" data-name="${name}" aria-label="Lưu trữ bài ${name}" title="Lưu trữ">${icon("archive")}</button>` +
    "</div></td></tr>"
  );
}

function unitBlock(u) {
  const uid = escapeHtml(u.unit_id);
  const name = escapeHtml(u.title);
  const table = u.lessons.length
    ? '<table class="t-lessons"><thead><tr><th scope="col">Bài học</th><th scope="col">Các bước</th>' +
      '<th scope="col">Trạng thái</th><th scope="col"><span class="visually-hidden">Thao tác</span></th></tr></thead>' +
      `<tbody>${u.lessons.map(lessonRow).join("")}</tbody></table>`
    : '<p class="muted t-empty">Chặng này chưa có bài học.</p>';
  return (
    `<div class="t-unit topic-${topicOf(u)}">` +
    '<div class="t-unit-head">' +
    `<span class="unit-icon">${icon(TOPICS[u.topic] ? TOPICS[u.topic][1] : "layers")}</span>` +
    '<div class="t-unit-title"><div class="unit-tags">' +
    (u.band ? `<span class="badge band-badge">${escapeHtml(u.band)}</span>` : "") +
    (TOPICS[u.topic] ? `<span class="badge topic-badge">${escapeHtml(TOPICS[u.topic][0])}</span>` : "") +
    (u.criterion ? `<span class="badge">${escapeHtml(criterionName(u.criterion))}</span>` : "") +
    `</div><h3>${escapeHtml(u.title)}</h3>` +
    (u.function ? `<p class="muted">${escapeHtml(u.function)}</p>` : "") +
    '</div><div class="t-actions">' +
    `<button type="button" class="small secondary icon-only" data-action="unit-up" data-id="${uid}" aria-label="Đưa chặng ${name} lên trên">${icon("arrow-up")}</button>` +
    `<button type="button" class="small secondary icon-only" data-action="unit-down" data-id="${uid}" aria-label="Đưa chặng ${name} xuống dưới">${icon("arrow-down")}</button>` +
    `<button type="button" class="small secondary" data-action="edit-unit" data-id="${uid}">${icon("pencil")}<span>Sửa chặng</span></button>` +
    (u.lessons.length
      ? ""
      : `<button type="button" class="small secondary" data-action="delete-unit" data-id="${uid}" data-name="${name}">${icon("trash")}<span>Xoá chặng</span></button>`) +
    `<button type="button" class="small" data-action="add-lesson" data-id="${uid}" data-band="${escapeHtml(u.band || "A2")}">${icon("plus")}<span>Thêm bài học</span></button>` +
    "</div></div>" +
    table +
    "</div>"
  );
}

function pathCard(p, i) {
  const all = p.units.flatMap((u) => u.lessons);
  const live = all.filter((l) => l.published_version).length;
  const published = p.status === "published";
  const pid = escapeHtml(p.path_id);
  const bands = p.band_from && p.band_to ? `${escapeHtml(p.band_from)} → ${escapeHtml(p.band_to)} · ` : "";
  return (
    `<section class="card t-path" aria-labelledby="path-h-${i}">` +
    '<div class="t-path-head"><div class="t-path-title">' +
    `<p class="eyebrow">${bands}${p.units.length} chặng · ${live}/${all.length} bài đã xuất bản</p>` +
    `<h2 id="path-h-${i}">${escapeHtml(p.title)}</h2>` +
    '<div class="unit-tags">' +
    (published
      ? '<span class="badge state-on">Sinh viên đang thấy lộ trình này</span>'
      : '<span class="badge state-off">Nháp: sinh viên chưa thấy</span>') +
    (p.sample ? '<span class="badge sample-badge">Nội dung mẫu, chờ giảng viên duyệt</span>' : "") +
    "</div>" +
    (p.description ? `<p class="muted">${escapeHtml(p.description)}</p>` : "") +
    '</div><div class="t-actions">' +
    `<button type="button" class="small${published ? " secondary" : ""}" data-action="toggle-path" data-id="${pid}">` +
    `${icon(published ? "eye-off" : "upload")}<span>${published ? "Gỡ xuất bản" : "Xuất bản lộ trình"}</span></button>` +
    `<button type="button" class="small secondary" data-action="edit-path" data-id="${pid}">${icon("pencil")}<span>Sửa thông tin</span></button>` +
    `<a class="button small secondary" href="/api/v1/teach/paths/${encodeURIComponent(p.path_id)}/export" download>${icon("download")}Xuất JSON</a>` +
    `<button type="button" class="small" data-action="add-unit" data-id="${pid}">${icon("plus")}<span>Thêm chặng</span></button>` +
    "</div></div>" +
    (p.units.length ? p.units.map(unitBlock).join("") : '<p class="muted t-empty">Lộ trình chưa có chặng nào.</p>') +
    "</section>"
  );
}

function render() {
  window.clearBusy(root);
  if (!paths.length) {
    root.innerHTML =
      '<div class="card"><div class="empty-state"><div class="empty-mark" aria-hidden="true">◇</div>' +
      "<h2>Chưa có lộ trình nào</h2><p>Tạo lộ trình đầu tiên, hoặc nhập một lộ trình từ tệp JSON.</p>" +
      '<div class="button-row"><button type="button" data-action="new-path">Tạo lộ trình</button></div></div></div>';
    return;
  }
  root.innerHTML = paths.map(pathCard).join("");
}

// The school's plan (D034): without lesson writing, the sample path is still
// there to teach with, and the page says what would open the rest.
async function planNote() {
  const r = await fetch("/api/v1/plan");
  if (!r.ok) return;
  const plan = await r.json();
  if (!plan.enabled || plan.features.includes("lesson_authoring")) return;
  const note = $("plan-note");
  note.innerHTML =
    `Trường đang dùng gói <b>${escapeHtml(plan.plan_name)}</b>: dạy bằng lộ trình mẫu và các lộ trình ` +
    "đã xuất bản, sinh viên học như thường. Tạo, sửa và xuất bản lộ trình có ở gói Chuẩn và Nâng cao; " +
    "quản trị viên nâng cấp ở tab Gói dịch vụ.";
  note.hidden = false;
  for (const id of ["new-path", "import-path"]) $(id).disabled = true;
}

async function load() {
  planNote().catch(() => {});
  try {
    paths = await api("GET", "/api/v1/teach/paths");
    render();
  } catch (err) {
    window.clearBusy(root);
    if (err.status === 403) root.innerHTML = NO_RIGHTS;
    else if (err.message !== "expired") root.innerHTML = '<p class="error">Không tải được danh sách lộ trình.</p>';
  }
}

const findUnit = (id) => paths.flatMap((p) => p.units).find((u) => u.unit_id === id);

// ---------------------------------------------------------------- dialogs
let editingPath = null;
let unitTarget = { path: null, unit: null };
let lessonUnit = null;

document.querySelectorAll("[data-close]").forEach((b) =>
  b.addEventListener("click", () => $(b.dataset.close).close())
);

function openPath(id) {
  editingPath = id;
  const p = id ? paths.find((x) => x.path_id === id) : null;
  $("path-dialog-h").textContent = p ? "Sửa thông tin lộ trình" : "Lộ trình mới";
  $("path-title").value = p ? p.title : "";
  $("path-description").value = p ? p.description || "" : "";
  $("path-band-from").value = (p && p.band_from) || "A2";
  $("path-band-to").value = (p && p.band_to) || "B2";
  $("path-dialog").showModal();
}

$("path-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = {
    title: $("path-title").value.trim(),
    description: $("path-description").value.trim(),
    band_from: $("path-band-from").value,
    band_to: $("path-band-to").value,
  };
  try {
    if (editingPath) await api("PATCH", `/api/v1/teach/paths/${encodeURIComponent(editingPath)}`, body);
    else await api("POST", "/api/v1/teach/paths", body);
    $("path-dialog").close();
    window.toast(editingPath ? "Đã lưu lộ trình." : "Đã tạo lộ trình. Thêm chặng đầu tiên cho nó.", "ok");
    load();
  } catch (err) {
    /* the message is already on screen */
  }
});

function openUnit(pathId, unitId) {
  unitTarget = { path: pathId, unit: unitId };
  const u = unitId ? findUnit(unitId) : null;
  $("unit-dialog-h").textContent = u ? "Sửa chặng" : "Chặng mới";
  $("unit-title").value = u ? u.title : "";
  $("unit-function").value = u ? u.function || "" : "";
  $("unit-band").value = (u && u.band) || "A2";
  $("unit-topic").value = (u && u.topic) || "";
  $("unit-criterion").value = (u && u.criterion) || "";
  $("unit-dialog").showModal();
}

$("unit-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = {
    title: $("unit-title").value.trim(),
    function: $("unit-function").value.trim(),
    band: $("unit-band").value,
    topic: $("unit-topic").value || null,
    criterion: $("unit-criterion").value || null,
  };
  try {
    if (unitTarget.unit) await api("PATCH", `/api/v1/teach/units/${encodeURIComponent(unitTarget.unit)}`, body);
    else await api("POST", `/api/v1/teach/paths/${encodeURIComponent(unitTarget.path)}/units`, body);
    $("unit-dialog").close();
    window.toast("Đã lưu chặng.", "ok");
    load();
  } catch (err) {
    /* shown */
  }
});

function openLesson(unitId, band) {
  lessonUnit = unitId;
  $("lesson-form").reset();
  $("lesson-band").value = band || "A2";
  $("lesson-dialog").showModal();
}

$("lesson-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const submit = e.target.querySelector('button[type="submit"]');
  submit.disabled = true;
  const body = {
    title: $("lesson-title").value.trim(),
    band: $("lesson-band").value,
    criterion: $("lesson-criterion").value || null,
    summary: $("lesson-summary").value.trim(),
    model_text: $("lesson-text").value.trim(),
    keywords: $("lesson-keywords")
      .value.split(",")
      .map((w) => w.trim())
      .filter(Boolean),
    free_prompt: $("lesson-prompt").value.trim(),
  };
  try {
    const d = await api("POST", `/api/v1/teach/units/${encodeURIComponent(lessonUnit)}/lessons`, body);
    location.href = `/teach/lessons/${encodeURIComponent(d.lesson_id)}`;
  } catch (err) {
    submit.disabled = false;
  }
});

// ---------------------------------------------------------------- actions
async function act(button) {
  const id = button.dataset.id;
  const action = button.dataset.action;
  if (action === "new-path") return openPath(null);
  if (action === "edit-path") return openPath(id);
  if (action === "add-unit") return openUnit(id, null);
  if (action === "edit-unit") return openUnit(null, id);
  if (action === "add-lesson") return openLesson(id, button.dataset.band);

  button.disabled = true;
  try {
    if (action === "toggle-path") {
      const p = paths.find((x) => x.path_id === id);
      const publish = p.status !== "published";
      const question = publish
        ? "Xuất bản lộ trình này? Sinh viên sẽ thấy các bài đã xuất bản trong lộ trình."
        : "Gỡ xuất bản? Sinh viên sẽ không thấy lộ trình này nữa; các lượt luyện đã có vẫn được giữ.";
      if (!confirm(question)) return;
      await api("PATCH", `/api/v1/teach/paths/${encodeURIComponent(id)}`, { status: publish ? "published" : "draft" });
      window.toast(publish ? "Đã xuất bản lộ trình." : "Đã gỡ xuất bản lộ trình.", "ok");
    } else if (action === "unit-up" || action === "unit-down") {
      await api("POST", `/api/v1/teach/units/${encodeURIComponent(id)}/move`, { direction: action === "unit-up" ? -1 : 1 });
    } else if (action === "lesson-up" || action === "lesson-down") {
      await api("POST", `/api/v1/teach/lessons/${encodeURIComponent(id)}/move`, { direction: action === "lesson-up" ? -1 : 1 });
    } else if (action === "delete-unit") {
      if (!confirm(`Xoá chặng «${button.dataset.name}»?`)) return;
      await api("DELETE", `/api/v1/teach/units/${encodeURIComponent(id)}`);
      window.toast("Đã xoá chặng.", "ok");
    } else if (action === "archive-lesson") {
      const question =
        `Lưu trữ bài «${button.dataset.name}»? Sinh viên sẽ không thấy bài này nữa; ` +
        "các lượt luyện đã có vẫn được giữ.";
      if (!confirm(question)) return;
      await api("DELETE", `/api/v1/teach/lessons/${encodeURIComponent(id)}`);
      window.toast("Đã lưu trữ bài học.", "ok");
    }
    await load();
  } catch (err) {
    /* shown by api() */
  } finally {
    button.disabled = false;
  }
}

root.addEventListener("click", (e) => {
  const button = e.target.closest("[data-action]");
  if (button) act(button);
});
$("new-path").addEventListener("click", () => openPath(null));

// Import: a path exported from this or another installation arrives as a draft.
$("import-path").addEventListener("click", () => $("import-file").click());
$("import-file").addEventListener("change", async () => {
  const file = $("import-file").files[0];
  $("import-file").value = "";
  if (!file) return;
  try {
    await api("POST", "/api/v1/teach/paths/import", await file.text());
    window.toast("Đã nhập lộ trình. Lộ trình ở trạng thái nháp cho tới khi bạn xuất bản.", "ok");
    load();
  } catch (err) {
    /* shown */
  }
});

load();
