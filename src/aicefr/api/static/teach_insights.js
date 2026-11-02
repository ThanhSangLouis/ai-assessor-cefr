// How the class moves through a path (D025, M18).
//
// Totals per lesson and per step, the words a class keeps leaving out, and the
// latest attempts. Never a ranking of people. A teacher can open an attempt,
// listen, and correct what the machine said about a word or about the step:
// the learner then sees "giáo viên đã xem lại", the change is audited, and
// nothing is ever blocked or scored.
const escapeHtml = window.escapeHtml;
const root = document.getElementById("insights");
const $ = (id) => document.getElementById(id);
const chosen = new URLSearchParams(location.search).get("path");

const STATUS_NAMES = { heard: "máy nghe ra", unsure: "chưa chắc", missed: "máy chưa nghe ra" };
const NEXT_STATUS = { heard: "unsure", unsure: "missed", missed: "heard" };
const MAX_PICK = 12;

let data = null;
let units = [];
const picked = new Set();
let open = null; // the attempt in the dialog: { id, words, machine }

const pct = (x) => Math.round((Number(x) || 0) * 100);
const makeLabel = () =>
  picked.size ? `Tạo bài ôn từ ${picked.size} từ đã chọn` : "Chọn từ để tạo bài ôn";

function errorText(d) {
  if (typeof d.detail === "string") return d.detail.charAt(0).toUpperCase() + d.detail.slice(1);
  return "Không thực hiện được.";
}

// ---------------------------------------------------------------- sections
function bar(ratio, low) {
  return (
    `<span class="bar${low ? " low" : ""}" aria-hidden="true">` +
    `<span style="width:${Math.min(100, pct(ratio))}%"></span></span>`
  );
}

function lessonsSection(d) {
  if (!d.lessons.length) {
    return (
      '<section class="card"><div class="empty-state"><div class="empty-mark" aria-hidden="true">◇</div>' +
      "<h2>Lộ trình chưa có bài học nào được xuất bản</h2>" +
      '<p>Xuất bản bài học ở trang <a href="/teach">Lộ trình luyện</a> để sinh viên bắt đầu học.</p></div></section>'
    );
  }
  const attempts = d.lessons.reduce((n, l) => n + l.attempts, 0);
  const done = d.lessons.reduce((n, l) => n + l.completed, 0);
  const active = d.lessons.filter((l) => l.attempts).length;
  const rows = d.lessons
    .map((l) => {
      const steps = l.steps
        .map(
          (s, i) =>
            `<tr><td>${i + 1}. ${escapeHtml(s.title)}</td><td class="num">${Number(s.attempts)}</td>` +
            `<td class="num">${Number(s.learners)}</td><td>` +
            (s.pass_rate == null
              ? '<span class="muted">chưa có lượt</span>'
              : `<span class="rate">${bar(s.pass_rate, s.pass_rate < 0.6)}<span>${pct(s.pass_rate)}%</span></span>`) +
            "</td></tr>"
        )
        .join("");
      const ratio = l.learners ? l.completed / l.learners : 0;
      return (
        '<details class="ins-lesson"><summary>' +
        `<span class="ins-title"><b>${escapeHtml(l.title)}</b><span class="muted">${escapeHtml(l.unit)} · ${escapeHtml(l.band)}</span></span>` +
        (l.learners
          ? `<span class="ins-num"><b>${Number(l.learners)}</b> người học</span>` +
            `<span class="ins-done">${bar(ratio)}<span>${Number(l.completed)}/${Number(l.learners)} hoàn thành</span></span>` +
            `<span class="ins-num"><b>${Number(l.attempts)}</b> lượt</span>`
          : '<span class="ins-idle">Chưa có ai học bài này</span>') +
        `<span class="ins-stall">${l.stall_step ? `Hay dừng ở: <b>${escapeHtml(l.stall_step)}</b>` : ""}</span>` +
        "</summary>" +
        '<table class="ins-steps"><thead><tr><th scope="col">Bước</th><th scope="col" class="num">Lượt</th>' +
        '<th scope="col" class="num">Người</th><th scope="col">Tỷ lệ đạt</th></tr></thead>' +
        `<tbody>${steps}</tbody></table></details>`
      );
    })
    .join("");
  return (
    '<section class="card" aria-labelledby="ins-lessons-h">' +
    '<div class="card-head"><h2 id="ins-lessons-h">Theo bài học</h2>' +
    `<span class="muted">${attempts} lượt luyện · ${done} lượt hoàn thành bài · ${active}/${d.lessons.length} bài đã có người học</span></div>` +
    '<p class="muted">Bấm một bài để xem tỷ lệ đạt của từng bước. «Hay dừng» là bước có tỷ lệ đạt thấp nhất, dưới 60%, tính trên ít nhất ba lượt.</p>' +
    `<div class="ins-lessons">${rows}</div></section>`
  );
}

