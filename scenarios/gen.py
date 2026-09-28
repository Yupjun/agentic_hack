"""Scenario generator: variant = base spec + parameter overrides (deterministic).

A scenario is data, like an autoresearch hypothesis: `generator_params` says what
changes relative to a base spec; `generate()` applies them and, with a seed,
jitters lane rates by +-rate_jitter_pct so the same seed gives the same spec.

Parameters (all optional):
  due_days            demand due = t0 + N days            (S1)
  budget_usd          budget
  shelf_life_days     {item: days}
  min_remaining_pct   {item: pct}
  max_exposure_hours  constraint
  allowed_modes       list
  delay_scale         {mode: factor} on mean and sd of delays
  delay_mean_days     {mode: days}  (overrides mean)
  lead_time_add_days  {item: days}  added to every production option (S2)
  moq                 {item: n}
  capacity_per_week   {item: n}
  batch_shift_days    int, shift every batch start (S2)
  rate_jitter_pct     float, seeded +- jitter on cost_per_unit and cost_fixed of every lane
"""
from __future__ import annotations

import copy
import datetime as dt
import json
import os
import random

from planner import timeutil as tu

HERE = os.path.dirname(os.path.abspath(__file__))


def _iso(d: dt.datetime) -> str:
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


def generate(base: dict, params: dict, seed: int = 0, new_id: str | None = None) -> dict:
    s = copy.deepcopy(base)
    p = params or {}
    if new_id:
        s["id"] = new_id
    t0 = tu.parse(s["t0"])
    if "due_days" in p:
        for d in s["demand"]:
            d["due"] = _iso(t0 + dt.timedelta(days=p["due_days"]))
    if "budget_usd" in p:
        s["budget_usd"] = p["budget_usd"]
    for it, v in p.get("shelf_life_days", {}).items():
        s["items"][it]["shelf_life_days"] = v
    for it, v in p.get("min_remaining_pct", {}).items():
        s["items"][it]["min_remaining_shelf_life_pct"] = v
    if "max_exposure_hours" in p:
        s.setdefault("constraints", {})["max_exposure_hours"] = p["max_exposure_hours"]
    if "allowed_modes" in p:
        s.setdefault("constraints", {})["allowed_modes"] = p["allowed_modes"]
    delay = s.setdefault("uncertainty", {}).setdefault("delay", {})
    for m, f in p.get("delay_scale", {}).items():
        if m in delay:
            delay[m] = {"mean_days": delay[m]["mean_days"] * f, "sd_days": delay[m]["sd_days"] * f}
    for m, v in p.get("delay_mean_days", {}).items():
        if m in delay:
            delay[m]["mean_days"] = v
    for x in s.get("production", []):
        add = p.get("lead_time_add_days", {}).get(x["item"])
        if add:
            for o in x["options"]:
                o["lead_time_days"] += add
        if x["item"] in p.get("moq", {}):
            x["moq"] = p["moq"][x["item"]]
        if x["item"] in p.get("capacity_per_week", {}):
            x["capacity_per_week"] = p["capacity_per_week"][x["item"]]
    if p.get("batch_shift_days") and s.get("production_plan"):
        for b in s["production_plan"]["batches"]:
            b["start"] = _iso(tu.parse(b["start"]) + dt.timedelta(days=p["batch_shift_days"]))
    j = p.get("rate_jitter_pct", 0)
    if j:
        rng = random.Random(seed)
        for l in s["lanes"]:
            for k in ("cost_per_unit_usd", "cost_fixed_usd"):
                l[k] = round(l[k] * (1 + rng.uniform(-j, j) / 100), 2)
    return s


def load_bank(status: tuple = ("approved", "provisional")) -> list[dict]:
    out = []
    bank = os.path.join(HERE, "bank")
    for f in sorted(os.listdir(bank)):
        if f.endswith(".json"):
            e = json.load(open(os.path.join(bank, f), encoding="utf-8"))
            if e.get("status") in status:
                out.append(e)
    return out


def spec_for(entry: dict) -> dict:
    base = json.load(open(os.path.join(HERE, "examples", entry["base"]), encoding="utf-8"))
    return generate(base, entry.get("generator_params", {}), entry.get("seed", 0), new_id=entry["id"])


def write_specs() -> list[str]:
    paths = []
    for e in load_bank():
        spec = spec_for(e)
        spec["hypothesis"] = e["rationale"]
        p = os.path.join(HERE, "specs", f"{e['id']}.json")
        json.dump(spec, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        paths.append(p)
    return paths


if __name__ == "__main__":
    for p in write_specs():
        print(p)
