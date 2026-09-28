// solar.ts — 태양 직하점(주야 터미네이터)의 순수 수학 (W5+, 2026-08-26). React/deck 없음 — vitest 검증.
//
// 표시용 근사다: 적위는 코사인 근사(±0.3°), 경도는 균시차(equation of time) 1차 근사(±0.5°) —
// 렌더 목적(밤 반구 음영)엔 화면에서 구분 불가능한 오차. 천문력 정밀도가 필요해지면 이 파일만 간다.
import type { LonLat } from './geo';

const RAD = Math.PI / 180;

/** 연중 일수(1..365.x) — UTC 기준. */
function dayOfYearUTC(d: Date): number {
  const start = Date.UTC(d.getUTCFullYear(), 0, 1);
  return (d.getTime() - start) / 86400000 + 1;
}

/** 태양 적위(도) — cos 근사: -23.44° · cos(360/365 · (N+10)). 하지 +23.4, 동지 -23.4, 춘/추분 ≈ 0. */
export function solarDeclination(d: Date): number {
  const n = dayOfYearUTC(d);
  return -23.44 * Math.cos(((360 / 365) * (n + 10)) * RAD);
}

/** 균시차(분) — 1차 근사(Whitman). 태양 경도 보정용. */
export function equationOfTimeMin(d: Date): number {
  const n = dayOfYearUTC(d);
  const b = ((360 / 365) * (n - 81)) * RAD;
  return 9.87 * Math.sin(2 * b) - 7.53 * Math.cos(b) - 1.5 * Math.sin(b);
}

/** 태양 직하점 [lon, lat] — 그 순간 태양이 천정에 있는 지점. */
export function subsolarPoint(d: Date): LonLat {
  const utcHours = d.getUTCHours() + d.getUTCMinutes() / 60 + d.getUTCSeconds() / 3600;
  const solarHours = utcHours + equationOfTimeMin(d) / 60;
  let lon = (12 - solarHours) * 15;                 // 정오(태양시 12시)의 경도
  if (lon > 180) lon -= 360;
  if (lon < -180) lon += 360;
  return [lon, solarDeclination(d)];
}

/** 반태양점(밤 반구 중심)의 단위벡터 [x,y,z] — **deck.gl GlobeViewport 의 CARTESIAN 프레임**:
 *  [sinλ·cosφ, −cosλ·cosφ, sinφ] (globe-viewport.js 실측, 2026-08-26 — 처음 x=cosλcosφ 관례로
 *  썼다가 밤 반구가 경도 90° 틀어져 렌더로 잡았다). 밤 반구 메시의 방향축. */
export function antisolarUnitVector(d: Date): [number, number, number] {
  const [lon, lat] = subsolarPoint(d);
  const phi = lat * RAD, lam = lon * RAD;
  return [-Math.sin(lam) * Math.cos(phi), Math.cos(lam) * Math.cos(phi), -Math.sin(phi)];
}

/** 단위 +Z 반구(폴라 캡 90°)의 삼각 메시를 만들어 `axis` 방향으로 회전시킨 위치 배열.
 *  반환 {positions: Float32Array(xyz…), indices: Uint32Array} — SimpleMeshLayer 용.
 *  구면 폴리곤의 극점-교차 테셀레이션 문제(earcut 가 lon/lat 평면에서 깨짐)를 피해
 *  메시를 직접 만든다 — 터미네이터 원은 이 반구의 가장자리 그 자체다. */
export function hemisphereMesh(axis: [number, number, number], radius: number,
                               rings = 24, slices = 48): { positions: Float32Array; indices: Uint32Array } {
  // +Z 를 axis 로 보내는 회전: r = axis, 임의 직교기저 (u, v, r)
  const [rx, ry, rz] = axis;
  const ref: [number, number, number] = Math.abs(rz) < 0.9 ? [0, 0, 1] : [1, 0, 0];
  let ux = ry * ref[2] - rz * ref[1], uy = rz * ref[0] - rx * ref[2], uz = rx * ref[1] - ry * ref[0];
  const ul = Math.hypot(ux, uy, uz); ux /= ul; uy /= ul; uz /= ul;
  const vx = ry * uz - rz * uy, vy = rz * ux - rx * uz, vz = rx * uy - ry * ux;

  const pos: number[] = [];
  for (let i = 0; i <= rings; i++) {
    const polar = (i / rings) * (Math.PI / 2);      // 0(중심) → 90°(터미네이터)
    const s = Math.sin(polar), c = Math.cos(polar);
    for (let j = 0; j <= slices; j++) {
      const az = (j / slices) * 2 * Math.PI;
      const lx = s * Math.cos(az), ly = s * Math.sin(az), lz = c;   // 로컬 (+Z 캡)
      pos.push(radius * (lx * ux + ly * vx + lz * rx),
               radius * (lx * uy + ly * vy + lz * ry),
               radius * (lx * uz + ly * vz + lz * rz));
    }
  }
  const idx: number[] = [];
  const row = slices + 1;
  for (let i = 0; i < rings; i++) {
    for (let j = 0; j < slices; j++) {
      const a = i * row + j, b = a + row;
      idx.push(a, b, a + 1, a + 1, b, b + 1);
    }
  }
  return { positions: new Float32Array(pos), indices: new Uint32Array(idx) };
}
