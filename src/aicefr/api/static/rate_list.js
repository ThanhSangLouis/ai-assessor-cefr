// Blind rating assignments adapted to the M12 repository API payload.
const escapeHtml = window.escapeHtml;
const host = document.getElementById("rate-batches");
const labels = { OPEN: "Chưa chấm", SUBMITTED: "Đã nộp", VOID: "Không còn mù" };

function batchCard(batch) {
  const completed = batch.items.filter((item) => item.state === "SUBMITTED").length;
  const voided = batch.items.filter((item) => item.state === "VOID").length;
  const open = batch.batchState === "OPEN" ? batch.items.find((item) => item.state === "OPEN") : null;
  const settled = completed + voided;
  const percent = batch.items.length ? Math.round((settled * 100) / batch.items.length) : 0;
  const next = open
    ? `<a class="button" href="/rate/${encodeURIComponent(open.token)}">Bắt đầu hoặc tiếp tục chấm</a>`
    : batch.batchState === "OPEN"
      ? '<span class="success">Bạn đã xử lý các phiếu còn mở.</span>'
      : '<span class="muted">Đợt chấm đã đóng.</span>';
  const items = batch.items.map((item) => {
    const state = labels[item.state] || item.state;
    const visualState = item.state === "OPEN" ? "opened" : item.state === "SUBMITTED" ? "done" : "seen";
    const disabled = item.state === "VOID" || batch.batchState !== "OPEN";
    return `<li>${disabled
      ? `<span class="sheet-chip ${visualState}" aria-label="Phiếu ${item.position}, ${escapeHtml(state)}">${item.position}</span>`
      : `<a class="sheet-chip ${visualState}" href="/rate/${encodeURIComponent(item.token)}" aria-label="Phiếu ${item.position}, ${escapeHtml(state)}">${item.position}${item.adjudication ? "*" : ""}</a>`}</li>`;
  }).join("");
  return `<section class="card rate-batch"><div class="card-head"><h2>Đợt ${escapeHtml(batch.id)}</h2><span class="muted">${completed}/${batch.items.length} đã nộp</span></div>` +
    `<div class="progress-bar" role="progressbar" aria-valuenow="${percent}" aria-valuemin="0" aria-valuemax="100" aria-label="Đã nộp ${percent}%"><span style="width:${percent}%"></span></div>` +
    `<div class="button-row">${next}</div><ol class="sheet-grid">${items}</ol>` +
    `${batch.items.some((item) => item.adjudication) ? '<p class="muted small-note">* Phiếu phân xử.</p>' : ""}` +
    `${voided ? `<p class="muted small-note">${voided} phiếu không còn mù nên không nhận điểm.</p>` : ""}</section>`;
}

function groupAssignments(assignments) {
  const groups = new Map();
  assignments.forEach((item) => {
    if (!groups.has(item.batch_id)) groups.set(item.batch_id, { id: item.batch_id, batchState: item.batch_state, items: [] });
    const group = groups.get(item.batch_id);
    group.items.push({ ...item, adjudication: false });
  });
  return [...groups.values()].map((group) => {
    group.items.sort((left, right) => left.position - right.position);
    return group;
  });
}

fetch("/api/v1/rating/assignments")
  .then((response) => (window.redirectToLoginIfExpired(response) ? null : response.ok ? response.json() : Promise.reject(response)))
  .then((payload) => {
    if (!payload) return;
    window.clearBusy(host);
    const batches = groupAssignments(Array.isArray(payload.assignments) ? payload.assignments : []);
    host.innerHTML = batches.length
      ? batches.map(batchCard).join("")
      : '<div class="empty-state"><div class="empty-mark" aria-hidden="true">◉</div><h2>Chưa có phiếu chấm</h2><p>Phiếu sẽ xuất hiện tại đây sau khi đợt chấm mù được phân công.</p></div>';
  })
  .catch(() => {
    window.clearBusy(host);
    host.innerHTML = '<p class="error">Không tải được danh sách phiếu chấm.</p>';
  });
