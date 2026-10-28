// One lesson, one step at a time (D025, M14). Also today's review (M15) and a
// teacher's preview of a draft: three sources, one player.
//
// Feedback follows the research the design rests on: in the controlled steps it
// comes right after the attempt and asks the learner to fix one thing
// themselves; in the free step it comes after the talk and names at most a
// couple of points, so speaking is never interrupted. Words the machine did not
// hear are shown as "máy chưa nghe ra", never as mistakes.
const escapeHtml = window.escapeHtml;
const icon = (name, cls) => window.ui.icon(name, cls);
// The icon of each kind of step, as on the path (D027).
const KIND_ICON = window.ui.STEP_ICONS;
const root = document.getElementById("lesson");
const LESSON_ID = root.dataset.lessonId;
const MODE = root.dataset.mode || "lesson"; // lesson | review | preview

const headEl = document.getElementById("lesson-head");
const layoutEl = document.getElementById("lesson-layout");
const railEl = document.getElementById("step-rail");
const bodyEl = document.getElementById("step-body");
const formEl = document.getElementById("step-form");
const feedbackEl = document.getElementById("step-feedback");
const summaryEl = document.getElementById("lesson-summary");

let data = null;
let steps = [];
let index = 0;
let round = 1;
const results = {}; // step id -> latest result, from the server or this session
// A step counts as passed once any attempt passed, as the server counts it.
const passedSteps = new Set();
// Step id -> the latest stored attempt, so a learner can reopen its result
// (and see a teacher's correction) on coming back to the lesson.
const lastAttempt = {};
let lastAudio = null;
// True while the server runs the simulated recogniser: every result is then a
// fixed sentence, not the learner's voice, and must say so where it is read.
let simulated = false;
// Countdowns of the step on screen (show the sentence, planning time); stopped
// when the learner moves to another step, or they would pull focus back later.
let timers = [];
const stopTimers = () => {
  timers.forEach(clearInterval);
  timers = [];
};

// Kinds whose unheard words come back in the review, as on the server.
const REVIEWED_KINDS = ["read_aloud", "gap", "keywords", "starter"];

const current = () => steps[index];
const limitOf = (step, r) =>
  step.kind === "free" ? step.round_limits[Math.min(r, step.round_limits.length) - 1] : step.max_seconds;

const recorder = window.setUpRecorder({
  minSeconds: () => (current() ? current().min_seconds : 0),
  maxSeconds: () => (current() ? limitOf(current(), round) : 60),
  onSubmit: submit,
});

// "2026-10-09" as 09/10/2026, without passing through a time zone.
const dmy = (iso) => window.ui.dmy(iso);

// ---------------------------------------------------------------- content

function highlight(text, words) {
  // Bold the hint words in the passage: whole words, any case, longest first.
  // One pass over the raw text, escaping each piece: replacing word after word
  // in the escaped HTML would also hit the markup already inserted (a hint word
  // "word" inside class="hint-word").
  const list = (words || []).map((w) => w.trim()).filter(Boolean);
  if (!list.length) return escapeHtml(text);
  const alts = list
    .sort((a, b) => b.length - a.length)
    .map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/\s+/g, "\\s+"));
  let out = "";
  let last = 0;
  for (const m of text.matchAll(new RegExp(`\\b(?:${alts.join("|")})\\b`, "gi"))) {
    out += escapeHtml(text.slice(last, m.index)) + `<b class="hint-word">${escapeHtml(m[0])}</b>`;
    last = m.index + m[0].length;
  }
  return out + escapeHtml(text.slice(last));
}

function chips(words, cls = "word-chips") {
  if (!words || !words.length) return "";
  return `<ul class="${cls}">${words.map((w) => `<li lang="en">${escapeHtml(w)}</li>`).join("")}</ul>`;
}

function modelAudio(step, label) {
  if (!step.model_audio_url) return "";
  return (
    `<div class="model-audio"><span class="eyebrow">${icon("volume")}${escapeHtml(label || "Giọng mẫu")}</span>` +
    `<audio controls preload="none" src="${escapeHtml(step.model_audio_url)}"></audio></div>`
  );
}

