// Assessment submission: choose a task, record or pick a file, listen back, submit.
// See SPEC_WEB.md M2 and FR-39. Recording and upload live in recorder.js, shared
// with the practice screen, so both screens behave the same way.
const escapeHtml = window.escapeHtml;
const taskListEl = document.getElementById("task-list");
const taskIdEl = document.getElementById("task_id");
const promptEl = document.getElementById("chosen-prompt");

let chosenTask = null;
let maySubmit = true;
// How long a recording the scoring model can take in one pass. Read from the
// server, which reads it from the model artifact, so this number cannot drift
// away from the rule applied after submission.
let scorableMaxS = null;
const WINDOW_TARGET_S = 45;
// The preparation countdown, declared before the recorder because the
// recorder reports its first state while it is being set up.
let prepTimer = null;

const recorder = window.setUpRecorder({
  minSeconds: () => (chosenTask ? chosenTask.min_seconds : 20),
  maxSeconds: () => (chosenTask ? chosenTask.max_seconds : 300),
  onTake: tooLongToScore,
  onSubmit: submit,
  // Recording started by hand, or a file chosen: the countdown has no job left.
  onChange: (state) => {
    if (state !== "idle" && prepTimer) stopPrep();
  },
});

// ---------------------------------------------------------------- preparation
// Thirty seconds to read the prompt and plan, then recording starts by itself
// (D028), as in the survey protocol and in a test room. Optional and easy to
// leave: the record button works at any moment and ends the countdown. The
// status line speaks at the start, at ten seconds and at the end -- not every
// second, which would drown a screen reader.
const prepEl = document.getElementById("prep");
const prepSeconds = Number(document.getElementById("f").dataset.prepSeconds) || 30;
const prepLeftEl = document.getElementById("prep-left");
const prepRing = document.getElementById("prep-ring");
const prepTitle = document.getElementById("prep-title");
const prepStart = document.getElementById("prep-start");
const prepSkip = document.getElementById("prep-skip");
const prepCancel = document.getElementById("prep-cancel");
const prepStatus = document.getElementById("prep-status");
let prepEnds = 0;
let prepWarned = false;

function paintPrep(left) {
  prepLeftEl.textContent = String(left);
  prepRing.style.setProperty("--p", String(1 - left / prepSeconds));
}

function setPrepRunning(running) {
  prepEl.dataset.state = running ? "running" : "ready";
  prepStart.hidden = running;
  prepSkip.hidden = !running;
  prepCancel.hidden = !running;
  prepTitle.textContent = running ? "Đang chuẩn bị" : `Chuẩn bị ${prepSeconds} giây như phòng thi`;
}

function stopPrep(message) {
  clearInterval(prepTimer);
  prepTimer = null;
  setPrepRunning(false);
  paintPrep(prepSeconds);
  if (message) prepStatus.textContent = message;
}

function finishPrep() {
  stopPrep();
  const started = recorder.startNow();
  prepStatus.textContent = started
    ? "Hết giờ chuẩn bị. Đang ghi âm, hãy bắt đầu nói."
    : "Hết giờ chuẩn bị. Bấm nút ghi âm để bắt đầu nói.";
  if (!started) window.toast("Hết giờ chuẩn bị. Bấm nút ghi âm để bắt đầu.", "info");
}

function tickPrep() {
  const left = Math.max(0, Math.ceil((prepEnds - Date.now()) / 1000));
  paintPrep(left);
  if (left <= 10 && !prepWarned) {
    prepWarned = true;
    prepStatus.textContent = "Còn 10 giây chuẩn bị.";
  }
  if (left <= 0) finishPrep();
}

prepStart.addEventListener("click", () => {
  prepEnds = Date.now() + prepSeconds * 1000;
  prepWarned = false;
  setPrepRunning(true);
  paintPrep(prepSeconds);
  prepStatus.textContent = `Bắt đầu ${prepSeconds} giây chuẩn bị.`;
  prepTimer = setInterval(tickPrep, 250);
});
prepSkip.addEventListener("click", finishPrep);
prepCancel.addEventListener("click", () => stopPrep("Đã huỷ thời gian chuẩn bị."));

