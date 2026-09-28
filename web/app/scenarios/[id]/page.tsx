// Question: what exactly was predicted for this scenario, and what did the engine and the rules produce?
import { get, usd, pct, days } from "@/lib/api";
import type { Check, PlanRow } from "@/lib/types";
import { Panel, Badge } from "@/components/ui";
import { CostRiskChart } from "@/components/CostRiskChart";

export const dynamic = "force-dynamic";

type Detail = { entry: { id: string; family: string; rationale: string; falsifier: string; generator_params: Record<string, unknown>; prediction_registered: string };
  result: { rows: PlanRow[]; judge: { verdict: string; checks: Check[] }; seconds: number; n_candidates: number } | null };

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const d = await get<Detail>(`/api/scenarios/${id}`);
  const r = d.result;
  return (
    <div className="space-y-6">
      <div>
        <div className="kicker">{d.entry.family} · {d.entry.prediction_registered === "before_run" ? "pre-registered" : "registered after observation"}</div>
        <h1 className="text-h1 font-semibold">{d.entry.id}</h1>
        <p className="mt-2 max-w-4xl text-lead">{d.entry.rationale}</p>
        <p className="mt-2 max-w-4xl text-body text-muted">Falsifier: {d.entry.falsifier}</p>
        <p className="mt-2 font-mono text-meta text-faint">params {JSON.stringify(d.entry.generator_params)}</p>
      </div>
      {r && (
        <>
          <Panel title="예측 검사" kicker={`verdict ${r.judge.verdict} · judged by a fixed operator menu`}>
            <table className="w-full text-body">
              <thead><tr className="border-b border-line text-left text-meta text-muted"><th className="py-2">prediction</th><th>got</th><th className="w-20">result</th></tr></thead>
              <tbody>
                {r.judge.checks.map((c, i) => (
                  <tr key={i} className="border-b border-line">
                    <td className="py-2 font-mono">{c.metric} {c.op} {JSON.stringify(c.value)}</td>
                    <td className="font-mono text-muted">{JSON.stringify(c.got)}</td>
                    <td><Badge tone={c.ok ? "green" : "tomato"}>{c.ok ? "holds" : "fails"}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Panel>
          <Panel title="엔진 네 안과 규칙 두 개" kicker={`${r.n_candidates} candidates · ${r.seconds} s · every row re-checked by the independent verifier`}>
            <table className="w-full text-body">
              <thead><tr className="border-b border-line text-left text-meta text-muted"><th className="py-2">plan</th><th className="text-right">cost USD</th><th className="text-right">min slack</th><th className="text-right">on time</th><th className="text-right">expected cost</th><th>routes</th></tr></thead>
              <tbody>
                {r.rows.map((p) => (
                  <tr key={p.plan} className="border-b border-line">
                    <td className="py-2"><span className={p.plan === "risk_adjusted" ? "font-semibold text-cobalt" : "font-semibold"}>{p.plan}</span>{!p.verify_ok && <span className="ml-2"><Badge tone="tomato">verify fail</Badge></span>}
                      {p.verify_problems?.length ? <div className="text-meta text-tomato">{p.verify_problems[0]}</div> : null}</td>
                    <td className="text-right font-mono">{usd(p.cost_usd)}</td>
                    <td className="text-right font-mono">{days(p.min_slack_days)}</td>
                    <td className={`text-right font-mono ${p.p_all_on_time != null && p.p_all_on_time < 0.5 ? "text-tomato" : ""}`}>{pct(p.p_all_on_time)}</td>
                    <td className="text-right font-mono">{usd(p.cost_mean_usd)}</td>
                    <td className="font-mono text-muted">{p.routes.join("+")}{p.expedite.length ? ` · expedite ${p.expedite.join(",")}` : ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="mt-6"><CostRiskChart rows={r.rows} /></div>
          </Panel>
        </>
      )}
    </div>
  );
}