function stageChip(step) {
  return (
    `<span class="stage-chip stage-${escapeHtml(step.stage)}">${icon(KIND_ICON[step.kind] || "mic")}${escapeHtml(step.stage_name)}` +
    ` · ${escapeHtml(step.kind_name)}</span>`
  );
}

function content(step) {
  const k = step.kind;
  if (k === "read_aloud") {
    return modelAudio(step) + `<p class="read-text" lang="en">${highlight(step.text, step.hint_words)}</p>`;
  }
  if (k === "repeat") {
    const audio = step.model_audio_url
      ? modelAudio(step, "Nghe câu mẫu")
      : '<p class="notice notice-info">Bài này chưa có giọng mẫu: đọc câu dưới đây rồi nhắc lại không nhìn chữ.</p>';
    return (
      audio +
      `<p class="read-text" lang="en" id="repeat-text">${escapeHtml(step.text)}</p>` +
      `<button type="button" class="secondary small" id="toggle-text">${icon("eye-off")}<span>Ẩn chữ để tự thử</span></button>`
    );
  }
  if (k === "look_up") {
    return (
      `<div class="look-up"><p class="read-text" lang="en" id="look-text" hidden>${escapeHtml(step.text)}</p>` +
      `<p class="look-hidden" id="look-hidden">Câu đang ẩn. Bấm để xem trong ${Number(step.show_seconds) || 5} giây.</p>` +
      `<button type="button" class="secondary" id="show-text">${icon("eye")}<span>Hiện câu</span></button>` +
      '<span class="look-countdown" id="look-countdown" aria-live="polite"></span></div>'
    );
  }
  if (k === "gap") {
    let n = 0;
    const html = escapeHtml(step.text).replace(/_{3,}/g, () => {
      n += 1;
      return `<span class="blank" aria-label="chỗ trống ${n}">(${n})</span>`;
    });
    return `<p class="read-text" lang="en">${html}</p><p class="eyebrow">Ngân hàng từ</p>${chips(step.hint_words, "word-chips bank")}`;
  }
  if (k === "keywords") {
    return `<p class="eyebrow">Từ khóa</p>${chips(step.keywords, "word-chips big")}`;
  }
  if (k === "starter") {
    return (
      `<p class="question" lang="en">${escapeHtml(step.text)}</p>` +
      `<p class="eyebrow">Khung câu</p><p class="frame" lang="en">${escapeHtml(step.starter)} …</p>` +
      (step.keywords.length ? `<p class="eyebrow">Nên dùng</p>${chips(step.keywords)}` : "")
    );
  }
  if (k === "picture") {
    const img = step.image_url
      ? `<img class="step-image" src="${escapeHtml(step.image_url)}" alt="${escapeHtml(step.image_alt || "Ảnh để mô tả")}">`
      : "";
    return (
      img +
      (step.text ? `<p class="question" lang="en">${escapeHtml(step.text)}</p>` : "") +
      `<p class="eyebrow">Ngân hàng từ</p>${chips(step.hint_words, "word-chips bank")}`
    );
  }
  if (k === "outline") {
    const points = step.outline.length
      ? `<ol class="outline-points">${step.outline.map((p) => `<li>${escapeHtml(p)}</li>`).join("")}</ol>`
      : "";
    const markers = step.markers.map((g) => g.join(" / "));
    const prep = Number(step.prep_seconds)
      ? `<div class="prep"><button type="button" class="secondary" id="start-prep">${icon("clock")}<span>Bắt đầu chuẩn bị ${Number(step.prep_seconds)} giây</span></button>` +
        '<span class="prep-clock" id="prep-clock" aria-live="polite"></span></div>'
      : "";
    return (
      (step.text ? `<p class="question" lang="en">${escapeHtml(step.text)}</p>` : "") +
      points +
      (markers.length ? `<p class="eyebrow">Từ nối theo thứ tự</p>${chips(markers)}` : "") +
      prep
    );
  }
  if (k === "free") {
    const limits = step.round_limits;
    const pills = limits
      .map(
        (s, i) =>
          `<li class="${i + 1 === round ? "now" : i + 1 < round ? "done" : ""}">Lượt ${i + 1} · ${s} giây</li>`
      )
      .join("");
    const missions = (step.missions || []).length
      ? `<p class="eyebrow">Mục tiêu</p><ul class="mission-mini">${step.missions
          .map((m) => `<li>${escapeHtml(m.label)}${m.words && m.words.length ? `: <span lang="en">${escapeHtml(m.words.join(", "))}</span>` : ""}</li>`)
          .join("")}</ul>`
      : "";
    return (
      `<p class="prompt">${escapeHtml(step.text)}</p>` +
      (limits.length > 1 ? `<ol class="round-pills" aria-label="Các lượt nói">${pills}</ol>` : "") +
      missions
    );
  }
  return "";
}

