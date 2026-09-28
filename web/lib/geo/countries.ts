import { feature } from 'topojson-client';
import type { FeatureCollection, Geometry, Position } from 'geojson';
// world-atlas ships TopoJSON; convert to GeoJSON for a clean vector map.
import topology from 'world-atlas/countries-110m.json';

let cache: FeatureCollection<Geometry> | null = null;

export function getCountriesGeoJson(): FeatureCollection<Geometry> {
  if (cache) return cache;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const topo = topology as any;
  const collection = feature(topo, topo.objects.countries) as unknown as FeatureCollection<Geometry>;
  cache = collection;
  return collection;
}

export interface CountryRing {
  id: string | number | undefined;
  ring: [number, number][];
}

/** Extracts every polygon ring (exterior + holes) from all country features. */
export function getCountryRings(fc: FeatureCollection<Geometry>): CountryRing[] {
  const out: CountryRing[] = [];
  for (const f of fc.features) {
    const g = f.geometry;
    const pushPolygon = (poly: Position[][]) => {
      for (const ring of poly) {
        out.push({ id: f.id, ring: ring.map((p) => [p[0], p[1]] as [number, number]) });
      }
    };
    if (g.type === 'Polygon') pushPolygon(g.coordinates);
    else if (g.type === 'MultiPolygon') g.coordinates.forEach(pushPolygon);
  }
  return out;
}
