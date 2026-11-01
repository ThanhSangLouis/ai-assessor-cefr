// The lesson builder (D025, M17).
//
// The working draft is saved as the teacher types (a draft reaches no student),
// and each save returns the linter's warnings, so the list on the left is
// always about the text on screen. Students keep the last published version
// until "Xuất bản". Media (model audio, a picture) is uploaded per step; the
// draft is saved first so the server checks the audio against the text the
// teacher is looking at, not an older one.
const escapeHtml = window.escapeHtml;
const root = document.getElementById("builder");
const icon = (name, cls) => window.ui.icon(name, cls);
const KIND_ICON = window.ui.STEP_ICONS;
const LESSON_ID = root.dataset.lessonId;
const $ = (id) => document.getElementById(id);

const KIND_NAMES = {
  read_aloud: "Đọc to có từ gợi ý",
  repeat: "Nghe và nhắc lại",
  look_up: "Đọc rồi nói lại",
  gap: "Đọc đoạn có chỗ trống",
  keywords: "Ghép câu từ từ khóa",
  starter: "Trả lời có khung câu",
  picture: "Mô tả tranh",
  outline: "Nói theo dàn ý",
  free: "Nói tự do",
};
const STAGE_OF = window.ui.STEP_STAGES;
const STAGE_NAMES = { model: "Mẫu", controlled: "Có kiểm soát", guided: "Có hướng dẫn", free: "Tự do" };
const DEFAULT_INSTRUCTION = {
  read_aloud: "Nghe giọng mẫu (nếu có) rồi đọc to cả đoạn. Từ gợi ý được tô đậm; đọc rõ, đúng nhịp.",
  repeat: "Nghe câu mẫu một lần rồi nhắc lại. Lần thứ hai thử không nhìn chữ.",
  look_up: "Đọc câu trong lúc nó còn hiện. Khi chữ ẩn đi, nhìn lên và nói lại câu.",
  gap: "Đọc to đoạn văn, tự điền từ vào chỗ trống. Có từ trong ngân hàng không dùng đến.",
  keywords: "Nói một hay hai câu của riêng bạn có các từ dưới đây. Mọi dạng của từ đều được tính.",
  starter: "Trả lời câu hỏi, bắt đầu bằng khung câu cho sẵn.",
  picture: "Tả bức tranh bằng vài câu, dùng các từ trong ngân hàng từ.",
  outline: "Chuẩn bị trong thời gian cho phép, rồi nói theo dàn ý. Dùng từ nối để chuyển ý.",
  free: "Nói tự do về đề dưới đây, ba lượt. Mỗi lượt ngắn hơn lượt trước.",
};

