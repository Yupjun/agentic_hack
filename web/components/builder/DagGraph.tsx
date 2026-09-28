// The user's plan tree as a left-to-right graph: one column per step, one box per task node, edges from `after`.
// A selected plan colours its critical path cobalt and shows the chosen supplier in each box.
import type { DagSpec, Plan } from "./types";

const BW = 200, BH = 64, GX = 70, GY = 22, PAD = 16;

export function DagGraph({ spec, plan, sel, onSel }: { spec: DagSpec; plan?: Plan; sel?: string; onSel?: (id: string) => void }) {
  const pos: Record<string, { x: number; y: number }> = {};
  spec.steps.forEach((s, c) => s.nodes.forEach((n, r) => { pos[n.id] = { x: PAD + c * (BW + GX), y: PAD + 22 + r * (BH + GY) }; }));
  const rows = Math.max(1, ...spec.steps.map((s) => s.nodes.length));
  const W = PAD * 2 + spec.steps.length * (BW + GX) - GX, H = PAD * 2 + 22 + rows * (BH + GY) - GY;
  const crit = new Set(plan?.critical_path ?? []);
  const nodes = spec.steps.flatMap((s) => s.nodes);
  return (
    <div className="overflow-x-auto"><svg width={W} height={H}>
      {spec.steps.map((s, c) => <text key={s.id} x={PAD + c * (BW + GX)} y={PAD + 8} fontSize={12} fontWeight={600} fill="var(--muted)">{c + 1}. {s.name}</text>)}
      {nodes.flatMap((n) => n.after.filter((a) => pos[a]).map((a) => {
        const p = pos[a], q = pos[n.id], hot = crit.has(a) && crit.has(n.id), mx = (p.x + BW + q.x) / 2;
        return <path key={`${a}-${n.id}`} d={`M${p.x + BW},${p.y + BH / 2} C${mx},${p.y + BH / 2} ${mx},${q.y + BH / 2} ${q.x},${q.y + BH / 2}`}
          fill="none" stroke={hot ? "var(--cobalt)" : "var(--graphite)"} strokeWidth={hot ? 2.5 : 1.2} />;
      }))}
      {nodes.map((n) => {
        const p = pos[n.id], r = plan?.nodes[n.id], hot = crit.has(n.id), on = sel === n.id;
        return <g key={n.id} style={{ cursor: onSel ? "pointer" : undefined }} onClick={() => onSel?.(n.id)}>
          <rect x={p.x} y={p.y} width={BW} height={BH} fill="var(--sheet)" stroke={on ? "var(--ink)" : hot ? "var(--cobalt)" : "var(--line)"} strokeWidth={on || hot ? 2 : 1} />
          <text x={p.x + 8} y={p.y + 18} fontSize={13} fontWeight={600} fill="var(--ink)">{n.task.slice(0, 22)}</text>
          <text x={p.x + 8} y={p.y + 36} fontSize={11} fill="var(--muted)">
            {r ? `${r.supplier.slice(0, 20)}${r.expedite ? " · 급행" : ""}` : `공급처 ${n.options.length}곳 · ${n.join === "any" ? "하나만" : "모두 필요"}`}
          </text>
          <text x={p.x + 8} y={p.y + 53} fontSize={11} fill={r && r.slack < 0.01 ? "var(--cobalt)" : "var(--faint)"}>
            {r ? `${r.ES.toFixed(0)}–${r.EF.toFixed(0)} d · 여유 ${r.slack.toFixed(1)} d` : `단위당 ${n.qty_per_unit}`}
          </text>
        </g>;
      })}
    </svg></div>
  );
}
