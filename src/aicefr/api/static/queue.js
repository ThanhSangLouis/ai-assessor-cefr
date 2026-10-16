// Teacher review queue adapted to the repository's M07 ReviewCandidate API.
const escapeHtml = window.escapeHtml;
const listEl = document.getElementById("ds");
const filtersEl = document.getElementById("filters");
const reasonFilterEl = document.getElementById("filter-reason");
const lockFilterEl = document.getElementById("filter-lock");
const filterCountEl = document.getElementById("filter-count");
const queueCountEl = document.getElementById("queue-count");
const nextEl = document.getElementById("next-review");
let rows = [];

function fillOptions(select, values, nameOf) {
  const keep = select.value;
  const first = select.options[0];
  select.innerHTML = "";
  select.appendChild(first);
  Array.from(values).sort().forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = nameOf(value);
    select.appendChild(option);
  });
  select.value = keep;
}

function renderRows(visible) {
  if (!visible.length) {
    return '<div class="empty-state"><div class="empty-mark" aria-hidden="true">✓</div>' +
      "<h2>Hàng đợi trống</h2><p>Không có bài nào đang chờ review.</p></div>";
  }
  const body = visible.map((item) => {
    const reasons = item.reasons.length
      ? item.reasons.map((code) => `<span class="badge">${escapeHtml(window.ui.reasonName(code))}</span>`).join(" ")
      : '<span class="muted">—</span>';
    const claimed = item.claimed_by
      ? `<span class="muted lock-note">Đang được ${escapeHtml(item.claimed_by)} xử lý</span>`
      : '<span class="muted">Chưa nhận xử lý</span>';
    const proposed = item.proposed_band
      ? escapeHtml(item.proposed_band)
      : '<span class="muted">Chưa có band đề xuất</span>';
    const href = `/teacher/reviews/${encodeURIComponent(item.response_id)}`;
    return `<tr${item.claimed_by ? ' class="is-locked"' : ""}>` +
      `<td><b>${escapeHtml(item.response_id)}</b><span class="cell-sub">${escapeHtml(window.ui.localTime(item.created_at))}</span></td>` +
      `<td>${proposed}<span class="cell-sub">${escapeHtml(item.assessment_status)}</span></td>` +
      `<td>${reasons}</td><td class="action-cell">${claimed}<a class="button small" href="${href}">Mở review</a></td></tr>`;
  }).join("");
  return '<table class="queue-table"><thead><tr><th>Bài nộp</th><th>Kết quả đề xuất</th><th>Lý do review</th><th>Xử lý</th></tr></thead>' +
    `<tbody>${body}</tbody></table>`;
}

function apply() {
  const reason = reasonFilterEl.value;
  const freeOnly = lockFilterEl.value === "free";
  const visible = rows.filter((item) => (!reason || item.reasons.includes(reason)) && (!freeOnly || !item.claimed_by));
  listEl.innerHTML = renderRows(visible);
  filterCountEl.textContent = `Hiện ${visible.length} / ${rows.length} bài`;
  const firstFree = rows.find((item) => !item.claimed_by);
  if (firstFree) {
    nextEl.href = `/teacher/reviews/${encodeURIComponent(firstFree.response_id)}`;
    nextEl.removeAttribute("aria-disabled");
  } else {
    nextEl.href = "/review";
    nextEl.setAttribute("aria-disabled", "true");
  }
  const reset = document.getElementById("reset-filters");
  if (reset) reset.addEventListener("click", () => {
    reasonFilterEl.value = "";
    lockFilterEl.value = "";
    apply();
  });
}

nextEl.addEventListener("click", (event) => {
  if (nextEl.getAttribute("aria-disabled") === "true") {
    event.preventDefault();
    window.toast("Không còn bài chưa được nhận xử lý.", "info");
  }
});

async function load() {
  window.showSkeleton(listEl, "table");
  try {
    const response = await fetch("/api/teacher/reviews");
    if (window.redirectToLoginIfExpired(response)) return;
    if (!response.ok) throw new Error("queue unavailable");
    const payload = await response.json();
    rows = Array.isArray(payload.items) ? payload.items : [];
    queueCountEl.textContent = `${rows.length} bài`;
    window.clearBusy(listEl);
    if (!rows.length) {
      filtersEl.hidden = true;
      listEl.innerHTML = '<div class="empty-state"><div class="empty-mark" aria-hidden="true">✓</div><h2>Hàng đợi trống</h2><p>Không có bài nào cần giảng viên xem.</p></div>';
      nextEl.href = "/review";
      nextEl.setAttribute("aria-disabled", "true");
      return;
    }
    filtersEl.hidden = false;
    const reasons = new Set(rows.flatMap((item) => item.reasons || []));
    fillOptions(reasonFilterEl, reasons, window.ui.reasonName);
    apply();
  } catch (error) {
    window.clearBusy(listEl);
    listEl.innerHTML = '<p class="error">Không tải được hàng đợi review.</p>';
    window.toast("Không tải được hàng đợi review.", "error");
  }
}

[reasonFilterEl, lockFilterEl].forEach((element) => element.addEventListener("change", apply));
document.getElementById("queue-refresh").addEventListener("click", load);
load();
