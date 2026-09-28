"use client";
// Result panels for one solve. Every number comes from the /api/dag/solve response; nothing is recomputed here.
import { Panel, BigStat, Badge } from "../ui";
import { Bars, Gantt, Histogram, ParetoChart } from "./charts";
import type { DagSpec, Result } from "./types";
import { OBJ, usd } from "./types";

const pct = (v: number) => `${(v * 100).toFixed(1)} %`;

export function Results({ spec, r, sel, setSel }: { spec: DagSpec; r: Result; sel: string; setSel: (k: string) => void }) {
  const p = r.plans?.[sel];
  if (!p) return null;
  const dl = spec.demand.deadline_days;
  const nodes = spec.steps.flatMap((s) => s.nodes);
  const nameOf = (id: string) => nodes.find((n) => n.id === id)?.task ?? id;
  const tags = Object.entries(r.named ?? {}).filter(([, k]) => k === sel).map(([o]) => OBJ.find((x) => x[0] === o)?.[1] ?? o);
  const f = r.flow;
  return (
    <div className="grid gap-5">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <BigStat label="계획 비용" value={`${usd(p.cost_usd)} USD`} sub={`예산 ${usd(spec.demand.budget_usd)} · 기대비용 ${usd(p.mc.expected_cost_usd)}`} tone="cobalt" />
        <BigStat label="완료 (CPM)" value={`${p.makespan_days.toFixed(1)} 일`} sub={`기한 ${dl}일 · 여유 ${p.slack_days.toFixed(1)}일`} />
        <BigStat label="정시 확률 (몬테카를로)" value={pct(p.mc.p_on_time)} sub={`P10 ${p.mc.makespan_p10.toFixed(0)} · P50 ${p.mc.makespan_p50.toFixed(0)} · P90 ${p.mc.makespan_p90.toFixed(0)}일`} tone={p.mc.p_on_time < 0.8 ? "tomato" : "green"} />
        <BigStat label="납품 후 MOS" value={p.mos_after_months == null ? "-" : `${p.mos_after_months.toFixed(2)} 개월`} sub={`목표 ${spec.inventory.mos_target_months}개월 · 필요 수량 ${r.required_units ?? "-"}`} />
      </div>

      <Panel title="목표별로 어떤 안이 뽑혔나?" kicker={`${r.n_plans}개 안 중 실행 가능 ${r.n_feasible}개 · ${r.seconds}초`}>
        <div className="overflow-x-auto"><table className="w-full text-body">
          <thead><tr className="border-b border-ink text-left text-meta text-muted"><th className="py-1">목표</th><th>비용 USD</th><th>완료 일</th><th>정시 확률</th><th>기대비용 USD</th><th>공급처 선택</th></tr></thead>
          <tbody>{OBJ.map(([o, label]) => { const k = r.named?.[o]; const q = k ? r.plans?.[k] : undefined; if (!k || !q) return null;
            return <tr key={o} className={`cursor-pointer border-b border-line ${k === sel ? "bg-ground" : ""}`} onClick={() => setSel(k)}>
              <td className="py-1.5 font-semibold">{label}{o === spec.objective && <span className="ml-2"><Badge tone="cobalt">선택한 목표</Badge></span>}</td>
              <td>{usd(q.cost_usd)}</td><td>{q.makespan_days.toFixed(1)}</td><td>{pct(q.mc.p_on_time)}</td><td>{usd(q.mc.expected_cost_usd)}</td>
              <td className="text-meta text-muted">{nodes.map((n) => q.nodes[n.id]?.supplier + (q.nodes[n.id]?.expedite ? "+급행" : "")).join(" → ")}</td></tr>; })}</tbody>
        </table></div>
      </Panel>

      <div className="grid gap-5 xl:grid-cols-2">
        <Panel title="같은 기간이면 가장 싼 안은?" kicker="비용–기간 파레토 · 회색 점 = 실행 가능한 모든 안" right={tags.length ? <Badge tone="cobalt">{tags.join(" · ")}</Badge> : undefined}>
          <ParetoChart r={r} sel={sel} onSel={setSel} deadline={dl} />
        </Panel>
        <Panel title="기한 안에 끝날 확률은?" kicker={`리드타임 삼각분포 ${spec.uncertainty.n_samples}회 · seed ${spec.uncertainty.seed}`}>
          <Histogram p={p} deadline={dl} />
        </Panel>
      </div>

      <Panel title="언제 무엇이 돌고, 어디에 여유가 있나?" kicker="CPM · 파란 막대 = 주공정, 얇은 회색 = 여유">
        <Gantt spec={spec} p={p} deadline={dl} />
      </Panel>

      <div className="grid gap-5 xl:grid-cols-2">
        <Panel title="돈은 어디로 가나?" kicker="작업별 비용 · 괄호 = MOQ·로트 때문에 더 산 수량">
          <Bars rows={nodes.map((n) => { const x = p.nodes[n.id]; return { label: n.task, value: x?.cost_usd ?? 0, sub: x?.overbuy ? `(+${x.overbuy})` : "", hot: x?.critical }; })} fmt={(v) => usd(v)} />
        </Panel>
        <Panel title="어느 작업이 자주 주공정이 되나?" kicker="몬테카를로에서 주공정에 든 비율">
          <Bars rows={nodes.map((n) => ({ label: n.task, value: p.mc.criticality[n.id] ?? 0, hot: (p.mc.criticality[n.id] ?? 0) > 0.5 }))} fmt={pct} tone="tomato" />
        </Panel>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        {f && <Panel title="기한까지 만들 수 있는 최대량은?" kicker={`최대 유량 (${f.method}) · ${f.units_by_deadline.toFixed(0)} / ${f.demand_units} 단위`}
          right={<Badge tone={f.enough ? "green" : "tomato"}>{f.enough ? "용량 충분" : "용량 부족"}</Badge>}>
          <Bars rows={Object.entries(f.node_capacity_units).map(([id, v]) => ({ label: nameOf(id), value: v, hot: f.bottleneck.includes(id) }))} fmt={(v) => `${v.toFixed(0)} 단위`} tone="tomato" />
          <div className="mt-2 text-meta text-muted">병목: {f.bottleneck.map(nameOf).join(", ") || "-"}</div>
        </Panel>}
        <Panel title="하루 당기려면 얼마가 드나?" kicker="크래싱 · 주공정 작업에 급행을 걸 때 일당 비용">
          {r.crashing?.length ? <table className="w-full text-body">
            <thead><tr className="border-b border-ink text-left text-meta text-muted"><th className="py-1">작업</th><th>단축 일</th><th>추가 비용 USD</th><th>USD/일</th><th>예산 안</th></tr></thead>
            <tbody>{r.crashing.map((c) => <tr key={c.node} className="border-b border-line">
              <td className="py-1.5">{nameOf(c.node)}</td><td>{c.days_saved.toFixed(1)}</td><td>{usd(c.extra_cost_usd)}</td><td>{usd(c.usd_per_day)}</td>
              <td>{c.within_budget ? <Badge tone="green">예</Badge> : <Badge tone="tomato">아니오</Badge>}</td></tr>)}</tbody>
          </table> : <div className="text-body text-muted">주공정에 걸 수 있는 급행이 없습니다.</div>}
        </Panel>
      </div>

      {p.shelf_problems.length > 0 && <Panel title="유통기한 문제" kicker="이 안에서 걸린 조건"><ul className="list-disc pl-5 text-body">{p.shelf_problems.map((s) => <li key={s}>{s}</li>)}</ul></Panel>}
    </div>
  );
}
