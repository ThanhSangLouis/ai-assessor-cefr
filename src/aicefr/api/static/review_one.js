// Single-response review screen. See docs/web/SPEC_WEB.md section M6.
//
// SDD R-10 sets a target of under 3 minutes of average review time per
// response, so everything has to fit on ONE screen and have keyboard shortcuts,
// rather than forcing the teacher to scroll back and forth between the audio,
// the transcript and the input fields. The player is sticky for the same
// reason: scrolling back up to press play burns that budget.
const ID = document.getElementById("td").dataset.responseId;
const player = document.getElementById("phat");
const machineEl = document.getElementById("machine-score");
const decisionEl = document.getElementById("decision");
const historyEl = document.getElementById("history");
const transcriptEl = document.getElementById("transcript");
const warningEl = document.getElementById("lock-warning");

const evidencePanel = document.getElementById("evidence-panel");
const escapeHtml = window.escapeHtml;
const mmss = window.ui.mmss;
const CRITERION_NAMES = window.ui.CRITERION_NAMES;
let evidenceMarks = [];
let evidenceIndex = -1;
let hasLock = false;

// Take the lock before showing the edit fields. Without the lock the response
// can still be read, but the inputs stay disabled, so two teachers cannot
// overwrite each other's decision.
async function acquireLock() {
  const r = await fetch(`/api/v1/review/${ID}/lock`, { method: "POST" });
  if (window.redirectToLoginIfExpired(r)) return false;
  if (r.status === 409) {
    const d = await r.json();
    warningEl.innerHTML = `<div class="notice notice-danger"><b>${escapeHtml(d.detail)}.</b>
      Ô nhập bị khóa để hai người không ghi đè quyết định của nhau.</div>`;
    window.toast("Bài này đang được người khác duyệt. Chỉ xem được, không sửa được.", "warn");
    return false;
  }
  return r.ok;
}

async function load() {
  hasLock = await acquireLock();

  const r = await fetch(`/api/v1/responses/${ID}`);
  if (window.redirectToLoginIfExpired(r)) return;
  window.clearBusy(machineEl);
  window.clearBusy(transcriptEl);
  if (!r.ok) {
    machineEl.innerHTML = '<p class="error">Không tìm thấy bài này.</p>';
    transcriptEl.textContent = "";
    return;
  }
  const d = await r.json();
  const a = d.assessment || {};

  renderTranscript(d);
  renderMachineScore(d, a);
  renderDecisionForm(a, d.assessment == null);
  await renderHistory();
}

function renderTranscript(d) {
  const words = (d.asr && d.asr.words) || [];
  if (!words.length) {
    transcriptEl.textContent = (d.asr && d.asr.text) || "Không có bản chép.";
    return;
  }
  transcriptEl.innerHTML = words
    .map((x) => {
      const uncertain = x.is_uncertain;  // luat nam o may chu, xem Word.is_uncertain
      return `<span class="word${uncertain ? " ngo" : ""}" data-seconds="${x.start_s}"${
        uncertain ? ' title="Máy có thể nghe nhầm từ này"' : ""
      }>${escapeHtml(x.text)}</span>`;
    })
    .join(" ");
  transcriptEl.querySelectorAll("[data-seconds]").forEach((n) =>
    n.addEventListener("click", () => seekTo(parseFloat(n.dataset.seconds)))
  );
  wireKaraoke(words);
}

// Highlight the word being spoken as the audio plays. A word ends where the
// next one begins; a moving cursor avoids rescanning the whole array on every
// `timeupdate`, which fires about four times a second.
function wireKaraoke(words) {
  const nodes = Array.from(transcriptEl.querySelectorAll(".word"));
  const starts = words.map((w) => (w.start_s == null ? Infinity : w.start_s));
  let current = -1;

  function paint() {
    const t = player.currentTime;
    let i = current < 0 ? 0 : current;
    while (i + 1 < starts.length && starts[i + 1] <= t) i += 1;
    while (i > 0 && starts[i] > t) i -= 1;
    const next = starts[i] > t ? -1 : i;
    if (next === current) return;
    if (current >= 0 && nodes[current]) nodes[current].classList.remove("speaking");
    current = next;
    if (current < 0 || !nodes[current]) return;
    nodes[current].classList.add("speaking");
    const top = nodes[current].offsetTop - transcriptEl.offsetTop;
    if (top < transcriptEl.scrollTop || top > transcriptEl.scrollTop + transcriptEl.clientHeight - 40) {
      transcriptEl.scrollTop = top - transcriptEl.clientHeight / 2;
    }
  }

  player.addEventListener("timeupdate", paint);
  player.addEventListener("seeked", paint);
}

