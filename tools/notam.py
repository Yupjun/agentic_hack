"""notam — NOTAMs for a location via the FAA NOTAM API (api.faa.gov; key by registration).

Needs FAA_NOTAM_CLIENT_ID and FAA_NOTAM_CLIENT_SECRET. Without them: 503 with the
reason. There is no keyless official NOTAM feed, and this tool does not scrape.
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Query

from .common import TTLCache, client, upstream_error

router = APIRouter()
_cache = TTLCache(600)
URL = "https://external-api.faa.gov/notamapi/v1/notams"


@router.get("/notam")
def notam(icao: str = Query(..., min_length=4, max_length=4), limit: int = Query(50, ge=1, le=200)):
    cid, sec = os.environ.get("FAA_NOTAM_CLIENT_ID"), os.environ.get("FAA_NOTAM_CLIENT_SECRET")
    if not (cid and sec):
        raise upstream_error("faa-notam", "FAA_NOTAM_CLIENT_ID / FAA_NOTAM_CLIENT_SECRET not set (register at api.faa.gov)", status=503)
    st = icao.upper()
    hit = _cache.get(st)
    if hit:
        return hit
    with client() as c:
        try:
            r = c.get(URL, params={"icaoLocation": st, "pageSize": limit, "responseFormat": "geoJson"},
                      headers={"client_id": cid, "client_secret": sec})
        except Exception as e:  # noqa: BLE001
            raise upstream_error("faa-notam", f"{type(e).__name__}: {e}")
    if r.status_code != 200:
        raise upstream_error("faa-notam", f"HTTP {r.status_code}")
    items = []
    for f in r.json().get("items") or []:
        core = ((f.get("properties") or {}).get("coreNOTAMData") or {}).get("notam") or {}
        items.append({"number": core.get("number"), "type": core.get("type"), "classification": core.get("classification"),
                      "effective": core.get("effectiveStart"), "expires": core.get("effectiveEnd"), "text": core.get("text")})
    out = {"station": st, "count": len(items), "notams": items}
    _cache.put(st, out)
    return out
