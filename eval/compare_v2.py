"""Run every banked scenario: engine (4 named plans) + two rule baselines, all
checked by the same verify and Monte Carlo; judge the pre-registered predictions.

Writes eval/scenarios-v2.json, eval/scenarios-v2.md and one journal row per scenario.
Usage: python -m eval.compare_v2 [scenario-id ...]
"""
from __future__ import annotations

import json
import os
import sys
import time
import warnings

warnings.filterwarnings("ignore")
from engine import journal  # noqa: E402
from engine.mc import simulate  # noqa: E402
from engine.run import solve_spec  # noqa: E402
from engine.verify import verify  # noqa: E402
from eval.baseline_v2 import rule_plan  # noqa: E402
from scenarios.gen import load_bank, spec_for  # noqa: E402
from scenarios.judge import derived, judge  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_one(entry: dict) -> dict:
    spec = spec_for(entry)
    t = time.time()
    res = solve_spec(spec, time_limit=90)
    rows = []
    for name in ("cost_optimal", "risk_adjusted", "balanced", "time_optimal"):
        p = res.get("plans", {}).get(name)
        if p:
            rows.append({"plan": name, "cost_usd": p["cost_usd"], "min_slack_days": p["metrics"]["min_slack_days"], "verify_ok": p["verify_ok"],
                         "p_all_on_time": p["mc"]["p_all_on_time"], "cost_mean_usd": p["mc"]["cost_mean_usd"],
                         "left_over": p["metrics"]["units_left_over"], "routes": derived(p)["route_classes"], "expedite": derived(p)["expedite_items"]})
    for rule in ("cheapest", "fastest"):
        r = rule_plan(spec, rule)
        v = verify(spec, r)
        r["cost_usd"] = v["metrics"]["cost_usd"]
        mc = simulate(spec, r) if r["shipments"] else None
        rows.append({"plan": f"rule_{rule}", "cost_usd": v["metrics"]["cost_usd"], "min_slack_days": v["metrics"]["min_slack_days"],
                     "verify_ok": v["ok"], "verify_problems": v["problems"][:4], "p_all_on_time": mc and mc["p_all_on_time"],
                     "cost_mean_usd": mc and mc["cost_mean_usd"], "left_over": v["metrics"]["units_left_over"],
                     "routes": derived(r)["route_classes"], "expedite": derived(r)["expedite_items"]})
    j = judge(entry, res)
    out = {"id": entry["id"], "family": entry["family"], "status": res["status"], "seconds": round(time.time() - t, 1),
           "n_candidates": res.get("n_candidates"), "problems": res.get("problems"), "rows": rows, "judge": j,
           "time_limited": res.get("time_limited")}
    journal.append("scenario_run", id=entry["id"], verdict=j["verdict"], passed=j["passed"], total=j["total"],
                   seconds=out["seconds"], status=res["status"])
    return out


def md(results: list[dict]) -> str:
    L = ["# Scenario bank v2 — engine vs rule baselines", "",
         "All plans re-checked by engine/verify.py (independent recomputation) and scored by engine/mc.py (10,000 samples, seed 7, CPU).",
         "p_on_time = probability every demand is met by its due date; mean cost includes the late penalty.", ""]
    L.append("| scenario | verdict | plan | cost USD | min slack d | verify | p_on_time | mean cost USD | left over | routes | expedite |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in results:
        v = f"{r['judge']['verdict']} {r['judge']['passed']}/{r['judge']['total']}" + (" (post-hoc)" if r["judge"]["prediction_registered"] == "after_observation" else "")
        for i, x in enumerate(r["rows"]):
            f = lambda k, d=0: "-" if x.get(k) is None else (f"{x[k]:,.{d}f}" if isinstance(x[k], (int, float)) else str(x[k]))
            L.append(f"| {r['id'] if i == 0 else ''} | {v if i == 0 else ''} | {x['plan']} | {f('cost_usd')} | {f('min_slack_days', 2)} | "
                     f"{'ok' if x['verify_ok'] else 'FAIL'} | {f('p_all_on_time', 3)} | {f('cost_mean_usd')} | {f('left_over')} | "
                     f"{','.join(x['routes'])} | {','.join(x['expedite']) or '-'} |")
    L += ["", "## Failed checks", ""]
    for r in results:
        for c in r["judge"]["checks"]:
            if not c["ok"]:
                L.append(f"- {r['id']}: `{c['metric']} {c['op']} {c['value']}` got `{c['got']}`")
        for x in r["rows"]:
            if not x["verify_ok"] and x.get("verify_problems"):
                L.append(f"- {r['id']} {x['plan']} verify: {'; '.join(x['verify_problems'])}")
    return "\n".join(L) + "\n"


def main(ids: list[str]) -> int:
    bank = [e for e in load_bank() if not ids or e["id"] in ids]
    results = []
    for e in bank:
        r = run_one(e)
        print(f"{r['id']:28s} {r['judge']['verdict']:9s} {r['judge']['passed']}/{r['judge']['total']}  {r['seconds']}s", flush=True)
        results.append(r)
    json.dump(results, open(os.path.join(ROOT, "eval", "scenarios-v2.json"), "w"), indent=1, ensure_ascii=False, default=str)
    open(os.path.join(ROOT, "eval", "scenarios-v2.md"), "w").write(md(results))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
