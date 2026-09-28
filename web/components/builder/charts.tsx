// SVG charts for the Plan Builder. Graphite for everything, cobalt only for the selected plan, tomato for the
// deadline / late side. Direct labels, no legends where avoidable. Never scaled down: containers scroll.
import type { DagSpec, Plan, Result } from "./types";
import { usd } from "./types";

const AX = { fontSize: 11, fill: "var(--faint)" } as const;

// Q: which plans are cheapest for each finish time, and where does the chosen one sit?
export function ParetoChart({ r, sel, onSel, deadline }: { r: Result; sel: string; onSel: (k: string) => void; deadline: number }) {
  const W = 620, H = 300, L = 70, R = 20, T = 16, B = 40;
  const pts = r.cloud ?? [];
  const front = [...(r.pareto ?? [])].sort((a, b) => a.makespan_days - b.makespan_days);
  const xs = [...pts.map((p) => p.makespan_days), ...front.map((p) => p.makespan_days), deadline];
  const ys = [...pts.map((p) => p.cost_usd), ...front.map((p) => p.cost_usd)];
  const x0 = Math.min(...xs) * 0.95, x1 = Math.max(...xs) * 1.03, y0 = Math.min(...ys) * 0.95, y1 = Math.max(...ys) * 1.03;
  const X = (v: number) => L + ((v - x0) / (x1 - x0 || 1)) * (W - L - R), Y = (v: number) => T + (1 - (v - y0) / (y1 - y0 || 1)) * (H - T - B);
  const named = Object.entries(r.named ?? {});
  return (
    <div className="overflow-x-auto"><svg width={W} height={H}>
      {[0, 0.5, 1].map((f) => { const v = y0 + (y1 - y0) * f; return <g key={f}><line x1={L} x2={W - R} y1={Y(v)} y2={Y(v)} stroke="var(--line)" /><text x={L - 6} y={Y(v) + 4} textAnchor="end" {...AX}>{usd(v)}</text></g>; })}
      {[0, 0.5, 1].map((f) => { const v = x0 + (x1 - x0) * f; return <text key={f} x={X(v)} y={H - B + 16} textAnchor="middle" {...AX}>{v.toFixed(0)} d</text>; })}
      <text x={W - R} y={H - 6} textAnchor="end" {...AX}>finish time (days) →</text><text x={L} y={T - 4} {...AX}>plan cost USD</text>
      <line x1={X(deadline)} x2={X(deadline)} y1={T} y2={H - B} stroke="var(--tomato)" strokeWidth={1.5} strokeDasharray="4 3" />
      <text x={X(deadline) + 4} y={T + 10} fontSize={11} fill="var(--tomato)">deadline</text>
      {pts.map((p, i) => <circle key={i} cx={X(p.makespan_days)} cy={Y(p.cost_usd)} r={2} fill="var(--graphite)" opacity={0.35} />)}
      <polyline points={front.map((p) => `${X(p.makespan_days)},${Y(p.cost_usd)}`).join(" ")} fill="none" stroke="var(--ink)" strokeWidth={1.5} />
      {front.map((p) => <rect key={p.key} x={X(p.makespan_days) - 4} y={Y(p.cost_usd) - 4} width={8} height={8} fill={p.key === sel ? "var(--cobalt)" : "var(--ink)"} style={{ cursor: "pointer" }} onClick={() => onSel(p.key)} />)}
      {named.map(([name, key], i) => { const p = front.find((f) => f.key === key); if (!p) return null;
        return <text key={name} x={X(p.makespan_days) + 8} y={Y(p.cost_usd) - 6 - (i % 2) * 12} fontSize={12} fill={key === sel ? "var(--cobalt)" : "var(--ink)"}>{name}</text>; })}
    </svg></div>
  );
}

