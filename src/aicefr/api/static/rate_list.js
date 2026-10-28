// A rater's sheets, batch by batch (D030). A batch is a card with its progress
// and a "next sheet" button; the sheets themselves are numbered in this
// rater's own order and say only whether they are done. A sheet whose
// machine result the rater has opened since is no longer blind ("seen"): it
// takes no rating and is not waiting for one.
const escapeHtml = window.escapeHtml;
const host = document.getElementById("rate-batches");
const STATE = { new: "Chưa mở", opened: "Đang chấm", done: "Đã nộp", seen: "Không còn mù" };

function batchCard(b) {
  const settled = b.done + (b.voided || 0);
  const pct = b.total ? Math.round((100 * settled) / b.total) : 0;
  const next = b.open && b.next_assignment_id
    ? `<a class="button" href="/rate/${encodeURIComponent(b.next_assignment_id)}">${window.ui.icon("play")} ${b.done ? "Chấm tiếp" : "Bắt đầu chấm"}</a>`
    : b.open
      ? '<span class="success">Bạn đã chấm xong đợt này.</span>'
      : '<span class="muted">Đợt đã đóng.</span>';
  const items = b.items
    .map(
      (i) => `<li><a class="sheet-chip ${i.state}" href="/rate/${encodeURIComponent(i.assignment_id)}"
        aria-label="${escapeHtml(`Bài ${i.position}, ${STATE[i.state]}`)}">${i.position}${i.adjudication ? "*" : ""}</a></li>`
    )
    .join("");
  return `<section class="card rate-batch">
    <div class="card-head"><h2>${escapeHtml(b.name)}</h2>
      <span class="muted">${b.done}/${b.total} bài</span></div>
    <div class="progress-bar" role="progressbar" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100"
      aria-label="Đã chấm ${pct}%"><span style="width:${pct}%"></span></div>
    <div class="button-row">${next}</div>
    <ol class="sheet-grid">${items}</ol>
    ${b.items.some((i) => i.adjudication) ? '<p class="muted small-note">* Bài phân xử: hai giám khảo trước lệch nhau nhiều.</p>' : ""}
    ${b.voided ? `<p class="muted small-note">${b.voided} bài gạch ngang: bạn đã mở kết quả của máy cho bài đó nên phiếu không còn mù và không nhận điểm.</p>` : ""}
  </section>`;
}

fetch("/api/v1/rate/assignments")
  .then((r) => (window.redirectToLoginIfExpired(r) ? null : r.ok ? r.json() : Promise.reject(r)))
  .then((data) => {
    if (!data) return;
    window.clearBusy(host);
    host.innerHTML = data.batches.length
      ? data.batches.map(batchCard).join("")
      : `<div class="empty-state"><div class="empty-mark" aria-hidden="true">${window.ui.icon("eye-off", "icon")}</div>
          <h2>Chưa có phiếu chấm nào</h2>
          <p>Quản trị viên tạo đợt chấm mù và phân bài cho giám khảo. Khi có bài cho bạn, chúng hiện ở đây.</p></div>`;
  })
  .catch(() => {
    window.clearBusy(host);
    host.innerHTML = '<p class="error">Không tải được danh sách phiếu chấm.</p>';
  });
