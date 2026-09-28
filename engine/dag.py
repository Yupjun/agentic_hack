"""dag/v1 — a user-defined process graph (steps -> task nodes -> approved supplier options) and its solver.

The user draws the tree in the UI: each step has task nodes, each node lists the nodes it waits for
(`after`) and one or more approved supplier options with their SCM parameters (capacity, PERT lead
time, unit and fixed cost, MOQ, lot size, shelf life, expedite = crash option). We search the tree for
the plan that best fits the user's objective, using standard graph / OM methods:

  CPM            earliest/latest start, slack and the critical path of every candidate plan
  PERT + MC      triangular(min, likely, max) lead times -> P(finish by deadline), criticality index
  Crashing       expedite options per node; for the chosen plan, cost per day saved on the critical path
  Max flow       Edmonds-Karp on the node-split graph: how many finished units can pass by the deadline,
                 and the min cut = the bottleneck nodes. Joins: "all" (every input is needed, BOM) is
                 modelled by giving each input edge the capacity of its branch in finished-unit
                 equivalents and taking the min at the join; "any" (alternative inputs) sums them.
  MOQ / lot / MOS  order qty = max(MOQ, lots(required)); required = qty_per_unit x (demand + MOS
                 safety stock - on hand); overbuy is costed; months of supply after the plan is reported.

Every plan is enumerated (options x expedite per node); the tree is small by design (a hackathon demo),
and the enumeration size is reported. Pure Python + numpy/torch-free; deterministic with the seed.
"""
from __future__ import annotations

import itertools
import math
import random
from collections import deque

from pydantic import BaseModel, Field

MAX_COMBOS = 200_000


class LeadTime(BaseModel):
    min: float = Field(ge=0)
    likely: float = Field(ge=0)
    max: float = Field(ge=0)


class Expedite(BaseModel):
    lead_time_cut_days: float = Field(ge=0, default=0)
    premium_pct: float = Field(ge=0, default=0)


class Option(BaseModel):
    id: str
    supplier: str
    site: str = ""
    lat: float | None = None
    lon: float | None = None
    approved: bool = True
    capacity_per_day: float = Field(gt=0)
    lead_time_days: LeadTime
    unit_cost_usd: float = Field(ge=0)
    fixed_cost_usd: float = Field(ge=0, default=0)
    moq: float = Field(ge=0, default=0)
    lot_size: float = Field(gt=0, default=1)
    shelf_life_days: float | None = None
    min_remaining_pct: float = Field(ge=0, le=100, default=0)
    expedite: Expedite | None = None


class Node(BaseModel):
    id: str
    task: str
    qty_per_unit: float = Field(gt=0, default=1)
    after: list[str] = []
    join: str = "all"          # all = every input needed (BOM); any = alternative inputs
    options: list[Option] = Field(min_length=1)


class Step(BaseModel):
    id: str
    name: str
    nodes: list[Node] = Field(min_length=1)


class Demand(BaseModel):
    qty: float = Field(gt=0)
    unit: str = "units"
    deadline_days: float = Field(gt=0)
    budget_usd: float = Field(gt=0)
    product_age_at_start_days: float = Field(ge=0, default=0)
    shelf_life_days: float | None = None
    min_remaining_pct_at_delivery: float = Field(ge=0, le=100, default=0)


class Inventory(BaseModel):
    mos_target_months: float = Field(ge=0, default=0)
    monthly_usage: float = Field(ge=0, default=0)
    on_hand: float = Field(ge=0, default=0)


class Uncertainty(BaseModel):
    n_samples: int = Field(ge=200, le=50_000, default=4000)
    seed: int = 7
    late_penalty_usd_per_day: float = Field(ge=0, default=0)


class DagSpec(BaseModel):
    spec: str = "dag/v1"
    id: str
    title: str = ""
    hypothesis: str = ""
    start: str = "2026-10-01T00:00:00Z"
    objective: str = "balanced"          # min_cost | min_time | balanced | max_on_time | risk
    demand: Demand
    inventory: Inventory = Inventory()
    uncertainty: Uncertainty = Uncertainty()
    steps: list[Step] = Field(min_length=1)


