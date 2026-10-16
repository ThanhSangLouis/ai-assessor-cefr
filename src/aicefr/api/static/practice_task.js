// One practice task (D023): missions shown BEFORE speaking, record, listen back,
// submit, wait, result.
//
// Missions and word lists appear before the record button, like a short lesson:
// the learner knows exactly what the machine will count. A mission revealed only
// after submitting would be a disguised test, not practice. Recording itself is
// the shared recorder (recorder.js), the same one the assessment screen uses.
const escapeHtml = window.escapeHtml;
const root = document.getElementById("practice-task");
const TASK_ID = root.dataset.taskId;
const form = document.getElementById("practice-form");
const brief = document.getElementById("practice-brief");
const referenceEl = document.getElementById("practice-reference");
const waitEl = document.getElementById("practice-wait");

let task = null;

const KIND_ICON = {
  speak_seconds: "⏱",
  max_pause: "⏸",
  use_words: "✎",
  unique_words: "✎",
  past_verbs: "✎",
  conditionals: "✎",
  read_aloud: "◉",
};

function goalLabel(goal) {
  const target = Number(goal.target);
  const shown = Number.isFinite(target) ? String(target) : "";
  const labels = {
    speak_seconds: `Nói ít nhất ${shown} giây`,
    max_pause: `Giữ khoảng dừng không quá ${shown} giây`,
    use_words: "Dùng các từ gợi ý",
    unique_words: `Dùng ít nhất ${shown} từ khác nhau`,
    past_verbs: `Dùng ít nhất ${shown} động từ quá khứ`,
    conditionals: `Dùng ít nhất ${shown} câu điều kiện`,
    read_aloud: "Đọc to đoạn văn mẫu",
  };
  return labels[goal.kind] || "Hoàn thành mục tiêu luyện tập";
}

const recorder = window.setUpRecorder({
  minSeconds: () => (task ? task.min_seconds : 0),
  maxSeconds: () => (task ? task.max_seconds : 300),
  onSubmit: submit,
});

function missionItem(m) {
  const chips =
    m.words && m.words.length
      ? `<ul class="word-chips">${m.words.map((w) => `<li>${escapeHtml(w)}</li>`).join("")}</ul>`
      : "";
  return (
    `<li class="mission todo"><span class="mission-icon" aria-hidden="true">${
      KIND_ICON[m.kind] || "•"
    }</span><div><p class="mission-label">${escapeHtml(m.label)}</p>${chips}</div></li>`
  );
}

function historyCard(history) {
  if (!history.length) return "";
  const rows = history
    .map((a) => {
      const state = a.result
        ? `Đã xử lý · ${a.result.status}`
        : ["NOT_EVALUATED", "LEGACY"].includes(a.status)
          ? "Bản ghi chưa dùng được"
          : "Đang xử lý";
      return (
        `<li><a href="/practice/results/${encodeURIComponent(a.attempt_id)}">` +
        `${escapeHtml(window.ui.localTime(a.created_at))}</a>` +
        ` <span class="muted">· ${escapeHtml(state)}</span></li>`
      );
    })
    .join("");
  return `<h2>Các lần đã thử</h2><ul class="review-list">${rows}</ul>`;
}

function render(t) {
  window.clearBusy(root);
  root.innerHTML = `
    <div class="page-head">
      <p class="task-tags">
        <span class="badge">${escapeHtml(t.criterion_name)}</span>
        <span class="badge">Mức ${escapeHtml(t.band)}</span>
      </p>
      <h1>${escapeHtml(t.title)}</h1>
      <p class="lede">${escapeHtml(t.prompt_text)}</p>
    </div>`;
  const tips = t.tips.length
    ? `<details class="tips"><summary>Mẹo cho lần nói này</summary><ul>${t.tips
        .map((x) => `<li>${escapeHtml(x)}</li>`)
        .join("")}</ul></details>`
    : "";
  brief.innerHTML = `
    <h2 id="missions-h">Mục tiêu của lần luyện này</h2>
    <ul class="mission-list">${t.missions.map(missionItem).join("")}</ul>
    <p class="muted">Máy đếm trên bản chép tự động của bản ghi, rồi chỉ ra chỗ làm căn cứ
      cho từng mục tiêu. Bài luyện không chấm điểm.</p>
    ${tips}`;
  referenceEl.innerHTML = t.reference_text
    ? `<div class="reference-card"><p class="eyebrow">Đọc to đoạn này</p>` +
      `<p class="reference-text" lang="en">${escapeHtml(t.reference_text)}</p></div>`
    : "";
  document.title = t.title + " · Luyện tập";
  const history = document.getElementById("practice-history");
  history.innerHTML = historyCard(t.history);
  history.hidden = !t.history.length;
  brief.hidden = false;
  form.hidden = false;
  recorder.repaint();
}