// What each kind of step asks the teacher for, in order.
const FIELDS = {
  read_aloud: ["text", "hint_words", "max_seconds"],
  repeat: ["text", "max_seconds"],
  look_up: ["text", "show_seconds", "max_seconds"],
  gap: ["text", "answers", "hint_words", "max_seconds"],
  keywords: ["keywords", "min_words", "max_seconds"],
  starter: ["text", "starter", "keywords", "min_words", "max_seconds"],
  picture: ["text", "hint_words", "use_at_least", "min_words", "image_alt", "max_seconds"],
  outline: ["text", "outline", "markers", "keywords", "prep_seconds", "min_seconds", "max_seconds"],
  free: ["text", "rounds"],
};
const TEXT_LABEL = {
  read_aloud: "Đoạn văn để đọc to (tiếng Anh)",
  repeat: "Câu để nhắc lại (tiếng Anh)",
  look_up: "Câu để đọc rồi nói lại (tiếng Anh)",
  gap: "Đoạn văn có chỗ trống: viết ___ ở mỗi chỗ trống",
  starter: "Câu hỏi (tiếng Anh)",
  picture: "Câu hỏi về bức tranh (không bắt buộc)",
  outline: "Đề bài",
  free: "Đề nói tự do",
};
const LABEL = {
  answers: "Đáp án từng chỗ trống, theo thứ tự, cách nhau bằng dấu phẩy. Sinh viên không thấy.",
  starter: "Khung câu mở đầu, ví dụ: In my opinion,",
  outline: "Dàn ý, mỗi dòng một ý",
  markers: "Từ nối theo thứ tự: mỗi dòng một nhóm, các từ cùng nhóm cách nhau bằng /",
  use_at_least: "Dùng ít nhất bao nhiêu từ của ngân hàng (0 = ba từ)",
  min_words: "Số từ tối thiểu (0 = mặc định)",
  show_seconds: "Hiện câu trong bao nhiêu giây",
  prep_seconds: "Thời gian chuẩn bị (giây)",
  min_seconds: "Nói tối thiểu (giây)",
  max_seconds: "Nói tối đa (giây)",
  rounds: "Thời gian từng lượt (giây), cách nhau bằng dấu phẩy. Ví dụ 45, 35, 25 cho kỹ thuật 4/3/2",
  image_alt: "Mô tả ảnh cho người dùng trình đọc màn hình",
};
const LIST_LABEL = {
  read_aloud: "Từ gợi ý được tô đậm, cách nhau bằng dấu phẩy",
  gap: "Ngân hàng từ: đáp án và từ gây nhiễu, cách nhau bằng dấu phẩy",
  picture: "Ngân hàng từ, cách nhau bằng dấu phẩy",
  keywords: "Từ khóa, cách nhau bằng dấu phẩy",
  starter: "Từ nên dùng (không bắt buộc), cách nhau bằng dấu phẩy",
  outline: "Ý cần nhắc tới (không bắt buộc), cách nhau bằng dấu phẩy",
};
const COMMA = new Set(["hint_words", "answers", "keywords"]);
const NUMBERS = new Set(["use_at_least", "min_words", "show_seconds", "prep_seconds", "min_seconds", "max_seconds"]);
const ENGLISH = new Set(["text", "hint_words", "answers", "keywords", "starter", "markers"]);

let lesson = null;
let meta = null;
let unit = null;
let path = null;
let lint = [];
let selected = 0;
let dirty = false;
let saving = null;
let again = false;
let timer = null;

const step = () => (lesson ? lesson.steps[selected] : null);

