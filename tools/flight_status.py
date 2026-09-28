"""flight_status — live aircraft position by callsign from community ADS-B feeds.

Sources, in order: adsb.lol, adsb.fi. Both are public, no key. The tool stops at the
first source that answers with a position. 404 = no source sees the callsign right now.
502 = every source failed (network or upstream error) — distinct from "not flying".
"""
from __future__ import annotations

from fastapi import APIRouter, Query

from .common import TTLCache, client, now_iso, upstream_error

router = APIRouter()
_cache = TTLCache(60)

SOURCES = [
    ("adsb.lol", "https://api.adsb.lol/v2/callsign/{cs}"),
    ("adsb.fi", "https://opendata.adsb.fi/api/v2/callsign/{cs}"),
]


def _pick(ac: list[dict]) -> dict | None:
    for a in ac:
        if a.get("lat") is not None and a.get("lon") is not None:
            return a
    return None


@router.get("/flight")
def flight(callsign: str = Query(..., min_length=3, max_length=8, description="ICAO callsign, e.g. KAL073")):
    cs = callsign.strip().upper()
    cached = _cache.get(cs)
    if cached:
        return cached
    failures = []
    with client() as c:
        for name, tpl in SOURCES:
            try:
                r = c.get(tpl.format(cs=cs))
                if r.status_code != 200:
                    failures.append(f"{name}: HTTP {r.status_code}")
                    continue
                a = _pick(r.json().get("ac") or [])
                if not a:
                    failures.append(f"{name}: no position")
                    continue
                out = {
                    "callsign": cs,
                    "found": True,
                    "source": name,
                    "hex": a.get("hex"),
                    "type": a.get("t"),
                    "lat": a.get("lat"),
                    "lon": a.get("lon"),
                    "alt_ft": a.get("alt_baro"),
                    "gs_kt": a.get("gs"),
                    "track_deg": a.get("track"),
                    "on_ground": a.get("alt_baro") == "ground",
                    "observed_at": now_iso(),
                }
                _cache.put(cs, out)
                return out
            except Exception as e:  # noqa: BLE001 — report, never swallow
                failures.append(f"{name}: {type(e).__name__}: {e}")
    if all(f.endswith("no position") for f in failures):
        raise upstream_error("adsb", f"{cs} not seen by any feed right now", status=404)
    raise upstream_error("adsb", "; ".join(failures))