Promise.all([
  fetch(`/api/v1/practice/missions/${encodeURIComponent(TASK_ID)}`).then((r) => {
    if (window.redirectToLoginIfExpired(r)) throw new Error("SESSION_REQUIRED");
    if (!r.ok) throw new Error(String(r.status));
    return r.json();
  }),
  fetch("/api/v1/practice/attempts?limit=100").then((r) => (r.ok ? r.json() : { attempts: [] })),
])
  .then(([mission, history]) => {
    task = {
      ...mission,
      min_seconds: 0,
      max_seconds: 300,
      criterion_name: window.ui.practiceName(mission.criterion),
      band: mission.target_band,
      prompt_text: mission.prompt,
      missions: (mission.goals || []).map((goal) => ({
        kind: goal.kind,
        label: goalLabel(goal),
        words: goal.words || [],
      })),
      reference_text: (mission.goals || []).find((goal) => goal.reference_text)?.reference_text || "",
      tips: [],
      history: (history.attempts || [])
        .filter((attempt) => attempt.mission && attempt.mission.mission_id === mission.mission_id)
        .map((attempt) => ({
          attempt_id: attempt.attempt_id,
          status: attempt.state,
          result: attempt.result,
          created_at: attempt.created_at,
        })),
    };
    render(task);
  })
  .catch(() => {
    window.clearBusy(root);
    root.innerHTML =
      '<div class="empty-state"><div class="empty-mark" aria-hidden="true">◇</div>' +
      "<h2>Không tìm thấy nhiệm vụ này</h2>" +
      '<p><a href="/practice">Quay lại trang luyện tập</a> để chọn nhiệm vụ khác.</p></div>';
  });

// ---------------------------------------------------------------- consent, health
fetch("/api/v1/me/consent")
  .then((r) => (r.ok ? r.json() : null))
  .then((c) => {
    if (!c || c.may_submit) return;
    const gate = document.getElementById("consent-gate");
    gate.innerHTML =
      "<b>Chưa có đồng thuận lưu bản ghi.</b> Bài luyện tập cũng là bản ghi giọng nói của bạn. " +
      '<a href="/consent">Ký đồng thuận</a> rồi quay lại.';
    gate.hidden = false;
    recorder.block("Cần ký đồng thuận trước khi ghi âm.");
  })
  .catch(() => {});

if (document.body.dataset.asrIsReal !== "true") {
  document.getElementById("fake-asr-warning").hidden = false;
}
recorder.enable(document.body.dataset.recordingEnabled === "true");

// ---------------------------------------------------------------- submit + wait
const POLL_MS = 1500;
const POLL_LIMIT_MS = 5 * 60 * 1000;

function waitFor(responseId) {
  const started = Date.now();
  const result = `/practice/results/${encodeURIComponent(responseId)}`;
  waitEl.innerHTML =
    '<div class="notice notice-info"><b>Đang xử lý bản ghi…</b> Nhận dạng giọng nói rồi đếm ' +
    "từng mục tiêu. Trang tự chuyển sang kết quả khi xong.</div>";
  (function poll() {
    fetch(`/api/v1/practice/attempts/${encodeURIComponent(responseId)}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((s) => {
        if (s && (s.result || ["NOT_EVALUATED", "LEGACY"].includes(s.state))) {
          location.href = result;
        } else if (Date.now() - started > POLL_LIMIT_MS) {
          waitEl.innerHTML =
            '<div class="notice notice-warn">Xử lý lâu hơn bình thường. ' +
            `<a href="${result}">Mở trang kết quả</a> sau ít phút.</div>`;
        } else {
          setTimeout(poll, POLL_MS);
        }
      })
      .catch(() => setTimeout(poll, POLL_MS * 2));
  })();
}

async function submit(audio, name) {
  const body = new FormData();
  body.append("audio", audio, name);
  body.append("mission_id", task.mission_id);
  body.append("prompt_version", task.prompt_version);
  body.append("purpose", "PRACTICE");
  body.append("idempotency_key", crypto.randomUUID());
  try {
    const r = await fetch("/api/v1/practice/attempts", { method: "POST", body });
    if (window.redirectToLoginIfExpired(r)) return;
    const d = await r.json();
    if (!r.ok) {
      window.toast(typeof d.detail === "string" ? d.detail : "Nộp không thành công.", "error", {
        sticky: true,
      });
      return;
    }
    recorder.done();
    waitFor(d.attempt_id);
  } catch (err) {
    window.toast("Mất kết nối khi nộp. Bản ghi vẫn còn, hãy thử lại.", "error", { sticky: true });
  }
}
