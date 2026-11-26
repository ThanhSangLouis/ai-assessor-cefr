(() => {
 const $ = id => document.getElementById(id);
 const main = document.querySelector('.prototype');
 const preview = $('preview');
 const syncTheme = () => {
  const theme = $('theme').value;
  preview.dataset.theme = theme;
  $('mode').ariaPressed = String(theme === 'night');
  $('mode').textContent = theme === 'night' ? 'Giao diện sáng' : 'Giao diện tối';
  const scene = new URL('../../../../src/aicefr/api/static/art/adventure/' + main.dataset.world + '-' + theme + '-a-v3-960.webp', document.baseURI);
  main.style.setProperty('--scene', 'url("' + scene.href + '")');
 };
 $('theme').addEventListener('change', syncTheme);
 $('mode').onclick = () => {
  $('theme').value = $('theme').value === 'day' ? 'night' : 'day';
  $('theme').dispatchEvent(new Event('change'));
 };
 $('world-choice').value = main.dataset.world;
 $('world-choice').onchange = () => {
  main.dataset.world = $('world-choice').value;
  main.querySelector('.landscape img').src = new URL('../../../../src/aicefr/api/static/art/adventure/mascot-' + main.dataset.world + '-v3.webp', document.baseURI).href;
  syncTheme();
 };
 syncTheme();

 if ($('record')) {
  let clock;
  let started;
  const setState = state => {
   main.classList.toggle('recording', state === 'recording');
   main.dataset.recordState = state;
   $('record').hidden = state === 'recorded';
   $('record-actions').hidden = state !== 'recorded';
   $('feedback').hidden = true;
   $('record').querySelector('span').textContent = state === 'recording' ? 'Dừng ghi âm' : 'Bắt đầu ghi âm';
   $('record').setAttribute('aria-label', state === 'recording' ? 'Dừng ghi âm' : 'Bắt đầu ghi âm');
   main.querySelector('.mic-hint').textContent = state === 'recording' ? 'Chạm để kết thúc lượt nói' : state === 'recorded' ? 'Bạn có thể thu lại hoặc xem phản hồi' : 'Nói tự nhiên, theo nhịp của bạn.';
   $('record-status').textContent = {
    ready: 'Chưa bắt đầu',
    recording: 'Đang ghi âm mô phỏng',
    recorded: 'Đã thu xong bản mẫu'
   }[state];
  };
  const reset = () => {
   clearInterval(clock);
   $('timer').textContent = '0:00';
   setState('ready');
  };
  $('record').onclick = () => {
   if (main.classList.contains('recording')) {
    clearInterval(clock);
    setState('recorded');
    $('finish').focus();
    return;
   }
   started = Date.now();
   clock = setInterval(() => {
    const seconds = Math.floor((Date.now() - started) / 1000);
    $('timer').textContent = Math.floor(seconds / 60) + ':' + String(seconds % 60).padStart(2,'0');
   }, 250);
   setState('recording');
  };
  $('retry').onclick = () => { reset(); $('record').focus(); };
  $('finish').onclick = () => { $('feedback').hidden = false; $('feedback').focus(); };
  main.addEventListener('practice-change', reset);
 }

 const words = {
  comfortable: ['/ˈkʌm.fɚ.tə.bəl/', 'I felt comfortable speaking with them.', 'Nhấn âm đầu. Nói nhẹ các âm phía sau.'],
  usually: ['/ˈjuː.ʒu.ə.li/', 'I usually take a short walk after lunch.', 'Nhấn âm đầu, giữ âm /ʒ/ nhẹ ở giữa.'],
  world: ['/wɝːld/', 'It opened up a whole new world.', 'Giữ âm cuối /ld/ nhẹ, tránh thêm nguyên âm.']
 };
 document.querySelectorAll('.word-pills button').forEach(button => {
  button.onclick = () => {
   const word = button.textContent;
   $('word').textContent = word;
   [$('phonetic').textContent, $('sample').textContent, $('tip').textContent] = words[word];
   document.querySelectorAll('.word-pills button').forEach(item => { item.ariaPressed = String(item === button); });
   main.dispatchEvent(new Event('practice-change'));
  };
 });
 if ($('listen')) $('listen').onclick = () => {
  if (!('speechSynthesis' in window)) { $('tip').textContent = 'Thiết bị chưa hỗ trợ giọng đọc mẫu.'; return; }
  speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance($('sample').textContent);
  utterance.lang = 'en-US';
  speechSynthesis.speak(utterance);
 };
 const savedPassage = $('passage-text')?.innerHTML;
 document.querySelectorAll('[data-mode]').forEach(button => {
  button.ariaPressed = String(button.dataset.mode === 'phrases');
  button.onclick = () => {
   const generated = button.dataset.mode === 'model';
   $('passage-title').textContent = generated ? 'A morning at the market · mẫu AI' : 'A slower weekend';
   $('passage-text').innerHTML = generated
    ? 'I left home early to <mark>make the most of</mark> the morning. The market was <mark>within walking distance</mark>. A different route gave me a welcome <mark>change of scenery</mark>.'
    : savedPassage;
   document.querySelectorAll('[data-mode]').forEach(item => { item.ariaPressed = String(item === button); });
   main.dispatchEvent(new Event('practice-change'));
  };
 });
 document.querySelectorAll('.settings').forEach(form => {
  form.onsubmit = event => {
   event.preventDefault();
   const passwords = form.querySelectorAll('input[type=password]');
   form.querySelector('output').textContent = passwords.length && passwords[1].value !== passwords[2].value
    ? 'Hai mật khẩu mới chưa khớp.' : 'Đã xác nhận thao tác trong bản xem thử.';
   passwords.forEach(input => { input.value = ''; });
  };
 });
 if ($('font-size')) $('font-size').onchange = () => main.style.setProperty('--font-scale', Number($('font-size').value) / 100);
})();

