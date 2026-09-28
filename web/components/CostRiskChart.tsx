// Question: does the cheapest plan actually arrive on time?
// x = plan cost, y = probability every demand is on time (Monte Carlo). Plans that land on the same
// point share ONE marker and ONE label (listing their names). Graphite for all points; cobalt only for
// the point that contains the hero plan, drawn last so nothing covers it. Direct labels, no legend.
// Labels are placed in a column to the right of the plot so they never overlap. Never scaled down.
import type { PlanRow } from "@/lib/types";

const W = 900, H = 320, L = 64, PR = 620, T = 20, B = 48;

export function CostRiskChart({ rows, hero = "risk_adjusted" }: { rows: PlanRow[]; hero?: string }) {
  const pts = rows.filter((r) => r.cost_usd != null && r.p_all_on_time != null && r.verify_ok);
  if (!pts.length) return <div className="text-body text-muted">no verified plans</div>;
  const groups = new Map<string, { cost: number; p: number; names: string[]; routes: string }>();
  for (const r of pts) {
    const k = `${r.cost_usd}|${r.p_all_on_time}`;
    const g = groups.get(k) ?? { cost: r.cost_usd as number, p: r.p_all_on_time as number, names: [], routes: r.routes.join("+") };
    g.names.push(r.plan.replace("_", " "));
    groups.set(k, g);
  }
  const gs = [...groups.values()].sort((a, b) => b.p - a.p || a.cost - b.cost);
  const xs = gs.map((g) => g.cost);
  const lo = Math.min(...xs), hi = Math.max(...xs);
  const step = Math.pow(10, Math.floor(Math.log10(Math.max(1, hi - lo || hi)))) ;
  const x0 = Math.floor((lo * 0.9) / step) * step, x1 = Math.ceil((hi * 1.05) / step) * step;
  const X = (v: number) => L + ((v - x0) / (x1 - x0 || 1)) * (PR - L);
  const Y = (v: number) => T + (1 - v) * (H - T - B);
  const xt: number[] = [];
  for (let v = x0; v <= x1 + 1e-9; v += (x1 - x0) / 4) xt.push(v);
  const labelY = gs.map((_, i) => T + 8 + i * ((H - T - B) / Math.max(1, gs.length - 1 || 1)));
  const heroName = hero.replace("_", " ");
  const order = [...gs.keys()].sort((a, b) => Number(gs[a].names.includes(heroName)) - Number(gs[b].names.includes(heroName)));
  return (
    <div className="overflow-x-auto">
      <svg width={W} height={H} role="img" aria-label="plan cost versus on-time probability">
        {[0, 0.25, 0.5, 0.75, 1].map((t) => (
          <g key={t}>
            <line x1={L} x2={PR} y1={Y(t)} y2={Y(t)} stroke="var(--line)" />
            <text x={L - 8} y={Y(t) + 4} textAnchor="end" fontSize={11} fill="var(--faint)">{Math.round(t * 100)}%</text>
          </g>
        ))}
        {xt.map((v) => (
          <text key={v} x={X(v)} y={H - B + 18} textAnchor="middle" fontSize={11} fill="var(--faint)">{Math.round(v).toLocaleString("en-US")}</text>
        ))}
        <text x={PR} y={H - 6} textAnchor="end" fontSize={11} fill="var(--faint)">plan cost, USD</text>
        <text x={L} y={T - 6} fontSize={11} fill="var(--faint)">on time (every demand)</text>
        {order.map((i) => {
          const g = gs[i];
          const isHero = g.names.includes(heroName);
          const c = isHero ? "var(--cobalt)" : "var(--graphite)";
          const px = X(g.cost), py = Y(g.p), ly = labelY[i];
          return (
            <g key={i}>
              <line x1={px + 6} y1={py} x2={PR + 16} y2={ly - 4} stroke={c} strokeWidth={1} />
              <rect x={px - 6} y={py - 6} width={12} height={12} fill={c} />
              <text x={PR + 22} y={ly} fontSize={12} fill={isHero ? "var(--cobalt)" : "var(--ink)"} fontWeight={isHero ? 600 : 400}>
                {g.names.join(", ")}
              </text>
              <text x={PR + 22} y={ly + 15} fontSize={11} fill="var(--faint)">{g.routes} · {Math.round(g.cost).toLocaleString("en-US")} USD · {(g.p * 100).toFixed(1)}%</text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
