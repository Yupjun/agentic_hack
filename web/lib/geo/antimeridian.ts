import type { Feature, FeatureCollection, Geometry, Position } from 'geojson';

type Ring = [number, number][];

function toXY(ring: Position[]): Ring {
  return ring.map((p) => [p[0], p[1]] as [number, number]);
}

/** Makes a ring's longitudes continuous (no ±360 jumps between consecutive points). */
function unwrap(ring: Ring): Ring {
  const out: Ring = [[ring[0][0], ring[0][1]]];
  for (let i = 1; i < ring.length; i++) {
    let lon = ring[i][0];
    const prev = out[i - 1][0];
    while (lon - prev > 180) lon -= 360;
    while (lon - prev < -180) lon += 360;
    out.push([lon, ring[i][1]]);
  }
  return out;
}

function intersectX(a: [number, number], b: [number, number], x: number): [number, number] {
  const t = (x - a[0]) / (b[0] - a[0]);
  return [x, a[1] + t * (b[1] - a[1])];
}

/** Sutherland-Hodgman clip of a closed polygon against a vertical half-plane. */
function clipHalf(poly: Ring, x: number, keepGreaterEqual: boolean): Ring {
  const out: Ring = [];
  const n = poly.length;
  if (n === 0) return out;
  const inside = (p: [number, number]) => (keepGreaterEqual ? p[0] >= x : p[0] <= x);
  for (let i = 0; i < n; i++) {
    const cur = poly[i];
    const prev = poly[(i + n - 1) % n];
    const curIn = inside(cur);
    const prevIn = inside(prev);
    if (curIn) {
      if (!prevIn) out.push(intersectX(prev, cur, x));
      out.push(cur);
    } else if (prevIn) {
      out.push(intersectX(prev, cur, x));
    }
  }
  return out;
}

export function ringCrossesAntimeridian(ring: Ring): boolean {
  for (let i = 1; i < ring.length; i++) {
    if (Math.abs(ring[i][0] - ring[i - 1][0]) > 180) return true;
  }
  return false;
}

/** Splits a crossing outer ring into pieces, each with longitudes in [-180,180]. */
function splitOuterRing(ring: Ring): Ring[] {
  let r = ring;
  if (r.length > 1 && r[0][0] === r[r.length - 1][0] && r[0][1] === r[r.length - 1][1]) {
    r = r.slice(0, -1);
  }
  const uw = unwrap(r);
  const lons = uw.map((p) => p[0]);
  const kMin = Math.floor((Math.min(...lons) + 180) / 360);
  const kMax = Math.floor((Math.max(...lons) + 180) / 360);

  const pieces: Ring[] = [];
  for (let k = kMin; k <= kMax; k++) {
    const lo = -180 + 360 * k;
    const hi = 180 + 360 * k;
    let clipped = clipHalf(uw, lo, true);
    if (clipped.length < 3) continue;
    clipped = clipHalf(clipped, hi, false);
    if (clipped.length < 3) continue;
    const shifted: Ring = clipped.map(([x, y]) => [x - 360 * k, y] as [number, number]);
    shifted.push([shifted[0][0], shifted[0][1]]); // close
    pieces.push(shifted);
  }
  return pieces;
}

/**
 * Returns a FeatureCollection where every polygon that crosses the antimeridian
 * is split into pieces that stay within [-180,180], so they fill cleanly on a
 * globe. Non-crossing polygons (including their holes) are kept unchanged.
 */
export function splitFeatureCollectionAtAntimeridian(
  fc: FeatureCollection<Geometry>,
): FeatureCollection<Geometry> {
  const features: Feature<Geometry>[] = [];
  //: `srcIndex` = 이 조각이 나온 **원본 피처의 첨자**. 잘라 내면 새 객체가 되므로 원본과의
  //  연결이 끊긴다 — 그 연결을 잃어버려서 국가 채움(코로플레스)이 화면에 아예 안 나왔다
  //  (2026-08-31 실측: 채움 맵을 원본 피처 참조로 잡아 뒀는데, 레이어가 그리는 것은 조각이었다).
  //  id 로 잇지 않는 이유는 이 topojson 에 id 없는 피처가 있기 때문이다.
  const addPolygon = (id: Feature['id'], rings: Position[][], srcIndex: number) => {
    if (rings.length === 0) return;
    const outer = toXY(rings[0]);
    if (!ringCrossesAntimeridian(outer)) {
      features.push({ type: 'Feature', id, properties: { srcIndex }, geometry: { type: 'Polygon', coordinates: rings } });
    } else {
      for (const piece of splitOuterRing(outer)) {
        features.push({ type: 'Feature', id, properties: { srcIndex }, geometry: { type: 'Polygon', coordinates: [piece] } });
      }
    }
  };
  fc.features.forEach((f, i) => {
    const g = f.geometry;
    if (g.type === 'Polygon') addPolygon(f.id, g.coordinates, i);
    else if (g.type === 'MultiPolygon') g.coordinates.forEach((poly) => addPolygon(f.id, poly, i));
  });
  return { type: 'FeatureCollection', features };
}