OBJECTIVES = ("min_cost", "min_time", "balanced", "max_on_time", "risk")


def validate(spec: dict) -> tuple[DagSpec | None, list[str]]:
    from pydantic import ValidationError
    try:
        s = DagSpec.model_validate(spec)
    except ValidationError as e:
        return None, [f"structure: {'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in e.errors()]
    P = []
    ids = [n.id for st in s.steps for n in st.nodes]
    if len(ids) != len(set(ids)):
        P.append("duplicate node ids")
    known = set(ids)
    order = {n.id: i for i, st in enumerate(s.steps) for n in st.nodes}
    for st in s.steps:
        for n in st.nodes:
            for a in n.after:
                if a not in known:
                    P.append(f"node {n.id}: unknown predecessor {a!r}")
                elif order[a] >= order[n.id]:
                    P.append(f"node {n.id}: predecessor {a} must be in an earlier step")
            if n.join not in ("all", "any"):
                P.append(f"node {n.id}: join must be all or any")
            for o in n.options:
                lt = o.lead_time_days
                if not (lt.min <= lt.likely <= lt.max):
                    P.append(f"option {o.id}: lead time must satisfy min <= likely <= max")
                if not o.approved:
                    P.append(f"option {o.id}: supplier {o.supplier} is not approved — only approved suppliers may be planned")
    if s.objective not in OBJECTIVES:
        P.append(f"objective must be one of {OBJECTIVES}")
    n_combos = math.prod(sum(1 + (o.expedite is not None) for o in n.options) for st in s.steps for n in st.nodes)
    if n_combos > MAX_COMBOS:
        P.append(f"{n_combos} candidate plans exceed the enumeration limit {MAX_COMBOS}; remove options")
    return (None if P else s), P


def _nodes(s: DagSpec) -> list[Node]:
    return [n for st in s.steps for n in st.nodes]


def _required_units(s: DagSpec) -> float:
    inv = s.inventory
    safety = max(0.0, inv.mos_target_months * inv.monthly_usage - inv.on_hand)
    return s.demand.qty + safety


def _choice_metrics(s: DagSpec, choice: dict[str, tuple[Option, bool]], lead: dict[str, float] | None = None) -> dict:
    """CPM + cost for one plan. lead overrides the lead time per node (Monte Carlo)."""
    units = _required_units(s)
    ES, EF, dur, cost, rows = {}, {}, {}, 0.0, {}
    nodes = _nodes(s)
    for n in nodes:
        o, exp = choice[n.id]
        need = n.qty_per_unit * units
        lots = math.ceil(need / o.lot_size - 1e-9) * o.lot_size
        order = max(o.moq, lots)
        lt = (lead or {}).get(n.id, o.lead_time_days.likely)
        prem = 0.0
        if exp and o.expedite:
            lt = max(0.0, lt - o.expedite.lead_time_cut_days)
            prem = o.expedite.premium_pct / 100
        d = lt + order / o.capacity_per_day
        es = max([EF[a] for a in n.after], default=0.0)
        ES[n.id], dur[n.id], EF[n.id] = es, d, es + d
        c = o.fixed_cost_usd + order * o.unit_cost_usd * (1 + prem)
        cost += c
        rows[n.id] = {"option": o.id, "supplier": o.supplier, "site": o.site, "expedite": bool(exp), "need": round(need, 2), "order_qty": round(order, 2),
                      "overbuy": round(order - need, 2), "cost_usd": round(c, 2), "duration_days": round(d, 2), "lead_time_days": round(lt, 2)}
    makespan = max(EF.values())
    # backward pass
    succ = {n.id: [m.id for m in nodes if n.id in m.after] for n in nodes}
    LF, LS = {}, {}
    for n in reversed(nodes):
        LF[n.id] = min([LS[m] for m in succ[n.id]], default=makespan)
        LS[n.id] = LF[n.id] - dur[n.id]
    critical = [n.id for n in nodes if abs(LS[n.id] - ES[n.id]) < 1e-6]
    shelf_problems = []
    for n in nodes:
        o, _ = choice[n.id]
        if o.shelf_life_days:
            # the node is made as late as its slack allows (latest finish), so its output ages from LF to delivery;
            # first version used EF and failed every plan whose shelf-limited input could simply be made later
            age_at_end = makespan - LF[n.id]
            if o.shelf_life_days - age_at_end < o.shelf_life_days * o.min_remaining_pct / 100 - 1e-9:
                shelf_problems.append(f"{n.id}: {o.shelf_life_days - age_at_end:.1f} d shelf life left at completion, needs {o.shelf_life_days * o.min_remaining_pct / 100:.1f}")
    dm = s.demand
    if dm.shelf_life_days:
        left = dm.shelf_life_days - dm.product_age_at_start_days - makespan
        if left < dm.shelf_life_days * dm.min_remaining_pct_at_delivery / 100 - 1e-9:
            shelf_problems.append(f"product: {left:.1f} d shelf life left at delivery, needs {dm.shelf_life_days * dm.min_remaining_pct_at_delivery / 100:.1f}")
    for n in nodes:
        rows[n.id].update(ES=round(ES[n.id], 2), EF=round(EF[n.id], 2), LS=round(LS[n.id], 2), slack=round(LS[n.id] - ES[n.id], 2),
                          critical=n.id in critical)
    return {"cost_usd": round(cost, 2), "makespan_days": round(makespan, 3), "slack_days": round(dm.deadline_days - makespan, 3),
            "critical_path": critical, "nodes": rows, "shelf_problems": shelf_problems,
            "feasible": not shelf_problems and cost <= dm.budget_usd + 1e-6 and makespan <= dm.deadline_days + 1e-9,
            "within_budget": cost <= dm.budget_usd + 1e-6, "on_time_nominal": makespan <= dm.deadline_days + 1e-9}


def _tri(rng: random.Random, lt: LeadTime) -> float:
    if lt.max <= lt.min:
        return lt.likely
    return rng.triangular(lt.min, lt.max, lt.likely)


def monte_carlo(s: DagSpec, choice: dict[str, tuple[Option, bool]], n: int | None = None, bins: int = 24) -> dict:
    u = s.uncertainty
    rng = random.Random(u.seed)
    n = n or u.n_samples
    spans, costs, crit = [], [], {nd.id: 0 for nd in _nodes(s)}
    base = _choice_metrics(s, choice)
    for _ in range(n):
        lead = {nd.id: _tri(rng, choice[nd.id][0].lead_time_days) for nd in _nodes(s)}
        m = _choice_metrics(s, choice, lead)
        spans.append(m["makespan_days"])
        late = max(0.0, m["makespan_days"] - s.demand.deadline_days)
        costs.append(base["cost_usd"] + late * u.late_penalty_usd_per_day)
        for c in m["critical_path"]:
            crit[c] += 1
    spans.sort()
    q = lambda p: spans[min(len(spans) - 1, int(p * len(spans)))]
    lo, hi = spans[0], spans[-1]
    w = (hi - lo) / bins if hi > lo else 1.0
    hist = [0] * bins
    for x in spans:
        hist[min(bins - 1, int((x - lo) / w))] += 1
    return {"n_samples": n, "seed": u.seed, "p_on_time": round(sum(x <= s.demand.deadline_days for x in spans) / n, 4),
            "makespan_p10": round(q(0.1), 2), "makespan_p50": round(q(0.5), 2), "makespan_p90": round(q(0.9), 2),
            "expected_cost_usd": round(sum(costs) / n, 2),
            "histogram": {"lo": round(lo, 3), "width": round(w, 4), "counts": hist},
            "criticality": {k: round(v / n, 4) for k, v in crit.items()}}


# ---------------- max flow (Edmonds-Karp) ----------------

def _edmonds_karp(cap: dict, source: str, sink: str) -> tuple[float, set]:
    flow = {u: {v: 0.0 for v in cap[u]} for u in cap}
    for u in list(cap):
        for v in cap[u]:
            cap.setdefault(v, {}).setdefault(u, 0.0)
            flow.setdefault(v, {}).setdefault(u, 0.0)
    total = 0.0
    while True:
        parent = {source: None}
        dq = deque([source])
        while dq and sink not in parent:
            u = dq.popleft()
            for v, c in cap[u].items():
                if v not in parent and c - flow[u][v] > 1e-9:
                    parent[v] = u
                    dq.append(v)
        if sink not in parent:
            break
        v, b = sink, math.inf
        while parent[v] is not None:
            u = parent[v]
            b = min(b, cap[u][v] - flow[u][v])
            v = u
        v = sink
        while parent[v] is not None:
            u = parent[v]
            flow[u][v] += b
            flow[v][u] -= b
            v = u
        total += b
    return total, set(parent)   # reachable set from the last BFS = source side of the min cut


def max_flow(s: DagSpec, choice: dict[str, tuple[Option, bool]]) -> dict:
    """Finished units that can pass by the deadline. Node capacity (finished-unit equivalents) =
    capacity_per_day x days available after its lead time and its predecessors, / qty_per_unit."""
    m = _choice_metrics(s, choice)
    D = s.demand.deadline_days
    ucap = {}
    for n in _nodes(s):
        o, exp = choice[n.id]
        lt = m["nodes"][n.id]["lead_time_days"]
        avail = max(0.0, D - m["nodes"][n.id]["ES"] - lt)
        ucap[n.id] = o.capacity_per_day * avail / n.qty_per_unit
    nodes = _nodes(s)
    has_all_join = any(n.join == "all" and len(n.after) > 1 for n in nodes)
    succ = {n.id: [x.id for x in nodes if n.id in x.after] for n in nodes}
    if not has_all_join:
        cap: dict = {"SRC": {}, "SNK": {}}
        for n in nodes:
            cap.setdefault(f"{n.id}:in", {})[f"{n.id}:out"] = ucap[n.id]
            cap.setdefault(f"{n.id}:out", {})
            if not n.after:
                cap["SRC"][f"{n.id}:in"] = math.inf
            if not succ[n.id]:
                cap[f"{n.id}:out"]["SNK"] = math.inf
            for a in n.after:
                cap.setdefault(f"{a}:out", {})[f"{n.id}:in"] = math.inf
        total, side = _edmonds_karp(cap, "SRC", "SNK")
        cut = [n.id for n in nodes if f"{n.id}:in" in side and f"{n.id}:out" not in side]
        method = "edmonds-karp"
    else:
        # series-parallel with BOM joins: throughput(n) = min(own capacity, min over inputs) for all-joins
        thr = {}
        for n in nodes:
            ins = [thr[a] for a in n.after]
            inflow = (min(ins) if n.join == "all" else sum(ins)) if ins else math.inf
            thr[n.id] = min(ucap[n.id], inflow)
        leaves = [n.id for n in nodes if not succ[n.id]]
        total = min(thr[x] for x in leaves)
        cut = [n.id for n in nodes if abs(ucap[n.id] - total) < 1e-6]
        method = "bottleneck recursion (all-joins are not flow-additive)"
    return {"units_by_deadline": round(total, 2), "demand_units": round(_required_units(s), 2), "bottleneck": cut,
            "node_capacity_units": {k: round(v, 2) for k, v in ucap.items()}, "method": method,
            "enough": total + 1e-6 >= _required_units(s)}


# ---------------- search ----------------

def _choices(s: DagSpec):
    per = []
    for n in _nodes(s):
        alts = []
        for o in n.options:
            alts.append((o, False))
            if o.expedite:
                alts.append((o, True))
        per.append([(n.id, a) for a in alts])
    for combo in itertools.product(*per):
        yield {nid: a for nid, a in combo}


def solve(spec: dict) -> dict:
    s, P = validate(spec)
    if s is None:
        return {"status": "invalid", "problems": P}
    evals = []
    for ch in _choices(s):
        m = _choice_metrics(s, ch)
        evals.append((m, ch))
    feas = [(m, ch) for m, ch in evals if m["feasible"]]
    out = {"status": "ok", "n_plans": len(evals), "n_feasible": len(feas), "required_units": round(_required_units(s), 2),
           "objective": s.objective}
    if not feas:
        best = min(evals, key=lambda x: (not x[0]["within_budget"], x[0]["makespan_days"], x[0]["cost_usd"]))
        out.update(status="no_feasible_plan", closest=_summ(s, *best, mc=True),
                   hint="relax the deadline, the budget, or MOS; or add an approved option / expedite")
        return out
    # Pareto front on (cost, makespan)
    feas.sort(key=lambda x: (x[0]["cost_usd"], x[0]["makespan_days"]))
    front, best_t = [], math.inf
    for m, ch in feas:
        if m["makespan_days"] < best_t - 1e-9:
            front.append((m, ch))
            best_t = m["makespan_days"]
    front = front[:40]
    summ = [_summ(s, m, ch, mc=True) for m, ch in front]
    cmin, cmax = min(x["cost_usd"] for x in summ), max(x["cost_usd"] for x in summ)
    tmin, tmax = min(x["makespan_days"] for x in summ), max(x["makespan_days"] for x in summ)

    def knee(x):
        c = 0 if cmax == cmin else (x["cost_usd"] - cmin) / (cmax - cmin)
        t = 0 if tmax == tmin else (x["makespan_days"] - tmin) / (tmax - tmin)
        return (round(math.hypot(c, t), 9), x["mc"]["expected_cost_usd"])

    named = {"min_cost": min(summ, key=lambda x: (x["cost_usd"], x["makespan_days"])),
             "min_time": min(summ, key=lambda x: (x["makespan_days"], x["cost_usd"])),
             "balanced": min(summ, key=knee),
             "max_on_time": max(summ, key=lambda x: (x["mc"]["p_on_time"], -x["cost_usd"])),
             "risk": min(summ, key=lambda x: (x["mc"]["expected_cost_usd"], x["cost_usd"]))}
    rec = named[s.objective]
    out.update(pareto=[{k: x[k] for k in ("cost_usd", "makespan_days", "slack_days")} | {"p_on_time": x["mc"]["p_on_time"],
                        "expected_cost_usd": x["mc"]["expected_cost_usd"], "key": x["key"]} for x in summ],
               named={k: v["key"] for k, v in named.items()}, plans={x["key"]: x for x in summ}, recommended=rec["key"],
               crashing=_crashing(s, front[summ.index(rec)][1]), flow=max_flow(s, front[summ.index(rec)][1]),
               cloud=[{"cost_usd": m["cost_usd"], "makespan_days": m["makespan_days"]} for m, _ in random.Random(1).sample(feas, min(400, len(feas)))])
    return out


def _summ(s: DagSpec, m: dict, ch: dict, mc: bool) -> dict:
    key = "|".join(f"{nid}={o.id}{'+x' if e else ''}" for nid, (o, e) in ch.items())
    inv = s.inventory
    produced_extra = _required_units(s) - s.demand.qty
    mos_after = (inv.on_hand + produced_extra) / inv.monthly_usage if inv.monthly_usage else None
    return {**m, "key": key, "mos_after_months": None if mos_after is None else round(mos_after, 2),
            "mc": monte_carlo(s, ch, n=min(s.uncertainty.n_samples, 2000)) if mc else None}


def _crashing(s: DagSpec, ch: dict) -> list[dict]:
    """For each critical node without expedite: switch it on, report days saved and cost per day."""
    base = _choice_metrics(s, ch)
    out = []
    for nid in base["critical_path"]:
        o, e = ch[nid]
        if e or not o.expedite:
            continue
        alt = dict(ch)
        alt[nid] = (o, True)
        m = _choice_metrics(s, alt)
        saved = base["makespan_days"] - m["makespan_days"]
        if saved > 1e-6:
            out.append({"node": nid, "days_saved": round(saved, 2), "extra_cost_usd": round(m["cost_usd"] - base["cost_usd"], 2),
                        "usd_per_day": round((m["cost_usd"] - base["cost_usd"]) / saved, 2), "within_budget": m["within_budget"]})
    return sorted(out, key=lambda x: x["usd_per_day"])
