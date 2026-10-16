const escapeHtml = window.escapeHtml;
const root = document.getElementById("teach-paths");
const $ = (id) => document.getElementById(id);
const TOPICS = window.ui.TOPICS;
const topicOf = window.ui.topicOf;
const icon = (name, cls) => window.ui.icon(name, cls);
const PATHS_KEY = "aicefr-teacher-path-ids";
const PUBLISHED_KEY = "aicefr-teacher-published-path-ids";
const DRAFT_KEY = "aicefr-teacher-draft-path-ids";
const LESSONS_KEY = "aicefr-teacher-lessons";
let paths = [];
let editingPath = null;
let unitTarget = { path: null, unit: null };
let lessonUnit = null;

function storedIds(key) {
  try {
    const values = JSON.parse(localStorage.getItem(key) || "[]");
    return Array.isArray(values) ? values.filter((value) => typeof value === "string") : [];
  } catch (_) { return []; }
}
function remember(key, id) {
  const ids = new Set(storedIds(key));
  ids.add(id);
  localStorage.setItem(key, JSON.stringify(Array.from(ids)));
}
function forget(key, id) {
  localStorage.setItem(key, JSON.stringify(storedIds(key).filter((value) => value !== id)));
}
function makeId(prefix) {
  return prefix + "-" + crypto.randomUUID().replaceAll("-", "");
}
function api(method, url, body) {
  return window.apiJson(url, {
    method,
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  }).then((result) => {
    if (result === null) throw new Error("request failed");
    return result;
  });
}
function errorMessage(error) {
  return error && error.message && error.message !== "request failed" ? error.message : "Không tải hoặc lưu được dữ liệu.";
}
async function fetchPath(pathId) {
  const path = await api("GET", "/api/v1/teacher/learn/paths/" + encodeURIComponent(pathId));
  path.status = storedIds(PUBLISHED_KEY).includes(pathId) ? "published" :
    (storedIds(DRAFT_KEY).includes(pathId) ? "draft" : "unknown");
  path.units = await Promise.all((path.units || []).map(async (unit) => {
    const lessons = await Promise.all((unit.lesson_ids || []).map(async (lessonId) => {
      try {
        const lesson = await api("GET", "/api/v1/teacher/learn/lessons/" + encodeURIComponent(lessonId));
        return { ...lesson, published_version: null, draft_changed: false };
      } catch (_) {
        return { lesson_id: lessonId, title: lessonId, band: unit.band, steps: [], unavailable: true };
      }
    }));
    return { ...unit, function: unit.learning_function || "", criterion: null, lessons };
  }));
  return path;
}
function kinds(lesson) { return (lesson.steps || []).map((step) => step.kind); }
function lessonRow(lesson) {
  const id = encodeURIComponent(lesson.lesson_id);
  const state = lesson.unavailable
    ? '<span class="badge state-warn">Bài không đọc được</span>'
    : '<span class="badge state-off">Trạng thái xuất bản do API chưa trả về</span>';
  return '<tr><td><a class="t-lesson-link" href="/teach/lessons/' + id + '?unit_id=' + encodeURIComponent(lesson.unit_id || "") + '">' +
    escapeHtml(lesson.title) + '</a><div class="muted">' + escapeHtml(lesson.band || "") + '</div></td>' +
    '<td>' + (lesson.steps || []).length + ' bước · ' + escapeHtml(kinds(lesson).join(", ")) + '</td>' +
    '<td>' + state + '</td><td><div class="t-row-actions">' +
    '<a class="button small" href="/teach/lessons/' + id + '?unit_id=' + encodeURIComponent(lesson.unit_id || "") + '">' + icon("pencil") + "Soạn</a>" +
    '<a class="button small secondary" href="/practice/lessons/' + id + '?preview=1">' + icon("eye") + "Xem thử</a>" +
    '<button type="button" class="small secondary" data-action="delete-lesson" data-id="' + escapeHtml(lesson.lesson_id) +
    '" data-revision="' + Number(lesson.revision || 0) + '">Lưu trữ</button>' +
    "</div></td></tr>";
}
function unitBlock(unit) {
  const rows = unit.lessons.length
    ? '<table class="t-lessons"><thead><tr><th>Bài học</th><th>Các bước</th><th>Trạng thái</th><th></th></tr></thead><tbody>' +
      unit.lessons.map(lessonRow).join("") + "</tbody></table>"
    : '<p class="muted t-empty">Chặng này chưa có bài học.</p>';
  return '<section class="t-unit topic-' + escapeHtml(topicOf(unit) || "") + '">' +
    '<div class="t-unit-head"><span class="unit-icon">' + icon(TOPICS[unit.topic] ? TOPICS[unit.topic][1] : "layers") +
    '</span><div class="t-unit-title"><div class="unit-tags"><span class="badge band-badge">' +
    escapeHtml(unit.band) + "</span>" + (TOPICS[unit.topic] ? '<span class="badge topic-badge">' +
    escapeHtml(TOPICS[unit.topic][0]) + "</span>" : "") + "</div><h3>" + escapeHtml(unit.title) +
    "</h3>" + (unit.function ? '<p class="muted">' + escapeHtml(unit.function) + "</p>" : "") +
    '</div><div class="t-actions"><button type="button" class="small secondary icon-only" data-action="unit-up" data-path="' +
    escapeHtml(unit.path_id) + '" data-id="' + escapeHtml(unit.unit_id) + '" aria-label="Đưa chặng lên trên">↑</button>' +
    '<button type="button" class="small secondary icon-only" data-action="unit-down" data-path="' +
    escapeHtml(unit.path_id) + '" data-id="' + escapeHtml(unit.unit_id) + '" aria-label="Đưa chặng xuống dưới">↓</button>' +
    '<button type="button" class="small secondary" data-action="edit-unit" data-path="' +
    escapeHtml(unit.path_id) + '" data-id="' + escapeHtml(unit.unit_id) + '">Sửa chặng</button>' +
    (unit.lessons.length ? "" : '<button type="button" class="small secondary" data-action="delete-unit" data-path="' +
      escapeHtml(unit.path_id) + '" data-id="' + escapeHtml(unit.unit_id) + '" data-revision="' + Number(unit.revision) + '">Xoá chặng</button>') +
    '<button type="button" class="small" data-action="add-lesson" data-path="' + escapeHtml(unit.path_id) +
    '" data-id="' + escapeHtml(unit.unit_id) + '" data-band="' + escapeHtml(unit.band) + '">Thêm bài học</button>' +
    "</div></div>" + rows + "</section>";
}
function pathCard(path, index) {
  const published = path.status === "published";
  const draft = path.status === "draft";
  const buttons = published
    ? '<span class="badge state-on">Đã xuất bản · metadata chỉ đọc</span>'
    : '<button type="button" class="small secondary" data-action="edit-path" data-id="' + escapeHtml(path.path_id) + '">Sửa thông tin</button>' +
      '<button type="button" class="small" data-action="add-unit" data-id="' + escapeHtml(path.path_id) + '">Thêm chặng</button>' +
      '<button type="button" class="small secondary" data-action="publish-path" data-id="' + escapeHtml(path.path_id) + '">Xuất bản lộ trình</button>' +
      (draft ? '<button type="button" class="small secondary" data-action="delete-path" data-id="' + escapeHtml(path.path_id) +
        '" data-revision="' + Number(path.revision) + '">Xoá lộ trình nháp</button>' : "");
  return '<section class="card t-path" aria-labelledby="path-h-' + index + '"><div class="t-path-head"><div class="t-path-title">' +
    '<p class="eyebrow">' + escapeHtml(path.band_from) + " → " + escapeHtml(path.band_to) + " · " +
    path.units.length + ' chặng</p><h2 id="path-h-' + index + '">' + escapeHtml(path.title) + '</h2>' +
    '<div class="unit-tags">' + (published ? '<span class="badge state-on">Sinh viên đang thấy lộ trình này</span>' :
      (draft ? '<span class="badge state-off">Nháp: sinh viên chưa thấy</span>' :
        '<span class="badge state-warn">API chưa trả về trạng thái xuất bản</span>')) + "</div>" +
    (path.description ? '<p class="muted">' + escapeHtml(path.description) + "</p>" : "") +
    '</div><div class="t-actions">' + buttons +
    '<a class="button small secondary" href="/api/v1/teacher/learn/paths/' + encodeURIComponent(path.path_id) +
    '/export" download>Xuất JSON</a></div></div>' +
    (path.units.length ? path.units.map(unitBlock).join("") : '<p class="muted t-empty">Lộ trình chưa có chặng nào.</p>') +
    "</section>";
}
function render() {
  window.clearBusy(root);
  if (!paths.length) {
    root.innerHTML = '<div class="card"><div class="empty-state"><div class="empty-mark">◇</div><h2>Chưa có lộ trình đã lưu trên trình duyệt này</h2>' +
      "<p>Tạo lộ trình mới hoặc mở một lộ trình bằng ID. Danh sách được lưu cục bộ vì API hiện chưa có route liệt kê lộ trình.</p>" +
      '<div class="button-row"><button type="button" data-action="new-path">Tạo lộ trình</button>' +
      '<button type="button" data-action="load-path">Mở bằng ID</button></div></div></div>';
    return;
  }
  root.innerHTML = paths.map(pathCard).join("") +
    '<div class="card"><button type="button" class="secondary" data-action="load-path">Mở lộ trình khác bằng ID</button></div>';
}
async function load() {
  const ids = storedIds(PATHS_KEY);
  const results = await Promise.all(ids.map(async (id) => {
    try { return await fetchPath(id); }
    catch (_) { forget(PATHS_KEY, id); return null; }
  }));
  paths = results.filter(Boolean);
  render();
}
function findPath(id) { return paths.find((path) => path.path_id === id); }
function findUnit(pathId, unitId) { const path = findPath(pathId); return path && path.units.find((unit) => unit.unit_id === unitId); }
function openPath(id) {
  const path = id ? findPath(id) : null;
  editingPath = id || null;
  $("path-dialog-h").textContent = path ? "Sửa thông tin lộ trình" : "Lộ trình mới";
  $("path-title").value = path ? path.title : "";
  $("path-description").value = path ? path.description : "";
  $("path-band-from").value = path ? path.band_from : "A2";
  $("path-band-to").value = path ? path.band_to : "B2";
  $("path-dialog").showModal();
}
function openUnit(pathId, unitId) {
  const unit = unitId ? findUnit(pathId, unitId) : null;
  unitTarget = { path: pathId, unit: unitId || null };
  $("unit-dialog-h").textContent = unit ? "Sửa chặng" : "Chặng mới";
  $("unit-title").value = unit ? unit.title : "";
  $("unit-function").value = unit ? unit.learning_function || "" : "";
  $("unit-band").value = unit ? unit.band : "A2";
  $("unit-topic").value = unit && unit.topic ? unit.topic : "";
  $("unit-criterion").value = "";
  $("unit-dialog").showModal();
}
function openLesson(unitId, band) {
  lessonUnit = unitId;
  $("lesson-form").reset();
  $("lesson-band").value = band || "A2";
  $("lesson-dialog").showModal();
}
function newStep(kind, ordinal, instruction, payload) {
  return { step_id: makeId("step"), ordinal, stage: window.ui.STEP_STAGES[kind], kind,
    instruction, payload, rules_version: "lesson-rules-v1" };
}
function buildLesson(form) {
  const modelText = $("lesson-text").value.trim();
  const words = $("lesson-keywords").value.split(",").map((word) => word.trim()).filter(Boolean);
  const prompt = $("lesson-prompt").value.trim() || "Nói về chủ đề: " + $("lesson-title").value.trim();
  const band = $("lesson-band").value;
  const steps = [];
  if (modelText) steps.push(newStep("read_aloud", steps.length + 1,
    "Nghe giọng mẫu (nếu có) rồi đọc to cả đoạn.", { kind: "read_aloud", text: modelText, hint_words: words, max_seconds: 120 }));
  if (words.length) steps.push(newStep("keywords", steps.length + 1,
    "Nói một hay hai câu của riêng bạn có các từ dưới đây.", { kind: "keywords", keywords: words, min_words: 1, max_seconds: 60 }));
  steps.push(newStep("free", steps.length + 1, "Nói tự do về đề dưới đây.",
    { kind: "free", rounds: [{ duration_seconds: 45, prompt }, { duration_seconds: 30, prompt }], max_seconds: 45 }));
  return { lesson_id: makeId("lesson"), title: $("lesson-title").value.trim(),
    summary: $("lesson-summary").value.trim(), band, steps, revision: 1, content_version: "v1" };
}

