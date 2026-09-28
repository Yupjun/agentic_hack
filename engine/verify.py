"""verify(spec, result) -> {"ok", "problems", "metrics"} — recomputed from the spec alone.

Deliberately independent of lp.py and options.py: it re-reads lanes and schedules,
re-derives every time and cost, and checks every rule. A plan is proposed only if
this passes. v1 taught the rules that must be here: capacity per departure, due
date, and FULL COVERAGE (all quantity delivered; nothing stranded mid-route).
"""
from __future__ import annotations

from collections import defaultdict

from planner import timeutil as tu
from planner.grammar import PlanSpec
from planner.validate import demands_of

EPS = 1e-6


def verify(spec: dict, result: dict) -> dict:
    s = PlanSpec.model_validate(spec)
    P: list[str] = []
    lanes = {l.id: l for l in s.lanes}
    deps = {l.id: [tu.to_day(l.schedule.first, s.t0) + k * l.schedule.every_days for k in range(l.schedule.count)] for l in s.lanes}
    demands = {d["id"]: d for d in demands_of(s)}
    ships = {sh["id"]: sh for sh in result.get("shipments", [])}
    c = s.constraints
    load = defaultdict(float)
    used_deps = set()
    cost = 0.0
    orders = defaultdict(float)
    weekly = defaultdict(float)
    stock_used = defaultdict(float)
    prod = {p.item: p for p in s.production}
    arrive = {}
    for sid, sh in ships.items():
        item = s.items.get(sh["item"])
        if item is None:
            P.append(f"{sid}: unknown item {sh['item']}")
            continue
        q = sh["qty"]
        if q <= 0 or q % item.lot_size:
            P.append(f"{sid}: qty {q} is not a positive multiple of lot {item.lot_size}")
        legs = sh["legs"]
        if not legs:
            P.append(f"{sid}: no legs")
            continue
        if len(legs) > c.max_legs:
            P.append(f"{sid}: {len(legs)} legs > max_legs {c.max_legs}")
        expo = 0.0
        prev_arr = None
        for i, g in enumerate(legs):
            l = lanes.get(g["lane"])
            if l is None:
                P.append(f"{sid}: unknown lane {g['lane']}")
                break
            dep, arr = tu.to_day(g["depart"], s.t0), tu.to_day(g["arrive"], s.t0)
            if not any(abs(dep - d) < 1e-3 for d in deps[l.id]):
                P.append(f"{sid}: {l.id} has no scheduled departure at {g['depart']}")
            if abs(arr - (dep + l.transit_days)) > 1e-3:
                P.append(f"{sid}: {l.id} arrival {g['arrive']} != departure + transit")
            if l.mode not in c.allowed_modes:
                P.append(f"{sid}: mode {l.mode} not allowed")
            if c.qualified_lanes_only and not l.qualified:
                P.append(f"{sid}: lane {l.id} not qualified")
            if item.temp_band not in l.temp_bands:
                P.append(f"{sid}: lane {l.id} does not carry {item.temp_band}")
            if i > 0:
                if legs[i - 1]["to"] != l.frm and lanes[legs[i - 1]["lane"]].to != l.frm:
                    P.append(f"{sid}: leg {i} starts at {l.frm}, previous leg ended elsewhere")
                if dep + EPS < prev_arr + s.nodes[l.frm].min_connect_days:
                    P.append(f"{sid}: connection at {l.frm} shorter than min_connect_days")
            prev_arr = arr
            expo += l.exposure_hours
            key = (l.id, round(dep, 3))
            load[key] += q
            used_deps.add(key)
            cost += q * l.cost_per_unit_usd
        if expo > c.max_exposure_hours + EPS:
            P.append(f"{sid}: exposure {expo:.1f} h > {c.max_exposure_hours} h")
        arrive[sid] = prev_arr
        start = lanes[legs[0]["lane"]].frm if legs[0]["lane"] in lanes else None
        first_dep = tu.to_day(legs[0]["depart"], s.t0)
        src = sh["source"]
        if src.startswith("stock:"):
            i = int(src.split(":")[1])
            st = s.stock[i]
            stock_used[i] += q
            if start != st.node:
                P.append(f"{sid}: starts at {start}, stock is at {st.node}")
            if first_dep + EPS < tu.to_day(st.available_from, s.t0):
                P.append(f"{sid}: leaves before stock is available")
            sh_mfg = tu.to_day(st.mfg_date, s.t0)
        elif src.startswith("prod:"):
            _, it, od, opt = src.split(":")
            p = prod.get(it)
            if p is None or it != sh["item"]:
                P.append(f"{sid}: production source {src} does not match an approved source for {sh['item']}")
                continue
            od = float(od)
            o = next((x for x in p.options if x.name == opt), None)
            if o is None:
                P.append(f"{sid}: unknown option {opt}")
                continue
            if od + EPS < max(0.0, tu.to_day(p.order_from, s.t0)) or od > tu.to_day(p.order_to, s.t0) + EPS:
                P.append(f"{sid}: order day outside the order window")
            if start != p.site:
                P.append(f"{sid}: starts at {start}, approved site is {p.site}")
            ready = od + o.lead_time_days
            if first_dep + EPS < ready:
                P.append(f"{sid}: leaves before production is ready")
            orders[src] += q
            weekly[(it, int(ready // 7))] += q
            cost += q * p.unit_cost_usd * (1 + o.premium_pct / 100)
            sh_mfg = ready
        else:
            P.append(f"{sid}: unknown source {src}")
            continue
        sh["_mfg"] = sh_mfg
        sh["_end"] = legs[-1]["to"]
    for key, q in load.items():
        cap = lanes[key[0]].capacity_units
        if q > cap + EPS:
            P.append(f"capacity: {key[0]} departing day {key[1]} carries {q:.0f} > {cap}")
    cost += sum(lanes[k[0]].cost_fixed_usd for k in used_deps)
    for i, q in stock_used.items():
        if q > s.stock[i].qty + EPS:
            P.append(f"stock: {q:.0f} shipped from stock {i} > {s.stock[i].qty} on hand")
    for o, q in orders.items():
        it = o.split(":")[1]
        if q + EPS < prod[it].moq:
            P.append(f"moq: order {o} is {q:.0f} < MOQ {prod[it].moq}")
    for (it, wk), q in weekly.items():
        if q > prod[it].capacity_per_week + EPS:
            P.append(f"site capacity: {it} week {wk} {q:.0f} > {prod[it].capacity_per_week}")
    # allocations: coverage, due, place, shelf life
    got = defaultdict(float)
    per_ship = defaultdict(float)
    min_slack = None
    for a in result.get("allocations", []):
        sh, d = ships.get(a["shipment"]), demands.get(a["demand"])
        if sh is None or d is None:
            P.append(f"allocation refers to unknown shipment/demand {a}")
            continue
        per_ship[a["shipment"]] += a["qty"]
        got[a["demand"]] += a["qty"]
        if sh["item"] != d["item"]:
            P.append(f"{a['shipment']} ({sh['item']}) allocated to demand {d['id']} ({d['item']})")
        if sh.get("_end") != d["node"]:
            P.append(f"{a['shipment']} ends at {sh.get('_end')} but demand {d['id']} is at {d['node']}")
        due = tu.to_day(d["due"], s.t0)
        arr = arrive.get(a["shipment"])
        if arr is None:
            continue
        if arr > due + EPS:
            P.append(f"late: {a['shipment']} arrives day {arr:.2f} after due day {due:.2f} of {d['id']}")
        slack = due - arr
        min_slack = slack if min_slack is None else min(min_slack, slack)
        it = s.items[sh["item"]]
        check = arr if s.family == "S1" else due
        remaining = sh["_mfg"] + it.shelf_life_days - check
        if remaining + EPS < it.shelf_life_days * it.min_remaining_shelf_life_pct / 100:
            P.append(f"shelf: {a['shipment']} has {remaining:.1f} d left at {'receipt' if s.family == 'S1' else 'use'} for {d['id']}, needs {it.shelf_life_days * it.min_remaining_shelf_life_pct / 100:.1f}")
    for sid, q in per_ship.items():
        if q > ships[sid]["qty"] + EPS:
            P.append(f"{sid}: allocated {q:.1f} > shipped {ships[sid]['qty']}")
    for did, d in demands.items():
        if abs(got[did] - d["qty"]) > 1e-3:
            P.append(f"coverage: demand {did} gets {got[did]:.1f} of {d['qty']}")
    if cost > s.budget_usd + EPS:
        P.append(f"budget: cost {cost:.0f} > budget {s.budget_usd:.0f}")
    claimed = result.get("cost_usd")
    if claimed is not None and abs(claimed - cost) > 0.5:
        P.append(f"cost: plan claims {claimed:.2f}, recomputed {cost:.2f}")
    shipped = sum(sh["qty"] for sh in ships.values())
    required = sum(d["qty"] for d in demands.values())
    latest = max(arrive.values()) if arrive else None
    metrics = {"cost_usd": round(cost, 2), "units_shipped": shipped, "units_required": required,
               "units_left_over": round(shipped - sum(got.values()), 3),
               "min_slack_days": None if min_slack is None else round(min_slack, 3),
               "latest_arrival": None if latest is None else tu.from_day(latest, s.t0),
               "shipments": len(ships), "departures_used": len(used_deps)}
    for sh in ships.values():
        sh.pop("_mfg", None)
        sh.pop("_end", None)
    return {"ok": not P, "problems": P, "metrics": metrics}
