"""vessel — live ship position by MMSI via AISStream (websocket; free key by registration).

Needs AISSTREAM_API_KEY. Without it the tool answers 503 and says so: a missing
credential is a loud failure, not a silent "no ship".
"""
from __future__ import annotations

import asyncio
import json
import os

from fastapi import APIRouter, Query

from .common import upstream_error

router = APIRouter()


async def _listen(mmsi: str, key: str, wait_s: float) -> dict | None:
    import websockets  # local import: optional dependency

    sub = {"APIKey": key, "BoundingBoxes": [[[-90, -180], [90, 180]]], "FiltersShipMMSI": [mmsi],
           "FilterMessageTypes": ["PositionReport"]}
    async with websockets.connect("wss://stream.aisstream.io/v0/stream") as ws:
        await ws.send(json.dumps(sub))
        try:
            async with asyncio.timeout(wait_s):
                async for raw in ws:
                    m = json.loads(raw)
                    if m.get("MessageType") == "PositionReport":
                        pr = m["Message"]["PositionReport"]
                        meta = m.get("MetaData", {})
                        return {"mmsi": mmsi, "found": True, "name": meta.get("ShipName"), "lat": pr.get("Latitude"), "lon": pr.get("Longitude"),
                                "sog_kt": pr.get("Sog"), "cog_deg": pr.get("Cog"), "observed_at": meta.get("time_utc")}
        except TimeoutError:
            return None
    return None


@router.get("/vessel")
async def vessel(mmsi: str = Query(..., min_length=9, max_length=9), wait_s: float = Query(20, ge=5, le=90)):
    key = os.environ.get("AISSTREAM_API_KEY")
    if not key:
        raise upstream_error("aisstream", "AISSTREAM_API_KEY is not set (free key: aisstream.io)", status=503)
    try:
        hit = await _listen(mmsi, key, wait_s)
    except Exception as e:  # noqa: BLE001
        raise upstream_error("aisstream", f"{type(e).__name__}: {e}")
    if not hit:
        raise upstream_error("aisstream", f"no PositionReport for {mmsi} within {wait_s}s", status=404)
    return hit
