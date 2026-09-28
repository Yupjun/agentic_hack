"""nas_status — FAA National Airspace System status (public XML feed, no key).

Reports airport closures, ground stops, ground delay programs (GDP), and
arrival/departure delays. Source: https://nasstatus.faa.gov/api/airport-status-information

Optional replay: if NAS_OVERRIDE_FILE is set, entries from that JSON are merged in
and flagged "synthetic": true. This is how a demo scenario injects a GDP on a quiet day.
"""
from __future__ import annotations

import json
import os
import xml.etree.ElementTree as ET

from fastapi import APIRouter, Query

from .common import TTLCache, client, upstream_error

router = APIRouter()
_cache = TTLCache(120)
URL = "https://nasstatus.faa.gov/api/airport-status-information"


def _txt(el, tag):
    x = el.find(tag)
    return (x.text or "").strip() if x is not None and x.text else None


def _parse(xml_text: str) -> dict:
    root = ET.fromstring(xml_text)
    out = {"update_time": _txt(root, "Update_Time"), "closures": [], "ground_stops": [], "gdp": [], "delays": []}
    for dt in root.findall("Delay_type"):
        name = _txt(dt, "Name") or ""
        for ap in dt.iter("Airport"):
            arpt = _txt(ap, "ARPT")
            if not arpt:
                continue
            rec = {"airport": arpt, "reason": _txt(ap, "Reason")}
            low = name.lower()
            if "closure" in low:
                rec.update(start=_txt(ap, "Start"), reopen=_txt(ap, "Reopen"))
                out["closures"].append(rec)
            elif "ground stop" in low:
                rec.update(end_time=_txt(ap, "End_Time"))
                out["ground_stops"].append(rec)
            elif "ground delay" in low:
                rec.update(avg_delay=_txt(ap, "Avg"), max_delay=_txt(ap, "Max"))
                out["gdp"].append(rec)
            else:
                rec.update(kind=name, min_delay=_txt(ap, "Min"), max_delay=_txt(ap, "Max"), trend=_txt(ap, "Trend"))
                out["delays"].append(rec)
    return out


def _override() -> dict:
    p = os.environ.get("NAS_OVERRIDE_FILE")
    if not p:
        return {}
    with open(p, encoding="utf-8") as f:
        d = json.load(f)
    for k in ("closures", "ground_stops", "gdp", "delays"):
        for rec in d.get(k, []):
            rec["synthetic"] = True
    return d


@router.get("/nas")
def nas(airport: str | None = Query(None, description="FAA 3-letter id (JFK) or ICAO (KJFK); omit for all")):
    data = _cache.get("all")
    if data is None:
        with client() as c:
            try:
                r = c.get(URL)
            except Exception as e:  # noqa: BLE001
                raise upstream_error("nasstatus.faa.gov", f"{type(e).__name__}: {e}")
        if r.status_code != 200:
            raise upstream_error("nasstatus.faa.gov", f"HTTP {r.status_code}")
        try:
            data = _parse(r.text)
        except ET.ParseError as e:
            raise upstream_error("nasstatus.faa.gov", f"XML parse: {e}")
        ov = _override()
        for k in ("closures", "ground_stops", "gdp", "delays"):
            data[k] = data.get(k, []) + ov.get(k, [])
        data["synthetic_entries"] = sum(len(ov.get(k, [])) for k in ("closures", "ground_stops", "gdp", "delays"))
        _cache.put("all", data)
    if not airport:
        return data
    a = airport.strip().upper()
    a3 = a[1:] if len(a) == 4 and a.startswith("K") else a
    filt = {k: [x for x in data[k] if x["airport"] == a3] for k in ("closures", "ground_stops", "gdp", "delays")}
    filt["airport"] = a3
    filt["update_time"] = data["update_time"]
    filt["any_program"] = any(filt[k] for k in ("closures", "ground_stops", "gdp", "delays"))
    return filt
