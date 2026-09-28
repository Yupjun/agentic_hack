"use client";
// Spec editor. Every field the engine reads is a form field here; nothing is hidden in code.
// The editor only changes the spec object. Solving is a separate button (the page owns it).
import type { DagSpec, DNode, Opt } from "./types";

type Set = (f: (s: DagSpec) => void) => void;

export function Num({ label, v, on, step = 1, w = "w-24" }: { label: string; v: number | null | undefined; on: (n: number | null) => void; step?: number; w?: string }) {
  return (
    <label className="flex flex-col gap-1 text-meta text-muted">{label}
      <input type="number" step={step} value={v ?? ""} className={`${w} border border-line bg-sheet px-2 py-1 text-body text-ink`}
        onChange={(e) => on(e.target.value === "" ? null : Number(e.target.value))} />
    </label>
  );
}

// Demand, inventory policy and uncertainty: the hypothesis parameters shared by every plan.
export function GlobalParams({ spec, set }: { spec: DagSpec; set: Set }) {
  const d = spec.demand, inv = spec.inventory, u = spec.uncertainty;
  return (
    <div className="grid gap-4">
      <div><div className="kicker mb-2">수요</div><div className="flex flex-wrap gap-3">
        <Num label="수량" v={d.qty} on={(n) => set((s) => { s.demand.qty = n ?? 0; })} />
        <Num label="기한 (일)" v={d.deadline_days} on={(n) => set((s) => { s.demand.deadline_days = n ?? 0; })} />
        <Num label="예산 USD" v={d.budget_usd} step={1000} w="w-32" on={(n) => set((s) => { s.demand.budget_usd = n ?? 0; })} />
        <Num label="도착 시 잔여 유통기한 %" v={d.min_remaining_pct_at_delivery} on={(n) => set((s) => { s.demand.min_remaining_pct_at_delivery = n ?? 0; })} />
      </div></div>
      <div><div className="kicker mb-2">재고 정책 (MOS)</div><div className="flex flex-wrap gap-3">
        <Num label="목표 MOS (개월)" v={inv.mos_target_months} step={0.5} on={(n) => set((s) => { s.inventory.mos_target_months = n ?? 0; })} />
        <Num label="월 사용량" v={inv.monthly_usage} on={(n) => set((s) => { s.inventory.monthly_usage = n ?? 0; })} />
        <Num label="현재 재고" v={inv.on_hand} on={(n) => set((s) => { s.inventory.on_hand = n ?? 0; })} />
      </div></div>
      <div><div className="kicker mb-2">불확실성</div><div className="flex flex-wrap gap-3">
        <Num label="표본 수" v={u.n_samples} step={500} on={(n) => set((s) => { s.uncertainty.n_samples = n ?? 1000; })} />
        <Num label="seed" v={u.seed} on={(n) => set((s) => { s.uncertainty.seed = n ?? 0; })} />
        <Num label="지연 벌금 USD/일" v={u.late_penalty_usd_per_day} step={500} w="w-32" on={(n) => set((s) => { s.uncertainty.late_penalty_usd_per_day = n ?? 0; })} />
      </div></div>
    </div>
  );
}

const find = (s: DagSpec, id: string) => s.steps.flatMap((st) => st.nodes).find((n) => n.id === id)!;

