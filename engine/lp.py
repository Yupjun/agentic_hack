"""One MILP for both families, built with PuLP; solved by HiGHS (CPU) or cuOpt (GPU).

Variables
  n[k]    int >= 0   lots shipped on candidate k           (units x[k] = lot * n[k])
  v[l,d]  bin        lane departure (l, d) is used          (pays its fixed cost)
  z[o]    bin        production order o is placed           (S2; MOQ)
  w[k,j]  >= 0       units of candidate k allocated to demand j (only eligible pairs)

Constraints
  coverage     sum_k w[k,j] = qty_j                 every demand fully met (flow conservation)
  allocation   sum_j w[k,j] <= x[k]                 cannot allocate more than shipped
  capacity     sum_{k uses (l,d)} x[k] <= cap * v    per scheduled departure
  stock        sum_{k from stock i} x[k] <= qty_i    S1
  moq          moq*z <= sum_{k in o} x[k] <= M*z     S2, per production order
  site cap     sum_{orders ready in week} x <= capacity_per_week   S2
  budget       total cost <= budget_usd
  slack        only pairs with arrival <= due - slack and the shelf-life rule are eligible

Objective: minimise total cost = sum x*unit_cost + sum v*fixed.
The time side of the trade-off is handled by re-solving with a larger slack
(epsilon-constraint), see pareto.py.
"""
from __future__ import annotations

import os
import time

import pulp

from planner import timeutil as tu

from .options import Problem, eligible


def backend_solver(name: str, time_limit: float, msg: bool = False):
    name = (name or "highs").lower()
    if name == "highs":
        return pulp.HiGHS(msg=msg, timeLimit=time_limit)
    if name == "cuopt":
        return pulp.CUOPT(msg=msg, timeLimit=time_limit)
    raise ValueError(f"unknown backend {name!r} (highs | cuopt)")


def solve(prob: Problem, slack: float = 0.0, backend: str | None = None, time_limit: float = 60.0) -> dict:
    s = prob.spec
    backend = backend or os.environ.get("CARGO_LP_BACKEND", "highs")
    t_start = time.time()
    m = pulp.LpProblem("plan", pulp.LpMinimize)
    C = prob.candidates
    lot = {c.id: s.items[c.item].lot_size for c in C}
    n = {c.id: m.add_variable(f"n_{i}", lowBound=0, cat="Integer") for i, c in enumerate(C)}
    x = {c.id: lot[c.id] * n[c.id] for c in C}
    dep_keys = sorted(prob.departures)
    v = {k: m.add_variable(f"v_{i}", cat="Binary") for i, k in enumerate(dep_keys)}
    pairs = [(c, j) for c in C for j, d in enumerate(prob.demands) if eligible(s, c, d, slack)]
    w = {(c.id, j): m.add_variable(f"w_{i}", lowBound=0) for i, (c, j) in enumerate(pairs)}
    by_c: dict[str, list] = {}
    by_j: dict[int, list] = {}
    for (cid, j), var in w.items():
        by_c.setdefault(cid, []).append(var)
        by_j.setdefault(j, []).append(var)
    # a candidate that serves no demand at this slack is useless: pin it to zero
    for c in C:
        if c.id not in by_c:
            m += n[c.id] == 0
    for j, d in enumerate(prob.demands):
        if j not in by_j:
            return {"status": "infeasible", "reason": f"demand {d['id']} has no eligible candidate at slack {slack:.2f} d",
                    "slack": slack, "backend": backend, "seconds": round(time.time() - t_start, 3)}
        m += pulp.lpSum(by_j[j]) == d["qty"], f"cover_{j}"
    for c in C:
        if c.id in by_c:
            m += pulp.lpSum(by_c[c.id]) <= x[c.id]
    uses: dict = {}
    for c in C:
        for g in c.legs:
            uses.setdefault((g.lane, round(g.depart, 6)), []).append(c.id)
    for k in dep_keys:
        m += pulp.lpSum(x[cid] for cid in uses.get(k, [])) <= prob.departures[k]["capacity"] * v[k]
    if s.family == "S1":
        for i, st in enumerate(s.stock):
            m += pulp.lpSum(x[c.id] for c in C if c.source == f"stock:{i}") <= st.qty
    else:
        orders: dict[str, list] = {}
        for c in C:
            orders.setdefault(c.order, []).append(c)
        z = {o: m.add_variable(f"z_{i}", cat="Binary") for i, o in enumerate(sorted(orders))}
        prod = {p.item: p for p in s.production}
        big = {p.item: p.capacity_per_week * 52 for p in s.production}
        for o, cs in orders.items():
            item = cs[0].item
            tot = pulp.lpSum(x[c.id] for c in cs)
            m += tot >= prod[item].moq * z[o]
            m += tot <= big[item] * z[o]
        weeks: dict = {}
        for c in C:
            weeks.setdefault((c.item, c.week), []).append(c.id)
        for (item, wk), cids in weeks.items():
            m += pulp.lpSum(x[cid] for cid in cids) <= prod[item].capacity_per_week
    cost = pulp.lpSum(x[c.id] * c.unit_cost for c in C) + pulp.lpSum(v[k] * prob.departures[k]["fixed"] for k in dep_keys)
    m += cost <= s.budget_usd, "budget"
    m += cost
    solver = backend_solver(backend, time_limit)
    t_solve = time.time()
    stats = m.solve(solver)            # PuLP 4: returns LpSolveStats
    t_done = time.time()
    st = stats.status.name              # Optimal | Infeasible | TimeLimit | ...
    base = {"slack": slack, "backend": backend, "status": st.lower(), "n_candidates": len(C), "n_pairs": len(pairs),
            "n_vars": len(m.variables()), "n_constraints": m.numConstraints() if hasattr(m, "numConstraints") else len(m.constraints()),
            "seconds_build": round(t_solve - t_start, 3), "seconds_solve": round(t_done - t_solve, 3),
            "gap_rel": getattr(stats, "gap_rel", None)}
    if not (st == "Optimal" or (st == "TimeLimit" and stats.has_solution)):
        base["status"] = "infeasible" if st in ("Infeasible", "NotSolved", "Undefined") else st.lower()
        base["reason"] = f"solver status {st}"
        return base
    ships = []
    cand = {c.id: c for c in C}
    for cid, var in n.items():
        q = int(round(var.value() or 0)) * lot[cid]
        if q <= 0:
            continue
        c = cand[cid]
        ships.append({"id": f"S{len(ships)+1:03d}", "candidate": cid, "item": c.item, "qty": q, "source": c.source,
                      "option": c.option, "mfg": tu.from_day(c.mfg, s.t0), "ready": tu.from_day(c.ready, s.t0),
                      "legs": [{"lane": g.lane, "mode": g.mode, "from": g.frm, "to": g.to,
                                "depart": tu.from_day(g.depart, s.t0), "arrive": tu.from_day(g.arrive, s.t0)} for g in c.legs],
                      "unit_cost_usd": round(c.unit_cost, 2)})
    sid = {sh["candidate"]: sh["id"] for sh in ships}
    alloc = []
    for (cid, j), var in w.items():
        q = var.value() or 0
        if q > 1e-6:
            alloc.append({"shipment": sid.get(cid, "?"), "demand": prob.demands[j]["id"], "qty": round(q, 3)})
    base.update({"status": "optimal" if st == "Optimal" else "time_limit", "cost_usd": round(pulp.value(cost), 2), "shipments": ships, "allocations": alloc})
    return base