function wordsSection(d) {
  const items = d.missed_words
    .map(
      (w) =>
        `<li><button type="button" class="word-pick" aria-pressed="${picked.has(w.word)}" data-word="${escapeHtml(w.word)}" ` +
        `title="${escapeHtml(w.lessons.join(", "))}"><span lang="en">${escapeHtml(w.word)}</span>` +
        `<span class="count" aria-label="${Number(w.count)} lần">${Number(w.count)}</span></button></li>`
    )
    .join("");
  return (
    '<section class="card" aria-labelledby="ins-words-h">' +
    '<div class="card-head"><h2 id="ins-words-h">Từ cả lớp hay bỏ</h2>' +
    `<button type="button" class="small" id="make-review"${picked.size ? "" : " disabled"}>${makeLabel()}</button></div>` +
    '<p class="muted">Từ khóa, từ gợi ý và đáp án chỗ trống mà máy chưa nghe ra, đếm trên mọi lượt luyện của lộ trình. ' +
    `Chọn tối đa ${MAX_PICK} từ để tạo một bài ôn.</p>` +
    (items ? `<ul class="word-picks">${items}</ul>` : '<p class="muted">Chưa có từ nào.</p>') +
    "</section>"
  );
}

function recentSection(d) {
  if (!d.recent.length) {
    return (
      '<section class="card" aria-labelledby="ins-recent-h"><h2 id="ins-recent-h">Lượt luyện gần đây</h2>' +
      '<p class="muted">Chưa có lượt luyện nào.</p></section>'
    );
  }
  const rows = d.recent
    .map(
      (a) =>
        `<tr><td class="nowrap">${escapeHtml(window.ui.localTime(a.created_at))}</td>` +
        `<td><code>${escapeHtml(a.learner)}</code></td>` +
        `<td>${escapeHtml(a.lesson)}<div class="muted">${escapeHtml(a.step)}${a.round ? ` · lượt ${Number(a.round)}` : ""}</div></td>` +
        `<td>${a.passed ? '<span class="badge state-on">Đạt</span>' : '<span class="badge state-warn">Chưa đạt</span>'}</td>` +
        `<td>${a.teacher_reviewed ? '<span class="badge">Đã xem lại</span>' : '<span class="muted">—</span>'}</td>` +
        `<td><button type="button" class="small secondary" data-attempt="${escapeHtml(a.attempt_id)}">${window.ui.icon("headphones")}<span>Nghe và xem lại</span></button></td></tr>`
    )
    .join("");
  return (
    '<section class="card" aria-labelledby="ins-recent-h">' +
    '<div class="card-head"><h2 id="ins-recent-h">Lượt luyện gần đây</h2>' +
    `<span class="muted">${d.recent.length} lượt mới nhất</span></div>` +
    '<table class="ins-recent"><thead><tr><th scope="col">Lúc</th><th scope="col">Sinh viên</th>' +
    '<th scope="col">Bài và bước</th><th scope="col">Kết quả</th><th scope="col">Giáo viên</th>' +
    `<th scope="col"><span class="visually-hidden">Thao tác</span></th></tr></thead><tbody>${rows}</tbody></table></section>`
  );
}

function render() {
  window.clearBusy(root);
  if (!data.path) {
    root.innerHTML =
      '<div class="card"><div class="empty-state"><div class="empty-mark" aria-hidden="true">◇</div>' +
      '<h2>Chưa có lộ trình nào</h2><p>Tạo lộ trình ở trang <a href="/teach">Lộ trình luyện</a>.</p></div></div>';
    return;
  }
  const paths = data.paths || [];
  $("path-switch").innerHTML =
    paths.length > 1
      ? '<label for="path-select">Lộ trình</label><select id="path-select">' +
        paths
          .map(
            (p) =>
              `<option value="${escapeHtml(p.path_id)}"${p.path_id === data.path.path_id ? " selected" : ""}>` +
              `${escapeHtml(p.title)}</option>`
          )
          .join("") +
        "</select>"
      : "";
  const select = $("path-select");
  if (select) select.addEventListener("change", () => (location.search = `?path=${encodeURIComponent(select.value)}`));
  root.innerHTML = lessonsSection(data) + wordsSection(data) + recentSection(data);
}

