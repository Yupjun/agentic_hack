"""Reproducibility check: re-solve banked scenarios and compare with the committed results.

Compares, per scenario and plan row: cost, minimum slack, on-time probability, expected cost,
routes, and the verdict. Same inputs + HiGHS + seeded Monte Carlo must give the same numbers.
  python -m eval.replay_check            # all 11
  python -m eval.replay_check --family S1 # quick (~2 min)
Exit 1 on any difference (printed).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import warnings

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from eval.compare_v2 import run_one  # noqa: E402
from scenarios.gen import load_bank  # noqa: E402

KEYS = ("cost_usd", "min_slack_days", "p_all_on_time", "cost_mean_usd", "routes", "verify_ok")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", default=None)
    a = ap.parse_args()
    ref = {r["id"]: r for r in json.load(open(os.path.join(ROOT, "eval", "scenarios-v2.json")))}
    diffs, n = [], 0
    for e in load_bank():
        if a.family and e["family"] != a.family:
            continue
        got = run_one(e)
        want = ref.get(e["id"])
        if want is None:
            diffs.append(f"{e['id']}: no committed result")
            continue
        if got["judge"]["verdict"] != want["judge"]["verdict"]:
            diffs.append(f"{e['id']}: verdict {got['judge']['verdict']} != {want['judge']['verdict']}")
        w = {x["plan"]: x for x in want["rows"]}
        for x in got["rows"]:
            n += 1
            for k in KEYS:
                if x.get(k) != w.get(x["plan"], {}).get(k):
                    diffs.append(f"{e['id']} {x['plan']} {k}: replay {x.get(k)} != committed {w.get(x['plan'], {}).get(k)}")
        print(f"{e['id']:28s} replayed, {len(diffs)} differences so far", flush=True)
    print(f"compared {n} plan rows; differences: {len(diffs)}")
    for d in diffs:
        print("  " + d)
    return 1 if diffs else 0


if __name__ == "__main__":
    sys.exit(main())
