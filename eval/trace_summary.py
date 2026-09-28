"""Summarise one or more run traces: turns, tool calls, failures, and the feasible cost
calls the planner ended on (option_id -> kg), so runs can be compared for consistency.
Usage: python -m eval.trace_summary logs/dryrun-s1-d.jsonl [more...]"""
from __future__ import annotations

import json
import sys


def summarise(path: str) -> dict:
    turns = calls = fails = repeats = 0
    feasible_calls = []
    final = None
    for line in open(path, encoding="utf-8"):
        d = json.loads(line)
        k = d["kind"]
        if k == "tool":
            calls += 1
            turns = max(turns, d["turn"])
            if d["status"] >= 400:
                fails += 1
            if d["tool"] == "cost" and d["status"] == 200:
                try:
                    res = json.loads(d["result"])
                except json.JSONDecodeError:
                    continue  # truncated in log
                if res.get("feasible"):
                    alloc = {}
                    for leg in d["args"].get("legs", []):
                        alloc[leg.get("option_id")] = alloc.get(leg.get("option_id"), 0) + leg.get("chargeable_kg", 0)
                    feasible_calls.append({"awb_count": d["args"].get("awb_count"), "total_usd": res.get("total_usd"), "alloc": alloc})
        elif k == "tool_repeat":
            repeats += 1
        elif k == "final":
            final = {"turn": d["turn"], "chars": len(d["answer"]), "says_proposal": "PROPOSAL" in d["answer"].upper()}
        elif k == "error":
            final = {"error": d["error"][:120]}
    return {"run": path, "turns": turns, "tool_calls": calls, "tool_failures": fails, "repeats_blocked": repeats, "feasible_cost_calls": feasible_calls, "final": final}


if __name__ == "__main__":
    for p in sys.argv[1:]:
        s = summarise(p)
        print(f"== {s['run']}: turns {s['turns']} calls {s['tool_calls']} failures {s['tool_failures']} repeats {s['repeats_blocked']} final {s['final']}")
        for c in s["feasible_cost_calls"]:
            print(f"   feasible cost: awbs {c['awb_count']} usd {c['total_usd']} alloc {c['alloc']}")
