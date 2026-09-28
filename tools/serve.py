"""Mount every tool under one FastAPI app for local development.

Each tool is its own router and can be served alone:
  uvicorn tools.flight_status:app   (see __main__ pattern below)
Port: TOOLS_PORT (default 8090).
"""
from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from . import allocate, cost, flight_status, hazards, nas_status, notam, schedule, vessel, wx

app = FastAPI(title="cargo-recovery-agent tools", version="0.1")
for mod in (flight_status, nas_status, wx, hazards, vessel, notam, schedule, cost, allocate):
    app.include_router(mod.router)


@app.exception_handler(Exception)
async def _loud(_: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": {"source": "tool", "error": f"{type(exc).__name__}: {exc}"}})


@app.get("/health")
def health():
    return {"ok": True, "tools": ["flight", "nas", "wx", "hazards", "vessel", "notam", "schedule", "cost", "allocate"],
            "scenario_dir": os.environ.get("SCENARIO_DIR"), "nas_override": os.environ.get("NAS_OVERRIDE_FILE")}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("TOOLS_PORT", "8090")))
