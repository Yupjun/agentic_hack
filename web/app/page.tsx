// Question: what has this system demonstrated so far?
import { get, usd, pct } from "@/lib/api";
import type { Overview, ScenarioRow } from "@/lib/types";
import { BigStat, Panel, Row, Badge } from "@/components/ui";
import { CostRiskChart } from "@/components/CostRiskChart";
import RouteGlobe from "@/components/globe/RouteGlobeClient";
import type { Session } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function Page() {
  const [o, sc] = await Promise.all([get<Overview>("/api/overview"), get<ScenarioRow[]>("/api/scenarios")]);
  const base = await get<{ result: { rows: import("@/lib/types").PlanRow[] } | null }>("/api/scenarios/s1-base");
  // current status: the latest agent session that ended on a verified plan, shown on the globe at "now"
  const sessions = await get<Session[]>("/api/sessions");
  const latest = sessions.find((x) => x.status === "verified" && x.run_id && x.plan);
  const live = latest ? await get<{ run: { plans: Record<string, { shipments: any[] }> }; spec: any }>(`/api/runs/${latest.run_id}`).catch(() => null) : null;
  const liveDues = live?.spec?.production_plan ? live.spec.production_plan.batches.map((b: any) => ({ id: b.id, due: b.start }))
    : (live?.spec?.demand ?? []).map((d: any) => ({ id: d.id, due: d.due }));
  const co = base.result?.rows.find((r) => r.plan === "cost_optimal");
  const ra = base.result?.rows.find((r) => r.plan === "risk_adjusted");
  return (
    <div className="space-y-6">
      <div>
        <div className="kicker">order &amp; transport planning agent</div>
        <h1 className="text-h1 font-semibold">목표를 받으면 계획을 스펙으로 만들고, 풀고, 검증된 안만 제안한다<span className="text-cobalt">.</span></h1>
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <BigStat label="scenarios supported" value={`${o.supported}/${o.judged}`} sub={`${o.pre_registered} pre-registered before run`} tone="green" />
        <BigStat label="agent sessions verified" value={`${o.sessions_verified}/${o.sessions}`} sub={`${o.tool_calls} tool calls · ${o.llm_calls} guarded LLM calls`} tone="cobalt" />
        <BigStat label="agent eval: params right" value={`${o.agent_eval.params_ok}/${o.agent_eval.n}`} sub={`${o.agent_eval.verified}/${o.agent_eval.n} ended on a verified plan`} />
        <BigStat label="guardrail blocks" value={`${o.guardrail_blocks}`} sub="undeclared tool calls stopped" tone="tomato" />
      </div>
      {latest && live && (
        <Panel kicker={`latest verified agent plan · ${latest.plan} · ${Math.round(latest.cost_usd ?? 0).toLocaleString()} USD`} title="지금 각 발주는 어디에 있나?"
          right={<a className="text-body text-cobalt" href={`/runs/${latest.run_id}?plan=${latest.plan}`}>open the plan →</a>}>
          <p className="mb-3 text-body text-muted">{latest.goal}</p>
          <RouteGlobe ships={live.run.plans[latest.plan!].shipments} nodes={live.spec?.nodes ?? {}} dues={liveDues} />
        </Panel>
      )}
      <Panel kicker="scenario s1-base · 10,000 Monte Carlo samples" title="가장 싼 안은 제때 도착하는가?">
        <p className="mb-4 max-w-3xl text-lead">
          비용 최적안({usd(co?.cost_usd)} USD, {co?.routes.join("+")})은 정시 확률 {pct(co?.p_all_on_time)}, 지연 벌금 포함 기대비용 {usd(co?.cost_mean_usd)} USD.
          위험 조정안({usd(ra?.cost_usd)} USD, {ra?.routes.join("+")})은 {pct(ra?.p_all_on_time)}.
        </p>
        {base.result && <CostRiskChart rows={base.result.rows} />}
      </Panel>
      <Panel title="시나리오별 판정" kicker="predictions written before running" right={<a className="text-body text-cobalt" href="/scenarios">all →</a>}>
        {sc.slice(0, 5).map((s) => (
          <Row key={s.id} href={`/scenarios/${s.id}`} badge={<Badge tone={s.verdict === "supported" ? "green" : s.verdict ? "tomato" : "muted"}>{s.verdict ?? "not run"}</Badge>}
            title={<span><span className="font-semibold">{s.id}</span> — {s.rationale.split(". ")[0]}.</span>}
            meta={`${s.family} · ${s.passed}/${s.total} checks · ${s.registered === "before_run" ? "pre-registered" : "registered after observation"}`} />
        ))}
      </Panel>
    </div>
  );
}
