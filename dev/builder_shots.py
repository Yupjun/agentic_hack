"""Plan Builder check: load, pick each preset, run, switch objective. Screenshots + console errors + text < 12px.
  .venv/bin/python dev/builder_shots.py
"""
import os
from playwright.sync_api import sync_playwright
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "screens")
SMALL = """() => { let n = 0; for (const el of document.querySelectorAll('body *')) { if (el.closest('svg')) continue;
  const t = [...el.childNodes].some(c => c.nodeType === 3 && c.textContent.trim()); if (t && parseFloat(getComputedStyle(el).fontSize) < 12) n++; } return n; }"""
with sync_playwright() as p:
    b = p.chromium.launch()
    for tag, w, h in [("mac", 1512, 982), ("win", 1920, 1080)]:
        pg = b.new_page(viewport={"width": w, "height": h}); errs = []
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto("http://127.0.0.1:3200/builder"); pg.wait_for_selector("text=실행")
        for preset in ["P1", "P2"]:
            pg.get_by_role("button", name=preset, exact=True).click()
            pg.get_by_role("button", name="실행", exact=True).click()
            pg.wait_for_selector("text=목표별로 어떤 안이 뽑혔나?", timeout=60000)
            pg.get_by_role("button", name="최단 기간", exact=True).click()
            pg.wait_for_timeout(300)
            f = os.path.join(OUT, f"builder-{preset.lower()}-{tag}.png"); pg.screenshot(path=f, full_page=True)
            print(tag, preset, "small", pg.evaluate(SMALL), "errors", len(errs), errs[:2], f)
        pg.close()
    b.close()
