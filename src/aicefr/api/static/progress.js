// Processing progress screen. See docs/web/SPEC_WEB.md section M3.
const rootEl = document.getElementById("td");
const ID = rootEl.dataset.responseId;
const messageEl = document.getElementById("tb");
const elapsedEl = document.getElementById("elapsed");
const barEl = document.getElementById("progress-bar");
const fillEl = document.getElementById("progress-fill");

const POLL_MS = 2000;
// NFR-01 allows a 120 second response to take up to 60 seconds at P90. Wait at
// most 5 minutes, then stop and say so plainly, instead of leaving the page
// spinning with no idea how long it will go on.
const TIMEOUT_MS = 5 * 60 * 1000;
const startedAt = Date.now();
let finished = false;

// Which status maps to which step. The server does not report the exact step in
// progress because the pipeline runs in one go; this is an estimate so the user
// can see that something is moving.
const STEPS = ["badge", "qc", "asr", "cham"];

function mmss(ms) {
  const s = Math.floor(ms / 1000);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

// The elapsed clock runs on its own timer rather than only on each poll, so the
// page visibly keeps time between the two-second status checks. Seeing the
// seconds advance is what tells the reader the page is alive.
setInterval(() => {
  if (finished) return;
  elapsedEl.textContent = `Đã chờ ${mmss(Date.now() - startedAt)}`;
}, 1000);

function markSteps(currentStep, cls) {
  STEPS.forEach((step, i) => {
    const li = rootEl.querySelector(`[data-step="${step}"]`);
    li.className = i < currentStep ? "done" : i === currentStep ? cls : "";
  });
  // The bar shows the step that is finished plus a little of the one running,
  // so it moves at every stage instead of jumping from empty to full.
  const done = cls === "active" ? currentStep + 0.5 : currentStep;
  fillEl.style.width = `${Math.min(100, (done / STEPS.length) * 100)}%`;
  barEl.setAttribute("aria-valuenow", String(Math.min(STEPS.length, Math.round(done))));
  barEl.classList.toggle("failed", cls === "failed");
}

async function check() {
  let d;
  try {
    const r = await fetch(`/api/v1/responses/${ID}/status`);
    if (window.redirectToLoginIfExpired(r)) return;
    if (r.status === 404) {
      finished = true;
      messageEl.innerHTML =
        '<span class="error">Không tìm thấy bài này.</span> ' +
        'Có thể mã bài bị sai. <a href="/my-responses">Xem danh sách bài của bạn</a>.';
      return;
    }
    d = await r.json();
  } catch (err) {
    messageEl.innerHTML = '<span class="error">Mất kết nối máy chủ, đang thử lại…</span>';
    setTimeout(check, POLL_MS);
    return;
  }

  if (d.status === "QUEUED") {
    markSteps(0, "active");
    messageEl.textContent = "Bài đang xếp hàng chờ xử lý.";
  } else if (d.status === "RUNNING") {
    markSteps(2, "active");
    messageEl.textContent = "Đang nhận dạng và chấm điểm.";
  } else {
    // Done. Move on to the report so the user does not have to click again.
    // A practice attempt (D023) has no report: it opens its own result page.
    finished = true;
    markSteps(4, "done");
    if (d.purpose === "practice") {
      messageEl.textContent = "Đã xử lý xong, đang mở kết quả luyện tập…";
      location.href = `/practice/results/${ID}`;
      return;
    }
    messageEl.textContent = "Đã xử lý xong, đang mở báo cáo…";
    window.toast("Đã chấm xong. Đang mở báo cáo…", "ok");
    location.href = `/report/${ID}`;
    return;
  }

  if (Date.now() - startedAt > TIMEOUT_MS) {
    finished = true;
    markSteps(2, "failed");
    // A practice attempt has no report; send it to its own result page.
    const later = d.purpose === "practice" ? `/practice/results/${ID}` : `/report/${ID}`;
    messageEl.innerHTML =
      '<span class="error">Bài xử lý lâu bất thường.</span> ' +
      `Mở lại <a href="${later}">trang kết quả</a> sau ít phút, ` +
      "hoặc báo giảng viên nếu vẫn không có kết quả.";
    window.toast("Bài xử lý lâu bất thường. Hãy thử lại sau ít phút.", "warn", {
      sticky: true,
    });
    return;
  }
  setTimeout(check, POLL_MS);
}

check();
