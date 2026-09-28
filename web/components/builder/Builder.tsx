"use client";
// Plan Builder: the user writes the hypothesis as a spec (steps -> task nodes -> approved suppliers + SCM parameters),
// picks what "best" means, and runs it. The engine enumerates every supplier/expedite choice in the tree.
import { useEffect, useState } from "react";
import { Panel, Badge } from "../ui";
import { DagGraph } from "./DagGraph";
import { GlobalParams, NodeEditor } from "./Editor";
import { Results } from "./Results";
import type { DagSpec, Result } from "./types";
import { OBJ } from "./types";

function newNode(s: DagSpec, stepIdx: number) {
  const id = `n${Date.now().toString(36)}`, prev = s.steps[stepIdx - 1];
  const tmpl = s.steps.flatMap((x) => x.nodes)[0].options[0];
  s.steps[stepIdx].nodes.push({ id, task: "새 작업", qty_per_unit: 1, join: "all", after: prev ? prev.nodes.map((n) => n.id) : [],
    options: [{ ...structuredClone(tmpl), id: `${id}-opt1`, supplier: "새 승인 공급처" }] });
  return id;
}

export function Builder() {
  const [presets, setPresets] = useState<DagSpec[]>([]);
  const [spec, setSpec] = useState<DagSpec | null>(null);
  const [node, setNode] = useState<string>("");
  const [res, setRes] = useState<Result | null>(null);
  const [sel, setSel] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => { fetch("/api/dag/presets").then((r) => r.json()).then((ps: DagSpec[]) => { setPresets(ps); load(ps[0]); }).catch((e) => setErr(String(e))); }, []);

  function load(p: DagSpec) { setSpec(structuredClone(p)); setNode(p.steps[0]?.nodes[0]?.id ?? ""); setRes(null); setSel(""); setErr(""); }
  const set = (f: (s: DagSpec) => void) => setSpec((s) => { if (!s) return s; const c = structuredClone(s); f(c); return c; });

  async function solve() {
    if (!spec) return;
    setBusy(true); setErr("");
    try {
      const r = await fetch("/api/dag/solve", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(spec) });
      if (!r.ok) throw new Error(`solve ${r.status}`);
      const j: Result = await r.json();
      setRes(j); setSel(j.named?.[spec.objective] ?? j.recommended ?? "");
      if (j.status !== "ok") setErr([j.status, ...(j.problems ?? []), j.hint ?? ""].filter(Boolean).join(" · "));
    } catch (e) { setErr(String(e)); } finally { setBusy(false); }
  }

  function pickObjective(o: string) {
    set((s) => { s.objective = o; });
    if (res?.named?.[o]) setSel(res.named[o]);
  }
  function addNode(stepIdx: number) { if (!spec) return; const c = structuredClone(spec); setNode(newNode(c, stepIdx)); setSpec(c); }
  function addStep() {
    if (!spec) return;
    const c = structuredClone(spec);
    c.steps.push({ id: `st${c.steps.length + 1}-${Date.now().toString(36)}`, name: `단계 ${c.steps.length + 1}`, nodes: [] });
    setNode(newNode(c, c.steps.length - 1)); setSpec(c);
  }
  function removeNode(id: string) {
    set((s) => {
      s.steps.forEach((st) => { st.nodes = st.nodes.filter((n) => n.id !== id); st.nodes.forEach((n) => { n.after = n.after.filter((a) => a !== id); }); });
      s.steps = s.steps.filter((st) => st.nodes.length);
    });
    setNode("");
  }

  if (!spec) return <div className="text-body text-muted">{err || "불러오는 중…"}</div>;
  const plan = res?.plans?.[sel];
  return (
    <div className="grid gap-5">
      <Panel title="어떤 가설을 시험하나?" kicker="프리셋에서 시작해 무엇이든 바꿀 수 있습니다"
        right={<div className="flex gap-2">{presets.map((p) => <button key={p.id} onClick={() => load(p)} className={`border px-3 py-1 text-meta ${p.id === spec.id ? "border-ink bg-ink text-sheet" : "border-line"}`}>{p.title.split("·")[0].trim()}</button>)}</div>}>
        <div className="text-lead font-semibold">{spec.title}</div>
        <textarea value={spec.hypothesis} rows={2} onChange={(e) => set((s) => { s.hypothesis = e.target.value; })} className="mt-2 w-full border border-line bg-sheet p-2 text-body" />
      </Panel>

      <Panel title="단계와 작업, 누가 할 수 있나?" kicker="작업을 누르면 아래에서 승인 공급처와 SCM 파라미터를 고칩니다" right={<button onClick={addStep} className="border border-ink px-3 py-1 text-meta">단계 추가</button>}>
        <DagGraph spec={spec} plan={plan} sel={node} onSel={setNode} />
        <div className="mt-3 flex flex-wrap gap-2">{spec.steps.map((st, i) => <span key={st.id} className="flex items-center gap-1 text-meta">
          <input value={st.name} onChange={(e) => set((s) => { s.steps[i].name = e.target.value; })} className="w-28 border border-line bg-sheet px-1" />
          <button onClick={() => addNode(i)} className="border border-line px-2">작업 +</button></span>)}</div>
      </Panel>

      {node && spec.steps.some((s) => s.nodes.some((n) => n.id === node)) && <Panel title="이 작업의 승인 공급처와 조건" kicker={`작업 id ${node}`} right={<button onClick={() => removeNode(node)} className="text-meta text-tomato">작업 삭제</button>}>
        <NodeEditor spec={spec} id={node} set={set} />
      </Panel>}

      <Panel title="수요와 재고 정책, 불확실성" kicker="모든 안에 똑같이 적용되는 파라미터"><GlobalParams spec={spec} set={set} /></Panel>

      <Panel title="무엇을 가장 원하나?" kicker="목표를 바꾸면 다시 풀지 않고 이미 계산된 안 중에서 고릅니다">
        <div className="flex flex-wrap gap-2">{OBJ.map(([o, label, hint]) => <button key={o} onClick={() => pickObjective(o)} title={hint}
          className={`border px-4 py-2 text-body ${spec.objective === o ? "border-cobalt bg-cobalt text-sheet" : "border-line"}`}>{label}</button>)}</div>
        <div className="mt-2 text-meta text-muted">{OBJ.find((x) => x[0] === spec.objective)?.[2]}</div>
        <div className="mt-4 flex items-center gap-3">
          <button onClick={solve} disabled={busy} className="border-2 border-ink bg-ink px-6 py-2 text-body font-semibold text-sheet disabled:opacity-50">{busy ? "푸는 중…" : "실행"}</button>
          {res && <Badge tone={res.status === "ok" ? "green" : "tomato"}>{res.status}</Badge>}
          {err && <span className="text-meta text-tomato">{err}</span>}
        </div>
      </Panel>

      {res && res.status === "ok" && sel && <Results spec={spec} r={res} sel={sel} setSel={setSel} />}
    </div>
  );
}