// ---------------------------------------------------------------- health
// Two separate warnings: a fake recogniser means the scores are meaningless; a
// missing ffmpeg means recording in the browser is impossible.
fetch("/api/v1/health")
  .then((r) => r.json())
  .then((h) => {
    if (!h.asr_is_real) document.getElementById("fake-asr-warning").hidden = false;
    const d = h.scorable_duration_s || {};
    if (d.accepted_high) scorableMaxS = Number(d.accepted_high);
    recorder.enable(!!h.recording_enabled);
    // The countdown ends by starting the microphone, so it only makes sense
    // where recording in the page works.
    prepEl.hidden = !(maySubmit && recorder.canRecordLive());
  })
  .catch(() => recorder.enable(false));

// Tell the student what will happen to a long recording BEFORE it is
// submitted: past the model's range it is cut into windows, scored per window,
// and always goes to a teacher. Shown under the player in the listen-back step.
function tooLongToScore(take) {
  if (!scorableMaxS || !take.seconds || take.seconds <= scorableMaxS) return "";
  const windows = Math.max(2, Math.round(take.seconds / WINDOW_TARGET_S));
  return (
    `Bài ${take.seconds.toFixed(0)} giây: mô hình chỉ chấm trực tiếp bài tới khoảng ` +
    `${scorableMaxS.toFixed(0)} giây, nên bài này sẽ được cắt thành khoảng ${windows} ` +
    "đoạn và luôn chuyển giảng viên duyệt."
  );
}

// ---------------------------------------------------------------- tasks
// A real radio group: arrow keys move between prompts and a screen reader
// announces which one is selected.
function taskCard(t, i) {
  const windowed = t.windowed ? '<span class="badge">Bài dài, luôn qua giảng viên</span>' : "";
  return `
    <label class="task${i === 0 ? " chosen" : ""}">
      <input type="radio" name="task-choice" value="${escapeHtml(t.task_id)}"${i === 0 ? " checked" : ""}>
      <span class="chosen-mark" aria-hidden="true">✓ Đã chọn</span>
      <h3>${escapeHtml(t.task_id)} — ${escapeHtml(t.title)}</h3>
      <p class="task-prompt">${escapeHtml(t.prompt_text)}</p>
      <p class="task-meta">
        <span>${Number(t.min_seconds)}–${Number(t.max_seconds)} giây</span>
        ${windowed}
      </p>
    </label>`;
}

// The chosen prompt sits right above the record button, so it is in view while
// the student answers it.
function chooseTask(task) {
  if (prepTimer) stopPrep("Đã đổi đề, thời gian chuẩn bị bắt đầu lại từ đầu khi bạn bấm.");
  chosenTask = task;
  taskIdEl.value = task.task_id;
  promptEl.innerHTML =
    `<p class="eyebrow">Đề ${escapeHtml(task.task_id)} · ${escapeHtml(task.title)}</p>` +
    `<p class="prompt-text">${escapeHtml(task.prompt_text)}</p>` +
    `<p class="muted">Nói ${Number(task.min_seconds)}–${Number(task.max_seconds)} giây · ` +
    `phiên bản đề <code>${escapeHtml(task.prompt_version)}</code></p>` +
    '<p class="muted small" id="price-note" hidden></p>';
  recorder.repaint();
  showPrice(task);
}

// D057: on a metered deployment, what this task can cost at most, before the
// learner records. Nothing on a school deployment.
async function showPrice(task) {
  const r = await fetch(`/api/v1/me/credits/quote?seconds=${Number(task.max_seconds)}`);
  if (!r.ok) return;
  const q = await r.json();
  const note = document.getElementById("price-note");
  if (!q.metering || !note || chosenTask !== task) return;
  const left = q.free_runs_left + q.wallet_runs;
  const n = (x) => Number(x).toLocaleString("vi-VN", { maximumFractionDigits: 3 });
  note.innerHTML =
    `Bài này tối đa <b>${n(q.runs)} lượt</b> (${n(q.idpoint)} IDPoint), tính theo thời lượng thật; ` +
    `bạn còn ${n(left)} lượt. <a href="/credits">Lượt của tôi</a>`;
  note.hidden = false;
}

