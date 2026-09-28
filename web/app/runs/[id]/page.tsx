// Question: of the four verified plans, what does each cost, how much slack does it leave, how often is it on time, and what does it ship when?
import { get, usd, pct, days } from "@/lib/api";
import { Panel, Badge } from "@/components/ui";
import { Timeline } from "@/components/Timeline";

export const dynamic = "force-dynamic";
type Plan = { cost_usd: number; metrics: { min_slack_days: number; latest_arrival: string; units_left_over: number }; mc: { p_all_on_time: number; cost_mean_usd: number; cost_p95_usd: number; p_shelf_ok: number; p_no_excursion: number }; shipments: any[] };
type D = { run: { spec_id: string; family: string; backend: string; seconds: number; plans: Record<string, Plan>; frontier: { slack_required: number; cost_usd?: number; metrics?: { min_slack_days: number }; dominated?: boolean; verify_ok?: boolean }[] }; spec: any };
const ORDER = ["cost_optimal", "risk_adjusted", "balanced", "time_optimal"];

function dues(spec: any): { id: string; due: string }[] {
  if (spec?.production_plan) return spec.production_plan.batches.map((b: any) => ({ id: b.id, due: b.start }));
  return (spec?.demand ?? []).map((d: any) => ({ id: d.id, due: d.due }));
}

export default async function Page({ params, searchParams }: { params: Promise<{ id: string }>; searchParams: Promise<{ plan?: string }> }) {
  const { id } = await params;
  const { plan } = await searchParams;
  const d = await get<D>(`/api/runs/${id}`);
  const sel = plan && d.run.plans[plan] ? plan : "risk_adjusted";
  const p = d.run.plans[sel];
  return (
    <div className="space-y-6">
      <div>
        <div className="kicker">{d.run.family} · solved by {d.run.backend} in {d.run.seconds}s · verified by engine/verify.py · risk from 10,000 samples</div>
        <h1 className="text-h1 font-semibold">{d.run.spec_id}</h1>
        {d.spec?.hypothesis && <p className="mt-2 max-w-4xl text-body text-muted">{d.spec.hypothesis}</p>}
      </div>
      <Panel title="네 안 비교" kicker="click a plan to see its shipments">
        <table className="w-full text-body">
          <thead><tr className="border-b border-line text-left text-meta text-muted"><th className="py-2">plan</th><th className="text-right">cost USD</th><th className="text-right">min slack</th><th className="text-right">on time</th><th className="text-right">expected cost</th><th className="text-right">p95 cost</th><th className="text-right">left over</th></tr></thead>
          <tbody>
            {ORDER.filter((k) => d.run.plans[k]).map((k) => {
              const q = d.run.plans[k];
              return (
                <tr key={k} className="border-b border-line">
                  {/* the selected row is marked in its first cell only: a pseudo-element on <tr> becomes a table cell and shifts every column (seen 2026-09-28) */}
                  <td className={`py-2 pl-2 ${k === sel ? "border-l-2 border-cobalt" : "border-l-2 border-transparent"}`}><a href={`?plan=${k}`} className={k === sel ? "font-semibold text-cobalt" : "font-semibold"}>{k.replace("_", " ")}</a></td>
                  <td className="text-right font-mono">{usd(q.cost_usd)}</td>
                  <td className="text-right font-mono">{days(q.metrics.min_slack_days)}</td>
                  <td className={`text-right font-mono ${q.mc.p_all_on_time < 0.5 ? "text-tomato" : ""}`}>{pct(q.mc.p_all_on_time)}</td>
                  <td className="text-right font-mono">{usd(q.mc.cost_mean_usd)}</td>
                  <td className="text-right font-mono">{usd(q.mc.cost_p95_usd)}</td>
                  <td className="pr-6 text-right font-mono">{q.metrics.units_left_over}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Panel>
      <Panel title={`${sel.replace("_", " ")} — 언제 무엇이 움직이나`} kicker={`${p.shipments.length} shipments · shelf life ok ${pct(p.mc.p_shelf_ok)} · no excursion ${pct(p.mc.p_no_excursion)}`}
        right={<Badge tone="cobalt">{usd(p.cost_usd)} USD</Badge>}>
        <Timeline ships={p.shipments} dues={dues(d.spec)} t0={d.spec?.t0 ?? p.shipments[0]?.legs[0]?.depart} />
      </Panel>
    </div>
  );
}