function wireContent(step) {
  const toggle = document.getElementById("toggle-text");
  if (toggle) {
    toggle.addEventListener("click", () => {
      const t = document.getElementById("repeat-text");
      t.classList.toggle("veiled");
      toggle.querySelector("span").textContent = t.classList.contains("veiled") ? "Hiện lại chữ" : "Ẩn chữ để tự thử";
    });
  }
  const show = document.getElementById("show-text");
  if (show) {
    show.addEventListener("click", () => {
      const text = document.getElementById("look-text");
      const hidden = document.getElementById("look-hidden");
      const clock = document.getElementById("look-countdown");
      let left = Number(step.show_seconds) || 5;
      text.hidden = false;
      hidden.hidden = true;
      show.disabled = true;
      clock.textContent = `Còn ${left} giây`;
      const timer = setInterval(() => {
        left -= 1;
        clock.textContent = left > 0 ? `Còn ${left} giây` : "";
        if (left <= 0) {
          clearInterval(timer);
          text.hidden = true;
          hidden.hidden = false;
          hidden.textContent = "Câu đã ẩn. Bây giờ ghi âm và nói lại câu.";
          show.disabled = false;
          show.querySelector("span").textContent = "Xem lại câu";
          document.getElementById("rec-button").focus();
        }
      }, 1000);
      timers.push(timer);
    });
  }
  const prep = document.getElementById("start-prep");
  if (prep) {
    prep.addEventListener("click", () => {
      let left = Number(step.prep_seconds);
      const clock = document.getElementById("prep-clock");
      prep.disabled = true;
      clock.textContent = `Chuẩn bị: ${left} giây`;
      const timer = setInterval(() => {
        left -= 1;
        clock.textContent = left > 0 ? `Chuẩn bị: ${left} giây` : "Hết giờ chuẩn bị. Bắt đầu nói.";
        if (left <= 0) {
          clearInterval(timer);
          document.getElementById("rec-button").focus();
        }
      }, 1000);
      timers.push(timer);
    });
  }
}

// ---------------------------------------------------------------- frame

function statusOf(step) {
  if (passedSteps.has(step.step_id)) return "passed";
  return results[step.step_id] ? "tried" : "todo";
}

// Whether the lesson is complete by the server's rule: enough steps passed and
// every free step spoken. Used where the server has not said so (a preview).
function completeHere() {
  const ratio = data && data.lesson ? data.lesson.pass_ratio : 0.8;
  const passed = steps.filter((s) => passedSteps.has(s.step_id)).length;
  // As on the server: a free step counts once speech was measured in it.
  const spoke = (r) => r && r.measured && r.speaking_s > 0;
  const freeDone = steps.filter((s) => s.kind === "free").every((s) => spoke(results[s.step_id]));
  return steps.length > 0 && passed >= ratio * steps.length - 1e-9 && freeDone;
}

function renderRail() {
  railEl.innerHTML =
    "<ol>" +
    steps
      .map((s, i) => {
        const st = statusOf(s);
        const mark = icon(st === "passed" ? "check" : KIND_ICON[s.kind] || "mic", "icon rail-icon");
        const label = st === "passed" ? "đã đạt" : st === "tried" ? "đã thử" : "chưa làm";
        return (
          `<li class="${st}${i === index ? " now" : ""}"${i === index ? ' aria-current="step"' : ""}>` +
          `<button type="button" class="rail-step" data-step-index="${i}">` +
          `<span class="rail-mark" aria-hidden="true">${mark}</span>` +
          `<span class="rail-text"><span class="rail-stage">${i + 1} · ${escapeHtml(s.stage_name)}</span>` +
          `<span class="rail-title">${escapeHtml(s.display_title)}</span></span>` +
          `<span class="visually-hidden">, ${label}</span></button></li>`
        );
      })
      .join("") +
    "</ol>";
  railEl.querySelectorAll("[data-step-index]").forEach((b) =>
    b.addEventListener("click", () => showStep(Number(b.dataset.stepIndex)))
  );
  const passed = steps.filter((s) => statusOf(s) === "passed").length;
  const bar = document.getElementById("lesson-progress");
  if (bar) {
    bar.style.width = `${steps.length ? (passed / steps.length) * 100 : 0}%`;
    document.getElementById("lesson-progress-text").textContent = `${passed}/${steps.length} bước đã đạt`;
  }
}

