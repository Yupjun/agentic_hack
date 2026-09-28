// Question: for each registered scenario, did the prediction hold?
import { get, usd, pct } from "@/lib/api";
import type { ScenarioRow } from "@/lib/types";
import { Panel, Row, Badge } from "@/components/ui";

export const dynamic = "force-dynamic";

export default async function Page() {
  const sc = await get<ScenarioRow[]>("/api/scenarios");
  return (
    <Panel kicker="scenario bank · base spec + parameters, predictions committed before the run" title="예측은 맞았나?">
      {sc.map((s) => (
        <Row key={s.id} href={`/scenarios/${s.id}`}
          badge={<Badge tone={s.verdict === "supported" ? "green" : s.verdict ? "tomato" : "muted"}>{s.verdict ?? "not run"}</Badge>}
          title={<span><span className="font-semibold">{s.id}</span> — {s.rationale}</span>}
          meta={<span className="font-mono">{s.family} · {s.passed}/{s.total} checks · {s.registered === "before_run" ? "pre-registered" : "after observation"} · params {JSON.stringify(s.params)} · cost-optimal {usd(s.cost_optimal?.cost_usd)} USD on time {pct(s.cost_optimal?.p_all_on_time)} · rule {usd(s.rule_cheapest?.cost_usd)}</span>} />
      ))}
    </Panel>
  );
}
