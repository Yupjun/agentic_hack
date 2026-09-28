// Question: what do the public feeds say right now about the hubs our lanes use?
import { get } from "@/lib/api";
import { Panel, Badge } from "@/components/ui";

export const dynamic = "force-dynamic";
const HUBS = ["JFK", "ORD", "LAX", "RKSI", "EDDF", "OMDB"];

export default async function Page() {
  const rows = await Promise.all(HUBS.map(async (h) => {
    try { return { h, d: await get<any>(`/api/live/${h}`) }; } catch (e) { return { h, err: String(e) }; }
  }));
  return (
    <Panel kicker="FAA NAS status (US airports only) · aviationweather.gov METAR/TAF/SIGMET · fetched now" title="지금 허브 상태">
      <table className="w-full text-body">
        <thead><tr className="border-b border-line text-left text-meta text-muted"><th className="py-2">hub</th><th>airspace programs</th><th>flight category</th><th>METAR</th></tr></thead>
        <tbody>
          {rows.map((r) => {
            const a = r.d?.airspace, w = r.d?.weather;
            const programs = a && !a.error ? [...(a.gdp ?? []).map(() => "GDP"), ...(a.ground_stops ?? []).map(() => "ground stop"), ...(a.closures ?? []).map(() => "closure"), ...(a.delays ?? []).map(() => "delay")] : [];
            return (
              <tr key={r.h} className="border-b border-line align-top">
                <td className="py-2 font-semibold">{r.h}</td>
                <td>{r.err ? <Badge tone="tomato">error</Badge> : a?.error ? <span className="text-meta text-faint">not covered</span> : programs.length ? programs.map((p, i) => <span key={i} className="mr-1"><Badge tone="tomato">{p}</Badge></span>) : <Badge tone="green">none</Badge>}</td>
                <td>{w?.metar?.flight_category ? <Badge tone={w.metar.flight_category === "VFR" ? "green" : "tomato"}>{w.metar.flight_category}</Badge> : <span className="text-meta text-faint">{w?.error ?? "-"}</span>}</td>
                <td className="font-mono text-meta text-muted">{w?.metar?.raw ?? ""}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </Panel>
  );
}
