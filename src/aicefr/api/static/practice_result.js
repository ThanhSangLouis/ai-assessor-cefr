// Result of one practice attempt (D023).
//
// The screen follows the questions a learner actually asks: "am I done", "what
// should I fix first", "what is the machine basing this on", then "what next".
// No score and no band: every mission is a count backed by places in the
// recording, and clicking one plays the recording from that second.
const escapeHtml = window.escapeHtml;
const root = document.getElementById("practice-result");
const ID = root.dataset.responseId;

const REASON_TEXT = {
  AUDIO_TOO_SHORT: "Bản ghi quá ngắn. Hãy nói lâu hơn.",
  AUDIO_TOO_LONG: "Bản ghi dài hơn mức cho phép. Hãy nói gọn hơn.",
  AUDIO_TOO_LARGE: "File quá lớn.",
  AUDIO_UNSUPPORTED: "Không đọc được định dạng file này.",
  HIGH_SILENCE_RATIO: "Bản ghi có nhiều khoảng lặng. Hãy thu ở nơi yên tĩnh và nói liên tục hơn.",
  CLIPPING_DETECTED: "Âm thu quá to nên bị méo. Hãy để micro xa miệng hơn.",
  LOW_SNR: "Tiếng ồn nền lấn át giọng nói. Hãy thu ở nơi yên tĩnh hơn.",
  ASR_FAILED: "Hệ thống không nhận dạng được bản ghi này.",
  ASR_EMPTY_TRANSCRIPT: "Không nghe được lời nói nào trong bản ghi.",
  ASR_HALLUCINATION: "Máy chép ra một đoạn lặp bất thường và đã cắt bỏ đoạn đó trước khi đếm.",
  LANGUAGE_NOT_ENGLISH:
    "Bản ghi có vẻ không phải tiếng Anh nên máy không đếm được. Hãy nói lại bằng tiếng Anh.",
  PROCESSING_INTERRUPTED: "Quá trình xử lý bị gián đoạn. Hãy nộp lại.",
  FEATURE_NOT_COMPUTABLE: "Không đo được mục này trên bản ghi.",
  TOO_FEW_WORDS: "Bản ghi có quá ít từ để đo.",
};

function reasonText(code) {
  return REASON_TEXT[code] || `${window.ui.reasonName(code)}.`;
}

const clock = (seconds) => (seconds === null || seconds === undefined ? "" : window.ui.mmss(seconds));

function fmt(kind, v) {
  if (v === null || v === undefined) return "—";
  if (kind === "speak_seconds" || kind === "max_pause") {
    return `${v.toFixed(1).replace(".", ",")} giây`;
  }
  if (kind === "read_aloud") return `${Math.round(v * 100)}%`;
  return String(Math.round(v));
}

function hitChip(h) {
  const time = h.start_s === null || h.start_s === undefined ? "" : clock(h.start_s);
  if (!time) return `<li class="hit">${escapeHtml(h.text)}</li>`;
  return (
    `<li class="hit"><button type="button" class="hit-seek" data-seconds="${Number(h.start_s)}"` +
    ` aria-label="${escapeHtml(h.text)}, nghe từ ${time}">${escapeHtml(h.text)}` +
    ` <span class="hit-time">${time}</span></button></li>`
  );
}

