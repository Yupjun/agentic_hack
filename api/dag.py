"""Plan Builder API: the user's process graph (dag/v1) in, the searched plans out.
  GET  /api/dag/presets        the two preset graphs
  POST /api/dag/solve          body = dag/v1 spec -> CPM / PERT-MC / max flow / crashing / Pareto (engine/dag.py)
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import time

from fastapi import APIRouter, Request

from engine import journal
from engine.dag import solve

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
router = APIRouter()


@router.get("/api/dag/presets")
def presets():
    return [json.load(open(f, encoding="utf-8")) for f in sorted(glob.glob(os.path.join(ROOT, "scenarios", "dag", "*.json")))]


@router.post("/api/dag/solve")
async def dag_solve(request: Request):
    spec = await request.json()
    t = time.time()
    res = solve(spec)
    res["seconds"] = round(time.time() - t, 3)
    h = hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()[:12]
    os.makedirs(os.path.join(ROOT, "state", "dag_runs"), exist_ok=True)
    json.dump({"spec": spec, "result": res}, open(os.path.join(ROOT, "state", "dag_runs", f"{spec.get('id', 'dag')}-{h}.json"), "w"), ensure_ascii=False)
    journal.append("dag_solve", spec_id=spec.get("id"), hash=h, status=res["status"], n_plans=res.get("n_plans"), n_feasible=res.get("n_feasible"),
                   objective=spec.get("objective"), recommended=res.get("recommended"), seconds=res["seconds"])
    return res