function newId() {
  const bytes = new Uint8Array(5);
  crypto.getRandomValues(bytes);
  return "s" + Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

function errorText(d) {
  if (typeof d.detail === "string") return d.detail.charAt(0).toUpperCase() + d.detail.slice(1);
  if (Array.isArray(d.detail) && d.detail.length) {
    return String(d.detail[0].msg || "").replace(/^Value error, /, "") || "Dữ liệu không hợp lệ.";
  }
  return "Không lưu được.";
}

// ---------------------------------------------------------------- saving
function setState(text, kind = "") {
  const el = $("save-state");
  el.textContent = text;
  el.className = `save-state ${kind}`;
}

function markDirty() {
  dirty = true;
  setState("Có thay đổi chưa lưu", "pending");
  clearTimeout(timer);
  timer = setTimeout(() => save().catch(() => {}), 1200);
}

// One save at a time; a change made during a save triggers one more after it.
async function save() {
  clearTimeout(timer);
  if (saving) {
    again = true;
    return saving;
  }
  if (!dirty) return null;
  dirty = false;
  setState("Đang lưu…", "pending");
  saving = (async () => {
    const r = await fetch(`/api/v1/teach/lessons/${encodeURIComponent(LESSON_ID)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(lesson),
    });
    if (window.redirectToLoginIfExpired(r)) throw new Error("expired");
    const d = await r.json().catch(() => ({}));
    if (!r.ok) {
      dirty = true;
      setState("Chưa lưu được", "error");
      window.toast(errorText(d), "error");
      throw new Error("save failed");
    }
    lint = d.lint || [];
    if (meta.published_version) meta.draft_changed = true;
    setState(`Đã lưu nháp lúc ${new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" })}`, "ok");
    renderHead();
    renderLint();
    renderRail();
  })();
  try {
    await saving;
  } finally {
    saving = null;
    if (again) {
      again = false;
      if (dirty) save().catch(() => {});
    }
  }
  return null;
}

// Before anything that reads the draft on the server: media, preview, publish.
async function flush() {
  if (saving) await saving.catch(() => {});
  if (dirty) await save();
}

// ---------------------------------------------------------------- head + rail
function renderHead() {
  const state = meta.published_version
    ? `<span class="badge state-on">Đã xuất bản v${Number(meta.published_version)}</span>` +
      (meta.draft_changed ? ' <span class="badge state-warn">Có sửa đổi chưa xuất bản</span>' : "")
    : '<span class="badge state-off">Chưa xuất bản: sinh viên chưa thấy bài này</span>';
  $("builder-head").innerHTML =
    `<p class="eyebrow">${escapeHtml(path.title)} · ${escapeHtml(unit.title)}</p>` +
    `<h1>${escapeHtml(lesson.title || "Bài học chưa đặt tên")}</h1>` +
    `<div class="unit-tags">${state}</div>`;
  document.title = lesson.title + " · Soạn bài";
}

function issuesOf(stepId) {
  return lint.filter((i) => i.step_id === stepId).length;
}

function renderRail() {
  $("step-list").innerHTML = lesson.steps
    .map((s, i) => {
      const n = issuesOf(s.step_id);
      return (
        `<li class="${i === selected ? "now" : ""}${s.kind === "free" ? " free" : ""}"${i === selected ? ' aria-current="step"' : ""}>` +
        `<button type="button" class="rail-step" data-index="${i}">` +
        `<span class="rail-mark" aria-hidden="true">${icon(KIND_ICON[s.kind], "icon rail-icon")}</span>` +
        `<span class="rail-text"><span class="rail-stage">${i + 1} · ${STAGE_NAMES[STAGE_OF[s.kind]]}</span>` +
        `<span class="rail-title">${escapeHtml(s.title || KIND_NAMES[s.kind])}</span></span>` +
        (n ? `<span class="lint-dot" title="${n} cảnh báo">${n}</span>` : "") +
        "</button></li>"
      );
    })
    .join("");
}

function renderLint() {
  const items = lint.map((i) => {
    const at = i.step_id ? lesson.steps.findIndex((s) => s.step_id === i.step_id) : -1;
    const where = at >= 0 ? `Bước ${at + 1}` : "Cả bài";
    return (
      `<li class="lint-${escapeHtml(i.level)}">` +
      `<button type="button" class="lint-item" data-step="${escapeHtml(i.step_id || "")}" data-field="${escapeHtml(i.field || "")}">` +
      `<span class="lint-where">${where}</span> ${escapeHtml(i.message)}</button></li>`
    );
  });
  $("lint-list").innerHTML = items.length
    ? items.join("")
    : '<li class="lint-clear">Không có cảnh báo nào.</li>';
}

// ---------------------------------------------------------------- editor
function fieldValue(s, f) {
  const v = s[f];
  if (COMMA.has(f)) return (v || []).join(", ");
  if (f === "outline") return (v || []).join("\n");
  if (f === "markers") return (v || []).map((g) => g.join(" / ")).join("\n");
  if (f === "rounds") return (v || []).join(", ");
  return v == null ? "" : String(v);
}

function parseValue(f, raw) {
  if (COMMA.has(f)) return raw.split(",").map((w) => w.trim()).filter(Boolean);
  if (f === "outline") return raw.split("\n").map((w) => w.trim()).filter(Boolean);
  if (f === "markers") {
    return raw
      .split("\n")
      .map((line) => line.split("/").map((w) => w.trim()).filter(Boolean))
      .filter((g) => g.length);
  }
  if (f === "rounds") return raw.split(",").map((w) => parseInt(w, 10)).filter((n) => Number.isFinite(n));
  if (NUMBERS.has(f)) return Math.max(0, parseInt(raw, 10) || 0);
  return raw;
}

function labelOf(s, f) {
  if (f === "text") return TEXT_LABEL[s.kind];
  if (COMMA.has(f) && f !== "answers") return LIST_LABEL[s.kind] || "Danh sách từ";
  return LABEL[f];
}

function control(s, f) {
  const id = `e-${f}`;
  const lang = ENGLISH.has(f) && !(f === "text" && (s.kind === "outline" || s.kind === "free")) ? ' lang="en"' : "";
  const value = escapeHtml(fieldValue(s, f));
  let input;
  if (f === "text" || f === "outline" || f === "markers") {
    const rows = f === "text" && ["read_aloud", "gap"].includes(s.kind) ? 6 : 3;
    input = `<textarea id="${id}" data-field="${f}" rows="${rows}"${lang}>${value}</textarea>`;
  } else if (NUMBERS.has(f)) {
    input = `<input id="${id}" data-field="${f}" type="number" min="0" max="300" inputmode="numeric" value="${value}">`;
  } else {
    input = `<input id="${id}" data-field="${f}" autocomplete="off"${lang} value="${value}">`;
  }
  return `<div class="editor-field f-${f}"><label for="${id}">${escapeHtml(labelOf(s, f))}</label>${input}</div>`;
}

function renderEditor() {
  const s = step();
  if (!s) {
    $("editor-top").innerHTML = "<h2 id=\"editor-h\">Chưa có bước nào</h2>";
    $("editor-fields").innerHTML = '<p class="muted">Thêm bước đầu tiên ở cột bên trái.</p>';
    $("audio-panel").hidden = true;
    $("image-panel").hidden = true;
    return;
  }
  const last = lesson.steps.length - 1;
  $("editor-top").innerHTML =
    '<div class="editor-title">' +
    `<p class="eyebrow">Bước ${selected + 1}/${lesson.steps.length} · ${STAGE_NAMES[STAGE_OF[s.kind]]}</p>` +
    `<h2 id="editor-h"><span class="editor-kind">${icon(KIND_ICON[s.kind])}</span>${escapeHtml(KIND_NAMES[s.kind])}</h2></div>` +
    '<div class="t-actions">' +
    `<button type="button" class="small secondary icon-only" data-move="-1"${selected === 0 ? " disabled" : ""} aria-label="Đưa bước lên trên">${icon("arrow-up")}</button>` +
    `<button type="button" class="small secondary icon-only" data-move="1"${selected === last ? " disabled" : ""} aria-label="Đưa bước xuống dưới">${icon("arrow-down")}</button>` +
    `<button type="button" class="small secondary" data-remove="1">${icon("trash")}<span>Xoá bước</span></button></div>`;

  const numbers = FIELDS[s.kind].filter((f) => NUMBERS.has(f));
  const others = FIELDS[s.kind].filter((f) => !NUMBERS.has(f));
  $("editor-fields").innerHTML =
    others.map((f) => control(s, f)).join("") +
    (numbers.length ? `<div class="field-row numbers">${numbers.map((f) => control(s, f)).join("")}</div>` : "") +
    // The fields every kind shares, folded away: most steps keep the defaults.
    '<details class="editor-more"><summary>Tên bước, hướng dẫn, mẹo và mức chấm</summary>' +
    `<div class="editor-field"><label for="e-title">Tên bước (để trống thì dùng «${escapeHtml(KIND_NAMES[s.kind])}»)</label>` +
    `<input id="e-title" data-field="title" maxlength="120" autocomplete="off" value="${escapeHtml(s.title)}"></div>` +
    '<div class="editor-field"><label for="e-instruction">Hướng dẫn cho sinh viên</label>' +
    `<textarea id="e-instruction" data-field="instruction" rows="2" maxlength="600" placeholder="${escapeHtml(DEFAULT_INSTRUCTION[s.kind])}">${escapeHtml(s.instruction)}</textarea></div>` +
    '<div class="editor-field"><label for="e-tip">Mẹo (không bắt buộc)</label>' +
    `<input id="e-tip" data-field="tip" maxlength="400" autocomplete="off" value="${escapeHtml(s.tip)}"></div>` +
    '<div class="editor-field"><label for="e-strictness">Mức chấm</label>' +
    `<select id="e-strictness" data-field="strictness">` +
    ["easy", "normal", "strict"]
      .map(
        (v) =>
          `<option value="${v}"${s.strictness === v ? " selected" : ""}>` +
          `${{ easy: "Dễ: hợp với lớp mới bắt đầu", normal: "Vừa: mặc định", strict: "Chặt: cho lớp đã quen" }[v]}</option>`
      )
      .join("") +
    "</select></div></details>";

  renderAudio();
  renderImage();
}

function renderAudio() {
  const s = step();
  const show = s && (s.kind === "read_aloud" || s.kind === "repeat");
  $("audio-panel").hidden = !show;
  if (!show) return;
  $("audio-check").hidden = true;
  $("audio-current").innerHTML = s.model_audio
    ? '<div class="media-current"><span class="eyebrow">Giọng mẫu hiện tại</span>' +
      `<audio controls preload="none" src="${escapeHtml(s.model_audio_url || "")}"></audio>` +
      `<button type="button" class="small secondary" id="audio-remove">${icon("trash")}<span>Bỏ giọng mẫu</span></button></div>`
    : '<p class="muted">Bước này chưa có giọng mẫu.</p>';
  const remove = $("audio-remove");
  if (remove) {
    remove.addEventListener("click", () => {
      s.model_audio = null;
      s.model_audio_url = null;
      markDirty();
      renderAudio();
    });
  }
  recorder.reset();
  recorder.repaint();
}

function renderImage() {
  const s = step();
  const show = s && s.kind === "picture";
  $("image-panel").hidden = !show;
  if (!show) return;
  $("image-current").innerHTML = s.image
    ? `<img class="step-image" src="${escapeHtml(s.image_url || "")}" alt="${escapeHtml(s.image_alt || "Ảnh của bước")}">` +
      `<button type="button" class="small secondary" id="image-remove">${icon("trash")}<span>Bỏ ảnh</span></button>`
    : '<p class="muted">Bước này chưa có ảnh.</p>';
  const remove = $("image-remove");
  if (remove) {
    remove.addEventListener("click", () => {
      s.image = null;
      s.image_url = null;
      markDirty();
      renderImage();
    });
  }
}

function select(i) {
  selected = Math.max(0, Math.min(i, lesson.steps.length - 1));
  renderRail();
  renderEditor();
}

// ---------------------------------------------------------------- edits
$("editor-fields").addEventListener("input", (e) => {
  const f = e.target.dataset.field;
  const s = step();
  if (!f || !s) return;
  s[f] = parseValue(f, e.target.value);
  if (f === "rounds" && s.rounds.length) s.max_seconds = Math.max(...s.rounds);
  if (f === "title") renderRail();
  markDirty();
});

$("editor-top").addEventListener("click", (e) => {
  const b = e.target.closest("button");
  if (!b || !lesson.steps.length) return;
  if (b.dataset.move) {
    const to = selected + Number(b.dataset.move);
    if (to < 0 || to >= lesson.steps.length) return;
    const [moved] = lesson.steps.splice(selected, 1);
    lesson.steps.splice(to, 0, moved);
    markDirty();
    select(to);
  } else if (b.dataset.remove) {
    const s = step();
    const name = s.title || KIND_NAMES[s.kind];
    if (!confirm("Xoá bước " + (selected + 1) + " (" + name + ")? Lượt luyện đã có của bước này vẫn được giữ.")) return;
    lesson.steps.splice(selected, 1);
    markDirty();
    select(Math.min(selected, lesson.steps.length - 1));
  }
});

$("step-list").addEventListener("click", (e) => {
  const b = e.target.closest("[data-index]");
  if (b) select(Number(b.dataset.index));
});

$("lint-list").addEventListener("click", (e) => {
  const b = e.target.closest(".lint-item");
  if (!b) return;
  const at = lesson.steps.findIndex((s) => s.step_id === b.dataset.step);
  if (at < 0) {
    $("f-title").focus();
    return;
  }
  select(at);
  const field = b.dataset.field && document.querySelector(`#editor-fields [data-field="${CSS.escape(b.dataset.field)}"]`);
  (field || $("editor-h")).focus();
  if (field && field.closest("details")) field.closest("details").open = true;
});

$("add-step").addEventListener("click", () => {
  // The same ceiling as the server's lesson model (Lesson.steps, at most 12).
  if (lesson.steps.length >= 12) {
    window.toast("Một bài học có tối đa 12 bước. Tách thành hai bài nếu cần thêm.", "warn");
    return;
  }
  const kind = $("add-kind").value;
  const s = {
    step_id: newId(),
    kind,
    title: "",
    instruction: DEFAULT_INSTRUCTION[kind],
    text: "",
    hint_words: [],
    answers: [],
    keywords: [],
    starter: "",
    outline: [],
    markers: [],
    use_at_least: 0,
    min_words: 0,
    show_seconds: kind === "look_up" ? 6 : 0,
    prep_seconds: kind === "outline" ? 30 : 0,
    min_seconds: 0,
    max_seconds: kind === "free" ? 60 : 30,
    rounds: kind === "free" ? [60, 45, 35] : [],
    strictness: "normal",
    model_audio: null,
    image: null,
    image_alt: "",
    missions: [],
    tip: "",
  };
  // Free speech stays last: a new guided step goes in before it.
  const lastFree = lesson.steps.length && lesson.steps[lesson.steps.length - 1].kind === "free";
  const at = kind !== "free" && lastFree ? lesson.steps.length - 1 : lesson.steps.length;
  lesson.steps.splice(at, 0, s);
  markDirty();
  select(at);
  const first = document.querySelector("#editor-fields [data-field]");
  if (first) first.focus();
});

document.querySelectorAll("[data-lesson-field]").forEach((el) => {
  el.addEventListener(el.tagName === "SELECT" ? "change" : "input", () => {
    const f = el.dataset.lessonField;
    if (f === "keywords") lesson.keywords = el.value.split(",").map((w) => w.trim()).filter(Boolean);
    else if (f === "pass_ratio") lesson.pass_ratio = Number(el.value);
    else if (f === "criterion") lesson.criterion = el.value || null;
    else lesson[f] = el.value;
    if (f === "title") renderHead();
    markDirty();
  });
});

// ---------------------------------------------------------------- media
const recorder = window.setUpRecorder({
  minSeconds: () => 0,
  maxSeconds: () => Math.max(20, step() ? step().max_seconds : 60),
  onSubmit: async (audio, name) => {
    const s = step();
    try {
      await flush();
    } catch (err) {
      return;
    }
    const body = new FormData();
    body.append("audio", audio, name);
    const r = await fetch(
      `/api/v1/teach/lessons/${encodeURIComponent(LESSON_ID)}/steps/${encodeURIComponent(s.step_id)}/model-audio`,
      { method: "POST", body }
    );
    if (window.redirectToLoginIfExpired(r)) return;
    const d = await r.json().catch(() => ({}));
    if (!r.ok) {
      window.toast(errorText(d), "error");
      return;
    }
    s.model_audio = d.media_key;
    s.model_audio_url = d.url;
    if (meta.published_version) meta.draft_changed = true;
    renderAudio();
    renderHead();
    const check = $("audio-check");
    if (d.check) {
      check.className = d.check.warning ? "notice notice-warn" : "notice notice-ok";
      check.textContent =
        d.check.warning || `Máy chép giọng mẫu khớp ${d.check.heard}/${d.check.total} từ của văn bản.`;
      check.hidden = false;
    }
    window.toast("Đã lưu giọng mẫu.", "ok");
  },
});

$("image-upload").addEventListener("click", async () => {
  const file = $("image-file").files[0];
  const s = step();
  if (!file) {
    window.toast("Chọn một ảnh trước.", "warn");
    return;
  }
  const button = $("image-upload");
  button.disabled = true;
  try {
    await flush();
    const body = new FormData();
    body.append("image", file, file.name);
    const r = await fetch(
      `/api/v1/teach/lessons/${encodeURIComponent(LESSON_ID)}/steps/${encodeURIComponent(s.step_id)}/image`,
      { method: "POST", body }
    );
    if (window.redirectToLoginIfExpired(r)) return;
    const d = await r.json().catch(() => ({}));
    if (!r.ok) {
      window.toast(errorText(d), "error");
      return;
    }
    s.image = d.media_key;
    s.image_url = d.url;
    $("image-file").value = "";
    renderImage();
    window.toast("Đã tải ảnh lên.", "ok");
  } catch (err) {
    /* a failed save is already on screen */
  } finally {
    button.disabled = false;
  }
});

// ---------------------------------------------------------------- bar
$("save-draft").addEventListener("click", () => {
  dirty = true;
  save().catch(() => {});
});

$("preview").addEventListener("click", async () => {
  try {
    await flush();
  } catch (err) {
    return;
  }
  location.href = `/practice/lessons/${encodeURIComponent(LESSON_ID)}?preview=1`;
});

$("publish").addEventListener("click", async () => {
  try {
    await flush();
  } catch (err) {
    return;
  }
  const warnings = lint.filter((i) => i.level === "warn").length;
  const question = warnings
    ? `Còn ${warnings} cảnh báo soát lỗi. Vẫn xuất bản? Sinh viên sẽ thấy bản này ngay.`
    : "Xuất bản bài học? Sinh viên sẽ thấy bản này ngay; các lượt luyện cũ vẫn giữ nguyên.";
  if (!confirm(question)) return;
  const r = await fetch(`/api/v1/teach/lessons/${encodeURIComponent(LESSON_ID)}/publish`, { method: "POST" });
  if (window.redirectToLoginIfExpired(r)) return;
  const d = await r.json().catch(() => ({}));
  if (!r.ok) {
    window.toast(errorText(d), "error");
    return;
  }
  meta.published_version = d.version;
  meta.draft_changed = false;
  renderHead();
  window.toast(`Đã xuất bản phiên bản ${d.version}.`, "ok");
});

// Ctrl/Cmd+S saves, as in any editor.
document.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
    e.preventDefault();
    dirty = true;
    save().catch(() => {});
  }
});