// Q: how likely is this plan to finish by the deadline?
export function Histogram({ p, deadline }: { p: Plan; deadline: number }) {
  const W = 520, H = 220, L = 40, R = 16, T = 20, B = 36;
  const h = p.mc.histogram, n = h.counts.length, mx = Math.max(...h.counts, 1);
  const lo = Math.min(h.lo, deadline) - 1, hi = Math.max(h.lo + h.width * n, deadline) + 1;
  const X = (v: number) => L + ((v - lo) / (hi - lo)) * (W - L - R), bw = Math.max(2, X(h.lo + h.width) - X(h.lo) - 1);
  return (
    <div className="overflow-x-auto"><svg width={W} height={H}>
      {h.counts.map((c, i) => { const x = h.lo + i * h.width; const late = x + h.width / 2 > deadline;
        return <rect key={i} x={X(x)} y={T + (1 - c / mx) * (H - T - B)} width={bw} height={(c / mx) * (H - T - B)} fill={late ? "var(--tomato)" : "var(--graphite)"} />; })}
      <line x1={X(deadline)} x2={X(deadline)} y1={T - 8} y2={H - B} stroke="var(--tomato)" strokeWidth={2} />
      <text x={X(deadline) + 4} y={T - 2} fontSize={12} fill="var(--tomato)">deadline {deadline} d</text>
      {[lo, (lo + hi) / 2, hi].map((v) => <text key={v} x={X(v)} y={H - B + 16} textAnchor="middle" {...AX}>{v.toFixed(0)} d</text>)}
      <text x={W - R} y={H - 4} textAnchor="end" {...AX}>finish time, {p.mc.p_on_time >= 0 ? `${(p.mc.p_on_time * 100).toFixed(1)} % on time` : ""}</text>
    </svg></div>
  );
}

// Q: when does each task run, how much slack does it have, and which ones are critical?
export function Gantt({ spec, p, deadline }: { spec: DagSpec; p: Plan; deadline: number }) {
  const nodes = spec.steps.flatMap((s) => s.nodes);
  const W = 760, rowH = 26, L = 200, R = 20, T = 22, H = T + nodes.length * rowH + 26;
  const end = Math.max(deadline, ...nodes.map((n) => p.nodes[n.id]?.LS + (p.nodes[n.id]?.duration_days ?? 0)));
  const X = (v: number) => L + (v / (end * 1.04)) * (W - L - R);
  return (
    <div className="overflow-x-auto"><svg width={W} height={H}>
      {[0, 0.25, 0.5, 0.75, 1].map((f) => <g key={f}><line x1={X(end * f)} x2={X(end * f)} y1={T - 4} y2={H - 24} stroke="var(--line)" /><text x={X(end * f)} y={H - 8} textAnchor="middle" {...AX}>{(end * f).toFixed(0)} d</text></g>)}
      <line x1={X(deadline)} x2={X(deadline)} y1={T - 12} y2={H - 24} stroke="var(--tomato)" strokeWidth={2} /><text x={X(deadline) + 4} y={T - 4} fontSize={11} fill="var(--tomato)">deadline</text>
      {nodes.map((n, i) => { const r = p.nodes[n.id]; if (!r) return null; const y = T + i * rowH;
        return <g key={n.id}>
          <text x={8} y={y + 16} fontSize={12} fill="var(--ink)">{n.task.slice(0, 24)}</text>
          <rect x={X(r.ES)} y={y + 5} width={Math.max(2, X(r.EF) - X(r.ES))} height={rowH - 10} fill={r.critical ? "var(--cobalt)" : "var(--graphite)"} />
          {r.slack > 0.01 && <rect x={X(r.EF)} y={y + 11} width={X(r.EF + r.slack) - X(r.EF)} height={4} fill="var(--line)" />}
          <text x={X(r.EF) + 4} y={y + 16} fontSize={11} fill="var(--muted)">{r.duration_days.toFixed(1)} d{r.expedite ? " · expedite" : ""}{r.slack > 0.01 ? ` · slack ${r.slack.toFixed(1)}` : ""}</text>
        </g>; })}
    </svg></div>
  );
}

// Q: where does the money go (and how much of it is MOQ / lot overbuy)?  and Q: how often is each task critical?
export function Bars({ rows, fmt, tone }: { rows: { label: string; value: number; sub?: string; hot?: boolean }[]; fmt: (v: number) => string; tone?: "cobalt" | "tomato" }) {
  const W = 520, L = 190, R = 90, rowH = 24, H = rows.length * rowH + 8, mx = Math.max(...rows.map((r) => r.value), 1e-9);
  return (
    <div className="overflow-x-auto"><svg width={W} height={H}>
      {rows.map((r, i) => <g key={r.label}>
        <text x={8} y={i * rowH + 16} fontSize={12} fill="var(--ink)">{r.label.slice(0, 24)}</text>
        <rect x={L} y={i * rowH + 5} width={Math.max(1, (r.value / mx) * (W - L - R))} height={rowH - 10} fill={r.hot ? `var(--${tone ?? "cobalt"})` : "var(--graphite)"} />
        <text x={L + (r.value / mx) * (W - L - R) + 6} y={i * rowH + 16} fontSize={11} fill="var(--muted)">{fmt(r.value)}{r.sub ? ` ${r.sub}` : ""}</text>
      </g>)}
    </svg></div>
  );
}
