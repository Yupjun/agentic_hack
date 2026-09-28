"""judge(entry, result) -> verdict. Predictions are evaluated by a fixed menu of
operators on metric paths; the verdict never comes from a model.

Metric paths: dotted keys into the result (plans.cost_optimal.cost_usd), or
derived.<plan>.<name> computed here:
  route_classes    sorted set of shipment classes: ocean | sea-air | air | parcel | truck
  expedite_items   sorted items with at least one expedite order
  orders_by_item   {item: number of distinct production orders}
"""
from __future__ import annotations

OPS = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "<": lambda a, b: a is not None and a < b,
    "<=": lambda a, b: a is not None and a <= b,
    ">": lambda a, b: a is not None and a > b,
    ">=": lambda a, b: a is not None and a >= b,
    "between": lambda a, b: a is not None and b[0] <= a <= b[1],
    "contains": lambda a, b: a is not None and b in a,
}


def route_class(sh: dict) -> str:
    modes = {g["mode"] for g in sh["legs"]}
    if "ocean" in modes and "air" in modes:
        return "sea-air"
    for m in ("ocean", "air", "parcel", "rail"):
        if m in modes:
            return m
    return "truck"


def derived(plan: dict) -> dict:
    ships = plan.get("shipments", [])
    orders: dict[str, set] = {}
    for sh in ships:
        if sh["source"].startswith("prod:"):
            orders.setdefault(sh["item"], set()).add(sh["source"])
    return {"route_classes": sorted({route_class(sh) for sh in ships}),
            "expedite_items": sorted({sh["item"] for sh in ships if sh.get("option") == "expedite"}),
            "orders_by_item": {k: len(v) for k, v in orders.items()}}


def lookup(result: dict, path: str):
    parts = path.split(".")
    if parts[0] == "derived":
        plan = result.get("plans", {}).get(parts[1])
        if plan is None:
            return None
        cur = derived(plan)
        rest = parts[2:]
    else:
        cur, rest = result, parts
    for k in rest:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        elif isinstance(cur, dict) and parts[0] == "derived" and rest[0] == "orders_by_item":
            return 0
        else:
            return None
    return cur


def judge(entry: dict, result: dict) -> dict:
    checks = []
    for e in entry["expected"]:
        got = lookup(result, e["metric"])
        ok = bool(OPS[e["op"]](got, e["value"]))
        checks.append({**e, "got": got, "ok": ok})
    verdict = "supported" if all(c["ok"] for c in checks) else "refuted"
    return {"id": entry["id"], "verdict": verdict, "prediction_registered": entry.get("prediction_registered"),
            "passed": sum(c["ok"] for c in checks), "total": len(checks), "checks": checks}
