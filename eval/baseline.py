"""Baselines for the eval table. Both go through the same cost tool as the agent.

  do_nothing : keep every AWB on its booked (GDP-delayed) flight.
  rule       : per booked-flight group, pick the earliest-arriving option chain to the
               final destination with enough remaining capacity (greedy, capacity consumed).
Usage: SCENARIO_DIR=... python -m eval.baseline  (tool server on TOOLS_URL)
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

import httpx

TOOLS_URL = os.environ.get("TOOLS_URL", "http://127.0.0.1:8090").rstrip("/")
SD = os.environ["SCENARIO_DIR"]


def load(name):
    with open(os.path.join(SD, name), encoding="utf-8") as f:
        return json.load(f)


def cost(awb_count, cutoff, legs):
    r = httpx.post(TOOLS_URL + "/cost", json={"awb_count": awb_count, "cutoff": cutoff, "legs": legs}, timeout=30)
    r.raise_for_status()
    return r.json()


def chains(options, origin, final, max_legs=2):
    """All 1- or 2-leg chains origin -> final, time-feasible (next departs after prior arrives + 3h)."""
    out = []
    for a in options:
        if a["origin"] != origin:
            continue
        if a["dest"] == final:
            out.append([a])
            continue
        if max_legs < 2:
            continue
        for b in options:
            if b["origin"] == a["dest"] and b["dest"] == final and b["depart"] >= a["arrive"][:13] + ":00:00" and b["depart"] > a["arrive"]:
                out.append([a, b])
    return out


def main():
    goal = load("goal.json")
    options = load("options.json")
    cutoff = goal["awbs"][0]["cutoff"]
    final = goal["awbs"][0]["final_dest"]
    groups = defaultdict(list)
    for a in goal["awbs"]:
        groups[a["booked_flight"]].append(a)
    byid = {o["id"]: o for o in options}
    cap = {o["id"]: o["capacity_kg"] for o in options}
    rows = []
    # do nothing
    legs, kg_total = [], 0
    for fl, awbs in groups.items():
        kg = sum(a["chargeable_kg"] for a in awbs)
        o = byid[f"{fl}-0929"]
        legs.append({"mode": o["mode"], "option_id": o["id"], "origin": o["origin"], "dest": o["dest"], "depart": o["depart"], "arrive": o["arrive"], "chargeable_kg": kg, "rate_per_kg_usd": o["rate_per_kg_usd"]})
        if o["dest"] != final:  # DLH405 lands FRA: nobody moves it -> stranded; charge the truck as the implicit follow-on
            t = byid["TRK-FRA-LHR"]
            legs.append({"mode": t["mode"], "option_id": t["id"], "origin": t["origin"], "dest": t["dest"], "depart": t["depart"], "arrive": t["arrive"], "chargeable_kg": kg, "rate_per_kg_usd": t["rate_per_kg_usd"]})
    c = cost(len(goal["awbs"]), cutoff, legs)
    rows.append(("do_nothing", c["total_usd"], c["final_arrival"], c["meets_cutoff"], c["slack_hours"], [l["option_id"] for l in legs]))
    # rule: earliest arrival first, split allowed — fill each chain up to its remaining
    # capacity (bottleneck of the chain), move on to the next-earliest chain.
    legs_all, chosen = [], []
    cands = sorted(chains(options, "JFK", final), key=lambda ch: ch[-1]["arrive"])
    cands = [ch for ch in cands if ch[-1]["arrive"] <= cutoff]
    for fl, awbs in sorted(groups.items(), key=lambda kv: -sum(a["chargeable_kg"] for a in kv[1])):
        remaining = sum(a["chargeable_kg"] for a in awbs)
        for ch in cands:
            room = min(cap[o["id"]] for o in ch)
            if room <= 0 or remaining <= 0:
                continue
            kg = min(room, remaining)
            for o in ch:
                cap[o["id"]] -= kg
                legs_all.append({"mode": o["mode"], "option_id": o["id"], "origin": o["origin"], "dest": o["dest"], "depart": o["depart"], "arrive": o["arrive"], "chargeable_kg": kg, "rate_per_kg_usd": o["rate_per_kg_usd"]})
            chosen.append((fl, kg, [o["id"] for o in ch]))
            remaining -= kg
        if remaining > 0:
            print(f"rule: {remaining} kg of group {fl} unplaced before cutoff", file=sys.stderr)
    c = cost(len(goal["awbs"]), cutoff, legs_all)
    rows.append(("rule_split_greedy", c["total_usd"], c["final_arrival"], c["meets_cutoff"], c["slack_hours"], chosen))
    print(f"{'baseline':14} {'total_usd':>10} {'final_arrival':20} {'cutoff_ok':9} {'slack_h':>7}  plan")
    for r in rows:
        print(f"{r[0]:14} {r[1]:>10.0f} {r[2]:20} {str(r[3]):9} {r[4]:>7}  {r[5]}")
    json.dump([dict(zip(("name", "total_usd", "final_arrival", "meets_cutoff", "slack_hours", "plan"), r)) for r in rows],
              open(os.path.join("eval", "baseline-s1.json"), "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