function renderHead() {
  if (MODE === "review") {
    headEl.innerHTML =
      '<p class="eyebrow">Ôn tập giãn cách</p><h1>Ôn tập hôm nay</h1>' +
      '<p class="lede">Những từ máy chưa nghe ra và những bài nói tự do bạn đã làm quay lại sau 1, 3 rồi 7 ngày. Nói câu mới của riêng bạn, không cần nhớ nguyên văn.</p>';
    return;
  }
  const l = data.lesson;
  headEl.innerHTML =
    `<p class="eyebrow">${escapeHtml(data.unit.title)} · ${escapeHtml(l.band)}${l.sample ? " · Nội dung mẫu" : ""}</p>` +
    `<h1>${escapeHtml(l.title)}</h1>` +
    (l.summary ? `<p class="lede">${escapeHtml(l.summary)}</p>` : "") +
    '<div class="lesson-progress"><div class="lesson-progress-track"><span id="lesson-progress"></span></div>' +
    '<span class="muted" id="lesson-progress-text"></span></div>';
  document.title = l.title + " · Luyện tập";
}

function showStep(i) {
  stopTimers();
  index = Math.max(0, Math.min(i, steps.length - 1));
  round = 1;
  const step = current();
  const last = results[step.step_id];
  if (step.kind === "free" && last && last.round && last.round < step.round_limits.length) {
    round = last.round + 1; // pick up where the rounds stopped
  }
  summaryEl.hidden = true;
  layoutEl.hidden = false;
  feedbackEl.hidden = true;
  feedbackEl.innerHTML = "";
  formEl.hidden = false;
  bodyEl.innerHTML =
    `<div class="step-top">${stageChip(step)}<span class="muted">Bước ${index + 1}/${steps.length}</span></div>` +
    `<h2 id="step-h" tabindex="-1">${escapeHtml(step.display_title)}</h2>` +
    (step.instruction ? `<p class="instruction">${escapeHtml(step.instruction)}</p>` : "") +
    (MODE === "review" && step.lesson_title ? `<p class="muted">Từ bài «${escapeHtml(step.lesson_title)}»</p>` : "") +
    `<div class="step-content">${content(step)}</div>` +
    (step.tip ? `<p class="step-tip"><b>Mẹo:</b> ${escapeHtml(step.tip)}</p>` : "") +
    lastTry(lastAttempt[step.step_id]);
  wireContent(step);
  const again = document.getElementById("show-last");
  if (again) {
    again.addEventListener("click", () => {
      const a = lastAttempt[step.step_id];
      showFeedback({ result: a.result, audio_url: a.audio_url, replay: true });
    });
  }
  recorder.reset();
  renderRail();
}

function lastTry(a) {
  if (!a) return "";
  return (
    '<div class="last-try">' +
    `<span>${icon("clock")}Lần gần nhất: <b>${a.passed ? "Đạt" : "Chưa đạt"}</b> · ${escapeHtml(window.ui.localTime(a.created_at))}</span>` +
    (a.result.teacher_reviewed ? '<span class="badge state-on">Giáo viên đã xem lại</span>' : "") +
    '<button type="button" class="link-button" id="show-last">Xem lại kết quả</button></div>'
  );
}

// ---------------------------------------------------------------- feedback

