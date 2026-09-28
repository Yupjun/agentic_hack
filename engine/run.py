"""python -m engine.run solve <spec.json> [--backend highs|cuopt] [--points N] [--out path]

validate -> build candidates -> frontier (LP per slack level) -> verify + Monte Carlo
per point -> four named plans -> result JSON (state/runs/) + one journal row.
Exit 1 when the spec is invalid or no verified plan exists (fail noisily).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import warnings

warnings.filterwarnings("ignore", message=".*libcuopt.*")

from planner.grammar import PlanSpec  # noqa: E402
from planner.structure import spec_hash, structure_key  # noqa: E402
from planner.validate import validate  # noqa: E402

from . import journal  # noqa: E402
from .options import build  # noqa: E402
from .pareto import frontier, named  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def solve_spec(spec: dict, backend: str | None = None, points: int | None = None, time_limit: float = 60.0) -> dict:
    t0 = time.time()
    probs = validate(spec)
    base = {"result": "plan-result/v1", "spec_id": spec.get("id"), "family": spec.get("family"),
            "spec_hash": spec_hash(spec), "backend": backend or os.environ.get("CARGO_LP_BACKEND", "highs")}
    if probs:
        base.update(status="invalid_spec", problems=probs, seconds=round(time.time() - t0, 3))
        return base
    s = PlanSpec.model_validate(spec)
    prob = build(s)
    base.update(structure_key=structure_key(spec), n_candidates=len(prob.candidates), n_demands=len(prob.demands), notes=prob.notes)
    pts = frontier(spec, prob, points or s.objective.pareto_points, backend=backend, time_limit=time_limit)
    plans = named(pts)
    base.update(frontier=[{k: v for k, v in p.items() if k != "plan"} for p in pts],
                plans={k: {"slack_required": p["slack_required"], "cost_usd": p["cost_usd"], "metrics": p["metrics"], "mc": p["mc"],
                           "verify_ok": p["verify_ok"], **p["plan"]} for k, p in plans.items()},
                recommended={"min_cost": "cost_optimal", "max_slack": "time_optimal", "balanced": "balanced"}[s.objective.primary],
                status="ok" if plans else "no_verified_plan", seconds=round(time.time() - t0, 3),
                time_limited=[p["slack_required"] for p in pts if p.get("status") == "time_limit"])
    return base


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="engine.run")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("solve")
    a.add_argument("spec")
    a.add_argument("--backend", default=None)
    a.add_argument("--points", type=int, default=None)
    a.add_argument("--time-limit", type=float, default=60.0)
    a.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    spec = json.load(open(args.spec, encoding="utf-8"))
    res = solve_spec(spec, args.backend, args.points, args.time_limit)
    out = args.out or os.path.join(ROOT, "state", "runs", f"{spec.get('id')}-{res['spec_hash']}.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(res, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    summary = {k: {"cost_usd": v["cost_usd"], "min_slack_days": v["metrics"]["min_slack_days"], "p_all_on_time": v["mc"]["p_all_on_time"],
                   "cost_mean_usd": v["mc"]["cost_mean_usd"], "cost_p95_usd": v["mc"]["cost_p95_usd"]} for k, v in res.get("plans", {}).items()}
    journal.append("solve", spec_id=spec.get("id"), spec_hash=res["spec_hash"], structure_key=res.get("structure_key"),
                   backend=res["backend"], status=res["status"], seconds=res["seconds"], plans=summary, out=os.path.relpath(out, ROOT),
                   hypothesis=spec.get("hypothesis", ""))
    print(json.dumps({"status": res["status"], "seconds": res["seconds"], "out": out, "plans": summary,
                      "problems": res.get("problems"), "time_limited": res.get("time_limited")}, indent=1, ensure_ascii=False))
    return 0 if res["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
