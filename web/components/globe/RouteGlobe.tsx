"use client";
// Question: for this plan, where is each shipment at time t, by which mode, and what happens next?
// Globe rendering adapted from the earlier cold-chain globe (deck.gl _GlobeView, paper globe, night
// hemisphere from the sun position, great-circle legs split at the antimeridian). New here: multi-leg
// routes per order, a time cursor that can be played, and per-shipment state at that time.
import { useEffect, useMemo, useState } from "react";
import DeckGL from "@deck.gl/react";
import { _GlobeView as GlobeMapView, COORDINATE_SYSTEM } from "@deck.gl/core";
import { GeoJsonLayer, PathLayer, ScatterplotLayer } from "@deck.gl/layers";
import { PathStyleExtension } from "@deck.gl/extensions";
import { SimpleMeshLayer } from "@deck.gl/mesh-layers";
import { Geometry, SphereGeometry } from "@luma.gl/engine";
import { greatCirclePoints, interpolateGreatCircle, bearing, destinationPoint, splitAtAntimeridian } from "@/lib/geo/geo";
import type { LonLat } from "@/lib/geo/geo";
import { getCountriesGeoJson, getCountryRings } from "@/lib/geo/countries";
import { splitFeatureCollectionAtAntimeridian } from "@/lib/geo/antimeridian";
import { antisolarUnitVector, hemisphereMesh } from "@/lib/geo/solar";
import { G, MODE_RGB } from "@/lib/globeTokens";
import { lonlat, planWindow, shipState } from "@/lib/progress";
import type { Node, Ship, State } from "@/lib/progress";

type Any = any; // deck.gl accessor params
const EARTH_RADIUS = 6.3e6;
const FLAT = { ambient: 1, diffuse: 0, shininess: 1, specularColor: [0, 0, 0] };
const DAY = 86400000;
const SPEEDS = [0.5, 1, 3, 7];   // days per second of playback
const fmt = (t: number) => new Date(t).toISOString().slice(0, 16).replace("T", " ") + "Z";
const a = (c: number[], alpha: number) => [c[0], c[1], c[2], alpha];

function graticule(step = 20): { path: LonLat[] }[] {
  const out: { path: LonLat[] }[] = [];
  for (let lat = -80; lat <= 80; lat += step) { const p: LonLat[] = []; for (let lon = -180; lon <= 180; lon += 4) p.push([lon, lat]); out.push({ path: p }); }
  for (let lon = -180; lon < 180; lon += step) { const p: LonLat[] = []; for (let lat = -88; lat <= 88; lat += 4) p.push([lon, lat]); out.push({ path: p }); }
  return out;
}

