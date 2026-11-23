"""Đo mockup bằng Chrome cục bộ; chỉ ghi vào thư mục mockup."""
from functools import partial
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import argparse
import json
import re

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
PAGES = ["classes-list", "classes-detail", "tasks", "tasks-dialog", "path-dialog", "admin-accounts"]


class Markup(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.elements = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


def static_checks():
    """Kiểm tra cấu trúc và tham chiếu; không suy ra số đo trình duyệt."""
    report = {"status": "OK", "checks": []}

    def check(ok, description):
        report["checks"].append({"ok": bool(ok), "description": description})
        if not ok:
            report["status"] = "FAILED"

    for name in PAGES:
        text = (HERE / (name + ".html")).read_text(encoding="utf-8")
        dom = Markup(text).elements
        ids = [a["id"] for _, a in dom if "id" in a]
        check(text.startswith("<!doctype html>"), name + ": doctype")
        check(any(t == "html" and a.get("lang") == "vi" for t, a in dom), name + ": lang=vi")
        role = "admin" if name == "admin-accounts" else "teacher"
        check(any(t == "body" and a.get("class") == f"role-{role} has-sidebar staff" for t, a in dom), name + ": body")
        check(len(ids) == len(set(ids)), name + ": id duy nhất")
        styles = [a["href"] for t, a in dom if t == "link" and a.get("rel") == "stylesheet"]
        prefix = "../../../../../src/aicefr/api/static/"
        check(styles == [prefix + "style.css", prefix + "staff.css", "forms-staff.css"], name + ": thứ tự CSS")
        check(sum(t == "script" for t, _ in dom) == 1 and not any(t == "script" and "src" in a for t, a in dom), name + ": chỉ script theme")
        check(not any(t == "form" and "stack" in a.get("class", "").split() for t, a in dom), name + ": không form.stack")
        check(all("novalidate" in a for t, a in dom if t == "form"), name + ": novalidate")
        for tag, attrs in dom:
            if tag == "label":
                check(attrs.get("for") in ids, name + ": label " + str(attrs.get("for")))
            if tag == "select":
                check("hidden" in attrs and "c-select-hidden" in attrs.get("class", "") and attrs.get("data-enhanced") == "true", name + ": select gốc ẩn")
            if tag == "use":
                href = attrs["href"]
                file, fragment = href.split("#")
                check((HERE / file).is_file() and f'id="{fragment}"' in (HERE / file).read_text(encoding="utf-8"), name + ": SVG " + fragment)
        emails = re.findall(r"[\w.+-]+@[\w.-]+", text)
        check(all(e.endswith("@demo.speakup.fit") for e in emails), name + ": email demo")
        for css in styles:
            check((HERE / css).is_file(), name + ": tài nguyên " + css)
    css = (HERE / "forms-staff.css").read_text(encoding="utf-8")
    clean = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    selectors = re.findall(r"(?:^|[{}])\s*([^{}]+)\{", clean)
    check(all(s.strip().startswith(("body.staff", "@media")) for s in selectors), "CSS: mọi luật dưới body.staff")
    check(not re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(", clean), "CSS: không mã màu mới")
    source_css = (ROOT / "src/aicefr/api/static/style.css").read_text(encoding="utf-8") + (ROOT / "src/aicefr/api/static/staff.css").read_text(encoding="utf-8")
    variables = set(re.findall(r"var\((--[\w-]+)\)", css))
    check(all(re.search(re.escape(v) + r"\s*:", source_css) for v in variables), "CSS: mọi token đã tồn tại")
    check(not re.search(r"\bselect\b", clean), "CSS: không nhắm select")
    (HERE / "static-checks.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


class Assets(SimpleHTTPRequestHandler):
    """CSS gốc có URL /static/fonts; ánh xạ tại chỗ, không sửa CSS gốc."""

    def translate_path(self, path):
        if path.startswith("/static/"):
            path = "/src/aicefr/api" + path
        return super().translate_path(path)

    def log_message(self, *_):
        pass


MEASURE = r"""() => {
  const rect = e => { const r=e.getBoundingClientRect(); return {x:r.x,y:r.y,w:r.width,h:r.height,b:r.bottom,r:r.right}; };
  const visible = e => e.getBoundingClientRect().height > 0 && getComputedStyle(e).visibility !== 'hidden';
  const all = s => [...document.querySelectorAll(s)].filter(visible);
  const mobile = innerWidth <= 720;
  const result = {};
  const check = (id, pass, actual) => { (result[id] ||= []).push({ok:!!pass, actual}); };
  const eq = (a,b,t=0) => Math.abs(a-b)<=t;
  const controls = all('input:not([hidden]), .c-dropdown-trigger, .inline-form button, .toolbar-controls button, dialog.sheet button');
  controls.forEach(e=>check('S1',eq(rect(e).h,mobile?44:40), {element:e.id||e.className,height:rect(e).h}));
  all('.field').forEach(f=>{
    const label = f.querySelector(':scope > label');
    const control = f.querySelector(':scope > input, :scope > textarea, :scope > .c-dropdown');
    if(label && control) check('S2',eq(rect(control).y-rect(label).b,8),{label:label.htmlFor,gap:rect(control).y-rect(label).b});
    const hint=f.querySelector(':scope > .field-hint');
    if(hint && control) check('S4',eq(rect(hint).y-rect(control).b,8),{gap:rect(hint).y-rect(control).b});
  });
  all('dialog.sheet form').forEach(form=>{
    const blocks=[...form.children].filter(e=>e.matches('.field,.field-row'));
    for(let i=1;i<blocks.length;i++) {
      const a=blocks[i-1], b=blocks[i];
      const labels=b.querySelectorAll('label');
      const gap=rect(labels[0]).y-rect(a).b;
      check('S3',eq(gap,16),{form:form.id,gap});
    }
    all('#'+form.id+' .field-row').forEach(row=>{
      const fields=[...row.children];
      for(let i=1;i<fields.length;i++) if(rect(fields[i]).y>rect(fields[i-1]).y) {
        const gap=rect(fields[i]).y-rect(fields[i-1]).b;
        check('S3',eq(gap,16),{form:form.id,gap});
      }
    });
    check('S11',!form.classList.contains('stack'),{form:form.id,stack:form.classList.contains('stack')});
    const row=form.querySelector('.button-row');
    const previous=row.previousElementSibling;
    const buttons=[...row.querySelectorAll('button')];
    const r0=rect(buttons[0]), r1=rect(buttons[1]);
    check('S12',eq(rect(row).y-rect(previous).b,24),{before:rect(row).y-rect(previous).b});
    check('S12',mobile ? eq(r1.y-r0.b,12)&&eq(r0.w,rect(form).w)&&eq(r1.w,rect(form).w) : eq(r1.x-r0.r,12)&&eq(r0.y,r1.y),{gap:mobile?r1.y-r0.b:r1.x-r0.r,widths:[r0.w,r1.w]});
    check('S12',buttons[0].textContent==='Lưu'&&buttons[1].textContent==='Huỷ'&&buttons[1].classList.contains('secondary'),{order:buttons.map(b=>b.textContent)});
  });
  all('.inline-form.one-line').forEach(f=>{
    const input=f.querySelector('input'), button=f.querySelector('button');
    const a=rect(input),b=rect(button),w=rect(f).w;
    check('S5',mobile ? eq(a.w,w)&&eq(b.w,w)&&eq(b.y-a.b,12) : eq(a.y,b.y)&&eq(a.b,b.b),{input:a,button:b,gap:b.y-a.b});
  });
  all('.field-name input').forEach(e=>check('S6',eq(rect(e).w,mobile?324:360,1),{width:rect(e).w}));
  all('.field-list input').forEach(e=>check('S7',mobile?eq(rect(e).w,rect(e.closest('form')).w,1):rect(e).w>=359&&rect(e).w<=641,{width:rect(e).w}));
  if(!mobile) all('.one-line input').forEach(e=>{
    const s=getComputedStyle(e), canvas=document.createElement('canvas');
    const ctx=canvas.getContext('2d'); ctx.font=s.font;
    const text=ctx.measureText(e.placeholder).width;
    const available=e.clientWidth-parseFloat(s.paddingLeft)-parseFloat(s.paddingRight);
    check('S8',text<=available,{id:e.id,textWidth:text,available});
  });
  const tools=document.querySelector('.task-bank .toolbar-controls');
  if(tools) {
    const search=rect(tools.querySelector('input')), drop=rect(tools.querySelector('.c-dropdown')), button=rect(tools.querySelector('#bank-add')), t=rect(tools);
    check('S9',mobile ? [search,drop,button].every(r=>eq(r.w,t.w))&&eq(drop.y-search.b,8)&&eq(button.y-drop.b,8) : eq(t.h,40)&&eq(drop.w,160)&&search.w<=420&&eq(search.y,drop.y)&&eq(drop.y,button.y)&&eq(button.r,t.r),{toolbar:t,search,dropdown:drop,button});
  }
  const band=document.querySelector('#task-form .field-row .c-dropdown');
  if(band) { const form=rect(document.querySelector('#task-form')); check('S10',eq(rect(band).w,mobile?form.w:(form.w-16)/2,1),{width:rect(band).w,formWidth:form.w}); }
  all('.card').forEach(e=>{ const s=getComputedStyle(e);const p=['Top','Right','Bottom','Left'].map(k=>parseFloat(s['padding'+k])); check('S13',p.every(n=>eq(n,mobile?16:24)),p); });
  all('.row-actions button.danger').forEach(e=>{
    const s=getComputedStyle(e);
    check('S14',eq(rect(e).h,32)&&e.classList.contains('small')&&!!e.getAttribute('aria-label')&&s.borderTopStyle==='solid'&&parseFloat(s.borderTopWidth)===1,{height:rect(e).h,label:e.getAttribute('aria-label'),border:s.borderTopColor,background:s.backgroundColor,confirm:'NOT_EVALUATED: mockup không có JS nghiệp vụ'});
  });
  const classes=document.querySelector('.classes-table');
  if(classes) check('S15',classes.closest('.card').querySelector('.list-toolbar h2')&&classes.closest('.table-scroll')&&classes.querySelectorAll('tbody tr').length===3&&classes.querySelectorAll('.badge').length===3,{headings:[...classes.querySelectorAll('th')].map(e=>e.textContent),rows:classes.querySelectorAll('tbody tr').length,frame:rect(classes.closest('.table-scroll')),table:rect(classes)});
  // V1: so với h2 thật của thẻ; trang Đề chưa có h2 thì tạo probe tạm cùng selector.
  const dialogHeadings=all('dialog.sheet h2').map(heading=>{
    let reference=document.querySelector('.card h2');
    const probe=!reference;
    if(probe) {
      reference=document.createElement('h2');
      reference.textContent='Tiêu đề tham chiếu';
      reference.style.cssText='position:absolute;visibility:hidden';
      document.querySelector('.card').appendChild(reference);
    }
    const actual=getComputedStyle(heading), expected=getComputedStyle(reference);
    const values={
      heading:heading.id,color:actual.color,referenceColor:expected.color,
      fontFamily:actual.fontFamily,fontSize:actual.fontSize,
      fontWeight:actual.fontWeight,referenceFontWeight:expected.fontWeight
    };
    if(probe) reference.remove();
    return {element:heading,values};
  });
  // V2: nút giữ đệm ngang 16px, kể cả trigger dropdown; icon-only có luật vuông riêng.
  all('form button:not(.icon-only), .toolbar-controls button:not(.icon-only), dialog.sheet button:not(.icon-only)').forEach(e=>{
    const s=getComputedStyle(e), left=parseFloat(s.paddingLeft), right=parseFloat(s.paddingRight);
    check('V2',eq(left,16)&&eq(right,16),{element:e.id||e.className,paddingLeft:left,paddingRight:right});
  });
  // V3: toàn bộ thao tác theo hàng cao 32px; nút biểu tượng rộng đúng 32px.
  all('.row-actions button').forEach(e=>{
    const r=rect(e), square=e.classList.contains('icon-only');
    check('V3',eq(r.h,32)&&(!square||eq(r.w,32)),{element:e.id||e.className,height:r.h,width:r.w,iconOnly:square});
  });
  // V4: đo tới mép trong viền thẻ, không cộng 1px border vào padding.
  all('.card').forEach(card=>{
    const last=[...card.children].filter(visible).at(-1), s=getComputedStyle(card);
    const padding=parseFloat(s.paddingBottom), border=parseFloat(s.borderBottomWidth);
    const gap=last ? rect(card).b-border-rect(last).b : null;
    check('V4',last&&eq(gap,padding),{card:card.id||card.getAttribute('aria-labelledby')||card.className,lastChild:last?.id||last?.className,paddingBottom:padding,borderBottom:border,gap});
  });
  // V5: lưu trữ là trạng thái trung tính, không phải lỗi.
  if(classes) check('V5',classes.querySelectorAll('.badge.FAILED').length===0,{
    failedBadges:classes.querySelectorAll('.badge.FAILED').length,
    badges:[...classes.querySelectorAll('.badge')].map(e=>({text:e.textContent,classes:e.className}))
  });
  // V6: giữ bo góc hộp thoại 14px của style.css hiện hành.
  all('dialog.sheet').forEach(e=>{
    const s=getComputedStyle(e), radii=['TopLeft','TopRight','BottomRight','BottomLeft'].map(k=>s['border'+k+'Radius']);
    check('V6',radii.every(r=>r==='14px'),{dialog:e.id,borderRadius:s.borderRadius,corners:radii});
  });
  // V7: nhãn nhìn thấy giữ weight 650 và cỡ chữ --t-sm của style.css.
  all('label:not(.visually-hidden)').forEach(e=>{
    const s=getComputedStyle(e), expected=getComputedStyle(document.body).getPropertyValue('--t-sm').trim();
    const probe=document.createElement('span');
    probe.style.fontSize=expected;
    probe.style.position='absolute'; probe.style.visibility='hidden';
    document.body.appendChild(probe);
    const expectedSize=getComputedStyle(probe).fontSize;
    check('V7',s.fontWeight==='650'&&s.fontSize===expectedSize,{label:e.htmlFor,fontWeight:s.fontWeight,fontSize:s.fontSize,expectedFontSize:expectedSize});
    probe.remove();
  });
  check('S16',document.documentElement.scrollWidth===document.documentElement.clientWidth,{scrollWidth:document.documentElement.scrollWidth,clientWidth:document.documentElement.clientWidth});
  // W2: badge lưu trữ chỉ dùng màu chữ trung tính của staff ở đúng theme.
  all('.classes-table .badge').filter(e=>e.textContent.trim()==='Lưu trữ').forEach(e=>{
    const probe=document.createElement('span');
    probe.style.cssText='position:absolute;visibility:hidden;color:var(--fg-muted)';
    e.parentElement.appendChild(probe);
    const actual=getComputedStyle(e).color, expected=getComputedStyle(probe).color;
    check('W2',actual===expected,{color:actual,expectedColor:expected,classes:e.className});
    probe.remove();
  });
  // W1/V1: đo font gốc bằng cách tạm tắt CHỈ forms-staff.css, sau mọi phép đo hình học.
  // Luôn khôi phục stylesheet; không đụng đoạn chờ hiệu ứng trước MEASURE.
  const headings=all('main h1, .card h2').map(e=>({element:e,fontFamily:getComputedStyle(e).fontFamily}));
  const formStyles=[...document.querySelectorAll('link[rel="stylesheet"]')]
    .filter(e=>new URL(e.href).pathname.endsWith('/forms-staff.css'));
  const disabled=formStyles.map(e=>e.disabled);
  let baselineHeadings, baselineDialogs;
  try {
    formStyles.forEach(e=>{e.disabled=true;});
    baselineHeadings=headings.map(({element})=>getComputedStyle(element).fontFamily);
    baselineDialogs=dialogHeadings.map(({element})=>{
      const s=getComputedStyle(element); return {fontFamily:s.fontFamily,fontSize:s.fontSize};
    });
  } finally {
    formStyles.forEach((e,i)=>{e.disabled=disabled[i];});
  }
  headings.forEach(({element,fontFamily},i)=>check('W1',formStyles.length===1&&fontFamily===baselineHeadings[i],{
    element:element.id||element.textContent.trim(),fontFamily,baselineFontFamily:baselineHeadings[i]
  }));
  dialogHeadings.forEach(({values},i)=>{
    const baseline=baselineDialogs[i];
    check('V1',values.color===values.referenceColor&&values.fontWeight===values.referenceFontWeight&&
      values.fontFamily===baseline.fontFamily&&values.fontSize===baseline.fontSize,
      {...values,baselineFontFamily:baseline.fontFamily,baselineFontSize:baseline.fontSize});
  });
  return result;
}"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve", action="store_true", help="Chỉ phục vụ trang tại cổng 8765 để xem tay")
    parser.add_argument("--static-only", action="store_true", help="Chỉ kiểm tra cấu trúc, không mở Chrome")
    args = parser.parse_args()
    if not args.serve:
        static = static_checks()
        print(f"Static: {static['status']} ({len(static['checks'])} checks)", flush=True)
        if args.static_only or static["status"] != "OK":
            raise SystemExit(0 if static["status"] == "OK" else 1)
    server = ThreadingHTTPServer(("127.0.0.1", 8765 if args.serve else 0), partial(Assets, directory=str(ROOT)))
    base = f"http://127.0.0.1:{server.server_port}/docs/design/teacher/forms/mockup/"
    if args.serve:
        print(base + "classes-list.html", flush=True)
        server.serve_forever()
        return
    Thread(target=server.serve_forever, daemon=True).start()
    output = HERE / "evidence"
    output.mkdir(exist_ok=True)
    data = {"browser": "Chrome (channel=chrome)", "viewports": ["1440x900", "390x844"], "runs": []}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel="chrome", headless=True)
            data["browserVersion"] = browser.version
            for width, height in [(1440, 900), (390, 844)]:
                for theme in ["light", "dark"]:
                    for name in PAGES:
                        page = browser.new_page(viewport={"width": width, "height": height}, color_scheme="light", reduced_motion="reduce")
                        errors = []
                        page.on("pageerror", lambda e: errors.append(str(e)))
                        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
                        page.goto(base + name + ".html" + ("?theme=dark" if theme == "dark" else ""))
                        page.evaluate("document.fonts.ready")
                        # Hộp thoại mở có hiệu ứng scale(0.96) -> 1; đo giữa chừng ra 38,4px thay vì 40px.
                        page.evaluate("Promise.all(document.getAnimations().map(a => a.finished))")
                        page.wait_for_timeout(400)
                        measurements = page.evaluate(MEASURE)
                        # Thử Tab thật và đọc outline của mọi điểm focus đi qua.
                        focus = []
                        seen = set()
                        for _ in range(60):
                            page.keyboard.press("Tab")
                            item = page.evaluate("""() => {const e=document.activeElement,s=getComputedStyle(e);return {tag:e.tagName,id:e.id,cls:e.className,outline:s.outlineStyle,width:s.outlineWidth,visible:e.matches(':focus-visible'),key:e.tagName+'#'+e.id+'.'+e.className+':'+e.textContent.slice(0,40)}}""")
                            if item["tag"] == "BODY":
                                continue
                            if item["key"] in seen:
                                break
                            seen.add(item["key"])
                            focus.append(item)
                        focus_ok = bool(focus) and all(i["visible"] and i["outline"] != "none" and float(i["width"].removesuffix("px")) > 0 for i in focus)
                        measurements["S16"].append({"ok": focus_ok and not errors, "actual": {"consoleErrors": errors, "tabFocus": focus}})
                        # Ảnh ở đầu trang, không để lần Tab cuối cuộn khung ảnh.
                        page.evaluate("document.activeElement.blur(); window.scrollTo(0,0); document.querySelectorAll('.table-scroll,dialog').forEach(e=>e.scrollTo(0,0))")
                        page.screenshot(path=str(output / f"{name}-{width}-{theme}.png"), full_page=False)
                        run = {"page": name, "viewport": [width,height], "theme": theme, "measurements": measurements}
                        data["runs"].append(run)
                        bad = [s for s,checks in measurements.items() if not all(c["ok"] for c in checks)]
                        print(f"{name} {width} {theme}: " + ("OK" if not bad else ", ".join(bad)), flush=True)
                        page.close()
            browser.close()
    except Exception as exc:
        data["status"] = "NOT_RUN" if not data["runs"] else "INCOMPLETE"
        data["error"] = f"{type(exc).__name__}: {exc}"
        print(data["error"], flush=True)
    finally:
        server.shutdown()
    (output / "measurements.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    failures = [(r["page"], r["viewport"][0], r["theme"], s, c["actual"]) for r in data["runs"] for s, checks in r["measurements"].items() for c in checks if not c["ok"]]
    for failure in failures:
        print(json.dumps(failure, ensure_ascii=False))
    raise SystemExit(1 if failures or data.get("status") in ("NOT_RUN", "INCOMPLETE") else 0)


if __name__ == "__main__":
    main()