fetch("/api/v1/tasks")
  .then((r) => (window.redirectToLoginIfExpired(r) ? null : r.json()))
  .then((tasks) => {
    if (!tasks) return;
    window.clearBusy(taskListEl);
    if (!tasks.length) {
      taskListEl.innerHTML =
        '<div class="empty-state"><div class="empty-mark" aria-hidden="true">◇</div>' +
        "<h2>Chưa có đề bài nào</h2>" +
        "<p>Giảng viên chưa mở đề cho lớp này. Hãy quay lại sau, hoặc hỏi giảng viên phụ trách.</p></div>";
      return;
    }
    taskListEl.innerHTML =
      '<div class="task-grid" role="radiogroup" aria-label="Danh sách đề bài">' +
      tasks.map(taskCard).join("") +
      "</div>";
    const inputs = taskListEl.querySelectorAll('input[name="task-choice"]');
    const mark = (input) => {
      taskListEl.querySelectorAll(".task").forEach((el) => el.classList.remove("chosen"));
      input.closest(".task").classList.add("chosen");
    };
    inputs.forEach((input, i) => {
      input.addEventListener("change", () => {
        mark(input);
        chooseTask(tasks[i]);
      });
    });
    // D054: "Làm bài" on an assignment opens this page on the assigned task.
    const wanted = new URLSearchParams(window.location.search).get("task");
    const first = Math.max(0, tasks.findIndex((t) => t.task_id === wanted));
    inputs[first].checked = true;
    mark(inputs[first]);
    chooseTask(tasks[first]);
  })
  .catch(() => {
    window.clearBusy(taskListEl);
    taskListEl.innerHTML = '<p class="error">Không tải được danh sách đề bài.</p>';
  });

// ---------------------------------------------------------------- consent
// The server refuses a submission without consent to store recordings, and
// rightly so. Saying it at page load, before a minute of recording, is the
// courtesy layer; the protection itself stays on the server.
fetch("/api/v1/me/consent")
  .then((r) => (r.ok ? r.json() : null))
  .then((state) => {
    if (!state || state.may_submit) return;
    maySubmit = false;
    // "Never signed" and "signed but refused audio storage" are different: the
    // second is a deliberate choice and must not be worded as if forgotten.
    const signedButRefused = state.signed && !state.audio_storage_allowed;
    const box = document.getElementById("consent-gate");
    box.innerHTML = signedButRefused
      ? "<b>Bạn đã ký đồng thuận nhưng không cho phép lưu bản ghi âm.</b> " +
        "Hệ thống vì thế không nhận bài nói. Nếu đổi ý, " +
        '<a href="/consent">vào trang đồng thuận</a> và tích mục cho phép lưu bản ghi.'
      : "<b>Chưa nộp bài được: bạn chưa ký đồng thuận.</b> " +
        "Bản ghi giọng nói là dữ liệu cá nhân, nên hệ thống không lưu gì trước khi bạn đồng ý. " +
        '<a href="/consent">Ký đồng thuận ở đây</a> rồi quay lại; bạn rút lại lúc nào cũng được.';
    box.hidden = false;
    prepEl.hidden = true;
    recorder.block("Cần ký đồng thuận trước khi ghi âm và nộp bài.");
  })
  // A transient network error is no reason to block; the server still decides.
  .catch(() => {});

// ---------------------------------------------------------------- submit
async function submit(audio, name) {
  if (!maySubmit) {
    window.toast("Cần ký đồng thuận trước khi nộp bài.", "error");
    return;
  }
  const body = new FormData();
  body.append("task_id", taskIdEl.value);
  body.append("audio", audio, name);
  try {
    const r = await fetch("/api/v1/responses", { method: "POST", body });
    if (window.redirectToLoginIfExpired(r)) return;
    const d = await r.json();
    if (!r.ok) {
      const detail = typeof d.detail === "string" ? d.detail : JSON.stringify(d.detail);
      window.toast(`Không nộp được bài: ${detail || "lỗi không rõ"}`, "error", { sticky: true });
      return;
    }
    recorder.done();
    window.toast("Đã nhận bài, đang chuyển sang màn hình theo dõi…", "ok");
    location.href = `/progress/${d.response_id}`;
  } catch (err) {
    window.toast("Không kết nối được máy chủ. Bài chưa được gửi đi.", "error", { sticky: true });
  }
}
