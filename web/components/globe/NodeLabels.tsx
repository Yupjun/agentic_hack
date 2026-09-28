"use client";
// Node labels over the globe canvas: name + ARR / DEP / dwell per node, as HTML (deck Text/Icon layers
// rendered nothing in headless Chromium — texture atlas). Positions come from a GlobeViewport built
// from the same viewState and container size as the DeckGL canvas, so they match the drawn dots.
import { _GlobeViewport as GlobeViewport } from "@deck.gl/core";
import type { Node, Ship } from "@/lib/progress";

const DAY = 86400000;
const MAX_LABELS = 12;
const CARD_W = 236;
const GAP = 18;          // offset from the dot, so the card never covers it
const HORIZON = 0.18;    // cos of the angle from the view centre; below this the node is near/behind the limb

export type NodeEvent = { ship: string; node: string; role: "origin" | "mid" | "dest"; ready?: number; arr?: number; dep?: number };

const ms = (s?: string) => (s ? new Date(s).getTime() : undefined);
export const stamp = (t: number) => new Date(t).toISOString().slice(5, 16).replace("T", " ") + "Z";
const dwell = (x: number) => (x >= DAY ? `대기 ${(x / DAY).toFixed(1)}일` : `대기 ${(x / 3600000).toFixed(1)}시간`);

/** Every arrival / departure of every shipment, grouped by node. */
export function nodeEvents(ships: Ship[]): Map<string, NodeEvent[]> {
  const out = new Map<string, NodeEvent[]>();
  const push = (e: NodeEvent) => { const l = out.get(e.node) ?? []; l.push(e); out.set(e.node, l); };
  for (const s of ships) {
    const L = s.legs;
    if (!L.length) continue;
    push({ ship: s.id, node: L[0].from, role: "origin", ready: ms(s.ready), dep: ms(L[0].depart) });
    for (let i = 1; i < L.length; i++) push({ ship: s.id, node: L[i].from, role: "mid", arr: ms(L[i - 1].arrive), dep: ms(L[i].depart) });
    push({ ship: s.id, node: L[L.length - 1].to, role: "dest", arr: ms(L[L.length - 1].arrive) });
  }
  return out;
}

const startOf = (e: NodeEvent) => e.arr ?? e.ready ?? e.dep ?? 0;
const endOf = (e: NodeEvent) => e.dep ?? e.arr ?? e.ready ?? 0;

/** The event to show at a node: the selected shipment's, else the next one not finished at t, else the last. */
function pick(evs: NodeEvent[], t: number, sel: string | null): NodeEvent | null {
  if (sel) return evs.find((e) => e.ship === sel) ?? null;
  const open = evs.filter((e) => endOf(e) >= t).sort((a, b) => startOf(a) - startOf(b));
  if (open.length) return open[0];
  return [...evs].sort((a, b) => endOf(b) - endOf(a))[0] ?? null;
}

type Row = { k: string; v: string; tone?: "tomato" | "muted" };
function rows(e: NodeEvent, due: number | null): Row[] {
  const r: Row[] = [];
  if (e.role === "origin") {
    if (e.ready != null) r.push({ k: "생산 완료", v: stamp(e.ready) });
    if (e.dep != null) r.push({ k: "출발", v: stamp(e.dep) });
    if (e.ready != null && e.dep != null && e.dep > e.ready) r.push({ k: "", v: dwell(e.dep - e.ready), tone: "muted" });
  } else if (e.role === "mid") {
    if (e.arr != null) r.push({ k: "ARR", v: stamp(e.arr) });
    if (e.dep != null) r.push({ k: "DEP", v: stamp(e.dep) });
    if (e.arr != null && e.dep != null) r.push({ k: "", v: dwell(e.dep - e.arr), tone: "muted" });
  } else {
    if (e.arr != null) r.push({ k: "도착", v: stamp(e.arr) });
    if (due != null) r.push({ k: "기한", v: stamp(due).slice(0, 5), tone: e.arr != null && e.arr > due ? "tomato" : undefined });
  }
  return r;
}

type Placed = { id: string; x: number; y: number; lx: number; ly: number; w: number; h: number; head: string; kind: string;
  sub: string | null; rows: Row[]; late: boolean };

