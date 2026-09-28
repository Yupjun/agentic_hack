// Question: when does each shipment move, by which mode, and how close to its due date does it land?
// One row per shipment, one bar per leg. Mode colours are information (categorical, fixed order):
// air = cobalt, ocean = plum, parcel = mustard, truck = graphite. Due dates are tomato ticks.
type Leg = { lane: string; mode: string; depart: string; arrive: string; from: string; to: string };
type Ship = { id: string; item: string; qty: number; option: string | null; legs: Leg[] };
const MODE: Record<string, string> = { air: "var(--cobalt)", ocean: "var(--plum)", parcel: "var(--mustard)", truck: "var(--graphite)", rail: "var(--green)" };
const t = (s: string) => new Date(s).getTime();

export function Timeline({ ships, dues, t0 }: { ships: Ship[]; dues: { id: string; due: string }[]; t0: string }) {
  const start = t(t0);
  const end = Math.max(...ships.flatMap((s) => s.legs.map((g) => t(g.arrive))), ...dues.map((d) => t(d.due)));
  const DAY = 86400000;
  const pxPerDay = Math.max(10, Math.min(28, 900 / ((end - start) / DAY)));
  const W = 200 + ((end - start) / DAY) * pxPerDay + 40;
  const rowH = 26;
  const H = 36 + ships.length * rowH + 20;
  const X = (ms: number) => 200 + ((ms - start) / DAY) * pxPerDay;
  const weeks: number[] = [];
  for (let d = 0; d <= (end - start) / DAY; d += 7) weeks.push(start + d * DAY);
  return (
    <div className="overflow-x-auto">
      <svg width={W} height={H}>
        {weeks.map((w) => (
          <g key={w}>
            <line x1={X(w)} x2={X(w)} y1={24} y2={H - 16} stroke="var(--line)" />
            <text x={X(w) + 2} y={16} fontSize={11} fill="var(--faint)">{new Date(w).toISOString().slice(5, 10)}</text>
          </g>
        ))}
        {dues.map((d) => (
          <g key={d.id}>
            <line x1={X(t(d.due))} x2={X(t(d.due))} y1={24} y2={H - 16} stroke="var(--tomato)" strokeWidth={2} />
            <text x={X(t(d.due)) + 3} y={H - 4} fontSize={11} fill="var(--tomato)">due {d.id}</text>
          </g>
        ))}
        {ships.map((s, i) => (
          <g key={s.id}>
            <text x={8} y={36 + i * rowH + 14} fontSize={12} fill="var(--ink)">{s.item} × {s.qty}{s.option === "expedite" ? " · expedite" : ""}</text>
            {s.legs.map((g, k) => (
              <rect key={k} x={X(t(g.depart))} y={36 + i * rowH + 3} width={Math.max(3, X(t(g.arrive)) - X(t(g.depart)))} height={rowH - 10} fill={MODE[g.mode] ?? "var(--graphite)"}>
                <title>{`${g.mode} ${g.from}→${g.to} ${g.depart.slice(0, 16)} → ${g.arrive.slice(0, 16)}`}</title>
              </rect>
            ))}
          </g>
        ))}
      </svg>
      <div className="mt-2 flex gap-4 text-meta text-muted">
        {Object.entries(MODE).slice(0, 4).map(([m, c]) => <span key={m} className="flex items-center gap-1"><svg width={10} height={10}><rect width={10} height={10} fill={c} /></svg>{m}</span>)}
      </div>
    </div>
  );
}