async function load() {
  const q = chosen ? `?path_id=${encodeURIComponent(chosen)}` : "";
  try {
    const [r1, r2] = await Promise.all([fetch(`/api/v1/teach/insights${q}`), fetch("/api/v1/teach/paths")]);
    if (window.redirectToLoginIfExpired(r1)) return;
    if (r1.status === 403) {
      // Either no rights, or the school's plan does not include it (D034):
      // the server's sentence says which.
      const d = await r1.json().catch(() => ({}));
      window.clearBusy(root);
      root.innerHTML =
        typeof d.detail === "string" && d.detail.includes("gói")
          ? `<div class="notice notice-info">${escapeHtml(d.detail)}</div>`
          : '<p class="error">Tài khoản này không có quyền xem thống kê luyện tập. <a href="/">Về trang của bạn</a>.</p>';
      return;
    }
    if (!r1.ok) throw new Error(String(r1.status));
    data = await r1.json();
    const all = r2.ok ? await r2.json() : [];
    const mine = data.path ? all.find((p) => p.path_id === data.path.path_id) : null;
    units = mine ? mine.units : [];
    render();
  } catch (err) {
    window.clearBusy(root);
    root.innerHTML = '<p class="error">Không tải được thống kê. Hãy tải lại trang.</p>';
  }
}

// ---------------------------------------------------------------- words → review lesson
root.addEventListener("click", (e) => {
  const pick = e.target.closest(".word-pick");
  if (pick) {
    const w = pick.dataset.word;
    if (picked.has(w)) picked.delete(w);
    else if (picked.size >= MAX_PICK) {
      window.toast(`Chọn tối đa ${MAX_PICK} từ cho một bài.`, "warn");
      return;
    } else picked.add(w);
    pick.setAttribute("aria-pressed", String(picked.has(w)));
    const make = $("make-review");
    make.disabled = !picked.size;
    make.textContent = makeLabel();
    return;
  }
  if (e.target.closest("#make-review")) {
    if (!units.length) {
      window.toast("Lộ trình chưa có chặng nào để đặt bài ôn.", "warn");
      return;
    }
    $("words-unit").innerHTML = units
      .map((u) => `<option value="${escapeHtml(u.unit_id)}">${escapeHtml(u.title)}${u.band ? ` · ${escapeHtml(u.band)}` : ""}</option>`)
      .join("");
    $("words-picked").innerHTML = [...picked].map((w) => `<span class="chip" lang="en">${escapeHtml(w)}</span>`).join(" ");
    $("words-dialog").showModal();
    return;
  }
  const attempt = e.target.closest("[data-attempt]");
  if (attempt) openAttempt(attempt.dataset.attempt);
});

$("words-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const unit = units.find((u) => u.unit_id === $("words-unit").value);
  const body = {
    title: $("words-title").value.trim(),
    keywords: [...picked],
    free_prompt: $("words-prompt").value.trim(),
    summary: "Ôn những từ cả lớp hay bỏ: tự đặt câu với từng nhóm từ, rồi nói tự do.",
  };
  const r = await fetch(`/api/v1/teach/units/${encodeURIComponent($("words-unit").value)}/lessons`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (window.redirectToLoginIfExpired(r)) return;
  const d = await r.json().catch(() => ({}));
  if (!r.ok) {
    window.toast(errorText(d), "error");
    return;
  }
  location.href = `/teach/lessons/${encodeURIComponent(d.lesson_id)}`;
});

// ---------------------------------------------------------------- one attempt
function wordButtons() {
  return Object.keys(open.words)
    .map((i) => {
      const w = open.text[i];
      const st = open.words[i];
      const changed = st !== open.machine[i];
      return (
        `<button type="button" class="w ${st}${changed ? " teacher" : ""}" data-index="${i}" ` +
        `aria-label="${escapeHtml(w)}: ${STATUS_NAMES[st]}${changed ? ", giáo viên đã sửa" : ""}">${escapeHtml(w)}</button>`
      );
    })
    .join(" ");
}

