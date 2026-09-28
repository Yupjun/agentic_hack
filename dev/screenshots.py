"""Screenshots of every dashboard page at the two target resolutions, plus two
machine checks per page: console errors, and visible non-SVG text smaller than 12px
(readability contract: body 14 / meta 12; 11 only inside SVG axes).
  .venv/bin/python dev/screenshots.py
"""
import json
import os
import sys
import urllib.request

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:3200"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "screens")
runs = json.load(urllib.request.urlopen("http://127.0.0.1:8091/api/runs"))
s2run = next((r["run_id"] for r in runs if r["family"] == "S2" and r["status"] == "ok"), runs[0]["run_id"])
s1run = next((r["run_id"] for r in runs if r["family"] == "S1" and r["status"] == "ok"), runs[0]["run_id"])
PAGES = [("overview", "/"), ("scenarios", "/scenarios"), ("scenario-s1-base", "/scenarios/s1-base"), ("agent", "/agent"),
         ("plans-s1", f"/runs/{s1run}?plan=risk_adjusted"), ("plans-s2", f"/runs/{s2run}?plan=cost_optimal"), ("live", "/live")]
SIZES = [("mac", 1512, 982), ("win", 1920, 1080)]
SMALL = """() => { let n = 0, ex = [];
  for (const el of document.querySelectorAll('body *')) {
    if (el.closest('svg')) continue;
    const t = [...el.childNodes].filter(c => c.nodeType === 3 && c.textContent.trim()).map(c => c.textContent.trim()).join(' ');
    if (!t) continue;
    const fs = parseFloat(getComputedStyle(el).fontSize);
    if (fs < 12) { n++; if (ex.length < 3) ex.push(fs + 'px: ' + t.slice(0, 40)); }
  } return {n, ex}; }"""
TABLES = """() => { let bad = 0, ex = [];
  for (const t of document.querySelectorAll('table')) {
    const th = [...t.querySelectorAll('thead th')].map(e => e.getBoundingClientRect().left);
    if (!th.length) continue;
    for (const tr of t.querySelectorAll('tbody tr')) {
      const td = [...tr.children].map(e => e.getBoundingClientRect().left);
      const off = td.length !== th.length || td.some((x, i) => Math.abs(x - th[i]) > 2);
      if (off) { bad++; if (ex.length < 2) ex.push(tr.innerText.slice(0, 60)); }
    }
  } return {bad, ex}; }"""
report = []
with sync_playwright() as p:
    b = p.chromium.launch()
    for tag, w, h in SIZES:
        ctx = b.new_context(viewport={"width": w, "height": h})
        for name, path in PAGES:
            pg = ctx.new_page()
            errs = []
            pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(BASE + path, wait_until="networkidle", timeout=60000)
            if name == "agent":
                pg.wait_for_timeout(2500)
            small = pg.evaluate(SMALL)
            tab = pg.evaluate(TABLES)   # added 2026-09-28 after a <tr> pseudo-element shifted every column of a row
            f = os.path.join(OUT, f"{name}-{tag}-{w}x{h}.png")
            pg.screenshot(path=f, full_page=True)
            report.append({"page": name, "size": f"{w}x{h}", "console_errors": len(errs), "errors": errs[:2], "text_below_12px": small["n"], "examples": small["ex"], "misaligned_rows": tab["bad"], "misaligned_examples": tab["ex"], "file": os.path.relpath(f)})
            pg.close()
        ctx.close()
    b.close()
json.dump(report, open(os.path.join(OUT, "report.json"), "w"), indent=1)
for r in report:
    print(f"{r['page']:18s} {r['size']:10s} console_errors {r['console_errors']}  text<12px {r['text_below_12px']}  misaligned_rows {r['misaligned_rows']} {r['examples'] or ''} {r['misaligned_examples'] or ''} {r['errors'] or ''}")
sys.exit(1 if any(r["console_errors"] or r["text_below_12px"] or r["misaligned_rows"] for r in report) else 0)
