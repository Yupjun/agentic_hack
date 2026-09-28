"""wx — aviation weather for a station: METAR, TAF, active SIGMET/AIRMET near it,
plus surface wind forecast. Sources: aviationweather.gov data API and Open-Meteo.
Both public, no key.
"""
from __future__ import annotations

from fastapi import APIRouter, Query

from .common import TTLCache, client, upstream_error

router = APIRouter()
_cache = TTLCache(300)
AWC = "https://aviationweather.gov/api/data"


def _get(c, source, url, params=None):
    try:
        r = c.get(url, params=params)
    except Exception as e:  # noqa: BLE001
        raise upstream_error(source, f"{type(e).__name__}: {e}")
    if r.status_code != 200:
        raise upstream_error(source, f"HTTP {r.status_code}")
    return r.json()


@router.get("/wx")
def wx(icao: str = Query(..., min_length=4, max_length=4, description="ICAO station, e.g. KJFK")):
    st = icao.upper()
    hit = _cache.get(st)
    if hit:
        return hit
    with client() as c:
        metar = _get(c, "awc/metar", f"{AWC}/metar", {"ids": st, "format": "json"})
        taf = _get(c, "awc/taf", f"{AWC}/taf", {"ids": st, "format": "json"})
        if not metar:
            raise upstream_error("awc/metar", f"no METAR for {st}", status=404)
        m = metar[0]
        lat, lon = m.get("lat"), m.get("lon")
        sig = _get(c, "awc/airsigmet", f"{AWC}/airsigmet", {"format": "json"})
        near = []
        for s in sig or []:
            coords = s.get("coords") or []
            if not coords or lat is None:
                continue
            lats = [p.get("lat") for p in coords if p.get("lat") is not None]
            lons = [p.get("lon") for p in coords if p.get("lon") is not None]
            if lats and lons and min(lats) - 1 <= lat <= max(lats) + 1 and min(lons) - 1 <= lon <= max(lons) + 1:
                near.append({"hazard": s.get("hazard"), "severity": s.get("severity"), "valid_to": s.get("validTimeTo"), "raw": (s.get("rawAirSigmet") or "")[:200]})
        wind = _get(c, "open-meteo", "https://api.open-meteo.com/v1/forecast",
                    {"latitude": lat, "longitude": lon, "hourly": "wind_speed_10m,wind_gusts_10m,precipitation,visibility",
                     "forecast_hours": 24, "wind_speed_unit": "kn"})
    out = {
        "station": st, "lat": lat, "lon": lon,
        "metar": {"raw": m.get("rawOb"), "obs_time": m.get("reportTime"), "wind_kt": m.get("wspd"), "gust_kt": m.get("wgst"),
                  "vis_mi": m.get("visib"), "flight_category": m.get("fltCat"), "wx": m.get("wxString")},
        "taf_raw": (taf[0].get("rawTAF") if taf else None),
        "sigmet_airmet_near": near,
        "surface_forecast_24h": {k: wind.get("hourly", {}).get(k) for k in ("time", "wind_speed_10m", "wind_gusts_10m", "precipitation", "visibility")},
    }
    _cache.put(st, out)
    return out
