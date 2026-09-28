// Question: which solver runs exist, and what did each named plan cost?
import { get, usd } from "@/lib/api";
import { Panel, Row, Badge } from "@/components/ui";

export const dynamic = "force-dynamic";
type R = { run_id: string; spec_id: string; family: string; status: string; seconds: number; modified: string; costs: Record<string, number> };

export default async function Page() {
  const runs = await get<R[]>("/api/runs");
  return (
    <Panel kicker="state/runs · one row per solve" title="풀어본 계획들">
      {runs.map((r) => (
        <Row key={r.run_id} href={`/runs/${r.run_id}`} badge={<Badge tone={r.status === "ok" ? "cobalt" : "tomato"}>{r.status}</Badge>}
          title={<span><span className="font-semibold">{r.spec_id}</span> <span className="text-muted">({r.family})</span></span>}
          meta={<span className="font-mono">{r.modified} · {r.seconds}s · cost-optimal {usd(r.costs.cost_optimal)} · risk-adjusted {usd(r.costs.risk_adjusted)} · time-optimal {usd(r.costs.time_optimal)} USD</span>} />
      ))}
    </Panel>
  );
}