document.querySelectorAll("[data-close]").forEach((button) =>
  button.addEventListener("click", () => $(button.dataset.close).close()));
$("path-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const old = editingPath ? findPath(editingPath) : null;
  const path = old ? { ...old, units: old.units.map(({ lessons, function: unitFunction, criterion, ...unit }) => unit) } : { path_id: makeId("path"), description: "", band_from: "A2", band_to: "B2",
    content_version: "v1", revision: 0, units: [] };
  path.title = $("path-title").value.trim();
  path.description = $("path-description").value.trim();
  path.band_from = $("path-band-from").value;
  path.band_to = $("path-band-to").value;
  delete path.status;
  try {
    const saved = await api("POST", "/api/v1/teacher/learn/paths", { expected_revision: old ? old.revision : 0, path });
    remember(PATHS_KEY, saved.path_id);
    remember(DRAFT_KEY, saved.path_id);
    $("path-dialog").close();
    window.toast(old ? "Đã lưu lộ trình." : "Đã tạo lộ trình. Thêm chặng đầu tiên.", "ok");
    await load();
  } catch (error) { window.toast(errorMessage(error), "error"); }
});
$("unit-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const path = findPath(unitTarget.path);
  const old = unitTarget.unit ? findUnit(unitTarget.path, unitTarget.unit) : null;
  if (!path) return;
  const unit = old ? { ...old } : { unit_id: makeId("unit"), path_id: path.path_id,
    ordinal: path.units.length + 1, lesson_ids: [], revision: 0 };
  unit.title = $("unit-title").value.trim();
  unit.learning_function = $("unit-function").value.trim() || null;
  unit.band = $("unit-band").value;
  unit.topic = $("unit-topic").value || null;
  unit.ordinal = old ? old.ordinal : path.units.length + 1;
  delete unit.lessons; delete unit.function; delete unit.criterion;
  try {
    await api("POST", "/api/v1/teacher/learn/paths/" + encodeURIComponent(path.path_id) + "/units",
      { expected_revision: old ? old.revision : 0, unit });
    $("unit-dialog").close();
    window.toast("Đã lưu chặng.", "ok");
    await load();
  } catch (error) { window.toast(errorMessage(error), "error"); }
});
$("lesson-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const submit = event.target.querySelector('button[type="submit"]');
  const path = paths.find((item) => item.units.some((unit) => unit.unit_id === lessonUnit));
  const unit = path && findUnit(path.path_id, lessonUnit);
  if (!unit) return window.toast("Không tìm thấy chặng. Hãy tải lại trang.", "error");
  submit.disabled = true;
  try {
    const lesson = buildLesson(event.target);
    const saved = await api("POST", "/api/v1/teacher/learn/lessons",
      { unit_id: unit.unit_id, expected_revision: 0, lesson });
    const lessonMap = JSON.parse(localStorage.getItem(LESSONS_KEY) || "{}");
    lessonMap[saved.lesson_id] = { path_id: path.path_id, unit_id: unit.unit_id };
    localStorage.setItem(LESSONS_KEY, JSON.stringify(lessonMap));
    $("lesson-dialog").close();
    window.toast("Đã tạo bản nháp. Mở bài để soạn và xuất bản.", "ok");
    await load();
    location.href = "/teach/lessons/" + encodeURIComponent(saved.lesson_id) + "?unit_id=" + encodeURIComponent(unit.unit_id);
  } catch (error) {
    window.toast(errorMessage(error), "error");
    submit.disabled = false;
  }
});
root.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-action]");
  if (!button) return;
  const action = button.dataset.action;
  const id = button.dataset.id;
  if (action === "new-path") return openPath(null);
  if (action === "edit-path") return openPath(id);
  if (action === "add-unit") return openUnit(id, null);
  if (action === "edit-unit") return openUnit(button.dataset.path, id);
  if (action === "add-lesson") return openLesson(id, button.dataset.band);
  if (action === "load-path") {
    const pathId = window.prompt("Nhập ID lộ trình");
    if (!pathId) return;
    try { await fetchPath(pathId).then((path) => { remember(PATHS_KEY, path.path_id); }); await load(); }
    catch (error) { window.toast(errorMessage(error), "error"); }
    return;
  }
  if (action === "unit-up" || action === "unit-down") {
    const owner = findPath(button.dataset.path);
    if (!owner) return;
    const index = owner.units.findIndex((unit) => unit.unit_id === id);
    const target = index + (action === "unit-up" ? -1 : 1);
    if (index < 0 || target < 0 || target >= owner.units.length) return;
    const ordered = owner.units.map((unit) => unit.unit_id);
    [ordered[index], ordered[target]] = [ordered[target], ordered[index]];
    try {
      await api("POST", "/api/v1/teacher/learn/paths/" + encodeURIComponent(owner.path_id) + "/reorder",
        { expected_revision: owner.revision, unit_ids: ordered });
      await load();
    } catch (error) { window.toast(errorMessage(error), "error"); }
    return;
  }
  if (action === "delete-unit") {
    if (!window.confirm("Xoá chặng trống này?")) return;
    try {
      await api("DELETE", "/api/v1/teacher/learn/paths/" + encodeURIComponent(button.dataset.path) +
        "/units/" + encodeURIComponent(id) + "?expected_revision=" + encodeURIComponent(button.dataset.revision));
      await load();
    } catch (error) { window.toast(errorMessage(error), "error"); }
    return;
  }
  if (action === "delete-lesson") {
    if (!window.confirm("Lưu trữ bản nháp bài học này?")) return;
    try {
      await api("DELETE", "/api/v1/teacher/learn/lessons/" + encodeURIComponent(id) +
        "?expected_revision=" + encodeURIComponent(button.dataset.revision));
      await load();
    } catch (error) { window.toast(errorMessage(error), "error"); }
    return;
  }
  if (action === "delete-path") {
    if (!window.confirm("Xoá lộ trình nháp này và các nội dung nháp bên trong?")) return;
    try {
      await api("DELETE", "/api/v1/teacher/learn/paths/" + encodeURIComponent(id) +
        "?expected_revision=" + encodeURIComponent(button.dataset.revision));
      forget(PATHS_KEY, id); forget(DRAFT_KEY, id);
      await load();
    } catch (error) { window.toast(errorMessage(error), "error"); }
    return;
  }
  const path = findPath(id);
  if (!path) return;
  button.disabled = true;
  try {
    if (action === "publish-path") {
      const question = "Xuất bản lộ trình? Mọi chặng phải có bài học đã xuất bản.";
      if (!window.confirm(question)) return;
      await api("POST", "/api/v1/teacher/learn/paths/" + encodeURIComponent(id) + "/publish",
        { expected_revision: path.revision });
      remember(PUBLISHED_KEY, id);
      forget(DRAFT_KEY, id);
      window.toast("Đã xuất bản lộ trình.", "ok");
    }
    await load();
  } catch (error) { window.toast(errorMessage(error), "error"); }
  finally { button.disabled = false; }
});
$("new-path").addEventListener("click", () => openPath(null));
$("import-path").addEventListener("click", () => $("import-file").click());
$("import-file").addEventListener("change", async () => {
  const file = $("import-file").files[0];
  $("import-file").value = "";
  if (!file) return;
  try {
    const imported = await api("POST", "/api/v1/teacher/learn/paths/import", { path_json: await file.text() });
    const path = imported.path || imported;
    if (path.path_id) { remember(PATHS_KEY, path.path_id); remember(DRAFT_KEY, path.path_id); }
    await load();
    window.toast("Đã nhập lộ trình ở trạng thái nháp.", "ok");
  } catch (error) { window.toast(errorMessage(error), "error"); }
});
load().catch((error) => {
  window.clearBusy(root);
  root.innerHTML = '<section class="card"><p class="error">' + escapeHtml(errorMessage(error)) + "</p></section>";
});

