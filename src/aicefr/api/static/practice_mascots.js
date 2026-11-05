// The roadmap's companions (D092): one beside each part of the path, each
// with a short speaking tip. Drawn here as vector art so they keep their
// colours in both themes and stay sharp at any size; the owl of the first part
// is the mockup's own picture (static/art/mascot_owl.png).
(function () {
  const SHADOW = '<ellipse class="rm-m-shadow" cx="70" cy="143" rx="40" ry="6"/>';
  const BLUSH = (x, y) => `<ellipse cx="${x}" cy="${y}" rx="6.5" ry="3.8" fill="#ff8f86" opacity=".55"/>`;
  const EYE = (x, y) =>
    `<ellipse cx="${x}" cy="${y}" rx="5.2" ry="6.4" fill="#2b1a12"/><circle cx="${x + 1.6}" cy="${y - 2.2}" r="1.8" fill="#fff"/>`;

  const ART = {
    // A small SpeakUp robot, waving, a sound wave on its chest.
    robot:
      '<svg viewBox="0 0 140 150" aria-hidden="true" focusable="false"><defs>' +
      '<linearGradient id="rm-g-robot" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffa646"/><stop offset="1" stop-color="#ff6a0b"/></linearGradient></defs>' +
      SHADOW +
      '<path d="M70 24V12" stroke="#ff7a1a" stroke-width="5" stroke-linecap="round"/><circle cx="70" cy="10" r="7" fill="#ff8a2b"/><circle cx="68" cy="8" r="2.2" fill="#fff" opacity=".7"/>' +
      '<path d="M40 104c-14-2-22-12-24-26" stroke="#ff8a2b" stroke-width="9" stroke-linecap="round" fill="none"/><circle cx="16" cy="76" r="7" fill="#ff9a3a"/>' +
      '<path d="M100 106c10 4 14 12 14 22" stroke="#ff7a1a" stroke-width="9" stroke-linecap="round" fill="none"/>' +
      '<rect x="40" y="96" width="60" height="40" rx="17" fill="url(#rm-g-robot)"/>' +
      '<rect x="54" y="104" width="32" height="20" rx="7" fill="#fff4e8"/>' +
      '<path d="M60 114v-2M65 117v-8M70 119v-12M75 117v-8M80 114v-2" stroke="#ff7a1a" stroke-width="2.6" stroke-linecap="round"/>' +
      '<rect x="12" y="46" width="16" height="32" rx="8" fill="#ff7a1a"/><rect x="112" y="46" width="16" height="32" rx="8" fill="#ff7a1a"/>' +
      '<rect x="22" y="22" width="96" height="76" rx="34" fill="url(#rm-g-robot)"/>' +
      '<ellipse cx="52" cy="32" rx="18" ry="6" fill="#fff" opacity=".35"/>' +
      '<rect x="34" y="37" width="72" height="47" rx="22" fill="#3a1f14"/>' +
      '<path d="M48 61q7-9 14 0M78 61q7-9 14 0" stroke="#ffb46a" stroke-width="5" fill="none" stroke-linecap="round"/>' +
      '<path d="M62 71q8 6 16 0" stroke="#ffb46a" stroke-width="3.6" fill="none" stroke-linecap="round"/></svg>',

    // A fox reading a teal book.
    fox:
      '<svg viewBox="0 0 140 150" aria-hidden="true" focusable="false">' +
      SHADOW +
      '<path d="M96 126c28-4 38-34 22-54-3 22-16 34-32 38Z" fill="#ff8a2b"/><path d="M118 72c7 9 7 20 2 29-7-7-8-18-2-29Z" fill="#fff6ec"/>' +
      '<ellipse cx="68" cy="114" rx="34" ry="28" fill="#ff8a2b"/><ellipse cx="68" cy="120" rx="20" ry="18" fill="#fff4e6"/>' +
      '<path d="M32 44 26 8l32 22Z" fill="#ff7a1a"/><path d="M104 44l6-36-32 22Z" fill="#ff7a1a"/>' +
      '<path d="M35 36 32 17l15 11Z" fill="#4a2a1a"/><path d="M101 36l3-19-15 11Z" fill="#4a2a1a"/>' +
      '<path d="M20 56c0-23 21-36 48-36s48 13 48 36c0 21-21 36-48 36S20 77 20 56Z" fill="#ff8a2b"/>' +
      '<path d="M26 62c11 3 24 5 42 22 18-17 31-19 42-22-4 17-21 30-42 30S30 79 26 62Z" fill="#fff6ec"/>' +
      EYE(50, 57) + EYE(86, 57) + BLUSH(38, 70) + BLUSH(98, 70) +
      '<ellipse cx="68" cy="73" rx="5.4" ry="3.8" fill="#2b1a12"/><path d="M63 80q5 4 10 0" stroke="#2b1a12" stroke-width="2.2" fill="none" stroke-linecap="round"/>' +
      '<path d="M38 102l30 8 30-8v28l-30 8-30-8Z" fill="#2eb6a5"/><path d="M42 105l26 7v22l-26-7Z M94 105l-26 7v22l26-7Z" fill="#e9faf6"/>' +
      '<path d="M48 113l14 4M48 119l14 4M88 113l-14 4M88 119l-14 4" stroke="#9ad9cd" stroke-width="1.6" stroke-linecap="round"/>' +
      '<circle cx="40" cy="112" r="7" fill="#ff8a2b"/><circle cx="96" cy="112" r="7" fill="#ff8a2b"/></svg>',

    // A cat with headphones, singing into a microphone.
    cat:
      '<svg viewBox="0 0 140 150" aria-hidden="true" focusable="false">' +
      SHADOW +
      '<path d="M100 128c22 2 30-12 22-24" stroke="#ffb547" stroke-width="9" stroke-linecap="round" fill="none"/>' +
      '<ellipse cx="68" cy="114" rx="33" ry="28" fill="#ffc463"/><ellipse cx="68" cy="120" rx="19" ry="17" fill="#fff5e2"/>' +
      '<path d="M30 46 30 12l26 18Z" fill="#ffb547"/><path d="M106 46l0-34-26 18Z" fill="#ffb547"/>' +
      '<path d="M35 38V21l12 9Z" fill="#ff9d8f"/><path d="M101 38V21l-12 9Z" fill="#ff9d8f"/>' +
      '<ellipse cx="68" cy="58" rx="46" ry="38" fill="#ffc463"/>' +
      '<path d="M58 24l2 12M68 22v13M78 24l-2 12" stroke="#f29b2e" stroke-width="3.4" stroke-linecap="round"/>' +
      '<path d="M22 58c0-30 20-44 46-44s46 14 46 44" stroke="#3d4456" stroke-width="5" fill="none"/>' +
      '<rect x="12" y="48" width="16" height="26" rx="8" fill="#3d4456"/><rect x="108" y="48" width="16" height="26" rx="8" fill="#3d4456"/>' +
      '<path d="M48 58q5-6 10 0M78 58q5-6 10 0" stroke="#2b1a12" stroke-width="3.4" fill="none" stroke-linecap="round"/>' +
      BLUSH(40, 70) + BLUSH(96, 70) +
      '<path d="M64 70h8l-4 4Z" fill="#ff8f86"/><path d="M60 78q8 9 16 0" fill="#7a2e22"/>' +
      '<path d="M30 70h12M28 76h13M106 70H94M108 76H95" stroke="#e8a64a" stroke-width="1.8" stroke-linecap="round"/>' +
      '<rect x="88" y="94" width="9" height="30" rx="4" fill="#3d4456" transform="rotate(18 92 108)"/>' +
      '<circle cx="98" cy="90" r="11" fill="#5b6378"/><path d="M92 86h12M91 91h14M93 96h10" stroke="#8e97ab" stroke-width="1.6"/>' +
      '<circle cx="88" cy="112" r="8" fill="#ffc463"/>' +
      '<path d="M112 40c6-6 12-6 14-2M118 26c4-3 8-2 9 1" stroke="#ff7a1a" stroke-width="3" fill="none" stroke-linecap="round"/></svg>',

    // A penguin in a graduation cap.
    penguin:
      '<svg viewBox="0 0 140 150" aria-hidden="true" focusable="false">' +
      SHADOW +
      '<ellipse cx="50" cy="139" rx="12" ry="5" fill="#ff8a2b"/><ellipse cx="90" cy="139" rx="12" ry="5" fill="#ff8a2b"/>' +
      '<path d="M28 96c-12 10-14 24-8 30 8-4 14-14 16-24Z" fill="#3a4466"/><path d="M112 96c12 10 14 24 8 30-8-4-14-14-16-24Z" fill="#3a4466"/>' +
      '<path d="M70 26c28 0 44 26 44 62s-18 48-44 48-44-12-44-48 16-62 44-62Z" fill="#3a4466" stroke="#56628a" stroke-width="2"/>' +
      '<path d="M70 50c18 0 30 18 30 42s-12 36-30 36-30-12-30-36 12-42 30-42Z" fill="#fffaf2"/>' +
      '<path d="M44 58c4-10 14-14 26-6 12-8 22-4 26 6-8 6-18 8-26 4-8 4-18 2-26-4Z" fill="#fffaf2"/>' +
      EYE(57, 62) + EYE(83, 62) + BLUSH(48, 76) + BLUSH(92, 76) +
      '<path d="M63 72h14l-7 9Z" fill="#ff8a2b"/>' +
      '<path d="M30 26 70 12l40 14-40 14Z" fill="#232838"/><path d="M48 32v12c12 7 32 7 44 0V32l-22 8Z" fill="#2d3346"/>' +
      '<path d="M104 28v20" stroke="#ffc21a" stroke-width="2.6"/><circle cx="104" cy="51" r="4.4" fill="#ffc21a"/></svg>',

    // A bunny holding up a star.
    bunny:
      '<svg viewBox="0 0 140 150" aria-hidden="true" focusable="false">' +
      SHADOW +
      '<path d="M50 50C40 30 40 6 50 4s16 24 14 44Z" fill="#f7efff" stroke="#d9c5f2" stroke-width="2"/><path d="M52 42c-5-12-6-26-2-30s8 14 8 28Z" fill="#ffc6d4"/>' +
      '<path d="M86 50c10-20 10-44 0-46S70 28 72 48Z" fill="#f7efff" stroke="#d9c5f2" stroke-width="2"/><path d="M84 42c5-12 6-26 2-30s-8 14-8 28Z" fill="#ffc6d4"/>' +
      '<ellipse cx="68" cy="116" rx="32" ry="26" fill="#f7efff" stroke="#d9c5f2" stroke-width="2"/>' +
      '<ellipse cx="68" cy="66" rx="40" ry="32" fill="#f7efff" stroke="#d9c5f2" stroke-width="2"/>' +
      EYE(54, 64) + EYE(82, 64) + BLUSH(44, 76) + BLUSH(92, 76) +
      '<path d="M64 74h8l-4 4Z" fill="#ff8f9e"/><path d="M62 80q6 6 12 0" stroke="#2b1a12" stroke-width="2.2" fill="none" stroke-linecap="round"/>' +
      '<path d="M98 100c8-8 12-20 12-30" stroke="#d9c5f2" stroke-width="13" stroke-linecap="round" fill="none"/>' +
      '<path d="M98 100c8-8 12-20 12-30" stroke="#f7efff" stroke-width="9" stroke-linecap="round" fill="none"/>' +
      '<path d="m112 46 5 10 11 1.6-8 7.8 2 11-10-5.2-10 5.2 2-11-8-7.8 11-1.6Z" fill="#ffc21a" stroke="#f0a500" stroke-width="1.5" stroke-linejoin="round"/>' +
      '<path d="M100 36l-4-6M126 40l5-5M124 70l6 3" stroke="#ffc21a" stroke-width="2.6" stroke-linecap="round"/>' +
      '<path d="M40 104c-8 4-12 10-12 16" stroke="#d9c5f2" stroke-width="13" stroke-linecap="round" fill="none"/>' +
      '<path d="M40 104c-8 4-12 10-12 16" stroke="#f7efff" stroke-width="9" stroke-linecap="round" fill="none"/></svg>',
  };

  // A tip for each band, said by its companion.
  const CAST = {
    A1: { name: "owl", tip: "Câu ngắn cũng được, cứ nói ra nhé!" },
    A2: { name: "robot", tip: "Mỗi ngày 3 phút là giữ được chuỗi!" },
    B1: { name: "fox", tip: "Kể chuyện có mở đầu, diễn biến, kết thúc." },
    B2: { name: "cat", tip: "Nêu ý kiến, rồi thêm một ví dụ nhé!" },
    C1: { name: "penguin", tip: "Dùng từ nối để bài nói mạch lạc hơn." },
    C2: { name: "bunny", tip: "Sắp về đích rồi, cố lên!" },
  };

  window.rmMascots = { ART, CAST };
})();
