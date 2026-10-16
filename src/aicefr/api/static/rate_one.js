// Blind rating sheet adapted to M12's token-scoped assignment contract.
const escapeHtml = window.escapeHtml;
const sheet = document.getElementById("sheet");
const token = sheet.dataset.assignment;
const form = document.getElementById("sheet-form");
const unscorable = document.getElementById("unscorable");
const unscorableBox = document.getElementById("unscorable-box");
const scoreBox = document.getElementById("score-box");
const rationale = document.getElementById("sheet-reason");
const message = document.getElementById("sheet-message");
const submit = document.getElementById("sheet-submit");
const criteriaInputs = [...document.querySelectorAll("[data-criterion]")];
const overallInput = document.getElementById("score-overall");
let nextToken = null;
let adjudication = false;

function paintUnscorable() {
  unscorableBox.hidden = !unscorable.checked;
  scoreBox.hidden = unscorable.checked;
  criteriaInputs.forEach((input) => { input.disabled = unscorable.checked; });
  overallInput.disabled = unscorable.checked;
  document.querySelectorAll('input[name="band"]').forEach((input) => { input.disabled = unscorable.checked; });
  document.querySelectorAll('input[name="unscorable-reason"]').forEach((input) => { input.disabled = !unscorable.checked; });
}
unscorable.addEventListener("change", paintUnscorable);
paintUnscorable();

function lockForm() {
  form.querySelectorAll("input, button[type=submit]").forEach((element) => { element.disabled = true; });
}

function showSaved(rating) {
  const isUnrateable = Boolean(rating.unrateable_reason);
  unscorable.checked = isUnrateable;
  paintUnscorable();
  if (isUnrateable) {
    const input = document.querySelector(`input[name="unscorable-reason"][value="${CSS.escape(rating.unrateable_reason)}"]`);
    if (input) input.checked = true;
  } else {
    criteriaInputs.forEach((input) => { input.value = rating.criteria?.[input.dataset.criterion] ?? ""; });
    overallInput.value = rating.overall ?? "";
    const band = document.querySelector(`input[name="band"][value="${CSS.escape(rating.band || "")}"]`);
    if (band) band.checked = true;
  }
  rationale.value = rating.rationale || "";
  lockForm();
  message.innerHTML = `<p class="success">Đã nộp lúc ${escapeHtml(window.ui.localTime(rating.submitted_at))}.</p>`;
}

function findNext(assignments) {
  const current = assignments.find((item) => item.token === token);
  if (!current) return null;
  const sameBatch = assignments
    .filter((item) => item.batch_id === current.batch_id && item.batch_state === "OPEN" && item.state === "OPEN" && item.position > current.position)
    .sort((a, b) => a.position - b.position)[0];
  if (sameBatch) return sameBatch.token;
  return assignments.find((item) => item.batch_state === "OPEN" && item.state === "OPEN" && item.token !== token)?.token || null;
}