window.addEventListener("beforeunload", (e) => {
  if (dirty || saving) {
    e.preventDefault();
    e.returnValue = "";
  }
});

// ---------------------------------------------------------------- load
async function load() {
  const r = await fetch(`/api/v1/teach/lessons/${encodeURIComponent(LESSON_ID)}`);
  if (window.redirectToLoginIfExpired(r)) return;
  window.clearBusy(root);
  if (r.status === 403) {
    $("builder-head").innerHTML =
      '<p class="error">Tài khoản này không có quyền soạn bài. <a href="/">Về trang của bạn</a>.</p>';
    $("builder-bar").hidden = true;
    return;
  }
  if (!r.ok) {
    $("builder-head").innerHTML =
      '<div class="empty-state"><div class="empty-mark" aria-hidden="true">◇</div>' +
      '<h2>Không mở được bài học này</h2><p><a href="/teach">Quay lại danh sách lộ trình</a>.</p></div>';
    $("builder-bar").hidden = true;
    return;
  }
  const d = await r.json();
  lesson = d.lesson;
  meta = d.meta;
  unit = d.unit;
  path = d.path;
  lint = d.lint || [];
  $("f-title").value = lesson.title;
  $("f-summary").value = lesson.summary || "";
  $("f-band").value = lesson.band;
  $("f-criterion").value = lesson.criterion || "";
  $("f-pass").value = String(lesson.pass_ratio);
  $("f-model-text").value = lesson.model_text || "";
  $("f-keywords").value = (lesson.keywords || []).join(", ");
  $("builder-layout").hidden = false;
  setState(meta.updated_at ? `Lưu lần cuối: ${window.ui.localTime(meta.updated_at)}` : "");
  renderHead();
  renderLint();
  select(0);
}

fetch("/api/v1/health")
  .then((r) => (r.ok ? r.json() : null))
  .then((h) => {
    recorder.enable(!!(h && h.recording_enabled));
  })
  .catch(() => recorder.enable(false));

load();
