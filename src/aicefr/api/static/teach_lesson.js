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
  starter: ["text", "starter", "min_words", "max_seconds"],
  picture: ["text", "image_alt", "min_words", "max_seconds"],
  outline: ["text", "outline", "markers", "prep_seconds", "min_seconds", "max_seconds"],
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
let domainRevision = 0;
let draftVersion = 1;

function validationIssues(value) {
  return (value && value.errors || []).map((item) => ({ ...item, level: "error", field: "" }))
    .concat((value && value.warnings || []).map((item) => ({ ...item, level: "warn", field: "" })));
}
function domainPayload(s) {
  const max = Math.max(1, Number(s.max_seconds) || 30);
  switch (s.kind) {
    case "read_aloud": return { kind:s.kind, text:s.text, hint_words:s.hint_words || [], max_seconds:max };
    case "repeat": return { kind:s.kind, text:s.text, max_seconds:max };
    case "look_up": return { kind:s.kind, text:s.text, show_seconds:Math.max(1,Number(s.show_seconds)||6), max_seconds:max };
    case "gap": return { kind:s.kind, text:s.text, answers:s.answers || [], hint_words:s.hint_words || [], max_seconds:max };
    case "keywords": return { kind:s.kind, keywords:s.keywords || [], min_words:Math.max(1,Number(s.min_words)||1), max_seconds:max };
    case "starter": return { kind:s.kind, text:s.text, starter:s.starter, min_words:Math.max(1,Number(s.min_words)||1), max_seconds:max };
    case "picture": {
      const pictures = (s.pictures || []).map((item, index) => index === 0 && s.image_alt
        ? { ...item, description: s.image_alt } : item);
      return { kind:s.kind, prompt:s.text, pictures, min_words:Math.max(1,Number(s.min_words)||1), max_seconds:max };
    }
    case "outline": return { kind:s.kind, text:s.text, points:s.outline || [], markers:s.markers || [], prep_seconds:Math.max(0,Number(s.prep_seconds)||0), min_seconds:Math.max(0,Number(s.min_seconds)||0), max_seconds:max };
    case "free": {
      const values=(s.rounds || []).filter((item)=>Number(item)>0);
      const durations=values.length>=2 ? values.slice(0,3) : [45,30];
      return { kind:s.kind, rounds:durations.map((seconds)=>({duration_seconds:seconds,prompt:s.text})), max_seconds:durations[0] };
    }
    default: throw new Error("Loại bước này không được M10 hỗ trợ.");
  }
}
function toDomainLesson(value) {
  return { lesson_id:value.lesson_id, title:value.title, summary:value.summary || "", band:value.band,
    steps:(value.steps || []).map((item,index)=>({ step_id:item.step_id, ordinal:index+1,
      stage:STAGE_OF[item.kind], kind:item.kind, instruction:item.instruction || DEFAULT_INSTRUCTION[item.kind],
      payload:domainPayload(item), rules_version:item.rules_version || "lesson-rules-v1" })),
    revision:domainRevision, content_version:value.content_version || "v1" };
}
function fromDomainStep(item) {
  const p=item.payload, s={step_id:item.step_id,kind:item.kind,title:"",instruction:item.instruction || "",
    text:"",hint_words:[],answers:[],keywords:[],starter:"",outline:[],markers:[],use_at_least:0,
    min_words:1,show_seconds:6,prep_seconds:0,min_seconds:0,max_seconds:p.max_seconds || 30,
    rounds:[],strictness:"normal",model_audio:null,image:null,image_alt:"",pictures:[],missions:[],tip:"",
    rules_version:item.rules_version};
  if (["read_aloud","repeat","look_up","gap","starter","outline"].includes(item.kind)) s.text=p.text || "";
  if (item.kind==="read_aloud" || item.kind==="gap") s.hint_words=p.hint_words || [];
  if (item.kind==="gap") s.answers=p.answers || [];
  if (item.kind==="keywords") s.keywords=p.keywords || [];
  if (item.kind==="starter") s.starter=p.starter || "";
  if (["starter","keywords","picture"].includes(item.kind)) s.min_words=p.min_words || 1;
  if (item.kind==="look_up") s.show_seconds=p.show_seconds || 6;
  if (item.kind==="picture") { s.text=p.prompt || ""; s.pictures=p.pictures || []; s.image_alt=s.pictures.map((x)=>x.description).join("; "); }
  if (item.kind==="outline") { s.outline=p.points || []; s.markers=p.markers || []; s.prep_seconds=p.prep_seconds || 0; s.min_seconds=p.min_seconds || 0; }
  if (item.kind==="free") { s.text=p.rounds && p.rounds.length ? p.rounds[0].prompt : ""; s.rounds=(p.rounds || []).map((x)=>x.duration_seconds); }
  return s;
}
function fromDomainLesson(value) {
  return { lesson_id:value.lesson_id,title:value.title,summary:value.summary || "",band:value.band,
    revision:value.revision,content_version:value.content_version || "v1",model_text:"",keywords:[],
    criterion:null,pass_ratio:0.7,steps:(value.steps || []).map(fromDomainStep) };
}
async function requestJson(url, options) {
  const response=await fetch(url,options || {});
  if (window.redirectToLoginIfExpired(response)) throw new Error("expired");
  const body=await response.json().catch(()=>({}));
  if (!response.ok) throw new Error(errorText(body));
  return body;
}
async function resolveContext() {
  const map=JSON.parse(localStorage.getItem("aicefr-teacher-lessons") || "{}");
  const queryUnit=new URLSearchParams(location.search).get("unit_id");
  const relation=map[LESSON_ID] || (queryUnit ? {unit_id:queryUnit} : null);
  const ids=JSON.parse(localStorage.getItem("aicefr-teacher-path-ids") || "[]");
  for (const pathId of ids) {
    const response=await fetch("/api/v1/teacher/learn/paths/"+encodeURIComponent(pathId));
    if (!response.ok) continue;
    const candidate=await response.json();
    const found=(candidate.units || []).find((item)=>(relation && item.unit_id===relation.unit_id) || (item.lesson_ids || []).includes(LESSON_ID));
    if (found) {
      unit=found; path=candidate; map[LESSON_ID]={path_id:path.path_id,unit_id:unit.unit_id};
      localStorage.setItem("aicefr-teacher-lessons",JSON.stringify(map)); return;
    }
  }
  if (relation) { unit={unit_id:relation.unit_id,title:"Chặng"}; path={title:"Lộ trình"}; }
}
function attachMedia(value, media) {
  const byStep=new Map();
  for (const item of media || []) { if (!byStep.has(item.step_id)) byStep.set(item.step_id,[]); byStep.get(item.step_id).push(item); }
  for (const item of value.steps) {
    const artifact=(byStep.get(item.step_id) || []).find((entry)=>entry.media_kind==="sample_audio");
    if (artifact) { item.model_audio=artifact.media_id; item.model_audio_url=artifact.url; }
  }
}

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
function setState(text, kind = "") { const el=$("save-state"); el.textContent=text; el.className="save-state "+kind; }
function draftIssue() {
  for (const item of lesson.steps || []) {
    const label = KIND_NAMES[item.kind] || "Bước học";
    const hasText = typeof item.text === "string" && item.text.trim().length > 0;
    let missing = false;
    switch (item.kind) {
      case "read_aloud":
      case "repeat":
      case "look_up":
        missing = !hasText;
        break;
      case "gap":
        missing = !hasText || !(item.answers || []).some((value) => String(value).trim());
        break;
      case "keywords":
        missing = !(item.keywords || []).some((value) => String(value).trim());
        break;
      case "starter":
        missing = !hasText || !String(item.starter || "").trim();
        break;
      case "picture":
        missing = !hasText || !(item.pictures || []).some((picture) => String(picture.description || "").trim());
        break;
      case "outline":
        missing = !hasText || !(item.outline || []).some((value) => String(value).trim());
        break;
      case "free":
        missing = !hasText;
        break;
    }
    if (missing) return `Hoàn thiện nội dung bắt buộc của bước “${label}” trước khi lưu.`;
  }
  return "";
}
async function loadLint() {
  const result=await requestJson("/api/v1/teacher/learn/lessons/"+encodeURIComponent(LESSON_ID)+"/lint",{
    method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({lesson:toDomainLesson(lesson),for_publish:false})});
  lint=validationIssues(result);
}
async function save() {
  clearTimeout(timer);
  if (saving) { again=true; return saving; }
  if (!dirty) return null;
  const issue = draftIssue();
  if (issue) { setState("Hoàn thiện nội dung bắt buộc trước khi lưu", "pending"); return null; }
  if (!unit || !unit.unit_id) { window.toast("Không xác định được chặng. Hãy mở bài từ trang Soạn bài.","error"); throw new Error("unit unavailable"); }
  dirty=false; setState("Đang lưu…","pending");
  saving=(async()=>{
    try {
      const saved=await requestJson("/api/v1/teacher/learn/lessons",{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({unit_id:unit.unit_id,expected_revision:domainRevision,lesson:toDomainLesson(lesson)})});
      domainRevision=saved.revision; lesson.revision=saved.revision; await loadLint();
      if (meta.published_version) meta.draft_changed=true;
      setState("Đã lưu nháp lúc "+new Date().toLocaleTimeString("vi-VN",{hour:"2-digit",minute:"2-digit"}),"ok");
      renderHead(); renderLint(); renderRail();
    } catch(error) { dirty=true; setState("Chưa lưu được","error"); if(error.message!=="expired") window.toast(error.message || "Không lưu được bản nháp.","error"); throw error; }
  })();
  try { await saving; } finally { saving=null; if(again){again=false;if(dirty)save().catch(()=>{});} }
  return null;
}