function markedText(result) {
  if (!result.words || !result.words.length) return "";
  const words = result.words
    .map((w) => {
      const st = w.teacher || w.status;
      const title =
        st === "missed"
          ? w.said
            ? `Máy chưa nghe ra; máy nghe thành «${w.said}»`
            : "Máy chưa nghe ra"
          : st === "unsure"
            ? w.said
              ? `Chưa chắc: máy nghe «${w.said}»`
              : "Máy nghe ra nhưng chưa chắc"
            : "Máy nghe ra";
      const seek = w.start_s != null ? ` data-seconds="${Number(w.start_s)}"` : "";
      // D039: the Vietnamese-learner pattern this word shows, when the machine sees one.
      const named = w.pattern && st !== "heard" ? window.ui.PRONUNCIATION_NAMES[w.pattern] : "";
      const full = named ? `${title} · ${named}` : title;
      return `<span class="w ${escapeHtml(st)}${w.teacher ? " teacher" : ""}" title="${escapeHtml(full)}"${seek}>${escapeHtml(w.text)}</span>`;
    })
    .join(" ");
  return (
    `<p class="read-text marked" lang="en">${words}</p>` +
    '<ul class="specimen-legend"><li><span class="dot heard" aria-hidden="true"></span>Máy nghe ra</li>' +
    '<li><span class="dot unsure" aria-hidden="true"></span>Chưa chắc</li>' +
    '<li><span class="dot missed" aria-hidden="true"></span>Máy chưa nghe ra</li></ul>'
  );
}

function gapList(result) {
  if (!result.gaps || !result.gaps.length) return "";
  const name = { correct: "đúng", distractor: "từ khác trong ngân hàng", other: "từ khác", missing: "chưa nghe ra từ nào" };
  return (
    '<ul class="gap-list">' +
    result.gaps
      .map(
        (g) =>
          `<li class="${escapeHtml(g.status)}"><b>(${g.index + 1})</b> ` +
          (g.said ? `máy nghe «<span lang="en">${escapeHtml(g.said)}</span>» · ` : "") +
          `${escapeHtml(name[g.status] || g.status)}</li>`
      )
      .join("") +
    "</ul>"
  );
}

function foundList(result) {
  let h = "";
  if (result.found && result.found.length) {
    h +=
      '<p class="eyebrow">Máy nghe thấy</p><ul class="word-chips found">' +
      result.found
        .map(
          (f) =>
            `<li${f.start_s != null ? ` data-seconds="${Number(f.start_s)}"` : ""} lang="en">${escapeHtml(f.text)}` +
            (f.start_s != null ? ` <span class="hit-time">${window.ui.mmss(f.start_s)}</span>` : "") +
            "</li>"
        )
        .join("") +
      "</ul>";
  }
  if (result.missing && result.missing.length) {
    h += `<p class="eyebrow">Máy chưa nghe thấy</p>${chips(result.missing, "word-chips missing")}`;
  }
  return h;
}

function signalList(result) {
  const items = (result.signals || []).filter((s) => s.text);
  if (!items.length) return "";
  return (
    '<ul class="signal-list">' +
    items
      .map((s) => {
        const mark = s.met === true ? "✓" : s.met === false ? "✗" : "·";
        const cls = s.met === true ? "met" : s.met === false ? "unmet" : "";
        return `<li class="${cls}"><span aria-hidden="true">${mark}</span> ${escapeHtml(s.text)}</li>`;
      })
      .join("") +
    "</ul>"
  );
}

function verdict(result) {
  if (!result.measured) {
    return `<div class="verdict warn">${icon("info")}<span><b>Chưa đo được lượt này.</b> Xem gợi ý bên dưới rồi ghi lại.</span></div>`;
  }
  if (result.passed) return `<div class="verdict ok">${icon("check-circle")}<span><b>Đạt bước này.</b></span></div>`;
  return `<div class="verdict todo">${icon("refresh")}<span><b>Chưa đạt.</b> Thử lại một lượt nữa, theo gợi ý bên dưới.</span></div>`;
}

// Review only: what happens next to each word or talk of the session.
function reviewOutcome(items) {
  if (!items || !items.length) return "";
  const line = (i) => {
    const what = i.word ? `«<span lang="en">${escapeHtml(i.word)}</span>»` : "Bài nói này";
    if (!i.passed) return `${what}: máy chưa nghe ra, sẽ quay lại vào ngày mai.`;
    if (i.done) return `${what}: đã ôn đủ ba lần, không cần ôn nữa.`;
    return `${what}: đã nhớ, lần ôn tới vào ngày ${escapeHtml(dmy(i.due))}.`;
  };
  return `<p class="eyebrow">Lịch ôn</p><ul class="change-list">${items.map((i) => `<li>${line(i)}</li>`).join("")}</ul>`;
}