// Bài dài: cho giảng viên biết con số ở trên được ghép từ đâu.
//
// Đây là thông tin một người duyệt cần TRƯỚC khi nghe, không phải sau. Điểm của
// bài dài là trung vị của nhiều đoạn, mỗi đoạn được chấm riêng, và cách gộp đó
// chưa được kiểm định trên dữ liệu nào. Nếu các đoạn lệch nhau nhiều thì con số
// duy nhất ở trên đang che mất hai phần bài nói khác hẳn nhau — và chỗ phải
// nghe kỹ chính là ranh giới giữa chúng.
const SPREAD_DISAGREE = 0.8;

function windowSummary(a) {
  const ws = a.windows || [];
  if (ws.length < 2) return "";

  const spread = a.window_spread;
  const wide = spread != null && spread >= SPREAD_DISAGREE;
  let h =
    '<div class="notice notice-warn" style="margin-top:var(--sp-3)">' +
    `<b>Điểm gộp từ ${ws.length} đoạn.</b> Bản ghi dài hơn dải huấn luyện của mô hình nên ` +
    "được cắt nhỏ, chấm riêng rồi lấy trung vị. Cách gộp chưa được kiểm định, vì vậy bài " +
    "này bắt buộc qua giảng viên." +
    (spread == null
      ? ""
      : ` Khoảng cách giữa đoạn cao nhất và thấp nhất: <b>${spread.toFixed(2)} điểm</b>.` +
        (wide ? " Các đoạn lệch nhau nhiều — nên nghe cả hai phía ranh giới." : "")) +
    "</div>";

  h += '<div class="window-strip" role="list">';
  const total = ws[ws.length - 1].end_s || 0;
  for (const w of ws) {
    const width = total ? ((w.end_s - w.start_s) / total) * 100 : 100 / ws.length;
    const label = w.overall_0_6 == null ? "không chấm được" : `${w.overall_0_6.toFixed(2)} · ${w.band}`;
    // Bấm được: nhảy thẳng tới đầu đoạn trong bản ghi. Giảng viên nhìn thấy
    // một đoạn lệch điểm thì thứ họ muốn làm ngay là nghe đúng đoạn đó.
    h +=
      `<button type="button" class="window-chunk${w.overall_0_6 == null ? " unscored" : ""}"` +
      ` role="listitem" data-seconds="${w.start_s}" style="flex:0 0 ${width.toFixed(2)}%"` +
      ` title="Nghe đoạn ${w.index + 1}">` +
      `<b>${escapeHtml(label)}</b><span class="muted">${mmss(w.start_s)}–${mmss(w.end_s)}</span>` +
      "</button>";
  }
  return h + "</div>";
}