function markDirty() {
  dirty = true;
  if (meta && meta.published_version) meta.draft_changed = true;
  setState("Có thay đổi chưa lưu", "pending");
  renderHead();
  clearTimeout(timer);
  timer = window.setTimeout(() => {
    if (draftIssue()) { setState("Hoàn thiện nội dung bắt buộc trước khi lưu", "pending"); return; }
    save().catch(() => {});
  }, 500);
}

// Before anything that reads the draft on the server: media, preview, publish.
async function flush() {
  if (saving) await saving;
  if (!dirty) return;
  const issue = draftIssue();
  if (issue) {
    setState("Hoàn thiện nội dung bắt buộc trước khi lưu", "pending");
    window.toast(issue, "warn");
    throw new Error(issue);
  }
  await save();
  if (dirty) await flush();
}

// ---------------------------------------------------------------- head + rail
function renderHead() {
  const state=meta.published_version
    ? '<span class="badge state-on">Đã xuất bản v'+Number(meta.published_version)+'</span>'+(meta.draft_changed?' <span class="badge state-warn">Có sửa đổi chưa xuất bản</span>':"")
    : '<span class="badge state-off">Bản nháp · chưa xuất bản</span>';
  $("builder-head").innerHTML='<p class="eyebrow">'+escapeHtml(path && path.title || "Soạn bài")+' · '+escapeHtml(unit && unit.title || "Chặng chưa xác định")+'</p>'+
    '<h1>'+escapeHtml(lesson.title || "Bài học chưa đặt tên")+'</h1><div class="unit-tags">'+state+'</div>'+
    '<p class="notice notice-info">Bài được lưu theo typed lesson contract M10. Tiêu chí và tỷ lệ hoàn thành không thuộc contract này.</p>';
  document.title=lesson.title+" · Soạn bài";
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

  for (const field of ["title", "tip", "strictness"]) {
    const element = $("editor-fields").querySelector('[data-field="' + field + '"]');
    if (element && element.closest(".editor-field")) element.closest(".editor-field").hidden = true;
  }
  const metaDetails = document.querySelector(".meta-more");
  if (metaDetails) metaDetails.hidden = true;
  renderAudio();
  renderImage();
}

