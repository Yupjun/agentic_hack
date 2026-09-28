// geo.ts — 대권항로(great-circle) 순수 수학. 0702 이식(2026-08-25).
// 이식하며 자른 것: Shipment 도메인 타입 결합(→ 제네릭 GeoRoute), 하드코딩 색(→ 층에서 tokens 소비),
// 사장 함수 buildArcData/buildPointData/buildLabelData/colorForTempStatus (0702에서 테스트만 쓰던 잔재).

export type LonLat = [number, number];

/** 지구본에 그릴 경로 1건 — 도메인 무관(선적·이송·리니지 엣지 전부 이 모양으로 투영). */
export interface GeoRoute {
  id: string;
  origin: LonLat;
  dest: LonLat;
  /** 0..1 — 경로상 현재 위치 비율(표시 전용 파생값) */
  progress: number;
}

const toRad = (d: number) => (d * Math.PI) / 180;
const toDeg = (r: number) => (r * 180) / Math.PI;

/** 두 [lon,lat] 사이 대권(최단 표면 경로)을 segments 등분해 보간한다. */
export function greatCirclePoints(start: LonLat, end: LonLat, segments = 64): LonLat[] {
  const [lon1, lat1] = start;
  const [lon2, lat2] = end;
  const p1 = toRad(lat1);
  const l1 = toRad(lon1);
  const p2 = toRad(lat2);
  const l2 = toRad(lon2);

  const dp = p2 - p1;
  const dl = l2 - l1;
  const a = Math.sin(dp / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) ** 2;
  const d = 2 * Math.asin(Math.min(1, Math.sqrt(a))); // angular distance

  if (d === 0) return [start, end];

  const points: LonLat[] = [];
  for (let i = 0; i <= segments; i++) {
    const f = i / segments;
    const A = Math.sin((1 - f) * d) / Math.sin(d);
    const B = Math.sin(f * d) / Math.sin(d);
    const x = A * Math.cos(p1) * Math.cos(l1) + B * Math.cos(p2) * Math.cos(l2);
    const y = A * Math.cos(p1) * Math.sin(l1) + B * Math.cos(p2) * Math.sin(l2);
    const z = A * Math.sin(p1) + B * Math.sin(p2);
    const lat = Math.atan2(z, Math.sqrt(x * x + y * y));
    const lon = Math.atan2(y, x);
    points.push([toDeg(lon), toDeg(lat)]);
  }
  return points;
}

/** 대권 경로상 비율 f(0..1) 지점의 [lon,lat]. */
export function interpolateGreatCircle(start: LonLat, end: LonLat, f: number): LonLat {
  const pts = greatCirclePoints(start, end, 64);
  const idx = Math.min(pts.length - 1, Math.max(0, Math.round((pts.length - 1) * f)));
  return pts[idx];
}

/** 한 점에서 방위각 bearingDeg 로 distanceKm 간 지점 [lon,lat] — 실시간 침로 눈금용(W6).
 *  구면 삼각법 destination-point 공식. bearing() 의 역함수 관계(왕복 검증은 geo.test.ts). */
export function destinationPoint(origin: LonLat, bearingDeg: number, distanceKm: number): LonLat {
  const R = 6371;
  const d = distanceKm / R;
  const br = toRad(bearingDeg);
  const p1 = toRad(origin[1]);
  const l1 = toRad(origin[0]);
  const p2 = Math.asin(Math.sin(p1) * Math.cos(d) + Math.cos(p1) * Math.sin(d) * Math.cos(br));
  const l2 = l1 + Math.atan2(Math.sin(br) * Math.sin(d) * Math.cos(p1),
                             Math.cos(d) - Math.sin(p1) * Math.sin(p2));
  return [((toDeg(l2) + 540) % 360) - 180, toDeg(p2)];
}

/** start→end 초기 방위각(북 기준 시계방향, 0..360). */
export function bearing(start: LonLat, end: LonLat): number {
  const p1 = toRad(start[1]);
  const p2 = toRad(end[1]);
  const dl = toRad(end[0] - start[0]);
  const y = Math.sin(dl) * Math.cos(p2);
  const x = Math.cos(p1) * Math.sin(p2) - Math.sin(p1) * Math.cos(p2) * Math.cos(dl);
  return (toDeg(Math.atan2(y, x)) + 360) % 360;
}

export interface RoutePath {
  id: string;
  segment: 'traveled' | 'ahead';
  path: LonLat[];
}

/** 경로를 지나온 구간(실선)과 남은 구간(점선)으로 나눈다 — 항공지도 문법. 색은 층이 결정한다. */
export function buildRoutePaths(routes: GeoRoute[]): RoutePath[] {
  const out: RoutePath[] = [];
  for (const r of routes) {
    const full = greatCirclePoints(r.origin, r.dest, 64);
    const splitIdx = Math.min(full.length - 1, Math.max(1, Math.round((full.length - 1) * r.progress)));
    out.push({ id: r.id, segment: 'traveled', path: full.slice(0, splitIdx + 1) });
    out.push({ id: r.id, segment: 'ahead', path: full.slice(splitIdx) });
  }
  return out;
}

/** 연속 경도차가 180°를 넘는 지점(반자오선 이음새)에서 폴리라인을 끊는다. */
export function splitAtAntimeridian(path: LonLat[]): LonLat[][] {
  if (path.length === 0) return [];
  const segments: LonLat[][] = [];
  let current: LonLat[] = [path[0]];
  for (let i = 1; i < path.length; i++) {
    if (Math.abs(path[i][0] - path[i - 1][0]) > 180) {
      segments.push(current);
      current = [path[i]];
    } else {
      current.push(path[i]);
    }
  }
  if (current.length > 0) segments.push(current);
  return segments;
}

export interface PlaneDatum {
  id: string;
  position: LonLat;
  /** IconLayer angle 은 반시계 — bearing(시계)을 부호 반전해 담는다. */
  angle: number;
}

/** 이동 중(0<progress<1) 경로의 현재 위치 + 진행 방향 마커. */
export function buildPlaneData(routes: GeoRoute[]): PlaneDatum[] {
  return routes
    .filter((r) => r.progress > 0 && r.progress < 1)
    .map((r) => {
      const pos = interpolateGreatCircle(r.origin, r.dest, r.progress);
      return { id: r.id, position: pos, angle: -bearing(pos, r.dest) };
    });
}
