// One blind rating sheet (D030). The server sends the task, an audio address
// under this assignment and, once submitted, the rater's own rating: nothing
// else exists on this page to anchor the score.
const escapeHtml = window.escapeHtml;
const sheet = document.getElementById("sheet");
const ID = sheet.dataset.assignment;
const form = document.getElementById("sheet-form");
const unscorable = document.getElementById("unscorable");
const unscorableBox = document.getElementById("unscorable-box");
const scoreBox = document.getElementById("score-box");
const reasonEl = document.getElementById("sheet-reason");
const messageEl = document.getElementById("sheet-message");
const submitEl = document.getElementById("sheet-submit");
const criteriaInputs = [...document.querySelectorAll("[data-criterion]")];
const overallEl = document.getElementById("score-overall");

let nextId = null;

function paintUnscorable() {
  const off = unscorable.checked;
  unscorableBox.hidden = !off;
  scoreBox.hidden = off;
}
unscorable.addEventListener("change", paintUnscorable);

function readOnly(rating) {
  unscorable.checked = rating.unscorable;
  paintUnscorable();
  if (rating.unscorable) {
    const pick = document.querySelector(`input[name="unscorable-reason"][value="${rating.unscorable_reason}"]`);
    if (pick) pick.checked = true;
  } else {
    criteriaInputs.forEach((el) => {
      el.value = rating.criteria[el.dataset.criterion] ?? "";
    });
    overallEl.value = rating.overall ?? "";
    const band = document.querySelector(`input[name="band"][value="${rating.band}"]`);
    if (band) band.checked = true;
  }
  reasonEl.value = rating.reason || "";
  form.querySelectorAll("input, button[type=submit]").forEach((el) => {
    el.disabled = true;
  });
  messageEl.innerHTML =
    `<p class="success">Đã nộp lúc ${escapeHtml(window.ui.localTime(rating.submitted_at))}.</p>`;
}

function load() {
  fetch(`/api/v1/rate/assignments/${encodeURIComponent(ID)}`)
    .then((r) => {
      if (window.redirectToLoginIfExpired(r)) return null;
      if (!r.ok) throw new Error(String(r.status));
      return r.json();
    })
    .then((s) => {
      if (!s) return;
      nextId = s.next_assignment_id;
      document.getElementById("sheet-batch").textContent = `Phiếu chấm mù · ${s.batch.name}`;
      document.getElementById("sheet-h").lastChild.textContent = `Bài ${s.position}/${s.total}`;
      document.title = "Bài " + s.position + "/" + s.total + " · Chấm mù";
      document.getElementById("sheet-adjudication").hidden = !s.adjudication;
      if (s.task) {
        document.getElementById("task-title").textContent = s.task.title;
        document.getElementById("task-prompt").textContent = s.task.prompt_text;
        document.getElementById("task-time").textContent =
          `Đề yêu cầu nói ${s.task.min_seconds}–${s.task.max_seconds} giây.`;
      }
      document.getElementById("sheet-audio").src = s.audio_url;
      sheet.hidden = false;
      if (s.rating) readOnly(s.rating);
      else if (s.seen_machine) {
        // The rater opened the machine's result for this response after the
        // sheet was given: a rating now would not be blind, so none is taken.
        form.querySelectorAll("input, button[type=submit]").forEach((el) => {
          el.disabled = true;
        });
        messageEl.innerHTML =
          '<p class="notice notice-warn">Bạn đã mở kết quả của máy cho bài này nên phiếu không còn mù và không nhận điểm.' +
          (nextId ? ' <a href="/rate/' + encodeURIComponent(nextId) + '">Sang phiếu tiếp theo</a>.' : "") +
          "</p>";
      } else if (!s.batch.open) {
        form.querySelectorAll("input, button[type=submit]").forEach((el) => {
          el.disabled = true;
        });
        messageEl.innerHTML = '<p class="muted">Đợt chấm đã đóng, phiếu này không nộp được nữa.</p>';
      }
    })
    .catch(() => {
      document.getElementById("sheet-error").innerHTML =
        '<p class="error">Không mở được phiếu chấm này. <a href="/rate">Về danh sách phiếu</a>.</p>';
    });
}

function number(el) {
  const v = el.value.trim().replace(",", ".");
  return v === "" ? null : Number(v);
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  messageEl.innerHTML = "";
  let body;
  if (unscorable.checked) {
    const pick = document.querySelector('input[name="unscorable-reason"]:checked');
    if (!pick) {
      messageEl.innerHTML = '<p class="error">Hãy chọn lý do không chấm được.</p>';
      return;
    }
    body = { unscorable: true, unscorable_reason: pick.value, reason: reasonEl.value.trim() || null };
  } else {
    const criteria = {};
    for (const el of criteriaInputs) {
      const v = number(el);
      if (v === null || Number.isNaN(v) || v < 0 || v > 6 || (v * 2) % 1 !== 0) {
        messageEl.innerHTML = '<p class="error">Mỗi tiêu chí cần một điểm từ 0 đến 6, bước 0,5.</p>';
        el.focus();
        return;
      }
      criteria[el.dataset.criterion] = v;
    }
    const overall = number(overallEl);
    const band = document.querySelector('input[name="band"]:checked');
    if (overall === null || Number.isNaN(overall) || overall < 0 || overall > 6 || (overall * 2) % 1 !== 0) {
      messageEl.innerHTML = '<p class="error">Điểm tổng từ 0 đến 6, bước 0,5.</p>';
      overallEl.focus();
      return;
    }
    if (!band) {
      messageEl.innerHTML = '<p class="error">Hãy chọn band.</p>';
      return;
    }
    if (reasonEl.value.trim().length < 3) {
      messageEl.innerHTML = '<p class="error">Hãy ghi một dòng lý do.</p>';
      reasonEl.focus();
      return;
    }
    body = { criteria, overall, band: band.value, reason: reasonEl.value.trim() };
  }
  submitEl.disabled = true;
  try {
    const r = await fetch(`/api/v1/rate/assignments/${encodeURIComponent(ID)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (window.redirectToLoginIfExpired(r)) return;
    const d = await r.json().catch(() => ({}));
    if (!r.ok) {
      const detail = typeof d.detail === "string" ? d.detail : "Không nộp được phiếu.";
      messageEl.innerHTML = `<p class="error">${escapeHtml(detail)}</p>`;
      submitEl.disabled = false;
      return;
    }
    window.toast("Đã nộp phiếu.", "ok");
    const next = d.next_assignment_id || nextId;
    location.href = next ? `/rate/${encodeURIComponent(next)}` : "/rate";
  } catch (err) {
    messageEl.innerHTML = '<p class="error">Không kết nối được máy chủ. Phiếu chưa được nộp.</p>';
    submitEl.disabled = false;
  }
});

load();
