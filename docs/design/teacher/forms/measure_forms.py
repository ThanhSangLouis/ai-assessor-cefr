"""Chụp và đo form giảng viên so với form quản trị (localhost demo).

Cần app chạy ở http://localhost:8000 với 4 tài khoản demo của demo.sh và Chrome đã cài.
Chạy: python docs/design/teacher/forms/measure_forms.py docs/design/teacher/forms/after
Ra: ảnh 1440 px và 390 px (giao diện sáng) + measure.json (hộp và style của nhãn, ô, nút).
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://localhost:8000"
OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
PW = "matkhau123"

MEASURE_JS = r"""
(sel) => {
  const root = document.querySelector(sel);
  if (!root) return {missing: sel};
  const r = (el) => { const b = el.getBoundingClientRect(); return [Math.round(b.x), Math.round(b.y), Math.round(b.width), Math.round(b.height)]; };
  const cs = (el, ks) => { const s = getComputedStyle(el); return Object.fromEntries(ks.map(k => [k, s[k]])); };
  const out = {form: r(root), form_style: cs(root, ['display','gap','rowGap','columnGap','padding'])};
  out.labels = [...root.querySelectorAll('label')].filter(e => e.offsetParent).map(l => ({text: l.innerText.trim().slice(0,40), box: r(l), ...cs(l, ['fontSize','fontWeight','color','marginTop','marginBottom','display'])}));
  out.controls = [...root.querySelectorAll('input:not([type=hidden]):not([type=file]),select,textarea')].filter(e => e.offsetParent).map(c => ({tag: c.tagName.toLowerCase(), name: c.name || c.id, box: r(c), ...cs(c, ['height','paddingTop','paddingLeft','fontSize','borderRadius','borderColor','backgroundColor','marginTop','marginBottom'])}));
  out.buttons = [...root.querySelectorAll('button')].filter(e => e.offsetParent).map(b => ({text: b.innerText.trim().slice(0,30), cls: b.className, box: r(b), ...cs(b, ['height','paddingTop','paddingLeft','fontSize','fontWeight','borderRadius','backgroundColor','color','borderColor','marginTop'])}));
  const card = root.closest('.card, dialog');
  if (card) out.container = {tag: card.tagName.toLowerCase(), cls: card.className, box: r(card), ...cs(card, ['paddingTop','paddingLeft','borderRadius','borderColor','backgroundColor','width'])};
  const h = card && card.querySelector('h2');
  if (h) out.h2 = {text: h.innerText.trim(), box: r(h), ...cs(h, ['fontFamily','fontSize','fontWeight','color','marginBottom'])};
  out.overflowX = document.documentElement.scrollWidth > document.documentElement.clientWidth;
  return out;
}
"""


def login(ctx, email):
    r = ctx.request.post(f"{BASE}/api/v1/auth/login", data={"email": email, "password": PW})
    assert r.ok, r.text()


def seed(ctx):
    login(ctx, "gv-01@demo.speakup.fit")
    have = ctx.request.get(f"{BASE}/api/v1/classes").json()
    if not have:
        c = ctx.request.post(f"{BASE}/api/v1/classes", data={"name": "Tiếng Anh 2 · nhóm 03"}).json()
        ctx.request.post(
            f"{BASE}/api/v1/classes/{c['class_id']}/members",
            data={"people": ["sv-001@demo.speakup.fit", "sv-002@demo.speakup.fit"]},
        )
    return ctx.request.get(f"{BASE}/api/v1/classes").json()[0]["class_id"]


def shoot(page, name, sel=None):
    page.evaluate("document.fonts.ready")
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=True)
    return page.evaluate(MEASURE_JS, sel) if sel else None


def main():
    res = {}
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        for vw, vh in ((1440, 900), (390, 844)):
            tag = f"{vw}"
            # quản trị: mẫu chuẩn
            ctx = b.new_context(viewport={"width": vw, "height": vh}, color_scheme="light")
            login(ctx, "qt-01@demo.speakup.fit")
            pg = ctx.new_page()
            pg.goto(f"{BASE}/admin", wait_until="networkidle")
            res[f"admin_acc_form@{tag}"] = shoot(pg, f"admin-accounts-{tag}", "#acc-form")
            ctx.close()
            # giảng viên
            ctx = b.new_context(viewport={"width": vw, "height": vh}, color_scheme="light")
            cid = seed(ctx)
            pg = ctx.new_page()
            pg.goto(f"{BASE}/teach/classes", wait_until="networkidle")
            pg.wait_for_selector("#new-class")
            res[f"classes_new@{tag}"] = shoot(pg, f"classes-list-{tag}", "#new-class")
            pg.goto(f"{BASE}/teach/classes/{cid}", wait_until="networkidle")
            pg.wait_for_selector("#members-form")
            res[f"classes_members@{tag}"] = shoot(pg, f"classes-detail-{tag}", "#members-form")
            pg.goto(f"{BASE}/teach/tasks", wait_until="networkidle")
            res[f"tasks_toolbar@{tag}"] = shoot(pg, f"tasks-{tag}", ".bank-toolbar")
            pg.click("#bank-add")
            pg.wait_for_selector("#task-dialog[open]")
            res[f"tasks_dialog@{tag}"] = shoot(pg, f"tasks-dialog-{tag}", "#task-form")
            pg.goto(f"{BASE}/teach", wait_until="networkidle")
            pg.click("#new-path")
            pg.wait_for_selector("#path-dialog[open]")
            res[f"path_dialog@{tag}"] = shoot(pg, f"path-dialog-{tag}", "#path-form")
            ctx.close()
        b.close()
    (OUT / "measure.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("ok", OUT)


main()