// The machine's result, shown the way it actually is: ONE overall estimate.
//
// The old version of this panel printed a line per criterion. Those five lines
// always carried the same number, because `RidgeScorer.score` writes the
// overall score into every CriterionScore -- the corpus has no per-criterion
// labels to train on. Printing them made the teacher believe the model had
// five separate opinions to agree or disagree with.
function renderMachineScore(d, a) {
  let h = `<div class="card-head"><h2>Máy chấm</h2>${window.ui.statusBadge(d.status)}</div>`;
  if (a.overall_0_6 != null) {
    h += '<div class="score-panel">';
    h += `<div class="score-figure"><span class="score">${a.overall_0_6.toFixed(2)}</span>
      <span class="score-scale">trên thang 1 – 6</span></div>`;
    h += `<div class="score-meta"><span class="score-band">${escapeHtml(a.overall_band)}</span>
      <p class="score-caption">Một ước lượng tổng thể, chưa hiệu chuẩn. Mô hình không có
      điểm riêng cho từng tiêu chí.</p></div>`;
    h += "</div>";
    // Trust Layer (D022): giang vien can khoang nay nhat khi quyet band -- no cho
    // biet may phan van giua nhung band nao.
    const iv = a.interval;
    if (iv) {
      h +=
        '<p class="interval-line">Khoảng tin cậy ' + Math.round(iv.coverage * 100) + "%: <b>" +
        iv.low.toFixed(2) + " – " + iv.high.toFixed(2) + "</b> · band có thể: <b>" +
        (iv.band_set || []).map((b) => escapeHtml(b)).join(", ") + "</b> (" +
        escapeHtml(iv.method) + ", " + escapeHtml(iv.calibration_version) + ")</p>";
    }
  } else {
    h += '<p class="muted">Máy không chấm được bài này.</p>';
  }

  h += windowSummary(a);

  if (d.reasons && d.reasons.length) {
    // The same Vietnamese names as the queue, which is filtered by them; the
    // code itself stays in the tooltip for anyone matching it to a log line.
    h +=
      '<p class="muted reason-line">Lý do gắn cờ: ' +
      d.reasons
        .map((c) => `<span class="badge" title="${escapeHtml(c)}">${escapeHtml(window.ui.reasonName(c))}</span>`)
        .join(" ") +
      "</p>";
  }

  // What IS per-criterion is the data coverage, so that is what gets listed.
  // Xem ghi chu ve `coverage` / `confidence` trong report.js.
  const cov = (c) => c.coverage ?? c.confidence;
  const partial = (a.criteria || []).filter((c) => cov(c) != null && cov(c) < 1);
  if (partial.length) {
    h +=
      '<p class="muted">Thiếu phép đo ở: ' +
      partial
        .map(
          (c) =>
            `${escapeHtml(CRITERION_NAMES[c.criterion] || c.criterion)} ` +
            `(${Math.round(cov(c) * 100)}%)`
        )
        .join(", ") +
      "</p>";
  }

  machineEl.innerHTML = h;
  machineEl.querySelectorAll("[data-seconds]").forEach((n) =>
    n.addEventListener("click", () => seekTo(parseFloat(n.dataset.seconds)))
  );
  renderEvidence(a);
}

// Evidence sits under the transcript, on the listening side of the screen:
// each card seeks the pinned player to its moment.
function renderEvidence(a) {
  evidenceMarks = [];
  let h = "";
  const ev = (a.evidence || []).slice(0, 6);
  if (ev.length) {
    h += '<h3 class="block-title">Bằng chứng</h3>';
    h += '<div class="evidence-grid">';
    ev.forEach((e) => {
      const seekable = e.start_s != null;
      if (seekable) evidenceMarks.push(e.start_s);
      h += seekable
        ? `<button type="button" class="evidence" data-seconds="${e.start_s}">`
        : '<div class="evidence">';
      h += '<span class="evidence-head">';
      h += `<span class="evidence-kind">${escapeHtml(
        CRITERION_NAMES[e.criterion] || e.criterion
      )}</span>`;
      if (seekable) h += `<span class="evidence-time">${mmss(e.start_s)}</span>`;
      h += "</span>";
      h += `<p class="evidence-note">${escapeHtml(e.note)}</p>`;
      if (e.snippet) h += `<p class="evidence-snippet">…${escapeHtml(e.snippet)}…</p>`;
      if (seekable) h += '<span class="evidence-action">▶ Nghe đoạn này</span>';
      h += seekable ? "</button>" : "</div>";
    });
    h += "</div>";
  }
  evidencePanel.innerHTML = h;
  evidencePanel.querySelectorAll("[data-seconds]").forEach((n) =>
    n.addEventListener("click", () => seekTo(parseFloat(n.dataset.seconds)))
  );
}