function checkItem(c) {
  const state = c.met === true ? "met" : c.met === false ? "unmet" : "unknown";
  const icon = state === "met" ? "✓" : state === "unmet" ? "✗" : "–";
  const stateText =
    state === "met" ? "Hoàn thành" : state === "unmet" ? "Chưa hoàn thành" : "Chưa đo được";
  const prev =
    c.previous === null || c.previous === undefined
      ? ""
      : ` <span class="muted">· lần trước ${escapeHtml(fmt(c.kind, c.previous))}</span>`;
  const why = c.reason ? `<p class="muted">${escapeHtml(reasonText(c.reason))}</p>` : "";
  const hitsLabel = c.kind === "read_aloud" ? "Từ máy chưa nghe ra" : "Căn cứ trong bản ghi";
  const hits = c.hits && c.hits.length
    ? `<p class="hits-label">${hitsLabel}</p><ul class="hits">${c.hits.map(hitChip).join("")}</ul>`
    : "";
  return `
    <li class="mission ${state}">
      <span class="mission-icon" aria-hidden="true">${icon}</span>
      <div>
        <p class="mission-label">${escapeHtml(c.label)}</p>
        <p class="mission-measure"><span class="visually-hidden">${stateText}. </span>
          ${escapeHtml(c.measured_text)}${prev}</p>
        ${why}${hits}
      </div>
    </li>`;
}

function banner(d) {
  if (d.status === "REJECTED" || d.status === "FAILED") {
    const items = d.reasons.map((r) => `<li>${escapeHtml(reasonText(r))}</li>`).join("");
    return (
      '<div class="notice notice-danger practice-banner"><b>Bản ghi chưa dùng được.</b>' +
      `<ul>${items}</ul>Lần này không tính vào mục tiêu ngày. Hãy thử lại.</div>`
    );
  }
  const r = d.result;
  if (!r) return '<div class="notice">Chưa có kết quả cho lần luyện này.</div>';
  if (r.completed === true) {
    return (
      '<div class="notice notice-ok practice-banner"><b>Hoàn thành nhiệm vụ.</b> ' +
      `${Number(r.met_count)}/${Number(r.total)} mục tiêu.</div>`
    );
  }
  if (r.completed === false) {
    return (
      '<div class="notice notice-warn practice-banner"><b>Chưa hoàn thành.</b> ' +
      `${Number(r.met_count)}/${Number(r.total)} mục tiêu. Luyện lại ngay hoặc để vài ngày sau, ` +
      "nhiệm vụ này sẽ nằm trong mục Ôn lại.</div>"
    );
  }
  return (
    '<div class="notice notice-info practice-banner"><b>Chưa đo được đủ mục tiêu.</b> ' +
    "Xem lý do ở từng mục bên dưới.</div>"
  );
}

function qcWarnings(d) {
  if (d.status !== "COMPLETED" || !d.reasons.length) return "";
  const items = d.reasons.map((r) => `<li>${escapeHtml(reasonText(r))}</li>`).join("");
  return `<div class="notice notice-warn"><b>Lưu ý về bản ghi.</b><ul>${items}</ul></div>`;
}

// The next step stays on screen at the bottom while the learner reads the
// missions: "practise the next one" should never be a scroll away.
function nextActions(d) {
  const retry = `<a class="button secondary" href="/practice/${encodeURIComponent(
    d.task.task_id
  )}">Thử lại nhiệm vụ này</a>`;
  const n = d.next;
  const next =
    n && n.task_id !== d.task.task_id
      ? `<a class="button" href="/practice/${encodeURIComponent(n.task_id)}">` +
        `Luyện tiếp: ${escapeHtml(n.title)}</a>`
      : "";
  return (
    `<div class="action-bar">${next}${retry}<span class="spacer"></span>` +
    '<a class="button secondary" href="/practice">Về trang luyện tập</a></div>'
  );
}

function nextReason(d) {
  const n = d.next;
  if (!n || n.task_id === d.task.task_id) return "";
  return `<p class="muted next-reason"><b>Vì sao gợi ý nhiệm vụ tiếp theo:</b> ${escapeHtml(n.reason)}</p>`;
}

const CAVEAT =
  '<div class="notice practice-caveat"><b>Máy đếm trên bản chép tự động.</b> Bộ nhận dạng có ' +
  "thể bỏ sót hoặc chép sai từ, nên “chưa nghe ra” có thể là lỗi của máy chứ không phải của " +
  "bạn. Hãy nghe lại bản ghi để tự kiểm. Mục tiêu ngữ pháp chỉ xem bạn <b>có dùng</b> cấu trúc " +
  "hay không, không chấm đúng sai.</div>";