async function load() {
  try {
    const [sheetResponse, listResponse] = await Promise.all([
      fetch(`/api/v1/rating/assignments/${encodeURIComponent(token)}`),
      fetch("/api/v1/rating/assignments"),
    ]);
    if (window.redirectToLoginIfExpired(sheetResponse) || window.redirectToLoginIfExpired(listResponse)) return;
    if (!sheetResponse.ok || !listResponse.ok) throw new Error("assignment unavailable");
    const assignment = await sheetResponse.json();
    const list = await listResponse.json();
    const assignments = Array.isArray(list.assignments) ? list.assignments : [];
    nextToken = findNext(assignments);
    const current = assignments.find((item) => item.token === token);
    adjudication = Boolean(assignment.adjudication);
    document.getElementById("sheet-batch").textContent = `Phiếu chấm mù · bài ${assignment.position}`;
    document.getElementById("sheet-h").lastChild.textContent = `Bài ${assignment.position}`;
    document.title = `Bài ${assignment.position} · Chấm mù`;
    document.getElementById("sheet-adjudication").hidden = !adjudication;
    if (adjudication) {
      unscorable.checked = false;
      unscorable.closest("label").hidden = true;
      unscorableBox.hidden = true;
    }
    if (assignment.task) {
      document.getElementById("task-title").textContent = assignment.task.title || "Bài nói";
      document.getElementById("task-prompt").textContent = assignment.task.prompt_text || "";
      const min = assignment.task.min_seconds;
      const max = assignment.task.max_seconds;
      document.getElementById("task-time").textContent = Number.isFinite(min) && Number.isFinite(max)
        ? `Đề yêu cầu nói ${min}–${max} giây.` : "";
    }
    document.getElementById("sheet-audio").src = assignment.audio_url;
    sheet.hidden = false;
    if (assignment.rating) showSaved(assignment.rating);
    else if (current?.state === "SUBMITTED") {
      lockForm();
      message.innerHTML = '<p class="success">Phiếu đã được nộp.</p>';
    }
  } catch (error) {
    document.getElementById("sheet-error").innerHTML =
      '<p class="error">Không mở được phiếu hoặc đợt chấm đã đóng. <a href="/rate">Về danh sách phiếu</a>.</p>';
  }
}

function number(input) {
  const value = input.value.trim().replace(",", ".");
  return value === "" ? null : Number(value);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  message.textContent = "";
  let body;
  if (unscorable.checked) {
    const selected = document.querySelector('input[name="unscorable-reason"]:checked');
    if (!selected) {
      message.innerHTML = '<p class="error">Hãy chọn lý do không chấm được.</p>';
      return;
    }
    body = { criteria: {}, overall: null, band: null, rationale: rationale.value.trim(), unrateable_reason: selected.value };
  } else {
    const criteria = {};
    for (const input of criteriaInputs) {
      const value = number(input);
      if (value === null || Number.isNaN(value) || value < 0 || value > 6 || (value * 2) % 1 !== 0) {
        message.innerHTML = '<p class="error">Mỗi tiêu chí cần một điểm từ 0 đến 6, bước 0,5.</p>';
        input.focus();
        return;
      }
      criteria[input.dataset.criterion] = value;
    }
    const overall = number(overallInput);
    const band = document.querySelector('input[name="band"]:checked');
    if (overall === null || Number.isNaN(overall) || overall < 0 || overall > 6 || (overall * 2) % 1 !== 0) {
      message.innerHTML = '<p class="error">Điểm tổng từ 0 đến 6, bước 0,5.</p>';
      overallInput.focus();
      return;
    }
    if (!band) {
      message.innerHTML = '<p class="error">Hãy chọn band.</p>';
      return;
    }
    if (rationale.value.trim().length < 1 || rationale.value.trim().length > 300) {
      message.innerHTML = '<p class="error">Hãy ghi lý do từ 1 đến 300 ký tự.</p>';
      rationale.focus();
      return;
    }
    body = { criteria, overall, band: band.value, rationale: rationale.value.trim() };
  }

  submit.disabled = true;
  try {
    const action = adjudication ? "adjudicate" : "submit";
    const response = await fetch(`/api/v1/rating/assignments/${encodeURIComponent(token)}/${action}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (window.redirectToLoginIfExpired(response)) return;
    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      const code = typeof result.error === "string" ? result.error : "Không nộp được phiếu.";
      message.innerHTML = `<p class="error">${escapeHtml(code)}</p>`;
      submit.disabled = false;
      return;
    }
    window.toast("Đã nộp phiếu.", "ok");
    location.href = nextToken ? `/rate/${encodeURIComponent(nextToken)}` : "/rate";
  } catch (error) {
    message.innerHTML = '<p class="error">Không kết nối được máy chủ. Phiếu chưa được nộp.</p>';
    submit.disabled = false;
  }
});

load();
