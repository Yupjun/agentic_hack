"""Globe check: the plan page renders the WebGL globe, and moving the time cursor changes shipment states.
  .venv/bin/python dev/globe_shots.py"""
import json, os, urllib.request
from playwright.sync_api import sync_playwright
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "screens")
runs = json.load(urllib.request.urlopen("http://127.0.0.1:8091/api/runs"))
pick = {f: next(r["run_id"] for r in runs if r["family"] == f and r["status"] == "ok") for f in ("S1", "S2")}
res = []
with sync_playwright() as p:
    b = p.chromium.launch(args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
    pg = b.new_page(viewport={"width": 1920, "height": 1080})
    errs = []
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errs.append(str(e)))
    for fam, run in pick.items():
        pg.goto(f"http://127.0.0.1:3200/runs/{run}?plan=risk_adjusted", wait_until="networkidle", timeout=90000)
        pg.wait_for_selector("canvas", timeout=60000)
        pg.wait_for_timeout(4000)
        canvas = pg.locator("canvas").first
        box = canvas.bounding_box()
        states = []
        for frac, tag in ((0.0, "start"), (0.5, "mid"), (0.97, "end")):
            slider = pg.locator('input[aria-label="time"]')
            mn, mx = float(slider.get_attribute("min")), float(slider.get_attribute("max"))
            v = mn + (mx - mn) * frac
            slider.evaluate("(el, v) => { const s = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set; s.call(el, String(v)); el.dispatchEvent(new Event('input', {bubbles:true})); el.dispatchEvent(new Event('change', {bubbles:true})); }", v)
            pg.wait_for_timeout(1500)
            summary = pg.locator("text=at 20").first.locator("xpath=..").inner_text()
            f = os.path.join(OUT, f"globe-{fam}-{tag}.png")
            canvas.locator("xpath=../..").screenshot(path=f)
            states.append({"tag": tag, "summary": " ".join(summary.split())[:200], "file": os.path.relpath(f)})
        # does the canvas have non-blank pixels? sample via screenshot bytes size as a proxy + center pixel check
        res.append({"family": fam, "run": run, "canvas": box, "states": states})
    res.append({"console_errors": errs[:5], "n_errors": len(errs)})
    b.close()
print(json.dumps(res, indent=1, ensure_ascii=False))