// Reasons a teacher writes again and again, one click to insert and still
// editable. The reason stays mandatory: these only save the typing.
const QUICK_REASONS = [
  "Đã nghe lại toàn bài, kết quả máy hợp lý.",
  "Máy đánh giá thấp hơn thực tế.",
  "Máy đánh giá cao hơn thực tế.",
];

// `noResult`: may khong cham duoc (khong phai tieng Anh, ban chep rong, thieu
// model). Khong co gi de "dong y"; giang vien tu cham hoac dong bai.
function renderDecisionForm(a, noResult) {
  const disabled = hasLock ? "" : " disabled";
  const head = noResult
    ? `<div class="notice"><b>Máy không chấm được bài này.</b> Hãy nghe lại rồi nhập
        điểm hoặc band của bạn, hoặc đóng bài để sinh viên nộp lại.</div>`
    : `<div class="button-row">
        <button type="button" id="agree-button"${disabled}>Đồng ý với kết quả AI</button>
      </div>`;
  decisionEl.innerHTML = `
    <h2>Quyết định của giảng viên</h2>
    <p class="muted">Giảng viên quyết định cuối cùng. Kết quả chỉ được coi là xác nhận
      sau khi lưu ở đây.</p>
    ${head}
    <label for="sc">${noResult ? "Điểm của giảng viên" : "Điểm mới, để trống nếu giữ nguyên"}</label>
    <input id="sc" type="number" step="0.25" min="1" max="6"${disabled}
           placeholder="${a.overall_0_6 == null ? "1 – 6" : a.overall_0_6}">
    <label for="bd">Band mới</label>
    <select id="bd"${disabled}>
      <option value="">${noResult ? "Chọn band" : "Giữ nguyên"}</option><option>A1</option><option>A2</option><option>B1</option><option>B2</option><option>C1</option><option>C2</option>
    </select>
    <label for="ly">Lý do quyết định, bắt buộc kể cả khi đồng ý</label>
    <textarea id="ly" rows="3"${disabled}
      placeholder="Ví dụ: phát âm rõ hơn máy đánh giá, nội dung đủ ý"></textarea>
    <div class="chips reason-chips" role="group" aria-label="Lý do soạn sẵn, bấm để chèn">
      ${QUICK_REASONS.map((t) => `<button type="button" data-reason="${escapeHtml(t)}"${disabled}>${escapeHtml(t)}</button>`).join("")}
    </div>
    <div class="button-row">
      <button type="button" id="save-button"${disabled}>Lưu quyết định</button>
      ${noResult ? `<button type="button" id="close-button" class="secondary"${disabled}>Đóng — không chấm được</button>` : ""}
      <span class="muted"><kbd>Ctrl</kbd>+<kbd>Enter</kbd> để lưu nhanh</span>
    </div>
    <div id="tb" aria-live="polite"></div>`;
  if (!hasLock) return;
  const reasonEl = document.getElementById("ly");
  decisionEl.querySelectorAll("[data-reason]").forEach((b) =>
    b.addEventListener("click", () => {
      const text = b.dataset.reason;
      reasonEl.value = reasonEl.value.trim() ? `${reasonEl.value.trim()} ${text}` : text;
      reasonEl.focus();
    })
  );
  document.getElementById("save-button").addEventListener("click", () => save(false));
  if (noResult) {
    document.getElementById("close-button").addEventListener("click", () => save(false, true));
  } else {
    document.getElementById("agree-button").addEventListener("click", () => save(true));
  }
}