function renderAudio() {
  const current=step(), show=current && (current.kind==="read_aloud" || current.kind==="repeat");
  $("audio-panel").hidden=!show;
  if(!show)return;
  $("audio-check").hidden=true;
  $("audio-current").innerHTML=current.model_audio
    ? '<div class="media-current"><span class="eyebrow">Giọng mẫu hiện tại</span><audio controls preload="none" src="'+escapeHtml(current.model_audio_url || "")+'"></audio></div>'
    : '<p class="muted">Bước này chưa có giọng mẫu.</p>';
  recorder.reset(); recorder.repaint();
}

function renderImage() { $("image-panel").hidden=true; }

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
    const body=new FormData();
    body.append("media_kind","sample_audio"); body.append("audio",audio,name);
    const url="/api/v1/teacher/learn/lessons/"+encodeURIComponent(LESSON_ID)+"/versions/"+draftVersion+"/steps/"+encodeURIComponent(s.step_id)+"/media";
    const r=await fetch(url,{method:"POST",body});
    if (window.redirectToLoginIfExpired(r)) return;
    const d = await r.json().catch(() => ({}));
    if (!r.ok) {
      window.toast(errorText(d), "error");
      return;
    }
    s.model_audio = d.media_id;
    s.model_audio_url = d.url;
    if (meta.published_version) meta.draft_changed = true;
    renderAudio();
    renderHead();
    window.toast("Đã lưu giọng mẫu.", "ok");
  },
});

