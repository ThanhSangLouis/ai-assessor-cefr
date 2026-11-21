const $ = id => document.getElementById(id);
const art = '../../../../src/aicefr/api/static/art/adventure/';
// Review fixtures only. Never infer a server status from a click or elapsed time.
const states = {
 checking: ['Đang kiểm tra trạng thái', 'Đợi một chút để xác nhận tình trạng bài nói.', '◌'],
 queued: ['Đang chờ đến lượt', 'Bài đã được nhận và đang chờ xử lý.', '◷'],
 running: ['Đang xử lý bài nói', 'Hệ thống đang phân tích bản ghi để tạo kết quả.', '◌'],
 long: ['Bài cần thêm thời gian', 'Máy chủ vẫn báo đang xử lý. Bạn không cần gửi lại bài.', '◷'],
 offline: ['Tạm mất kết nối', 'Chưa cập nhật được trạng thái mới. Hãy kiểm tra lại kết nối.', '↻'],
 timeout: ['Đã tạm dừng theo dõi', 'Trang đã ngừng tự cập nhật sau 5 phút chờ. Bài chưa được xác nhận là thất bại.', '◷'],
 session: ['Cần đăng nhập lại', 'Phiên đăng nhập đã hết. Đăng nhập để tiếp tục xem bài này.', '↗'],
 unknown: ['Chưa đọc được trạng thái', 'Hệ thống chưa trả về trạng thái hợp lệ. Hãy kiểm tra lại sau.', '?'],
 done: ['Kết quả đã sẵn sàng', 'Báo cáo của bạn đã sẵn sàng để mở.', '✦'],
 failed: ['Chưa xử lý được bài này', 'Xem thông tin lỗi để biết bước tiếp theo.', '!'],
 rejected: ['Bản ghi chưa đạt yêu cầu', 'Xem lý do và hướng dẫn trước khi ghi lại.', '!'],
 missing: ['Không tìm thấy bài nói', 'Kiểm tra lại đường dẫn hoặc tìm bài trong danh sách đã nộp.', '?']
};
function render() {
 const state = $('state').value, [title, note, mark] = states[state];
 $('preview').dataset.state = state;
 const live = ['queued', 'running', 'long'].includes(state);
 $('status-content').innerHTML = `<span class="status-mark" aria-hidden="true">${mark}</span><h2>${title}</h2><p>${note}</p>${live ? '<span class="live-note"><i></i> Tự cập nhật trạng thái</span>' : ''}${state === 'offline' ? '<span class="last-known">Lần cập nhật cuối: đang xử lý · dữ liệu mẫu</span>' : ''}`;
 const steps = document.querySelector('.real-steps');
 steps.hidden = !['queued', 'running', 'long', 'done'].includes(state);
 const labels = state === 'queued' ? ['Đã nhận bài', 'Chờ đến lượt', 'Có kết quả'] : ['Đã nhận bài', 'Đang xử lý', 'Có kết quả'];
 document.querySelectorAll('[data-stage]').forEach((e, i) => {
  e.classList.toggle('complete', i < (state === 'done' ? 2 : 1));
  e.classList.toggle('current', i === (state === 'done' ? 2 : 1));
  e.removeAttribute('aria-current');
  if (e.classList.contains('current')) e.setAttribute('aria-current', 'step');
  e.replaceChildren(); const number = document.createElement('span'); number.textContent = i < (state === 'done' ? 2 : 1) ? '✓' : `0${i + 1}`;
  e.append(number, document.createTextNode(labels[i]));
 });
 const identified = !['checking', 'missing', 'session'].includes(state);
 document.querySelector('.submission-heading').hidden = !identified;
 document.querySelector('.processing-kicker').textContent = identified ? 'BÀI ĐÁNH GIÁ · ĐÃ NHẬN' : 'TIẾN TRÌNH BÀI NÓI';
 const history = '<a class="secondary-action" href="../my-responses/responses-c-mockup.html">Về bài đã nộp →</a>';
 const report = 'http://localhost:8000/report/demo-23';
 $('status-actions').innerHTML = state === 'done' ? `<a class="button" href="${report}">Xem kết quả →</a>` : ['failed', 'rejected'].includes(state) ? `<a class="button" href="${report}">Xem lý do & hướng dẫn →</a>${history}` : ['offline', 'timeout', 'unknown'].includes(state) ? `<button class="button" id="retry">Kiểm tra lại trạng thái</button>${history}` : state === 'session' ? '<a class="button" href="http://localhost:8000/login?next=%2Fprogress%2Fdemo-23">Đăng nhập để tiếp tục →</a>' : history;
 $('action-note').textContent = state === 'done' ? 'Ứng dụng sẽ tự mở báo cáo. Bản xem thử giữ màn này để bạn duyệt.' : '';
 const assurance = document.querySelector('.processing-assurance');
 assurance.hidden = !live;
 assurance.textContent = 'Bạn có thể rời trang. Bài vẫn tiếp tục được xử lý.';
 if ($('retry')) $('retry').onclick = () => {
  // No API in the mockup: preserve the last known status instead of pretending success.
  $('action-note').textContent = 'Bản xem thử chưa kết nối máy chủ. Chọn trạng thái trên thanh duyệt để xem kết quả tiếp theo.';
 };
}
function scene() {
 $('preview').dataset.theme = $('theme').value;
 $('preview').dataset.world = $('world').value;
 $('preview').style.setProperty('--scene', `url("${art}${$('world').value}-${$('theme').value}-a-v3-960.webp")`);
 $('mascot').src = `${art}mascot-${$('world').value}-v3.webp`;
}
$('theme').onchange = scene; $('world').onchange = scene; $('state').onchange = render;
$('mobile').onclick = () => { const on = $('preview').classList.toggle('mobile'); $('mobile').setAttribute('aria-pressed', String(on)); $('mobile').textContent = on ? 'Xem desktop' : 'Xem mobile'; };
scene(); render();