async function renderHistory() {
  const r = await fetch(`/api/v1/responses/${ID}/history`);
  if (!r.ok) return;
  const rows = await r.json();
  if (!rows.length) {
    historyEl.innerHTML =
      "<h2>Lịch sử</h2>" +
      '<p class="muted">Chưa có lần sửa nào. Bài này vẫn giữ nguyên kết quả của máy.</p>';
    return;
  }
  let h =
    "<h2>Lịch sử</h2><table><thead><tr><th>Lúc</th><th>Điểm</th><th>Band</th>" +
    "<th>Lý do</th></tr></thead><tbody>";
  rows.forEach((x) => {
    h +=
      `<tr><td class="muted">${escapeHtml(window.ui.localTime(x.created_at))}</td>` +
      `<td>${x.old_score ?? "—"} → ${x.new_score ?? "—"}</td>` +
      `<td>${escapeHtml(x.old_band ?? "—")} → ${escapeHtml(x.new_band ?? "—")}</td>` +
      `<td>${escapeHtml(x.reason)}</td></tr>`;
  });
  historyEl.innerHTML = h + "</tbody></table>";
}

async function save(agree, close = false) {
  if (!hasLock) return;
  const reason = document.getElementById("ly").value;
  const messageEl = document.getElementById("tb");
  // The API layer already enforces this; the interface mirrors the rule rather
  // than relaxing it.
  if (reason.trim().length < 5) {
    const text = "Cần ghi lý do (ít nhất 5 ký tự) cho mọi quyết định, kể cả khi đồng ý với máy.";
    messageEl.innerHTML = `<p class="error">${text}</p>`;
    window.toast(text, "error");
    document.getElementById("ly").focus();
    return;
  }
  const body = { reason: reason };
  if (!agree && !close) {
    const score = document.getElementById("sc").value;
    const band = document.getElementById("bd").value;
    if (score) body.new_score = parseFloat(score);
    if (band) body.new_band = band;
  }
  const r = await fetch(close ? `/api/v1/review/${ID}/close` : `/api/v1/review/${ID}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (window.redirectToLoginIfExpired(r)) return;
  const j = await r.json();
  if (!r.ok) {
    messageEl.innerHTML = `<p class="error">${escapeHtml(JSON.stringify(j.detail))}</p>`;
    window.toast("Không lưu được quyết định.", "error", { sticky: true });
    return;
  }
  // US-15: the response leaves the queue and the next one opens by itself in
  // under 2 seconds.
  messageEl.innerHTML = '<p class="success">Đã lưu. Đang mở bài kế tiếp…</p>';
  window.toast("Đã lưu quyết định. Đang mở bài kế tiếp…", "ok");
  const queue = await (await fetch("/api/v1/review/queue")).json();
  const next = queue.find((x) => x.response_id !== ID && !x.locked_by);
  location.href = next ? `/review/${next.response_id}` : "/review";
}

function seekTo(seconds) {
  player.currentTime = seconds;
  player.play();
}

// Keyboard shortcuts. Skipped while the caret sits in an input field, otherwise
// typing the letter "l" would seek the audio instead of typing the letter.
document.addEventListener("keydown", (e) => {
  const isTyping = ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName);
  if (isTyping) {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) save(false);
    return;
  }
  if (e.key === " ") {
    // A focused button, link or the player itself already uses the space bar.
    if (e.target.closest && e.target.closest("button, a, summary, audio")) return;
    e.preventDefault();
    player.paused ? player.play() : player.pause();
  } else if (e.key.toLowerCase() === "j") {
    player.currentTime = Math.max(0, player.currentTime - 5);
  } else if (e.key.toLowerCase() === "l") {
    player.currentTime += 5;
  } else if (e.key.toLowerCase() === "n" && evidenceMarks.length) {
    evidenceIndex = (evidenceIndex + 1) % evidenceMarks.length;
    seekTo(evidenceMarks[evidenceIndex]);
  }
});

// Release the lock when leaving the page, so one accidental open does not hold
// the response for 15 minutes.
window.addEventListener("pagehide", () => {
  // Not sendBeacon: it can only issue POST, and POST on this path CLAIMS the
  // lock. Leaving the page therefore renewed the lock for another 15 minutes
  // instead of releasing it, so a teacher who glanced at twenty responses
  // locked all twenty. `keepalive` lets the DELETE outlive the page.
  if (hasLock) {
    fetch(`/api/v1/review/${ID}/lock`, { method: "DELETE", keepalive: true });
  }
});

load();