export default function NodeLabels(props: {
  width: number; height: number; view: { longitude: number; latitude: number; zoom: number };
  nodes: Record<string, Node>; events: Map<string, NodeEvent[]>; ships: Ship[]; t: number; sel: string | null; due: number | null;
}) {
  const { width, height, view, nodes, events, ships, t, sel, due } = props;
  if (!width || !height) return null;
  const vp = new GlobeViewport({ width, height, longitude: view.longitude, latitude: view.latitude, zoom: view.zoom });
  const rad = Math.PI / 180;
  const c = [Math.cos(view.latitude * rad) * Math.cos(view.longitude * rad), Math.cos(view.latitude * rad) * Math.sin(view.longitude * rad), Math.sin(view.latitude * rad)];
  const shipById = new Map(ships.map((s) => [s.id, s]));

  // candidates: visible side, inside the canvas, with an event to show
  const cands: (Placed & { rank: number })[] = [];
  for (const [id, evs] of events) {
    const n = nodes[id];
    if (!n || n.lat == null || n.lon == null) continue;
    const u = [Math.cos(n.lat * rad) * Math.cos(n.lon * rad), Math.cos(n.lat * rad) * Math.sin(n.lon * rad), Math.sin(n.lat * rad)];
    if (u[0] * c[0] + u[1] * c[1] + u[2] * c[2] < HORIZON) continue;
    const [x, y] = vp.project([n.lon, n.lat]);
    if (!(x >= 0 && x <= width && y >= 0 && y <= height)) continue;
    const e = pick(evs, t, sel);
    if (!e) continue;
    const others = new Set(evs.map((v) => v.ship)).size - 1;
    const sh = shipById.get(e.ship);
    const rr = rows(e, due);
    const late = e.role === "dest" && due != null && e.arr != null && e.arr > due;
    const sub = sel ? null : `${e.ship}${sh ? ` · ${sh.item} × ${sh.qty}` : ""}${others > 0 ? ` · 외 ${others}건` : ""}`;
    const h = 30 + (sub ? 20 : 0) + rr.length * 20 + 10;
    cands.push({ id, x, y, lx: 0, ly: 0, w: CARD_W, h, head: n.name ?? id, kind: n.kind ?? "", sub, rows: rr, late,
      rank: Math.abs(startOf(e) - t) });
  }
  // keep at most 12, nearest to the time cursor first; then place greedily without overlap
  cands.sort((a, b) => a.rank - b.rank);
  const placed: Placed[] = [];
  const hit = (a: { lx: number; ly: number; w: number; h: number }, b: { lx: number; ly: number; w: number; h: number }) =>
    a.lx < b.lx + b.w + 4 && b.lx < a.lx + a.w + 4 && a.ly < b.ly + b.h + 4 && b.ly < a.ly + a.h + 4;
  const dots = cands.map((d) => ({ lx: d.x - 6, ly: d.y - 6, w: 12, h: 12 }));
  for (const d of cands) {
    if (placed.length >= MAX_LABELS) break;
    const spots = [[GAP, -d.h - GAP], [GAP, GAP], [-d.w - GAP, -d.h - GAP], [-d.w - GAP, GAP], [GAP, -d.h / 2], [-d.w - GAP, -d.h / 2],
      [-d.w / 2, -d.h - 2 * GAP], [-d.w / 2, 2 * GAP], [2 * GAP, -d.h - 3 * GAP], [2 * GAP, 3 * GAP], [-d.w - 2 * GAP, -d.h - 3 * GAP], [-d.w - 2 * GAP, 3 * GAP]];
    for (const [dx, dy] of spots) {
      // clamp into the canvas (below the clock), then reject if it covers any dot or another card
      const box = { lx: Math.min(Math.max(d.x + dx, 4), width - 4 - d.w), ly: Math.min(Math.max(d.y + dy, 40), height - 4 - d.h), w: d.w, h: d.h };
      if (placed.some((p) => hit(box, p)) || dots.some((o) => hit(box, o))) continue;
      placed.push({ ...d, lx: box.lx, ly: box.ly });
      break;
    }
  }

  return (
    <div className="pointer-events-none absolute inset-0" data-testid="node-labels" data-count={placed.length}>
      <svg width={width} height={height} className="absolute left-0 top-0">
        {placed.map((p) => {
          const ax = Math.min(Math.max(p.x, p.lx), p.lx + p.w), ay = Math.min(Math.max(p.y, p.ly), p.ly + p.h);
          return <line key={p.id} x1={p.x} y1={p.y} x2={ax} y2={ay} className={p.late ? "stroke-tomato" : "stroke-ink"} strokeWidth={1} />;
        })}
      </svg>
      {placed.map((p) => (
        <div key={p.id} className={`sheet absolute px-2 py-1 ${p.late ? "border-tomato" : ""}`} style={{ left: p.lx, top: p.ly, width: p.w }}>
          <div className="truncate text-body text-ink"><span className="font-mono font-semibold">{p.id}</span> {p.head}{p.kind ? <span className="text-meta text-muted"> ({p.kind})</span> : null}</div>
          {p.sub && <div className="truncate text-meta text-muted">{p.sub}</div>}
          {p.rows.map((r, i) => (
            <div key={i} className={`flex justify-between gap-2 text-meta ${r.tone === "tomato" ? "text-tomato" : r.tone === "muted" ? "text-muted" : "text-ink"}`}>
              <span>{r.k}</span><span className="font-mono">{r.v}</span>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