(() => {
 const main = document.querySelector('.prototype');
 const select = document.getElementById('review-state');
 const status = document.getElementById('review-status');
 const panels = main.querySelector('.panels');
 const copy = {
  loading: ['Đang tải nội dung…', 'Vui lòng chờ trong giây lát.'],
  empty: ['Chưa có nội dung để luyện', 'Mở một bài đã có kết quả để bắt đầu.'],
  error: ['Chưa tải được nội dung', 'Kiểm tra kết nối rồi thử lại.'],
  offline: ['Kết nối đang gián đoạn', 'Nội dung hiện tại được giữ để bạn tiếp tục khi có mạng.'],
  permission: ['Chưa truy cập được micro', 'Cho phép micro trong trình duyệt rồi thử lại.'],
  saving: ['Đang gửi dữ liệu…', 'Đợi phản hồi trước khi tiếp tục.'],
  'save-error': ['Chưa lưu được', 'Nội dung được giữ lại. Bạn có thể thử gửi lại.'],
  saved: ['Đã lưu thay đổi', 'Thông tin mẫu đã được cập nhật.']
 };
 const apply = () => {
  const state = select.value;
  main.dataset.reviewState = state;
  const message = copy[state];
  status.hidden = !message;
  panels.hidden = ['loading','empty','error','permission'].includes(state);
  if (message) {
   status.innerHTML = '<h2>' + message[0] + '</h2><p>' + message[1] + '</p>';
   if (['error','offline','permission','save-error'].includes(state)) {
    const retry = document.createElement('button');
    retry.className = 'quiet';
    retry.textContent = 'Thử lại';
    retry.onclick = () => { status.querySelector('p').textContent = 'Bản xem thử chưa kết nối dịch vụ. Chọn trạng thái Sẵn sàng để tiếp tục duyệt.'; };
    status.append(retry);
   }
  }
  const record = document.getElementById('record');
  if (record) {
   main.dispatchEvent(new Event('practice-change'));
   if (['recording','recorded','feedback'].includes(state)) record.click();
   if (['recorded','feedback'].includes(state)) record.click();
   if (state === 'feedback') document.getElementById('finish').click();
  }
  panels.querySelectorAll('button,input,select').forEach(el => { el.disabled = state === 'saving'; });
 };
 select.onchange = apply;
 document.getElementById('preview-mobile').onclick = event => {
  const active = document.getElementById('preview').classList.toggle('mobile');
  event.currentTarget.ariaPressed = String(active);
 };
})();

/* Live microphone meter for design review. Audio stays on the device. */
(() => {
 const main = document.querySelector('.prototype');
 const button = document.getElementById('record');
 if (!button) return;
 const bars = [...main.querySelectorAll('.level-bars i')];
 const status = document.getElementById('record-status');
 const hint = main.querySelector('.mic-hint');
 let stream;
 let context;
 let frame;
 let generation = 0;

 const stop = () => {
  generation += 1;
  cancelAnimationFrame(frame);
  stream?.getTracks().forEach(track => track.stop());
  stream = undefined;
  context?.close().catch(() => {});
  context = undefined;
  main.classList.remove('live-input');
  bars.forEach(bar => bar.style.removeProperty('height'));
 };
 const start = async () => {
  stop();
  const request = generation;
  if (!navigator.mediaDevices?.getUserMedia) {
   status.textContent = 'Chưa thể mở micro trên trình duyệt này';
   hint.textContent = 'Mở bằng localhost hoặc HTTPS để thử hiệu ứng giọng nói.';
   return;
  }
  try {
   const input = await navigator.mediaDevices.getUserMedia({audio:true});
   if (request !== generation || !main.classList.contains('recording')) {
    input.getTracks().forEach(track => track.stop());
    return;
   }
   stream = input;
   context = new AudioContext();
   await context.resume();
   if (request !== generation) return;
   const analyser = context.createAnalyser();
   analyser.fftSize = 256;
   analyser.smoothingTimeConstant = .75;
   context.createMediaStreamSource(input).connect(analyser);
   const samples = new Uint8Array(analyser.fftSize);
   const levels = Array(bars.length).fill(3);
   main.classList.add('live-input');
   status.textContent = 'Đang nhận giọng nói';
   hint.textContent = 'Sóng thay đổi theo âm lượng micro.';
   const paint = () => {
    if (request !== generation) return;
    analyser.getByteTimeDomainData(samples);
    let power = 0;
    for (const sample of samples) power += ((sample - 128) / 128) ** 2;
    const volume = Math.min(1, Math.sqrt(power / samples.length) * 5);
    levels.shift();
    levels.push(3 + volume * 40);
    bars.forEach((bar,index) => { bar.style.height = levels[index] + 'px'; });
    frame = requestAnimationFrame(paint);
   };
   paint();
  } catch (error) {
   if (request !== generation) return;
   stop();
   status.textContent = error.name === 'NotAllowedError' ? 'Micro chưa được cấp quyền' : 'Chưa mở được micro';
   hint.textContent = 'Cho phép micro rồi thu lại để thử.';
  }
 };
 button.addEventListener('click', () => {
  if (main.classList.contains('recording')) start();
  else stop();
 });
 document.getElementById('retry').addEventListener('click',stop);
 main.addEventListener('practice-change',stop);
 document.getElementById('review-state').addEventListener('change',stop);
 window.addEventListener('pagehide',stop);
})();
