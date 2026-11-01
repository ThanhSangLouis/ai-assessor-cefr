// Assessment submission: choose a task, record or pick a file, listen back, submit.
// See SPEC_WEB.md M2 and FR-39. Recording and upload live in recorder.js, shared
// with the practice screen, so both screens behave the same way.
const escapeHtml = window.escapeHtml;
const taskListEl = document.getElementById("task-list");
const taskIdEl = document.getElementById("task_id");
const promptEl = document.getElementById("chosen-prompt");

let chosenTask = null;
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
// A missing ffmpeg means recording in the browser is impossible. Which
// recogniser runs is the administrator's to see (tab Vận hành), not the learner's (D078).
fetch("/api/v1/health")
  .then((r) => r.json())
  .then((h) => {
    const d = h.scorable_duration_s || {};
    if (d.accepted_high) scorableMaxS = Number(d.accepted_high);
    recorder.enable(!!h.recording_enabled);
    // The countdown ends by starting the microphone, so it only makes sense
    // where recording in the page works.
    prepEl.hidden = !recorder.canRecordLive();
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
  return `
    <label class="task${i === 0 ? " chosen" : ""}">
      <input type="radio" name="task-choice" value="${escapeHtml(t.task_id)}"${i === 0 ? " checked" : ""}>
      <span class="chosen-mark" aria-hidden="true">✓ Đã chọn</span>
      <span class="task-band">${escapeHtml(t.band || "")}</span>
      <p class="task-prompt">${escapeHtml(t.prompt_text)}</p>
      <p class="task-meta"><span>${Number(t.min_seconds)}–${Number(t.max_seconds)} giây</span></p>
    </label>`;
}

// The chosen prompt sits right above the record button, so it is in view while
// the student answers it.
function chooseTask(task) {
  if (prepTimer) stopPrep("Đã đổi đề, thời gian chuẩn bị bắt đầu lại từ đầu khi bạn bấm.");
  chosenTask = task;
  taskIdEl.value = task.task_id;
  promptEl.innerHTML =
    `<p class="eyebrow">${escapeHtml(task.title)}</p>` +
    `<p class="prompt-text">${escapeHtml(task.prompt_text)}</p>` +
    `<p class="muted">Nói ${Number(task.min_seconds)}–${Number(task.max_seconds)} giây</p>` +
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

// D076: the prompts of one band, three at a time, drawn at random; "Đổi đề
// khác" draws three others. The band starts where the learner studies (their
// band path), else where their latest assessment put them, else the first band
// with prompts.
const BANDS = ["A1", "A2", "B1", "B2", "C1", "C2"];
const SHOWN = 3;
let allTasks = [];
let band = null;
let shown = [];

function draw(pinned) {
  const pool = allTasks.filter((t) => t.band === band);
  const rest = pool.filter((t) => !pinned || t.task_id !== pinned.task_id);
  for (let i = rest.length - 1; i > 0; i--) {
    const k = Math.floor(Math.random() * (i + 1));
    [rest[i], rest[k]] = [rest[k], rest[i]];
  }
  shown = (pinned ? [pinned, ...rest] : rest).slice(0, SHOWN);
  paintTasks();
}

function paintTasks() {
  const chips = BANDS.filter((b) => allTasks.some((t) => t.band === b))
    .map(
      (b) => `<label class="task-band-chip${b === band ? " on" : ""}"><input type="radio" name="task-band" value="${b}"${b === band ? " checked" : ""}>${b}</label>`,
    )
    .join("");
  const pool = allTasks.filter((t) => t.band === band).length;
  taskListEl.innerHTML =
    `<div class="task-band-bar"><div class="task-bands" role="radiogroup" aria-label="Band của đề">${chips}</div>` +
    (pool > SHOWN ? '<button type="button" class="secondary small" id="task-shuffle">Đổi đề khác</button>' : "") +
    "</div>" +
    '<div class="task-grid" role="radiogroup" aria-label="Danh sách đề bài">' +
    shown.map(taskCard).join("") +
    "</div>";
  const inputs = taskListEl.querySelectorAll('input[name="task-choice"]');
  const mark = (input) => {
    taskListEl.querySelectorAll(".task").forEach((el) => el.classList.remove("chosen"));
    input.closest(".task").classList.add("chosen");
  };
  inputs.forEach((input, i) => {
    input.addEventListener("change", () => {
      mark(input);
      chooseTask(shown[i]);
    });
  });
  taskListEl.querySelectorAll('input[name="task-band"]').forEach((r) =>
    r.addEventListener("change", () => {
      band = r.value;
      draw();
    }),
  );
  const shuffle = document.getElementById("task-shuffle");
  if (shuffle) shuffle.addEventListener("click", () => draw());
  if (inputs.length) {
    inputs[0].checked = true;
    mark(inputs[0]);
    chooseTask(shown[0]);
  }
}

async function startBand() {
  try {
    const r = await fetch("/api/v1/learn/bands");
    if (!r.ok) return null;
    const d = await r.json();
    return (d.plan && d.plan.goal && d.plan.goal.band_from) || d.suggested_from;
  } catch (e) {
    return null;
  }
}

Promise.all([
  fetch("/api/v1/tasks").then((r) => (window.redirectToLoginIfExpired(r) ? null : r.json())),
  startBand(),
])
  .then(([tasks, from]) => {
    if (!tasks) return;
    window.clearBusy(taskListEl);
    allTasks = tasks.filter((t) => t.band);
    if (!allTasks.length) {
      taskListEl.innerHTML =
        '<div class="empty-state"><div class="empty-mark" aria-hidden="true">◇</div>' +
        "<h2>Chưa có đề bài nào</h2>" +
        "<p>Trung tâm chưa mở đề đánh giá. Hãy quay lại sau.</p></div>";
      return;
    }
    // `?task=` opens this page on that task (a reminder or a link points there).
    const wanted = allTasks.find((t) => t.task_id === new URLSearchParams(window.location.search).get("task"));
    band = (wanted && wanted.band) || (BANDS.includes(from) && allTasks.some((t) => t.band === from) ? from : null) || allTasks[0].band;
    draw(wanted);
  })
  .catch(() => {
    window.clearBusy(taskListEl);
    taskListEl.innerHTML = '<p class="error">Không tải được danh sách đề bài.</p>';
  });

// ---------------------------------------------------------------- submit
async function submit(audio, name) {
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
