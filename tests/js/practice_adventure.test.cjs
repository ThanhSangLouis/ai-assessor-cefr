const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const adventure = require('../../src/aicefr/api/static/practice_adventure.js');
const lessons = count => Array.from({length: count}, (_, i) => ({lesson_id: `lesson-${i}`}));
for (const mobile of [false,true]) for (const count of [0,1,2,5,12,13,30,100]) {
  test(`${count} lessons, ${mobile?'mobile':'desktop'}: ordered, spaced, finite and contained`, () => {
    const g=adventure.geometry(mobile), points=adventure.layout(lessons(count),'lesson-0',g);
    assert.equal(points.length,count);
    const height=adventure.height(points,g);
    if (!count) assert.equal(height,0);
    points.forEach((point,i)=>{
      assert.ok(Number.isFinite(point.x)&&Number.isFinite(point.y));
      assert.ok(Math.abs(point.x)<=g.swing[1]);
      assert.ok(point.y < height);
      if(i) assert.ok(point.y-points[i-1].y >= g.row);
    });
    const chapters=adventure.chapters(points);
    assert.equal(chapters.length,count>12?Math.ceil(count/12):0);
    assert.equal(new Set(chapters.map(c=>c.number)).size,chapters.length);
    for(const band of Object.keys(adventure.THEMES)) {
      const html=adventure.sceneryHtml(band,'stable-key',points,height,'left',true);
      for(const [,url] of html.matchAll(/src="([^"]+)"/g)) {
        assert.ok(fs.existsSync(path.join(__dirname,'../../src/aicefr/api',url)),url);
      }
      assert.ok(!html.includes('<img'));
    }
  });
}
test('teacher inserts and removes lessons: IDs remain ordered and no input is mutated',()=>{
 const original=lessons(30), before=JSON.stringify(original);
 adventure.layout(original,'lesson-20',adventure.geometry(false));
 assert.equal(JSON.stringify(original),before);
 const inserted=[...original.slice(0,8),{lesson_id:'new-from-teacher'},...original.slice(8)];
 assert.equal(adventure.layout(inserted,null,adventure.geometry(false)).length,31);
 assert.equal(adventure.layout(inserted.slice(1),null,adventure.geometry(true)).length,30);
});
test('unified scenery excludes scattered props and injected keys',()=>{
 const g=adventure.geometry(false),p=adventure.layout(lessons(12),null,g);
 const html=adventure.sceneryHtml('A1','<img onerror=alert(1)>',p,adventure.height(p,g),'left',true);
 assert.ok(!html.includes('<img'));
 assert.ok(html.includes('aria-hidden="true"'));
 assert.ok(!html.includes('onerror'));
});
test('all six worlds use paired native day/night terrain without a dimming filter',()=>{
 const css=fs.readFileSync(path.join(__dirname,'../../src/aicefr/api/static/practice_adventure.css'),'utf8');
 const backgrounds=[...css.matchAll(/url\('([^']+-(?:day|night)-[ab]-v3-[^']+)'\)/g)].map(m=>m[1]);
 assert.equal(new Set(backgrounds).size,120);
 for(const world of ['forest','volcano','snow','river','desert','flowers']) {
  assert.equal(new Set(backgrounds.filter(url=>url.includes(`/${world}-`))).size,20);
 }
 for(const url of backgrounds) assert.ok(fs.existsSync(path.join(__dirname,'../../src/aicefr/api',url)),url);
 assert.ok(!css.includes('brightness('));
 assert.ok(!css.includes('/landscape-'));
});

for (const width of [280, 360, 760, 1240]) {
 test(`terrain at ${width}px: lesson count changes coverage, never scale`, () => {
  for (const ratio of [2/3, 3]) {
   for (const count of [1, 3, 5, 15, 50]) {
    const h = adventure.height(adventure.layout(lessons(count), 'lesson-0', adventure.geometry(width <= 700)), adventure.geometry(width <= 700));
    const tiles = adventure.terrainTiles(h, width, ratio);
    assert.equal(tiles[0].top, 0);
    assert.equal(tiles[0].height, width * ratio);
    assert.ok(tiles.at(-1).top + tiles.at(-1).height >= h);
    assert.ok(tiles.length === 1 || tiles.at(-2).top + tiles.at(-2).height < h);
    for (let i=1;i<tiles.length;i++) assert.ok(Math.abs(tiles[i-1].top + tiles[i-1].height - tiles[i].top - tiles[i].overlap) < .001);
   }
  }
 });
}
test('terrain ignores invalid dimensions', () => {
 for (const args of [[0,390], [200,0], [NaN,390], [200,Infinity], [200,390,0]]) assert.deepEqual(adventure.terrainTiles(...args), []);
});
test('forest day/night responsive exports referenced by CSS exist', () => {
 const css=fs.readFileSync(path.join(__dirname,'../../src/aicefr/api/static/practice_adventure.css'),'utf8');
 const urls=[...css.matchAll(/url\('([^']+forest-(?:day|night)-[^']+)'\)/g)].map(m=>m[1]);
 assert.equal(new Set(urls).size,20);
 for(const url of urls) assert.ok(fs.existsSync(path.join(__dirname,'../../src/aicefr/api',url)),url);
});