const OPT_COLS: [string, (o: Opt) => number | null | undefined, (o: Opt, n: number | null) => void, number][] = [
  ["용량/일", (o) => o.capacity_per_day, (o, n) => { o.capacity_per_day = n ?? 0; }, 1],
  ["LT 최소", (o) => o.lead_time_days.min, (o, n) => { o.lead_time_days.min = n ?? 0; }, 1],
  ["LT 최빈", (o) => o.lead_time_days.likely, (o, n) => { o.lead_time_days.likely = n ?? 0; }, 1],
  ["LT 최대", (o) => o.lead_time_days.max, (o, n) => { o.lead_time_days.max = n ?? 0; }, 1],
  ["단가", (o) => o.unit_cost_usd, (o, n) => { o.unit_cost_usd = n ?? 0; }, 10],
  ["고정비", (o) => o.fixed_cost_usd, (o, n) => { o.fixed_cost_usd = n ?? 0; }, 100],
  ["MOQ", (o) => o.moq, (o, n) => { o.moq = n ?? 0; }, 1],
  ["로트", (o) => o.lot_size, (o, n) => { o.lot_size = n ?? 1; }, 1],
  ["유통기한", (o) => o.shelf_life_days, (o, n) => { o.shelf_life_days = n; }, 1],
  ["급행 단축일", (o) => o.expedite?.lead_time_cut_days, (o, n) => { o.expedite = n == null ? null : { lead_time_cut_days: n, premium_pct: o.expedite?.premium_pct ?? 30 }; }, 1],
  ["급행 할증 %", (o) => o.expedite?.premium_pct, (o, n) => { if (o.expedite) o.expedite.premium_pct = n ?? 0; }, 5],
];

// One task node: what it needs, what it waits for, and the approved suppliers that can do it.
export function NodeEditor({ spec, id, set }: { spec: DagSpec; id: string; set: Set }) {
  const n = find(spec, id);
  const others = spec.steps.flatMap((s) => s.nodes).filter((m) => m.id !== id);
  const upd = (f: (m: DNode) => void) => set((s) => f(find(s, id)));
  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-meta text-muted">작업 이름
          <input value={n.task} className="w-56 border border-line bg-sheet px-2 py-1 text-body text-ink" onChange={(e) => upd((m) => { m.task = e.target.value; })} /></label>
        <Num label="제품 1단위당 소요" v={n.qty_per_unit} step={0.01} on={(v) => upd((m) => { m.qty_per_unit = v ?? 1; })} />
        <label className="flex flex-col gap-1 text-meta text-muted">선행 합류
          <select value={n.join} className="border border-line bg-sheet px-2 py-1 text-body text-ink" onChange={(e) => upd((m) => { m.join = e.target.value as "all" | "any"; })}>
            <option value="all">모두 끝나야 시작 (BOM)</option><option value="any">하나만 끝나면 시작</option></select></label>
      </div>
      <div className="flex flex-wrap items-center gap-2 text-meta text-muted">선행 작업:
        {others.map((m) => <label key={m.id} className="flex items-center gap-1 border border-line px-2 py-0.5">
          <input type="checkbox" checked={n.after.includes(m.id)} onChange={(e) => upd((x) => { x.after = e.target.checked ? [...x.after, m.id] : x.after.filter((a) => a !== m.id); })} />{m.task}</label>)}
      </div>
      <div className="overflow-x-auto">
        <table className="text-body">
          <thead><tr className="border-b border-ink text-left text-meta text-muted"><th className="px-2 py-1">승인 공급처</th>{OPT_COLS.map(([h]) => <th key={h} className="px-1 py-1">{h}</th>)}<th /></tr></thead>
          <tbody>{n.options.map((o, i) => <tr key={o.id} className="border-b border-line">
            <td className="px-2 py-1"><input value={o.supplier} className="w-44 border border-line bg-sheet px-1 text-ink" onChange={(e) => upd((m) => { m.options[i].supplier = e.target.value; })} /></td>
            {OPT_COLS.map(([h, get, put, st]) => <td key={h} className="px-1 py-1">
              <input type="number" step={st} value={get(o) ?? ""} className="w-20 border border-line bg-sheet px-1 text-ink"
                onChange={(e) => upd((m) => put(m.options[i], e.target.value === "" ? null : Number(e.target.value)))} /></td>)}
            <td className="px-1"><button className="text-meta text-tomato" disabled={n.options.length < 2} onClick={() => upd((m) => { m.options.splice(i, 1); })}>삭제</button></td>
          </tr>)}</tbody>
        </table>
      </div>
      <button className="w-fit border border-ink px-3 py-1 text-meta" onClick={() => upd((m) => {
        const b = m.options[m.options.length - 1];
        m.options.push({ ...structuredClone(b), id: `${m.id}-opt${m.options.length + 1}`, supplier: "새 승인 공급처" });
      })}>승인 공급처 추가</button>
    </div>
  );
}