function today(d) {
  const t = d.daily;
  const goal = t.goal_met
    ? "Đã đạt mục tiêu hôm nay."
    : `Hôm nay ${Number(t.today)}/${Number(t.goal)} lần, còn ${t.goal - t.today} lần nữa.`;
  return `<p class="practice-day"><b>${goal}</b> Chuỗi ${Number(t.streak)} ngày.</p>`;
}

function render(d) {
  window.clearBusy(root);
  const r = d.result;
  const takeawayBox =
    r && r.takeaway
      ? `<div class="takeaway"><p class="eyebrow">Điều nên làm tiếp</p><p>${escapeHtml(r.takeaway)}</p></div>`
      : "";
  const checks = r
    ? `<section class="card" aria-labelledby="checks-h"><h2 id="checks-h">Từng mục tiêu</h2>` +
      `<ul class="mission-list">${r.checks.map(checkItem).join("")}</ul>` +
      `<p class="muted">Bộ luật đếm <code>${escapeHtml(r.rules_version)}</code>.</p></section>`
    : "";
  root.innerHTML = `
    <div class="page-head">
      <p class="task-tags">
        <span class="badge">${escapeHtml(d.task.criterion_name)}</span>
        <span class="badge">Mức ${escapeHtml(d.task.band)}</span>
      </p>
      <h1>${escapeHtml(d.task.title)}</h1>
      <p class="lede">Lần luyện lúc ${escapeHtml(window.ui.localTime(d.created_at))}.</p>
    </div>
    ${banner(d)}
    ${takeawayBox}
    ${qcWarnings(d)}
    <section class="card" aria-labelledby="audio-h">
      <h2 id="audio-h">Nghe lại bản ghi</h2>
      <audio id="player" controls preload="metadata" src="/api/v1/responses/${encodeURIComponent(d.response_id)}/audio"></audio>
    </section>
    ${checks}
    ${CAVEAT}
    ${today(d)}
    ${nextReason(d)}
    ${nextActions(d)}`;
  document.title = "Kết quả: " + d.task.title;
  const player = document.getElementById("player");
  root.querySelectorAll(".hit-seek").forEach((b) =>
    b.addEventListener("click", () => {
      player.currentTime = Math.max(0, parseFloat(b.dataset.seconds) - 0.3);
      player.play().catch(() => {});
    })
  );
  if (d.daily.goal_met && d.daily.today === d.daily.goal && d.status === "COMPLETED") {
    window.toast("Đã đạt mục tiêu luyện tập hôm nay.", "ok");
  }
}

// Processing normally takes seconds; past this, say so instead of spinning on.
const POLL_LIMIT_MS = 5 * 60 * 1000;
const startedAt = Date.now();

function load() {
  fetch(`/api/v1/practice/attempts/${encodeURIComponent(ID)}`)
    .then((r) => {
      if (window.redirectToLoginIfExpired(r)) return null;
      if (r.status === 404) throw new Error("404");
      return r.json();
    })
    .then((d) => {
      if (!d) return;
      if (d.is_pending) {
        if (Date.now() - startedAt > POLL_LIMIT_MS) {
          root.innerHTML =
            '<div class="notice notice-warn"><b>Xử lý lâu hơn bình thường.</b> ' +
            "Hãy tải lại trang này sau ít phút.</div>";
          return;
        }
        root.innerHTML =
          '<div class="notice notice-info"><b>Đang xử lý bản ghi…</b> Trang tự cập nhật khi xong.</div>';
        setTimeout(load, 2000);
        return;
      }
      render(d);
    })
    .catch(() => {
      window.clearBusy(root);
      root.innerHTML =
        '<div class="empty-state"><div class="empty-mark" aria-hidden="true">◇</div>' +
        "<h2>Không tìm thấy lần luyện này</h2>" +
        '<p><a href="/practice">Quay lại trang luyện tập</a>.</p></div>';
    });
}

load();
