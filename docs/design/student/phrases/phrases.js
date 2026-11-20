const $ = id => document.getElementById(id);
const art = '../../../../src/aicefr/api/static/art/adventure/';
const phrases = [
 ['a change of scenery','đổi gió, thay đổi không gian','A weekend in Da Lat gave me a welcome change of scenery.',0,'Đến hạn hôm nay'],
 ['make the most of','tận dụng tối đa','We tried to make the most of our short trip.',1,'Đến hạn hôm nay'],
 ['within walking distance','trong khoảng cách đi bộ','Our hotel was within walking distance of the lake.',2,'Đến hạn hôm nay'],
 ['leave a lasting impression','để lại ấn tượng sâu sắc','The kindness of the local people left a lasting impression on me.',3,'Ôn lại 20/11'],
 ['take my mind off','giúp tôi tạm quên điều gì','Walking in the park helps take my mind off work.',4,'Ôn lại 26/11'],
 ['a sense of belonging','cảm giác thuộc về','That small town gave me a sense of belonging.',3,'Ôn lại 22/11'],
 ['step out of my comfort zone','bước ra khỏi vùng an toàn','Travelling alone helped me step out of my comfort zone.',1,'Ôn lại 18/11'],
 ['every now and then','thỉnh thoảng','I still visit that little café every now and then.',5,'Ôn lại 16/12']
];
let queue = [0,1,2], revealed = false, saved = new Set(), remembered = new Set(), filter = '', query = '', notice = '';
let collectionOpen = false;
const audioIcon = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M11 5 6 9H3v6h3l5 4V5Z"/><path d="M15 8a6 6 0 0 1 0 8m3-11a10 10 0 0 1 0 14"/></svg>';
function soundButton(text) { return `<button class="listen" data-speak="${phrases.findIndex(p=>p[0]===text)}" aria-label="Nghe cụm từ ${text}" title="Nghe phát âm">${audioIcon}</button>`; }
function highlightPhrase(sentence,phrase) {
 let index=sentence.toLowerCase().indexOf(phrase.toLowerCase());
 if(index<0){phrase=phrase.replace(/^(a|an|the) /i,'');index=sentence.toLowerCase().indexOf(phrase.toLowerCase());}
 if(index<0)return sentence;
 return sentence.slice(0,index)+'<strong>'+sentence.slice(index,index+phrase.length)+'</strong>'+sentence.slice(index+phrase.length);
}
function library() {
 return `<section class="library" aria-labelledby="library-title"><header class="library-head"><div><p class="eyebrow">MANG THEO MỖI NGÀY</p><h2 id="library-title">Bộ sưu tập của bạn <span>08</span></h2></div><span class="learned-count">${phrases.filter((p,i)=>p[3]>=3||(p[3]===2&&remembered.has(i))).length} cụm đã thuộc</span></header><div class="library-tools"><label class="search"><span aria-hidden="true">⌕</span><input id="search" type="search" placeholder="Tìm cụm từ hoặc nghĩa…" aria-label="Tìm cụm từ" value=""></label><div class="filters" aria-label="Lọc cụm từ"><button data-filter="" aria-pressed="${filter===''}">Tất cả</button><button data-filter="due" aria-pressed="${filter==='due'}">Đến hạn</button><button data-filter="learned" aria-pressed="${filter==='learned'}">Đã thuộc</button></div></div><div class="phrase-list" id="phrase-list"></div><p class="library-note">Đã thuộc: ôn đúng từ 3 lần liên tiếp. Lịch ôn thay đổi theo lần tự đánh giá.</p></section>`;
}
function paintList() {
 const list = phrases.map((p,i)=>({p,i})).filter(({p,i})=>(!query||(p[0]+' '+p[1]).toLocaleLowerCase('vi').includes(query))&&(!filter||(filter==='due'?queue.includes(i):p[3]>=3||(p[3]===2&&remembered.has(i)))));
 $('phrase-list').innerHTML = list.length ? list.map(({p,i})=>`<details class="phrase-row"><summary><span class="row-index">${String(i+1).padStart(2,'0')}</span><span class="row-copy"><strong lang="en">${p[0]}</strong><span>${p[1]}</span></span><span class="review-day">${saved.has(i)?(remembered.has(i)?'Đã ôn · hôm nay':'Ôn lại ngày mai'):p[4]}</span><span class="row-plus" aria-hidden="true">+</span></summary><div class="row-detail"><p lang="en">${p[2]}</p>${soundButton(p[0])}<span>Câu mẫu trong bài nói · dữ liệu minh họa</span></div></details>`).join('') : '<div class="no-results"><p>Không có cụm từ phù hợp.</p><button class="text-button" id="reset-search">Xóa tìm kiếm và bộ lọc</button></div>';
 if($('reset-search'))$('reset-search').onclick=()=>{query='';filter='';render();$('search').focus();};
}
function render() {
 const state = $('state').value;
 $('preview').dataset.state = state;
 const busy = state === 'loading'; $('phrase-content').setAttribute('aria-busy',String(busy));
 if (['loading','empty','error'].includes(state)) {
  const content = state==='loading'?'<div class="skeleton-line"></div><div class="skeleton-line short"></div><p>Đang mở sổ cụm từ…</p>':state==='empty'?'<span class="empty-symbol" aria-hidden="true">❋</span><h2>Trang đầu đang chờ bạn.</h2><p>Các cụm từ sẽ xuất hiện khi bạn mở bản nâng cấp bài nói trong báo cáo.</p><a class="button" href="http://localhost:8000/my-responses">Mở bài đã nộp →</a>':'<span class="empty-symbol" aria-hidden="true">↻</span><h2>Chưa mở được cuốn sổ.</h2><p>Kiểm tra kết nối rồi thử tải lại.</p><button class="button" id="reload">Thử tải lại</button><p id="reload-note" role="status"></p>';
  $('phrase-content').innerHTML = `<section class="empty-panel">${content}</section>`;
  if ($('reload')) $('reload').onclick=()=>{$('reload-note').textContent='Mockup chưa kết nối API. Chọn “Có cụm từ” trên thanh duyệt để xem dữ liệu.';};
  return;
 }
 const complete = state === 'done' || !queue.length;
 const id = queue[0] ?? 0, p = phrases[id];
 const lead = `<div class="session-intro"><span class="eyebrow">TRẠM NGHỈ / ÔN HÔM NAY</span><h2>Dừng chân. Nói một câu.</h2><p>Tự nói một câu có dùng cụm từ, rồi tự đánh giá.</p><div class="session-count"><strong>${complete?'3':saved.size}<span>/ 3</span></strong><span>${complete?'Đã xong hôm nay':'cụm đã ôn hôm nay'}</span></div><div class="session-track" aria-hidden="true"><i style="width:${complete?100:saved.size/3*100}%"></i></div><p class="session-caption">${complete?'Hẹn bạn ở lần ôn tiếp theo.':`Còn ${queue.length} cụm · không cần ghi âm`}</p></div>`;
 const card = complete ? `<article class="study-card completed"><span class="card-label">PHIÊN ÔN HÔM NAY</span><span class="completion-mark" aria-hidden="true">✿</span><h3>Hôm nay, đủ một chút hay.</h3><p>Bạn đã ôn xong các cụm đến hạn.</p><a class="button" href="http://localhost:8000/practice">Về lộ trình học →</a><button class="text-button" id="see-library">Xem bộ sưu tập ↓</button></article>` : `<article class="study-card"><div class="card-top"><span class="card-label">CỤM TỪ ${String(saved.size+1).padStart(2,'0')} / 03</span></div><div class="phrase-focus"><h3 lang="en">${p[0]}</h3>${soundButton(p[0])}</div>${revealed?`<p class="meaning">${p[1]}</p><section class="usage-example" aria-label="Câu mẫu"><span class="usage-label">TRONG CÂU</span><p lang="en">${highlightPhrase(p[2],p[0])}</p></section><div class="practice-footer"><p class="speaking-prompt">Thử nói một câu của bạn.</p><div class="review-actions"><button class="not-yet" data-review="no">Chưa nhớ</button><button class="button" data-review="yes">Nói được →</button></div></div>`:`<p class="recall-hint">Bạn nhớ cụm này dùng như thế nào?</p><button class="reveal" id="reveal">Xem nghĩa & ví dụ <span>↓</span></button>`}<p class="save-message" role="status">${notice}</p></article>`;
 $('phrase-content').innerHTML = `<section class="study-area" aria-label="Ôn cụm từ hôm nay">${lead}<div class="head-art" aria-hidden="true"><img id="mascot" alt="" src="${art}mascot-${$('world').value}-v3.webp"></div>${card}</section>${library()}`;

 {
  const toggle = document.createElement('button');toggle.className='collection-toggle';toggle.innerHTML='<span>Bộ sưu tập của bạn <small>8 cụm từ · '+phrases.filter((p,i)=>p[3]>=3||(p[3]===2&&remembered.has(i))).length+' đã thuộc</small></span><span aria-hidden="true">'+(collectionOpen?'−':'+')+'</span>';toggle.setAttribute('aria-expanded',String(collectionOpen));toggle.setAttribute('aria-controls','collection-panel');
  const collection=document.querySelector('.library');collection.id='collection-panel';collection.hidden=!collectionOpen;collection.before(toggle);
  toggle.onclick=()=>{collectionOpen=!collectionOpen;collection.hidden=!collectionOpen;toggle.setAttribute('aria-expanded',String(collectionOpen));toggle.lastElementChild.textContent=collectionOpen?'−':'+';};
  if ($('see-library')) $('see-library').onclick=()=>{collectionOpen=true;collection.hidden=false;toggle.setAttribute('aria-expanded','true');toggle.lastElementChild.textContent='−';collection.scrollIntoView({behavior:'instant'});};
 }
 $('search').value=query;paintList();
 if ($('reveal')) $('reveal').onclick=()=>{revealed=true;render();document.querySelector('.meaning').setAttribute('tabindex','-1');document.querySelector('.meaning').focus();};
 $('search').oninput=e=>{query=e.target.value.toLocaleLowerCase('vi').trim();paintList();};
 document.querySelectorAll('[data-filter]').forEach(b=>b.onclick=()=>{filter=b.dataset.filter;document.querySelectorAll('[data-filter]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));paintList();});
 document.querySelectorAll('[data-review]').forEach(b=>b.onclick=()=>{
  if(state==='save-error'){notice='Chưa lưu được. Cụm này vẫn ở đây, hãy thử lại khi có kết nối.';document.querySelector('.save-message').textContent=notice;return;}
  saved.add(id);if(b.dataset.review==='yes')remembered.add(id);queue.shift();revealed=false;notice='';render();
  const focus=document.querySelector('.study-card h3');focus.tabIndex=-1;focus.focus();
 });
}
document.addEventListener('click',e=>{
 const button=e.target.closest('[data-speak]');if(!button)return;
 if(!('speechSynthesis' in window)){$('audio-status').textContent='Trình duyệt chưa hỗ trợ đọc cụm từ.';return;}
 speechSynthesis.cancel();const utterance=new SpeechSynthesisUtterance(phrases[Number(button.dataset.speak)][0]);utterance.lang='en-US';utterance.onerror=()=>{$('audio-status').textContent='Chưa phát được âm thanh. Bạn thử lại nhé.';};speechSynthesis.speak(utterance);
});
function scene(){$('preview').dataset.theme=$('theme').value;$('preview').dataset.world=$('world').value;$('preview').style.setProperty('--scene',`url("${art}${$('world').value}-${$('theme').value}-a-v3-960.webp")`);if($('mascot'))$('mascot').src=`${art}mascot-${$('world').value}-v3.webp`;}
$('theme').onchange=scene;$('world').onchange=scene;
$('state').onchange=()=>{queue=$('state').value==='done'?[]:[0,1,2];saved=new Set();remembered=new Set();revealed=false;notice='';query='';filter='';collectionOpen=false;render();};
$('mobile').onclick=()=>{const on=$('preview').classList.toggle('mobile');$('mobile').setAttribute('aria-pressed',String(on));$('mobile').textContent=on?'Xem desktop':'Xem mobile';};
window.addEventListener('pagehide',()=>{if('speechSynthesis' in window)speechSynthesis.cancel();});scene();render();
