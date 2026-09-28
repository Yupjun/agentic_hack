"""hazards — natural-hazard events from GDACS (public, no key), optionally inside a bbox."""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Query

from .common import TTLCache, client, upstream_error

router = APIRouter()
_cache = TTLCache(900)
URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"


@router.get("/hazards")
def hazards(days: int = Query(7, ge=1, le=30), bbox: str | None = Query(None, description="minLon,minLat,maxLon,maxLat"),
            types: str = Query("EQ,TC,FL,VO,DR,WF")):
    key = f"{days}|{types}"
    data = _cache.get(key)
    if data is None:
        to = dt.date.today()
        frm = to - dt.timedelta(days=days)
        with client() as c:
            try:
                r = c.get(URL, params={"eventlist": types, "fromDate": frm.isoformat(), "toDate": to.isoformat()})
            except Exception as e:  # noqa: BLE001
                raise upstream_error("gdacs", f"{type(e).__name__}: {e}")
        if r.status_code != 200:
            raise upstream_error("gdacs", f"HTTP {r.status_code}")
        feats = r.json().get("features") or []
        data = []
        for f in feats:
            p = f.get("properties") or {}
            g = (f.get("geometry") or {}).get("coordinates") or [None, None]
            data.append({"id": p.get("eventid"), "type": p.get("eventtype"), "name": p.get("name"), "alert": p.get("alertlevel"),
                         "from": p.get("fromdate"), "to": p.get("todate"), "country": p.get("country"), "lon": g[0], "lat": g[1]})
        _cache.put(key, data)
    if bbox:
        x0, y0, x1, y1 = (float(v) for v in bbox.split(","))
        data = [d for d in data if d["lon"] is not None and x0 <= d["lon"] <= x1 and y0 <= d["lat"] <= y1]
    return {"count": len(data), "events": data}
