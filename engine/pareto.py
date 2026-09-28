"""Cost-vs-slack frontier by epsilon-constraint, plus the four named plans.

Sweep the required slack b over [0, b_max] (b_max = the largest slack any demand
could get from its fastest eligible candidate). At each b, minimise cost (lp.solve).
Every point is re-checked by verify and scored by mc.

Named plans (always returned when feasible):
  cost_optimal   lowest cost (b = 0)
  time_optimal   largest realised minimum slack (ties -> cheaper)
  balanced       knee: closest to the utopia point after min-max normalising cost and slack
  risk_adjusted  lowest expected (mean) cost including the late penalty from Monte Carlo
Only non-dominated verified points are eligible (mark_dominated).
"""
from __future__ import annotations

import math

from planner import timeutil as tu

from .lp import solve
from .mc import simulate
from .options import Problem, eligible
from .verify import verify


def slack_upper(prob: Problem) -> float:
    s = prob.spec
    best = []
    for d in prob.demands:
        arr = [c.arrive for c in prob.candidates if eligible(s, c, d, 0.0)]
        if not arr:
            return 0.0
        best.append(tu.to_day(d["due"], s.t0) - min(arr))
    return max(0.0, min(best))


def frontier(spec: dict, prob: Problem, points: int, backend: str | None = None, time_limit: float = 60.0) -> list[dict]:
    b_max = slack_upper(prob)
    grid = [b_max * i / (points - 1) for i in range(points)] if points > 1 else [0.0]
    out, seen = [], set()
    for b in grid:
        r = solve(prob, slack=b, backend=backend, time_limit=time_limit)
        pt = {"slack_required": round(b, 3), "status": r["status"], "backend": r["backend"],
              "seconds": round(r.get("seconds_build", 0) + r.get("seconds_solve", 0), 3), "gap_rel": r.get("gap_rel")}
        if r["status"] not in ("optimal", "time_limit"):
            pt["reason"] = r.get("reason")
            out.append(pt)
            continue
        v = verify(spec, r)
        key = (round(r["cost_usd"], 2), v["metrics"]["min_slack_days"])
        if key in seen:
            pt["duplicate_of"] = key
            out.append(pt)
            continue
        seen.add(key)
        pt.update({"cost_usd": r["cost_usd"], "verify_ok": v["ok"], "verify_problems": v["problems"], "metrics": v["metrics"],
                   "mc": simulate(spec, r), "plan": {"shipments": r["shipments"], "allocations": r["allocations"], "cost_usd": r["cost_usd"]}})
        out.append(pt)
    return out


def mark_dominated(points: list[dict]) -> None:
    """A verified point is dominated if another costs no more AND has at least as much
    slack, and is strictly better on one. Found 2026-09-28: two 21,400 USD plans with
    8.7 and 15.2 days of slack both survived and the worse one was named."""
    ok = [p for p in points if p.get("verify_ok")]
    for p in ok:
        c, t = p["cost_usd"], p["metrics"]["min_slack_days"]
        p["dominated"] = any(q is not p and q["cost_usd"] <= c + 1e-6 and q["metrics"]["min_slack_days"] >= t - 1e-6
                             and (q["cost_usd"] < c - 1e-6 or q["metrics"]["min_slack_days"] > t + 1e-6) for q in ok)


def named(points: list[dict]) -> dict:
    mark_dominated(points)
    ok = [p for p in points if p.get("verify_ok") and not p.get("dominated")]
    if not ok:
        return {}
    cost_opt = min(ok, key=lambda p: (p["cost_usd"], -p["metrics"]["min_slack_days"]))
    time_opt = max(ok, key=lambda p: (p["metrics"]["min_slack_days"], -p["cost_usd"]))
    cmin, cmax = cost_opt["cost_usd"], max(p["cost_usd"] for p in ok)
    smin, smax = min(p["metrics"]["min_slack_days"] for p in ok), time_opt["metrics"]["min_slack_days"]

    def dist(p):
        c = 0.0 if cmax == cmin else (p["cost_usd"] - cmin) / (cmax - cmin)
        t = 0.0 if smax == smin else (smax - p["metrics"]["min_slack_days"]) / (smax - smin)
        return math.hypot(c, t)

    balanced = min(ok, key=lambda p: (dist(p), p["cost_usd"]))
    risk = min(ok, key=lambda p: (p["mc"]["cost_mean_usd"], p["cost_usd"]))
    return {"cost_optimal": cost_opt, "time_optimal": time_opt, "balanced": balanced, "risk_adjusted": risk}
