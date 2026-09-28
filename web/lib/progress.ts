// Where is each shipment at time t? Pure function of the plan (no rendering), so it can be tested.
// Phases: in_production (before ready) -> waiting (at origin before the first departure)
//         -> moving (on a leg) -> connecting (at a node between legs) -> delivered.
import { interpolateGreatCircle } from "./geo/geo";
import type { LonLat } from "./geo/geo";

export type Leg = { lane: string; mode: string; from: string; to: string; depart: string; arrive: string };
export type Ship = { id: string; item: string; qty: number; option: string | null; source: string; mfg?: string; ready?: string; legs: Leg[] };
export type Node = { lat: number | null; lon: number | null; name?: string; kind?: string };
export type Phase = "in_production" | "waiting" | "moving" | "connecting" | "delivered";
export type State = { id: string; phase: Phase; pos: LonLat; legIndex: number; mode: string | null; fraction: number;
  at: string; text: string; next: { label: string; t: number } | null };

const ms = (s: string) => new Date(s).getTime();
export const lonlat = (n?: Node): LonLat | null => (n && n.lat != null && n.lon != null ? [n.lon, n.lat] : null);

export function shipState(s: Ship, t: number, nodes: Record<string, Node>): State | null {
  const legs = s.legs;
  if (!legs.length) return null;
  const first = legs[0];
  const origin = lonlat(nodes[first.from]);
  if (!origin) return null;
  const readyT = s.ready ? ms(s.ready) : ms(first.depart);
  if (s.source.startsWith("prod:") && t < readyT)
    return { id: s.id, phase: "in_production", pos: origin, legIndex: -1, mode: null, fraction: 0, at: first.from,
             text: `생산 중 @ ${nodes[first.from]?.name ?? first.from}`, next: { label: `생산 완료`, t: readyT } };
  for (let i = 0; i < legs.length; i++) {
    const g = legs[i];
    const a = lonlat(nodes[g.from]), b = lonlat(nodes[g.to]);
    if (!a || !b) return null;
    const d = ms(g.depart), r = ms(g.arrive);
    if (t < d) {
      const phase: Phase = i === 0 ? "waiting" : "connecting";
      return { id: s.id, phase, pos: a, legIndex: i, mode: g.mode, fraction: 0, at: g.from,
               text: `${i === 0 ? "출발 대기" : "환적 대기"} @ ${nodes[g.from]?.name ?? g.from}`, next: { label: `${g.mode} ${g.from}→${g.to} 출발`, t: d } };
    }
    if (t < r) {
      const f = (t - d) / (r - d);
      return { id: s.id, phase: "moving", pos: interpolateGreatCircle(a, b, f), legIndex: i, mode: g.mode, fraction: f, at: `${g.from}→${g.to}`,
               text: `${g.mode} ${g.from}→${g.to} ${Math.round(f * 100)}%`, next: { label: `${g.to} 도착`, t: r } };
    }
  }
  const last = legs[legs.length - 1];
  return { id: s.id, phase: "delivered", pos: lonlat(nodes[last.to])!, legIndex: legs.length, mode: null, fraction: 1, at: last.to,
           text: `도착 @ ${nodes[last.to]?.name ?? last.to}`, next: null };
}

export function planWindow(ships: Ship[]): [number, number] {
  const starts = ships.flatMap((s) => [s.ready ? ms(s.ready) : ms(s.legs[0].depart), ms(s.legs[0].depart)]);
  const ends = ships.map((s) => ms(s.legs[s.legs.length - 1].arrive));
  return [Math.min(...starts) - 86400000, Math.max(...ends) + 86400000];
}