$("image-upload").addEventListener("click", () => {
  window.toast("M10 chưa cung cấp route tải ảnh cho bài học; hãy dùng bước không cần ảnh.","info");
});

// ---------------------------------------------------------------- bar
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

$("publish").addEventListener("click",async()=>{
  try { await flush(); } catch(_) { return; }
  let validation;
  try { validation=await requestJson("/api/v1/teacher/learn/lessons/"+encodeURIComponent(LESSON_ID)+"/lint",{
    method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({lesson:toDomainLesson(lesson),for_publish:true})}); }
  catch(error){window.toast(error.message,"error");return;}
  if(!validation.valid){const first=validation.errors && validation.errors[0];window.toast(first?first.message:"Bài học chưa đạt điều kiện xuất bản.","error");lint=validationIssues(validation);renderLint();return;}
  if(!confirm("Xuất bản bài học? Sinh viên sẽ thấy phiên bản này."))return;
  try {
    const published=await requestJson("/api/v1/teacher/learn/lessons/"+encodeURIComponent(LESSON_ID)+"/publish",{
      method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({expected_revision:domainRevision})});
    meta.published_version=published.version;meta.draft_changed=false;
    localStorage.setItem("aicefr-published-lesson-"+LESSON_ID,String(published.version));
    renderHead();window.toast("Đã xuất bản phiên bản "+published.version+".","ok");
  } catch(error){window.toast(error.message,"error");}
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
  const response=await fetch("/api/v1/teacher/learn/lessons/"+encodeURIComponent(LESSON_ID));
  if(window.redirectToLoginIfExpired(response))return;
  window.clearBusy(root);
  if(response.status===403){$("builder-head").innerHTML='<p class="error">Tài khoản này không có quyền soạn bài.</p>';$("builder-bar").hidden=true;return;}
  if(!response.ok){$("builder-head").innerHTML='<div class="empty-state"><h2>Không mở được bài học này</h2><p><a href="/teach">Quay lại lộ trình</a>.</p></div>';$("builder-bar").hidden=true;return;}
  const raw=await response.json();domainRevision=raw.revision || 0;draftVersion=raw.version || 1;
  lesson=fromDomainLesson(raw);meta={published_version:Number(localStorage.getItem("aicefr-published-lesson-"+LESSON_ID))||null,draft_changed:false,updated_at:null};
  attachMedia(lesson,raw.sample_media);await resolveContext();
  if(!unit || !unit.unit_id){$("builder-bar").hidden=true;$("builder-head").innerHTML='<div class="empty-state"><h2>Chưa xác định được chặng</h2><p>Mở bài từ trang <a href="/teach">Soạn bài</a> để đồng bộ bản nháp.</p></div>';return;}
  $("f-title").value=lesson.title;$("f-summary").value=lesson.summary || "";$("f-band").value=lesson.band;
  $("f-criterion").disabled=true;$("f-pass").disabled=true;$("f-model-text").disabled=true;$("f-keywords").disabled=true;
  $("f-model-text").value="";$("f-keywords").value="";$("builder-layout").hidden=false;
  setState("Bản nháp hiện tại · revision "+domainRevision);renderHead();
  try{await loadLint();}catch(_){lint=[];}renderLint();select(0);
}


recorder.enable(document.body.dataset.recordingEnabled === "true");

load();