function showFeedback(payload) {
  const step = current();
  const result = payload.result;
  results[step.step_id] = { ...result, round: result.round };
  if (result.passed) passedSteps.add(step.step_id);
  if (payload.attempt_id) {
    lastAttempt[step.step_id] = {
      result,
      audio_url: payload.audio_url,
      passed: result.passed,
      created_at: new Date().toISOString(),
    };
  }
  lastAudio = payload.audio_url;
  const limits = step.kind === "free" ? step.round_limits : [];
  // A result reopened from an earlier visit offers no next round: the round
  // it belonged to is over.
  const moreRounds = !payload.replay && step.kind === "free" && round < limits.length && result.measured;
  const last = index === steps.length - 1;
  const next = moreRounds
    ? `<button type="button" id="next-round"><span>Lượt ${round + 1} · ${limits[round]} giây</span>${icon("arrow-right")}</button>`
    : last
      ? `<button type="button" id="finish">${icon("trophy")}<span>Xem tổng kết</span></button>`
      : `<button type="button" id="next-step"><span>Bước tiếp</span>${icon("arrow-right")}</button>`;
  feedbackEl.innerHTML =
    (simulated
      ? '<p class="notice notice-danger"><b>Kết quả giả lập, không phải của bạn.</b> Máy chủ đang dùng ' +
        "bộ nhận dạng giả lập: nó không nghe bản ghi mà luôn trả về cùng một câu, nên các từ " +
        "«máy chưa nghe ra» dưới đây không nói gì về cách bạn đọc. Cần bật bộ nhận dạng thật để " +
        "được đo.</p>"
      : "") +
    verdict(result) +
    (result.tip ? `<p class="tip">${icon("sparkle")}<span><b>Gợi ý:</b> ${escapeHtml(result.tip)}</span></p>` : "") +
    ((result.changes || []).length
      ? `<p class="eyebrow">So với lượt 1</p><ul class="change-list">${result.changes
          .map((c) => `<li>${escapeHtml(c)}</li>`)
          .join("")}</ul>`
      : "") +
    markedText(result) +
    gapList(result) +
    foundList(result) +
    signalList(result) +
    reviewOutcome(payload.items) +
    (result.teacher_reviewed
      ? `<p class="notice notice-info"><b>Giáo viên đã xem lại lượt này.</b>${result.teacher_note ? " " + escapeHtml(result.teacher_note) : ""}</p>`
      : "") +
    (lastAudio
      ? `<div class="replay"><span class="eyebrow">${icon("headphones")}Nghe lại lượt của bạn</span><audio id="attempt-audio" controls preload="metadata" src="${escapeHtml(lastAudio)}"></audio></div>`
      : "") +
    `<div class="button-row feedback-actions">${next}<button type="button" class="secondary" id="retry-step">${icon("refresh")}<span>Làm lại bước này</span></button></div>`;
  feedbackEl.hidden = false;
  formEl.hidden = true;
  feedbackEl.focus();

  const player = document.getElementById("attempt-audio");
  feedbackEl.querySelectorAll("[data-seconds]").forEach((n) => {
    n.classList.add("seekable");
    n.addEventListener("click", () => {
      if (!player) return;
      player.currentTime = Math.max(0, parseFloat(n.dataset.seconds) - 0.3);
      player.play().catch(() => {});
    });
  });
  const retry = document.getElementById("retry-step");
  retry.addEventListener("click", () => {
    feedbackEl.hidden = true;
    formEl.hidden = false;
    recorder.reset();
    document.getElementById("step-h").focus();
  });
  const nr = document.getElementById("next-round");
  if (nr) {
    nr.addEventListener("click", () => {
      round += 1;
      bodyEl.querySelector(".step-content").innerHTML = content(step);
      feedbackEl.hidden = true;
      formEl.hidden = false;
      recorder.reset();
    });
  }
  const ns = document.getElementById("next-step");
  if (ns) ns.addEventListener("click", () => showStep(index + 1));
  const fin = document.getElementById("finish");
  if (fin) fin.addEventListener("click", showSummary);

  if (payload.progress && data) data.progress = payload.progress;
  if (payload.completed_now) window.toast("Hoàn thành bài học. Làm tốt lắm!", "ok");
  renderRail();
}

