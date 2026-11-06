// Pure layout and scenery rules. Lesson IDs, order and access rules stay in practice_path.js.
(function (root) {
  'use strict';
  const CHAPTER_SIZE = 12;
  const THEMES = {
    A1: { title: 'Rừng xanh', world: 'forest' },
    A2: { title: 'Miền núi lửa', world: 'volcano' },
    B1: { title: 'Xứ tuyết', world: 'snow' },
    B2: { title: 'Dòng sông ngọc', world: 'river' },
    C1: { title: 'Sa mạc vàng', world: 'desert' },
    C2: { title: 'Đồng hoa', world: 'flowers' },
  };
  function geometry(mobile) {
    return mobile
      ? { row: 96, top: 48, flag: 32, tail: 48, swing: [-28, 28], chapterGap: 48, minHeight: 220 }
      : { row: 120, top: 64, flag: 40, tail: 60, swing: [-76, 76], chapterGap: 56, minHeight: 300 };
  }
  function layout(lessons, nextId, g) {
    let y = g.top;
    return lessons.map((lesson, i) => {
      if (i && i % CHAPTER_SIZE === 0) y += g.chapterGap;
      if (lesson.lesson_id === nextId) y += g.flag;
      // A wave, rather than a hard left/right switch, makes long trails less repetitive.
      const wave = [-.55, .55, 1, 0, -1, -.55, .55, 1, 0, -1, -.55, 0];
      const point = { x: Math.round(g.swing[1] * wave[i % wave.length]), y };
      y += g.row;
      return point;
    });
  }
  function height(points, g) {
    return points.length ? Math.max(g.minHeight, points[points.length - 1].y + g.tail) : 0;
  }
  function chapters(points) {
    const out = [];
    if (points.length <= CHAPTER_SIZE) return out;
    for (let start = 0; start < points.length; start += CHAPTER_SIZE) {
      out.push({ number: start / CHAPTER_SIZE + 1, start, end: Math.min(points.length, start + CHAPTER_SIZE), y: Math.max(8, points[start].y - 54) });
    }
    return out;
  }
  // Scale only with width. Clip excess terrain for short sections; append
  // overlapping strips for long ones without stretching the painted pixels.
  function terrainTiles(height, width, ratio = 3) {
    if (![height, width, ratio].every(Number.isFinite) || height <= 0 || width <= 0 || ratio <= .045) return [];
    const tileHeight = width * ratio;
    const overlap = width * .045;
    const step = tileHeight - overlap;
    const count = Math.max(1, Math.ceil((height - tileHeight) / step) + 1);
    return Array.from({ length: count }, (_, index) => ({ index, top: index * step, height: tileHeight, overlap }));
  }
  function sceneryHtml() {
    // The unified 2.5D environment replaces individually scattered decorations.
    return '<div class="rm-adventure-scenery" aria-hidden="true"></div>';
  }
  const api = { CHAPTER_SIZE, THEMES, geometry, layout, height, chapters, sceneryHtml, terrainTiles };
  root.rmAdventure = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
