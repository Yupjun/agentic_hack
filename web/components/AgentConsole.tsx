"use client";
// Question: what did the agent do for this goal — which tools, which guarded model calls, what was blocked, and is the answer a verified plan?
import { useEffect, useState } from "react";
import type { Session, Step } from "@/lib/types";

type Detail = { start: { goal: string }; end: { answer?: string; recommended?: { ok: boolean; plan?: string; run_id?: string; cost_usd?: number; reason?: string }; seconds?: number } | null; steps: Step[] };

const EXAMPLES = [
  "C 제품 100개를 A에서 B로 30일 안에 보내야 해. 예산은 4만 달러야. 비용과 납기를 둘 다 고려해줘.",
  "AA 배치 3개용 원료 발주 계획이 필요해. A3 사이트가 모든 발주에서 10일씩 늦어진대. 예산 25만 달러.",
];

export function AgentConsole({ initial }: { initial: Session[] }) {
  const [sessions, setSessions] = useState<Session[]>(initial);
  // default to the latest FINISHED session so the trace is not empty while a new one starts
  const [sel, setSel] = useState<string | null>((initial.find((s) => s.status !== "running") ?? initial[0])?.session ?? null);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [goal, setGoal] = useState(EXAMPLES[0]);
  const [msg, setMsg] = useState<string>("");

  useEffect(() => {
    const t = setInterval(async () => {
      const r = await fetch("/api/sessions", { cache: "no-store" });
      if (r.ok) setSessions(await r.json());
    }, 5000);
    return () => clearInterval(t);
  }, []);
  useEffect(() => {
    if (!sel) return;
    let stop = false;
    const load = async () => {
      const r = await fetch(`/api/sessions/${sel}`, { cache: "no-store" });
      if (r.ok && !stop) setDetail(await r.json());
    };
    load();
    const t = setInterval(load, 4000);
    return () => { stop = true; clearInterval(t); };
  }, [sel]);

  async function start() {
    setMsg("starting…");
    const r = await fetch("/api/agent/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ goal }) });
    const body = await r.json().catch(() => ({}));
    setMsg(r.ok ? "started — the session appears below in a few seconds" : `HTTP ${r.status}: ${body.detail ?? "error"}`);
  }

  const rec = detail?.end?.recommended;
  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[420px_1fr]">
      <div className="space-y-4">
        <section className="sheet p-5">
          <div className="kicker mb-2">goal · your words</div>
          <textarea className="human h-28 w-full p-3 text-body" value={goal} onChange={(e) => setGoal(e.target.value)} />
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <button className="stamp stamp-primary" onClick={start}>Plan it</button>
            {EXAMPLES.map((x, i) => <button key={i} className="stamp stamp-quiet text-meta" onClick={() => setGoal(x)}>example {i + 1}</button>)}
          </div>
          {msg && <div className="mt-2 text-meta text-muted">{msg}</div>}
          <div className="mt-2 text-meta text-faint">The agent can only propose. No tool books, orders or sends anything; a call to one is blocked by NeMo Guardrails.</div>
        </section>
        <section className="sheet">
          <div className="kicker px-5 pt-4">sessions</div>
          {sessions.map((s) => (
            <button key={s.session} onClick={() => setSel(s.session)} className={`block w-full border-b border-line px-5 py-3 text-left ${sel === s.session ? "accent-corners tone-cobalt" : ""}`}>
              <div className="text-body">{s.goal}</div>
              <div className={`mt-1 text-meta ${s.status === "failed" ? "text-tomato" : s.status === "verified" ? "text-green" : "text-faint"}`}>
                {s.status}{s.plan ? ` · ${s.plan}` : ""}{s.cost_usd ? ` · ${Math.round(s.cost_usd).toLocaleString()} USD` : ""}{s.seconds ? ` · ${s.seconds}s` : ""}{s.reason ? ` · ${s.reason}` : ""}
              </div>
            </button>
          ))}
        </section>
      </div>
      <section className="sheet p-5">
        {!detail ? <div className="text-body text-muted">select a session</div> : (
          <>
            <div className="kicker">trace · tool calls and guarded model calls in time order</div>
            <h2 className="mt-1 text-h2 font-semibold">{detail.start.goal}</h2>
            <ol className="mt-4">
              {detail.steps.map((s, i) => (
                <li key={i} className="flex gap-3 border-b border-line py-2">
                  <span className="w-12 shrink-0 font-mono text-meta text-faint">{s.ts.slice(11, 19)}</span>
                  <span className={`w-16 shrink-0 text-meta font-semibold uppercase ${s.kind === "block" ? "text-tomato" : s.kind === "tool" ? "text-cobalt" : "text-muted"}`}>{s.kind}</span>
                  <div className="min-w-0">
                    <div className="text-body">{s.kind === "llm" ? `model → ${s.name}` : s.name}{s.blocked?.length ? " · blocked by guardrail" : ""}</div>
                    {s.args?.length ? <div className="truncate font-mono text-meta text-faint">{s.args.join(" · ")}</div> : null}
                    {s.content ? <div className="text-meta text-tomato">{s.content}</div> : null}
                  </div>
                  <span className="ml-auto shrink-0 font-mono text-meta text-faint">{s.seconds != null ? `${s.seconds}s` : ""}</span>
                </li>
              ))}
            </ol>
            {detail.end && (
              <div className={`mt-5 sheet accent-corners p-4 ${rec?.ok ? "tone-green" : "tone-tomato"}`}>
                <div className="kicker">{rec?.ok ? `recommended plan verified · ${rec.plan} · ${Math.round(rec.cost_usd ?? 0).toLocaleString()} USD` : `not verified · ${rec?.reason ?? "unknown"}`}</div>
                <pre className="mt-2 whitespace-pre-wrap font-sans text-body">{detail.end.answer}</pre>
                {rec?.run_id && <a className="mt-2 inline-block text-body text-cobalt" href={`/runs/${rec.run_id}`}>open the plans →</a>}
              </div>
            )}
          </>
        )}
      </section>
    </div>
  );
}