function showSummary() {
  layoutEl.hidden = true;
  const passed = steps.filter((s) => statusOf(s) === "passed").length;
  // Only what the server really schedules: the words of these kinds of step,
  // at most six per attempt (WORD_REVIEW_KINDS in lessons_api.py). A preview
  // schedules nothing.
  const missed = [];
  steps.forEach((s) => {
    const r = results[s.step_id];
    if (MODE === "preview" || !r || !REVIEWED_KINDS.includes(s.kind)) return;
    const words = [...(r.missing || []), ...(r.gaps || []).filter((g) => g.status !== "correct").map((g) => g.expected)];
    words.slice(0, 6).forEach((w) => missed.includes(w) || missed.push(w));
  });
  const progress = data && data.progress ? data.progress : null;
  const done = MODE === "lesson" && progress ? progress.completed : completeHere();
  const next = data && data.next_lesson;
  summaryEl.innerHTML =
    `<div class="summary-mark${done ? " done" : ""}">${icon(done ? "trophy" : MODE === "review" ? "refresh" : "flame")}</div>` +
    `<p class="eyebrow">${MODE === "review" ? "Kết thúc buổi ôn" : "Tổng kết bài học"}</p>` +
    `<h2>${done ? "Hoàn thành bài học" : MODE === "review" ? "Đã ôn xong" : "Chưa hoàn thành bài học"}</h2>` +
    `<p>${passed}/${steps.length} bước đã đạt.` +
    (progress && !progress.free_done && MODE === "lesson" ? " Bài chỉ hoàn thành khi bạn đã làm bước nói tự do." : "") +
    "</p>" +
    (missed.length
      ? `<p class="eyebrow">Từ sẽ quay lại trong phần Ôn tập</p>${chips(missed.slice(0, 12))}`
      : "") +
    '<div class="button-row">' +
    (next ? `<a class="button" href="/practice/lessons/${encodeURIComponent(next.lesson_id)}">${icon("play")}Bài tiếp: ${escapeHtml(next.title)}</a>` : "") +
    `<a class="button${next ? " secondary" : ""}" href="${MODE === "preview" ? `/teach/lessons/${encodeURIComponent(LESSON_ID)}` : "/practice"}">${icon(MODE === "preview" ? "pencil" : "path")}${MODE === "preview" ? "Quay lại soạn bài" : "Về lộ trình"}</a>` +
    `<button type="button" class="secondary" id="again">${icon("refresh")}<span>Xem lại các bước</span></button></div>`;
  summaryEl.hidden = false;
  summaryEl.focus();
  document.getElementById("again").addEventListener("click", () => showStep(0));
}

// ---------------------------------------------------------------- submit

// Achievements this recording just reached (D032), said once in a toast. They
// stay "new" until the learner opens the list on the progress page.
function celebrate(list) {
  if (!Array.isArray(list) || !list.length) return;
  const names = list.map((a) => a.title).join(", ");
  const head = list.length > 1 ? list.length + " thành tựu mới: " : "Thành tựu mới: ";
  window.toast(head + names + ". Xem ở trang Tiến độ.", "ok");
}

async function submit(audio, name) {
  const step = current();
  const body = new FormData();
  body.append("audio", audio, name);
  let url;
  if (MODE === "review") {
    url = "/api/v1/learn/review/attempts";
    body.append("review_id", step.review_id);
  } else if (MODE === "preview") {
    url = "/api/v1/teach/preview";
    body.append("lesson_id", LESSON_ID);
    body.append("step_id", step.step_id);
    if (step.kind === "free") body.append("round", String(round));
  } else {
    url = `/api/v1/learn/lessons/${encodeURIComponent(LESSON_ID)}/steps/${encodeURIComponent(step.step_id)}/attempts`;
    if (step.kind === "free") body.append("round", String(round));
  }
  try {
    const r = await fetch(url, { method: "POST", body });
    if (window.redirectToLoginIfExpired(r)) return;
    const d = await r.json().catch(() => ({}));
    if (!r.ok) {
      window.toast(typeof d.detail === "string" ? d.detail : "Không gửi được bản ghi.", "error", { sticky: true });
      return;
    }
    recorder.done();
    showFeedback(d);
    celebrate(d.achievements);
  } catch (err) {
    window.toast("Mất kết nối khi gửi. Bản ghi vẫn còn, hãy thử lại.", "error", { sticky: true });
  }
}

