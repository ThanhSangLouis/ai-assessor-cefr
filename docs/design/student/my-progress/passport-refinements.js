const $ = (id) => document.getElementById(id);
const art = '../../../../src/aicefr/api/static/art/adventure/';
const titles = ['Kể về một ngày đáng nhớ', 'Nói về sở thích của bạn', 'Một nơi bạn yêu thích', 'Một ngày của bạn', 'Giới thiệu bản thân'];
const scores = ['3,4', '3,1', '2,6', '2,8', '2,4'];
let currentPage = 0;
let activeTab = 'assessment';
let selected = 0;
const perPage = 6;
function records() {
  return Array.from({length: Number($('data').value)}, (_, i) => ({
    id: i, title: titles[i % titles.length], score: scores[i % scores.length],
    date: `${String(17 - i % 17).padStart(2, '0')}/${i < 17 ? '11' : '10'}/2026`,
  }));
}
function selectedDetail(row) {

  return `<div class="selected-detail" role="status"><div><span class="micro">ĐANG XEM · ${row.date} · ĐIỂM ${row.score}/6</span><h3>${row.title}</h3><p>Điểm tổng thể của bài đánh giá này.</p></div><a class="text-link" href="http://localhost:8000/my-responses">Mở bài đã nộp ↗</a></div><p class="book-disclaimer">Chủ đề và độ dài khác nhau có thể ảnh hưởng điểm. Hãy nhìn xu hướng qua nhiều bài.</p>`;
}
function drawBook() {
  drawExtras();
  const list = records();
  const state = $('state').value;
  const pageCount = Math.ceil(list.length / perPage);
  currentPage = Math.min(currentPage, pageCount - 1);
  $('assessment-count').textContent = state === 'empty' ? '00' : state === 'ready' ? String(list.length).padStart(2, '0') : '—';
  document.querySelectorAll('[data-tab]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.tab === activeTab)));
  $('section-caption').textContent = activeTab === 'assessment' ? 'NHỮNG LẦN BẠN CẤT GIỌNG' : 'NỖ LỰC CŨNG CÓ DẤU ẤN RIÊNG';
  $('page-caption').textContent = activeTab === 'practice' ? 'THÀNH TỰU' : state === 'ready' ? `TRANG ${String(currentPage + 1).padStart(2, '0')} / ${String(pageCount).padStart(2, '0')}` : 'HÀNH TRÌNH ĐÁNH GIÁ';
  if (activeTab === 'practice') {
    $('stamp-content').innerHTML = `<section class="practice-panel"><div class="practice-medal"><b>12</b><small>BÀI LUYỆN</small></div><h3>Những lần bạn đã kiên trì.</h3><p>Bài luyện được ghi nhận riêng,<br>không quy đổi thành điểm đánh giá.</p><div class="practice-marks"><span><i>✦</i>Dám bắt đầu</span><span><i>♩</i>Chăm luyện nói</span><span><i>⚑</i>12 bước nhỏ</span></div></section>`;
    return;
  }
  if (state !== 'ready') {
    const views = {
      empty: '<span aria-hidden="true">✧</span><h3>Chưa có dấu mốc đầu tiên.</h3><p>Một lần thử là đủ để bắt đầu. Nộp bài đánh giá đầu tiên để có điểm theo dõi.</p><a class="button" href="http://localhost:8000/">Thử bài đầu tiên ↗</a>',
      loading: '<span aria-hidden="true">✥</span><h3>Đang mở hành trình của bạn…</h3><div class="skeleton"></div><div class="skeleton short"></div><p>Đang lấy các bài đánh giá.</p>',
      error: '<span aria-hidden="true">↻</span><h3>Chưa tải được các dấu mốc.</h3><p>Bạn thử lại nhé. Thành tựu luyện tập vẫn có thể xem ở tab bên cạnh.</p><button class="button" id="retry">Thử lại</button>',
    };
    $('stamp-content').innerHTML = `<section class="status-panel" role="status">${views[state]}</section>`;
    if ($('retry')) $('retry').onclick = () => { $('state').value = 'ready'; drawBook(); };
    return;
  }
  const from = currentPage * perPage;
  const visible = list.slice(from, from + perPage);
  const stamps = visible.map((row, index) => `<button class="passport-stamp" data-record="${row.id}" aria-label="${row.title}, ngày ${row.date}, điểm ${row.score} trên 6" aria-pressed="${row.id === selected}" style="--tilt:${[-4,3,-2,4,-3,2][index]}deg"><span class="stamp-top">SPEAKUP · DẤU MỐC ${String(row.id + 1).padStart(2, '0')}</span><span class="stamp-value">${row.score}<small>/6</small></span><span class="stamp-date">${row.date}</span><span class="stamp-ornament" aria-hidden="true">✦</span>${row.id === selected ? '<span class="stamp-pin" aria-hidden="true">✦</span>' : ''}</button>`).join('');
  const future = visible.length < perPage ? '<div class="future-stamp"><span aria-hidden="true">＋</span><b>Một dấu mốc đang chờ.</b><a href="http://localhost:8000/">Thử bài mới ↗</a></div>' : '';
  $('stamp-content').innerHTML = `<div class="stamp-grid">${stamps}${future}</div><div class="page-controls"><span>${from + 1}–${Math.min(from + perPage, list.length)} / ${list.length} bài đánh giá</span><div class="page-buttons"><button id="prev-page" aria-label="Trang dấu mốc trước" ${currentPage === 0 ? 'disabled' : ''}>←</button><span class="page-dots" aria-hidden="true">${Array.from({length:pageCount},(_,i)=>`<i class="${i === currentPage ? 'active' : ''}"></i>`).join('')}</span><button id="next-page" aria-label="Trang dấu mốc tiếp" ${currentPage >= pageCount - 1 ? 'disabled' : ''}>→</button></div></div><div id="selection">${selectedDetail(list[selected])}</div>`;
  document.querySelectorAll('[data-record]').forEach(button => button.onclick = () => {
    selected = Number(button.dataset.record);
    document.querySelectorAll('[data-record]').forEach(b => {
      const active = Number(b.dataset.record) === selected;
      b.setAttribute('aria-pressed', String(active));
      b.querySelector('.stamp-pin')?.remove();
      if (active) b.insertAdjacentHTML('beforeend', '<span class="stamp-pin" aria-hidden="true">✦</span>');
    });
    $('selection').innerHTML = selectedDetail(list[selected]);
  });
  function movePage(direction) {
    currentPage += direction;
    selected = currentPage * perPage;
    drawBook();
    const focusTarget = direction > 0 ? $('next-page') : $('prev-page');
    (focusTarget.disabled ? document.querySelector('[data-record]') : focusTarget).focus();
  }
  $('prev-page').onclick = () => movePage(-1);
  $('next-page').onclick = () => movePage(1);
}
function updateScene() {
  $('preview').dataset.world = $('world').value;
  $('preview').dataset.theme = $('theme').value;
  $('preview').style.setProperty('--scene', `url("${art}${$('world').value}-${$('theme').value}-a-v3-960.webp")`);
  $('mascot').src = `${art}mascot-${$('world').value}-v3.webp`;
}
$('theme').onchange = updateScene;
$('world').onchange = updateScene;
$('data').onchange = () => { currentPage = 0; selected = 0; drawBook(); };
$('state').onchange = () => { currentPage = 0; selected = 0; drawBook(); };
document.querySelectorAll('[data-tab]').forEach(button => button.onclick = () => { activeTab = button.dataset.tab; drawBook(); });
$('mobile').onclick = () => {
  const active = $('preview').classList.toggle('mobile');
  $('mobile').setAttribute('aria-pressed', String(active));
  $('mobile').textContent = active ? 'Xem đầy đủ' : 'Xem mobile';
};
function drawExtras() {

  if ($('state').value !== 'ready') {
    $('extra').innerHTML = '<p>Biểu đồ sẽ xuất hiện khi có điểm đánh giá. Bạn vẫn xem được thành tựu luyện tập trong tab riêng.</p>';
    return;
  }
  const rows = records().slice(0, 5).reverse();
  const coords = rows.map((row, index) => ({...row, x: rows.length === 1 ? 260 : 45 + index * 440 / (rows.length - 1), y: 185 - Number(row.score.replace(',', '.')) * 165 / 6}));
  const path = coords.map((r,i)=>`${i ? 'L' : 'M'}${r.x} ${r.y}`).join(' ');
  $('extra').innerHTML = `<article class="extra-chart"><h2>Điểm tổng thể qua từng bài</h2><p>${rows.length} bài gần nhất · Thang 0–6 · Riêng với bài đánh giá</p><svg class="chart" viewBox="0 0 520 210" role="img" aria-label="Điểm các bài minh họa: ${rows.map(r=>`${r.date}: ${r.score} trên 6`).join('; ')}"><path class="gridline" d="M35 20H500 M35 75H500 M35 130H500 M35 185H500" fill="none"/><text x="8" y="24">6</text><text x="8" y="79">4</text><text x="8" y="134">2</text><text x="8" y="189">0</text><path class="trend" d="${path}"/>${coords.map(r=>`<circle cx="${r.x}" cy="${r.y}" r="5"><title>${r.date}: ${r.score}/6</title></circle><text x="${r.x}" y="205" text-anchor="middle">${r.date.slice(0,5)}</text>`).join('')}</svg></article><article class="extra-habits"><h2>Thói quen nói</h2>${rows.length === 1 ? '<p>Cần thêm bài đánh giá để nhìn xu hướng. Một bài chưa đủ để kết luận về sự thay đổi.</p>' : '<p>Nhìn xu hướng qua nhiều bài · Dữ liệu minh họa</p><div class="habit"><span>Khoảng dừng dài</span><b>Ít hơn ↘</b></div><div class="habit"><span>Từ máy nghe chưa rõ</span><b>Giảm dần ↘</b></div><div class="habit"><span>Tốc độ nói</span><span>Ổn định →</span></div>'}</article>`;
}
updateScene();
drawBook();
