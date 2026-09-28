// Design guard (hard gate): Signal on Paper + readability contract, checked in source.
// Strips comments first (a guard must not read its own prose as a defect).
// Rules:
//  1 no raw hex outside app/globals.css           (colour lives in the palette only)
//  2 no rounded-* other than rounded-none         (radius 0)
//  3 no shadow-* utilities, no gradients          (elevation only on .stamp, in globals.css)
//  4 no dark: variants                            (no dark mode)
//  5 no arbitrary text sizes (text-[..px])        (type scale meta 12 / body 14 / lead 16 / h2 / h1 / stat)
//  6 SVG fontSize must be >= 11                   (11 only for axes and node subtitles)
//  7 colour utilities must use palette tokens     (bg-/text-/border-/fill-/stroke- + token)
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

const ROOT = new URL("..", import.meta.url).pathname;
const TOKENS = ["transparent", "current", "ground", "sheet", "ink", "muted", "faint", "line", "cobalt", "tomato", "butter", "butter-ink", "plum", "green", "mustard", "graphite"];
const SIZES = ["meta", "body", "lead", "h2", "h1", "stat", "left", "right", "center"];
const files = [];
const walk = (d) => { for (const f of readdirSync(d)) { const p = join(d, f); if (statSync(p).isDirectory()) walk(p); else if (/\.(tsx?|css)$/.test(f)) files.push(p); } };
walk(join(ROOT, "app")); walk(join(ROOT, "components"));

const strip = (s) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:"'`])\/\/.*$/gm, "$1");
const problems = [];
for (const f of files) {
  const rel = f.slice(ROOT.length);
  const src = strip(readFileSync(f, "utf8"));
  const lines = src.split("\n");
  lines.forEach((line, i) => {
    const at = `${rel}:${i + 1}`;
    if (!rel.endsWith("globals.css") && /#[0-9a-fA-F]{3,8}\b/.test(line) && !/href=|#anchor/.test(line)) problems.push(`${at} raw hex colour`);
    for (const m of line.matchAll(/\brounded(-[a-z0-9]+)?\b/g)) if (m[0] !== "rounded-none") problems.push(`${at} ${m[0]} (radius must be 0)`);
    if (/\bshadow-(sm|md|lg|xl|2xl|inner)\b|\bshadow\b(?![-:])/.test(line.replace(/box-shadow/g, "")) && !rel.endsWith("globals.css")) problems.push(`${at} shadow utility`);
    if (/gradient/.test(line)) problems.push(`${at} gradient`);
    if (/\bdark:/.test(line)) problems.push(`${at} dark: variant`);
    if (/\btext-\[\d+px\]/.test(line)) problems.push(`${at} arbitrary text size`);
    for (const m of line.matchAll(/fontSize=\{(\d+)\}/g)) if (Number(m[1]) < 11) problems.push(`${at} SVG fontSize ${m[1]} < 11`);
    for (const m of line.matchAll(/\b(bg|text|border|fill|stroke|outline|ring|divide)-([a-z]+(?:-[a-z]+)?)(?:-\d{2,3})?\b/g)) {
      const [, kind, name] = m;
      if (/-\d{2,3}$/.test(m[0]) && TOKENS.includes(name)) { problems.push(`${at} ${m[0]}: palette tokens have no shades (the class would silently render nothing)`); continue; }
      if (kind === "text" && SIZES.includes(name)) continue;
      if (kind === "border" && ["b", "t", "l", "r", "x", "y", "2", "solid", "dashed"].includes(name.split("-")[0])) continue;
      if (["outline", "ring"].includes(kind) && ["none", "offset"].includes(name.split("-")[0])) continue;
      if (!TOKENS.includes(name) && /^(red|blue|green|gray|grey|slate|zinc|neutral|stone|orange|amber|yellow|lime|emerald|teal|cyan|sky|indigo|violet|purple|fuchsia|pink|rose|white|black)$/.test(name.split("-")[0]) && !TOKENS.includes(name))
        problems.push(`${at} ${m[0]} is not a palette token`);
    }
  });
}
const svgSmall = problems.filter((p) => p.includes("SVG fontSize")).length;
if (problems.length) {
  console.error(`verify-design: ${problems.length} problem(s)`);
  for (const p of problems) console.error("  " + p);
  process.exit(1);
}
console.log(`verify-design: ok (${files.length} files, 0 problems, SVG small text ${svgSmall})`);