// ---------------------------------------------------------------- load

function emptyReview(d) {
  window.clearBusy(root);
  layoutEl.hidden = true;
  summaryEl.hidden = false;
  summaryEl.innerHTML =
    `<div class="empty-state"><div class="empty-mark" aria-hidden="true">${icon("check-circle")}</div>` +
    "<h2>Không có mục nào đến hạn hôm nay</h2>" +
    `<p>${d.open ? `Còn ${Number(d.open)} mục đang chờ, lần ôn tới vào ngày ${escapeHtml(dmy(d.next_due))}.` : "Học thêm bài mới, những từ máy chưa nghe ra sẽ quay lại đây."}</p>` +
    '<div class="button-row"><a class="button" href="/practice">Về lộ trình</a></div></div>';
}

async function load() {
  try {
    if (MODE === "review") {
      const r = await fetch("/api/v1/learn/review");
      if (window.redirectToLoginIfExpired(r)) return;
      const d = await r.json();
      renderHead();
      if (!d.steps.length) {
        emptyReview(d);
        return;
      }
      steps = d.steps.map((s) => ({ ...s.step, review_id: s.review_id, lesson_title: s.lesson_title }));
    } else {
      const url =
        MODE === "preview"
          ? `/api/v1/teach/lessons/${encodeURIComponent(LESSON_ID)}/preview`
          : `/api/v1/learn/lessons/${encodeURIComponent(LESSON_ID)}`;
      const r = await fetch(url);
      if (window.redirectToLoginIfExpired(r)) return;
      if (!r.ok) throw new Error(String(r.status));
      data = await r.json();
      steps = data.lesson.steps;
      Object.entries(data.latest || {}).forEach(([sid, a]) => {
        results[sid] = { ...a.result, passed: a.passed, round: a.round };
        lastAttempt[sid] = a;
      });
      (data.passed_steps || []).forEach((sid) => passedSteps.add(sid));
      renderHead();
    }
    window.clearBusy(root);
    const first = steps.findIndex((s) => statusOf(s) !== "passed");
    showStep(first < 0 ? 0 : first);
  } catch (err) {
    window.clearBusy(root);
    headEl.innerHTML =
      '<div class="empty-state"><div class="empty-mark" aria-hidden="true">◇</div>' +
      "<h2>Không mở được bài học này</h2>" +
      '<p>Bài có thể chưa được xuất bản hoặc đã bị gỡ. <a href="/practice">Quay lại lộ trình</a>.</p></div>';
  }
}

// Health: the fake recogniser warning and whether live recording works.
fetch("/api/v1/health")
  .then((r) => (r.ok ? r.json() : null))
  .then((h) => {
    simulated = !!(h && !h.asr_is_real);
    if (simulated) document.getElementById("fake-asr-warning").hidden = false;
    recorder.enable(!!(h && h.recording_enabled));
  })
  .catch(() => recorder.enable(false));

// Consent: a learner's recordings are personal data. A teacher previewing a
// draft stores nothing, so the check is for learners only.
if (MODE !== "preview") {
  fetch("/api/v1/me/consent")
    .then((r) => (r.ok ? r.json() : null))
    .then((c) => {
      if (!c || c.may_submit || c.role !== "student") return;
      const gate = document.getElementById("consent-gate");
      gate.innerHTML =
        "<b>Chưa có đồng thuận lưu bản ghi.</b> Bài luyện là bản ghi giọng nói của bạn. " +
        '<a href="/consent">Ký đồng thuận</a> rồi quay lại.';
      gate.hidden = false;
      recorder.block("Cần ký đồng thuận trước khi ghi âm.");
    })
    .catch(() => {});
}

load();
