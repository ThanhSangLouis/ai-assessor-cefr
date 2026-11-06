// Six transparent 2.5D companions, colored for their adventure landscapes.
(function () {
  const ART = {
    forest: '<img src="/static/art/adventure/mascot-forest-v3.webp" alt="" width="1254" height="1254" loading="lazy" decoding="async">',
    volcano: '<img src="/static/art/adventure/mascot-volcano-v3.webp" alt="" width="1254" height="1254" loading="lazy" decoding="async">',
    snow: '<img src="/static/art/adventure/mascot-snow-v3.webp" alt="" width="1254" height="1254" loading="lazy" decoding="async">',
    river: '<img src="/static/art/adventure/mascot-river-v3.webp" alt="" width="1254" height="1254" loading="lazy" decoding="async">',
    desert: '<img src="/static/art/adventure/mascot-desert-v3.webp" alt="" width="1254" height="1254" loading="lazy" decoding="async">',
    flowers: '<img src="/static/art/adventure/mascot-flowers-v3.webp" alt="" width="1254" height="1254" loading="lazy" decoding="async">',
  };

  // A tip for each band, said by its companion.
  const CAST = {
    A1: { name: "forest", tip: "Câu ngắn cũng được, cứ nói ra nhé!" },
    A2: { name: "volcano", tip: "Mỗi ngày 3 phút là giữ được chuỗi!" },
    B1: { name: "snow", tip: "Kể chuyện có mở đầu, diễn biến, kết thúc." },
    B2: { name: "river", tip: "Nêu ý kiến, rồi thêm một ví dụ nhé!" },
    C1: { name: "desert", tip: "Dùng từ nối để bài nói mạch lạc hơn." },
    C2: { name: "flowers", tip: "Sắp về đích rồi, cố lên!" },
  };

  window.rmMascots = { ART, CAST };
})();