async function openAttempt(id) {
  const r = await fetch(`/api/v1/teach/attempts/${encodeURIComponent(id)}`);
  if (window.redirectToLoginIfExpired(r)) return;
  const d = await r.json().catch(() => ({}));
  if (!r.ok) {
    window.toast(errorText(d), "error");
    return;
  }
  const res = d.result;
  const ov = d.override || {};
  open = { id, words: {}, machine: {}, text: {} };
  res.words.forEach((w) => {
    open.words[w.index] = w.teacher || w.status;
    open.machine[w.index] = w.status;
    open.text[w.index] = w.text;
  });
  const has = (k) => Object.prototype.hasOwnProperty.call(ov, k);
  const verdict = has("passed") ? (ov.passed ? "pass" : "fail") : "keep";
  const signals = (res.signals || [])
    .filter((s) => s.text)
    .map((s) => `<li>${s.met === true ? "✓" : s.met === false ? "✗" : "·"} ${escapeHtml(s.text)}</li>`)
    .join("");
  const found = (res.found || []).map((f) => escapeHtml(f.text)).join(", ");
  const missing = (res.missing || []).map((w) => escapeHtml(w)).join(", ");
  $("attempt-body").innerHTML =
    '<div class="sheet-head"><div>' +
    `<p class="eyebrow">${escapeHtml(d.lesson.title)}${d.step ? ` · ${escapeHtml(d.step.display_title)}` : ""}${d.round ? ` · lượt ${Number(d.round)}` : ""}</p>` +
    `<h2 id="attempt-h">Lượt luyện của <code>${escapeHtml(d.learner)}</code></h2>` +
    `<p class="muted">${escapeHtml(window.ui.localTime(d.created_at))} · máy nhận định: ${d.machine_passed ? "Đạt" : "Chưa đạt"}` +
    `${d.overridden_by ? ` · đã sửa bởi ${escapeHtml(d.overridden_by)}` : ""}</p></div>` +
    '<button type="button" class="small secondary" data-close="attempt-dialog">Đóng</button></div>' +
    (d.audio_url
      ? `<audio controls preload="metadata" src="${escapeHtml(d.audio_url)}"></audio>`
      : '<p class="muted">Bản ghi âm không còn.</p>') +
    (res.words.length
      ? '<p class="eyebrow">Từng từ của văn bản · bấm một từ để đổi nhận định</p>' +
        `<p class="read-text marked override-words" lang="en" id="override-words">${wordButtons()}</p>` +
        '<ul class="specimen-legend"><li><span class="dot heard" aria-hidden="true"></span>Máy nghe ra</li>' +
        '<li><span class="dot unsure" aria-hidden="true"></span>Chưa chắc</li>' +
        '<li><span class="dot missed" aria-hidden="true"></span>Máy chưa nghe ra</li>' +
        '<li><span class="teacher-key" aria-hidden="true"></span>Giáo viên đã sửa</li></ul>'
      : "") +
    (found ? `<p><b>Máy nghe thấy:</b> <span lang="en">${found}</span></p>` : "") +
    (missing ? `<p><b>Máy chưa nghe thấy:</b> <span lang="en">${missing}</span></p>` : "") +
    (signals ? `<ul class="signal-list plain">${signals}</ul>` : "") +
    (res.transcript
      ? `<details class="raw-transcript"><summary>Máy chép được</summary><p lang="en">${escapeHtml(res.transcript)}</p></details>`
      : "") +
    '<fieldset class="verdict-pick"><legend>Kết luận của bước</legend>' +
    `<label><input type="radio" name="verdict" value="keep"${verdict === "keep" ? " checked" : ""}> Giữ như máy (${d.machine_passed ? "Đạt" : "Chưa đạt"})</label>` +
    `<label><input type="radio" name="verdict" value="pass"${verdict === "pass" ? " checked" : ""}> Đạt</label>` +
    `<label><input type="radio" name="verdict" value="fail"${verdict === "fail" ? " checked" : ""}> Chưa đạt</label></fieldset>` +
    '<label for="override-note">Ghi chú cho sinh viên (không bắt buộc)</label>' +
    `<textarea id="override-note" maxlength="500" rows="2">${escapeHtml(ov.note || "")}</textarea>` +
    '<p class="field-hint">Sinh viên thấy «giáo viên đã xem lại» cùng ghi chú này. Mọi sửa đổi được ghi vào nhật ký kiểm toán.</p>' +
    '<div class="button-row"><button type="button" id="override-save">Lưu nhận định</button>' +
    '<button type="button" class="secondary" data-close="attempt-dialog">Huỷ</button></div>';
  $("attempt-dialog").showModal();
}

$("attempt-body").addEventListener("click", async (e) => {
  const word = e.target.closest("[data-index]");
  if (word && open) {
    const i = word.dataset.index;
    open.words[i] = NEXT_STATUS[open.words[i]];
    $("override-words").innerHTML = wordButtons();
    const again = $("override-words").querySelector(`[data-index="${CSS.escape(i)}"]`);
    if (again) again.focus();
    return;
  }
  if (!e.target.closest("#override-save") || !open) return;
  const words = {};
  Object.keys(open.words).forEach((i) => {
    if (open.words[i] !== open.machine[i]) words[i] = open.words[i];
  });
  const v = document.querySelector('input[name="verdict"]:checked').value;
  const body = { words, note: $("override-note").value.trim(), passed: v === "keep" ? null : v === "pass" };
  const r = await fetch(`/api/v1/teach/attempts/${encodeURIComponent(open.id)}/override`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (window.redirectToLoginIfExpired(r)) return;
  const d = await r.json().catch(() => ({}));
  if (!r.ok) {
    window.toast(errorText(d), "error");
    return;
  }
  $("attempt-dialog").close();
  window.toast("Đã lưu nhận định. Sinh viên sẽ thấy giáo viên đã xem lại lượt này.", "ok");
  load();
});

// Close buttons, including the ones drawn into a dialog after load.
document.addEventListener("click", (e) => {
  const b = e.target.closest("[data-close]");
  if (b) $(b.dataset.close).close();
});

load();