export default function RouteGlobe({ ships, nodes, dues }: { ships: Ship[]; nodes: Record<string, Node>; dues: { id: string; due: string }[] }) {
  const [t0, t1] = useMemo(() => planWindow(ships), [ships]);
  const now = Date.now();
  const [t, setT] = useState(() => (now >= t0 && now <= t1 ? now : t0));
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(3);
  const [sel, setSel] = useState<string | null>(null);

  useEffect(() => {
    if (!playing) return;
    let last = performance.now();
    let raf = 0;
    const step = (x: number) => {
      const dt = (x - last) / 1000; last = x;
      setT((cur) => { const n = cur + dt * speed * DAY; if (n >= t1) { setPlaying(false); return t1; } return n; });
      raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [playing, speed, t1]);

  const states = useMemo(() => ships.map((s) => shipState(s, t, nodes)).filter(Boolean) as State[], [ships, t, nodes]);
  const byId = useMemo(() => new Map(states.map((s) => [s.id, s])), [states]);

  // static geometry
  const sphere = useMemo(() => new SphereGeometry({ radius: EARTH_RADIUS, nlat: 96, nlong: 192 }), []);
  const grat = useMemo(() => graticule(), []);
  const countries = useMemo(() => getCountriesGeoJson(), []);
  const fills = useMemo(() => splitFeatureCollectionAtAntimeridian(countries), [countries]);
  const borders = useMemo(() => getCountryRings(countries).flatMap(({ ring }) => splitAtAntimeridian(ring).map((path) => ({ path }))), [countries]);
  const dayMin = Math.floor(t / 600000);   // night hemisphere follows the cursor, 10-minute steps
  const night = useMemo(() => {
    const { positions, indices } = hemisphereMesh(antisolarUnitVector(new Date(dayMin * 600000)), EARTH_RADIUS * 1.0125);
    return new Geometry({ topology: "triangle-list", attributes: { positions: { value: positions, size: 3 } }, indices: { value: indices, size: 1 } });
  }, [dayMin]);

  // legs: traveled (solid) vs ahead (dashed), coloured by mode
  const legSegs = useMemo(() => {
    const out: { path: LonLat[]; ship: string; mode: string; done: boolean }[] = [];
    for (const s of ships) {
      const st = byId.get(s.id);
      s.legs.forEach((g, i) => {
        const p = lonlat(nodes[g.from]), q = lonlat(nodes[g.to]);
        if (!p || !q) return;
        const done = !!st && (st.phase === "delivered" || i < st.legIndex);
        if (st && st.phase === "moving" && i === st.legIndex) {
          const mid = interpolateGreatCircle(p, q, st.fraction);
          for (const path of splitAtAntimeridian(greatCirclePoints(p, mid, 48))) out.push({ path, ship: s.id, mode: g.mode, done: true });
          for (const path of splitAtAntimeridian(greatCirclePoints(mid, q, 48))) out.push({ path, ship: s.id, mode: g.mode, done: false });
        } else {
          for (const path of splitAtAntimeridian(greatCirclePoints(p, q, 64))) out.push({ path, ship: s.id, mode: g.mode, done });
        }
      });
    }
    return out;
  }, [ships, nodes, byId]);

  const usedNodes = useMemo(() => {
    const ids = new Set(ships.flatMap((s) => s.legs.flatMap((g) => [g.from, g.to])));
    return [...ids].map((id) => ({ id, pos: lonlat(nodes[id]), name: nodes[id]?.name ?? id })).filter((n) => n.pos) as { id: string; pos: LonLat; name: string }[];
  }, [ships, nodes]);

  const lateIds = useMemo(() => {
    // a shipment is late at t if t passed the earliest due it serves and it has not arrived
    const firstDue = dues.length ? Math.min(...dues.map((d) => new Date(d.due).getTime())) : Infinity;
    return new Set(states.filter((s) => s.phase !== "delivered" && t > firstDue).map((s) => s.id));
  }, [states, dues, t]);

  const markers = states.map((s) => ({ ...s, air: s.phase === "moving" && s.mode === "air" }));
  const planes = markers.filter((m) => m.air).map((m) => {
    const sh = ships.find((x) => x.id === m.id)!;
    const g = sh.legs[m.legIndex];
    const q = lonlat(nodes[g.to])!;
    return { ...m, heading: bearing(m.pos, q) };
  });

  const layers = [
    new SimpleMeshLayer({ id: "earth", data: [0], mesh: sphere, coordinateSystem: COORDINATE_SYSTEM.CARTESIAN, getPosition: () => [0, 0, 0], getColor: G.ocean, material: FLAT as Any }),
    new GeoJsonLayer({ id: "land", data: fills as Any, stroked: false, filled: true, getFillColor: G.land }),
    new PathLayer({ id: "graticule", data: grat, getPath: (d: Any) => d.path, getColor: G.graticule, getWidth: 0.5, widthUnits: "pixels" }),
    new PathLayer({ id: "borders", data: borders, getPath: (d: Any) => d.path, getColor: G.border, getWidth: 0.6, widthUnits: "pixels" }),
    new SimpleMeshLayer({ id: "night", data: [0], mesh: night, coordinateSystem: COORDINATE_SYSTEM.CARTESIAN, getPosition: () => [0, 0, 0],
      getColor: a(G.night, 30) as Any, material: FLAT as Any, parameters: { depthWriteEnabled: false } as Any, updateTriggers: { mesh: [dayMin] } }),
    new PathLayer({ id: "legs-ahead", data: legSegs.filter((l) => !l.done), getPath: (d: Any) => d.path,
      getColor: (d: Any) => a(MODE_RGB[d.mode] ?? G.muted, sel && sel !== d.ship ? 50 : 150) as Any, getWidth: 1.6, widthUnits: "pixels",
      getDashArray: [3, 4], dashJustified: true, extensions: [new PathStyleExtension({ dash: true })], updateTriggers: { getColor: [sel] } }),
    new PathLayer({ id: "legs-done", data: legSegs.filter((l) => l.done), getPath: (d: Any) => d.path,
      getColor: (d: Any) => a(MODE_RGB[d.mode] ?? G.ink, sel && sel !== d.ship ? 70 : 240) as Any,
      getWidth: (d: Any) => (sel === d.ship ? 4 : 2.4), widthUnits: "pixels", capRounded: true, jointRounded: true,
      pickable: true, onClick: (i: Any) => i.object && setSel(i.object.ship), updateTriggers: { getColor: [sel], getWidth: [sel] } }),
    new ScatterplotLayer({ id: "nodes", data: usedNodes, pickable: true, getPosition: (d: Any) => d.pos, getFillColor: G.ocean, getLineColor: G.ink, stroked: true,
      lineWidthMinPixels: 1.2, getRadius: 4, radiusUnits: "pixels" }),
    new ScatterplotLayer({ id: "ships", data: markers.filter((m) => !m.air), getPosition: (d: Any) => d.pos,
      getFillColor: (d: Any) => (lateIds.has(d.id) ? G.tomato : d.phase === "delivered" ? G.green : d.phase === "in_production" ? G.ocean : (MODE_RGB[d.mode ?? ""] ?? G.ink)) as Any,
      getLineColor: (d: Any) => (d.phase === "in_production" ? G.ink : G.ocean) as Any, stroked: true, lineWidthMinPixels: 1.5,
      getRadius: (d: Any) => (sel === d.id ? 9 : 6), radiusUnits: "pixels", pickable: true, onClick: (i: Any) => i.object && setSel(i.object.id),
      updateTriggers: { getFillColor: [t, lateIds], getRadius: [sel] } }),
    // Moving air shipments: a larger dot plus a heading tick. (Icon/Text layers use texture atlases and
    // rendered nothing here — measured 2026-09-28 in headless Chromium; the old globe's comments record
    // the same IconLayer atlas trap. Names come from the hover tooltip and the side list instead.)
    new PathLayer({ id: "plane-heading", data: planes, getPath: (d: Any) => [d.pos, destinationPoint(d.pos, d.heading, 450)],
      getColor: (d: Any) => (lateIds.has(d.id) ? G.tomato : MODE_RGB.air) as Any, getWidth: 3, widthUnits: "pixels", capRounded: true,
      updateTriggers: { getColor: [lateIds] } }),
    new ScatterplotLayer({ id: "planes", data: planes, getPosition: (d: Any) => d.pos,
      getFillColor: (d: Any) => (lateIds.has(d.id) ? G.tomato : MODE_RGB.air) as Any, getLineColor: G.ocean, stroked: true, lineWidthMinPixels: 2,
      getRadius: (d: Any) => (sel === d.id ? 11 : 8), radiusUnits: "pixels", pickable: true, onClick: (i: Any) => i.object && setSel(i.object.id),
      updateTriggers: { getFillColor: [lateIds], getRadius: [sel] } }),
  ];

  const center = usedNodes.length ? usedNodes.reduce((acc, n) => [acc[0] + n.pos[0] / usedNodes.length, acc[1] + n.pos[1] / usedNodes.length], [0, 0]) : [100, 30];
  const [view, setView] = useState<Any>({ longitude: center[0], latitude: center[1], zoom: 1.35 });
  const counts = states.reduce((m: Record<string, number>, s) => ((m[s.phase] = (m[s.phase] ?? 0) + 1), m), {});
  const upcoming = states.filter((s) => s.next).sort((x, y) => x.next!.t - y.next!.t).slice(0, 5);
  const shipsById = new Map(ships.map((s) => [s.id, s]));

  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_420px]">
      <div>
        <div className="sheet relative h-[560px] overflow-hidden">
          <DeckGL views={new GlobeMapView()} viewState={view} controller={true} onViewStateChange={(e: Any) => setView(e.viewState)} layers={layers}
            onError={(e: Any, layer: Any) => console.error("deck layer error", layer?.id, String(e))}
            getTooltip={(info: Any) => { const o = info.object; if (!o) return null;
              if (o.name) return { text: `${o.id} — ${o.name}` };
              if (o.text) { const sh = shipsById.get(o.id); return { text: `${sh?.item} × ${sh?.qty}: ${o.text}${o.next ? `\nnext: ${o.next.label} ${fmt(o.next.t)}` : ""}` }; }
              return null; }} />
          <div className="pointer-events-none absolute left-4 top-3 bg-sheet px-2 py-1 font-mono text-body">{fmt(t)}</div>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <button className={`stamp ${playing ? "stamp-on" : "stamp-primary"}`} onClick={() => { if (t >= t1) setT(t0); setPlaying(!playing); }}>{playing ? "Pause" : "Play"}</button>
          <button className="stamp stamp-quiet" onClick={() => { setPlaying(false); setT(t0); }}>Start</button>
          <button className="stamp stamp-quiet" onClick={() => { setPlaying(false); setT(Math.min(Math.max(Date.now(), t0), t1)); }}>Now</button>
          {SPEEDS.map((sp) => <button key={sp} className={`stamp ${speed === sp ? "stamp-on" : "stamp-quiet"} text-meta`} onClick={() => setSpeed(sp)}>{sp} d/s</button>)}
          <input aria-label="time" type="range" min={t0} max={t1} step={3600000} value={t} onChange={(e) => { setPlaying(false); setT(Number(e.target.value)); }} className="min-w-[240px] flex-1" />
        </div>
        <div className="mt-2 flex flex-wrap gap-4 text-meta text-muted">
          {Object.entries(MODE_RGB).slice(0, 4).map(([m, c]) => <span key={m} className="flex items-center gap-1"><svg width={12} height={12}><rect width={12} height={12} fill={`rgb(${c.join(",")})`} /></svg>{m}</span>)}
          <span>solid = travelled · dashed = ahead · hollow dot = in production · green = delivered · tomato = past the first due date and not delivered</span>
          {Date.now() < t0 && <span className="text-butter-ink">실시간 기준으로는 아직 계획 시작 전입니다 (Now = 시작 시점)</span>}
        </div>
      </div>
      <div className="space-y-4">
        <section className="sheet p-4">
          <div className="kicker">at {fmt(t)}</div>
          <div className="mt-1 text-body">
            {(["in_production", "waiting", "moving", "connecting", "delivered"] as const).map((p) => <span key={p} className="mr-3">{p.replace("_", " ")} <span className="font-mono font-semibold">{counts[p] ?? 0}</span></span>)}
          </div>
        </section>
        <section className="sheet">
          <div className="kicker px-4 pt-3">shipments · click to focus</div>
          {states.map((s) => {
            const sh = shipsById.get(s.id)!;
            return (
              <button key={s.id} onClick={() => setSel(sel === s.id ? null : s.id)} className={`block w-full border-b border-line px-4 py-2 text-left ${sel === s.id ? "accent-corners tone-cobalt" : ""}`}>
                <div className="text-body"><span className="font-semibold">{sh.item} × {sh.qty}</span>{sh.option === "expedite" ? " · expedite" : ""} — <span className={lateIds.has(s.id) ? "text-tomato" : s.phase === "delivered" ? "text-green" : ""}>{s.text}</span></div>
                <div className="font-mono text-meta text-faint">{sh.legs.map((g) => g.from).concat(sh.legs[sh.legs.length - 1].to).join(" → ")}{s.next ? ` · next: ${s.next.label} ${fmt(s.next.t)}` : ""}</div>
              </button>
            );
          })}
        </section>
        <section className="sheet p-4">
          <div className="kicker mb-2">next events</div>
          {upcoming.map((s) => <div key={s.id} className="font-mono text-meta text-muted">{fmt(s.next!.t)} · {shipsById.get(s.id)!.item} × {shipsById.get(s.id)!.qty} · {s.next!.label}</div>)}
          {!upcoming.length && <div className="text-meta text-muted">all shipments delivered</div>}
        </section>
      </div>
    </div>
  );
}
