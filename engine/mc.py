"""Monte Carlo risk of a verified plan under transit-delay uncertainty (torch).

Per sample and per leg: delay = max(0, N(mean, sd)) of the leg's mode (spec.uncertainty.delay).
The next leg's scheduled departure is kept if the goods (plus min_connect_days)
arrive in time; otherwise they wait for the next departure of that lane
(every_days later) — a missed connection. Capacity on those later departures is
NOT modelled (optimistic; stated in the result).

Outputs: P(every demand on time), P(each demand on time), P(shelf-life rule still
met at receipt/use), P(no temperature excursion on any leg), expected late
unit-days, and cost = plan cost + late penalty (p50 / p95).

Device: CARGO_MC_DEVICE (default "cpu"; this server's GPUs are off-limits).
"""
from __future__ import annotations

import os
import time

import torch

from planner import timeutil as tu
from planner.grammar import PlanSpec
from planner.validate import demands_of


def simulate(spec: dict, result: dict, n_samples: int | None = None, device: str | None = None) -> dict:
    s = PlanSpec.model_validate(spec)
    u = s.uncertainty
    n = n_samples or u.n_samples
    dev = torch.device(device or os.environ.get("CARGO_MC_DEVICE", "cpu"))
    g = torch.Generator(device=dev).manual_seed(u.seed)
    t_start = time.time()
    lanes = {l.id: l for l in s.lanes}
    ships = result.get("shipments", [])
    arrive = {}
    exc_free = torch.ones(n, dtype=torch.bool, device=dev)
    for sh in ships:
        t = None
        for i, leg in enumerate(sh["legs"]):
            l = lanes[leg["lane"]]
            sched = torch.full((n,), tu.to_day(leg["depart"], s.t0), dtype=torch.float64, device=dev)
            if i == 0:
                dep = sched
            else:
                ready = t + s.nodes[l.frm].min_connect_days
                late_by = torch.clamp(ready - sched, min=0.0)
                waits = torch.ceil(late_by / l.schedule.every_days - 1e-9)
                dep = sched + waits * l.schedule.every_days
            md = u.delay.get(l.mode)
            if md is not None and (md.mean_days > 0 or md.sd_days > 0):
                delay = torch.clamp(md.mean_days + md.sd_days * torch.randn(n, generator=g, dtype=torch.float64, device=dev), min=0.0)
            else:
                delay = torch.zeros(n, dtype=torch.float64, device=dev)
            t = dep + l.transit_days + delay
            pe = u.excursion_prob_per_leg.get(l.mode, 0.0)
            if pe > 0:
                exc_free &= torch.rand(n, generator=g, dtype=torch.float64, device=dev) >= pe
        arrive[sh["id"]] = t
    demands = {d["id"]: d for d in demands_of(s)}
    by_d: dict[str, list] = {}
    for a in result.get("allocations", []):
        by_d.setdefault(a["demand"], []).append(a)
    all_ok = torch.ones(n, dtype=torch.bool, device=dev)
    shelf_all = torch.ones(n, dtype=torch.bool, device=dev)
    late_unit_days = torch.zeros(n, dtype=torch.float64, device=dev)
    per_demand = {}
    ship_by_id = {sh["id"]: sh for sh in ships}
    for did, allocs in by_d.items():
        d = demands[did]
        due = tu.to_day(d["due"], s.t0)
        ok = torch.ones(n, dtype=torch.bool, device=dev)
        for a in allocs:
            arr = arrive[a["shipment"]]
            ok &= arr <= due + 1e-9
            late_unit_days += torch.clamp(arr - due, min=0.0) * a["qty"]
            sh = ship_by_id[a["shipment"]]
            it = s.items[sh["item"]]
            mfg = tu.to_day(sh["mfg"], s.t0)
            check = arr if s.family == "S1" else torch.maximum(arr, torch.full_like(arr, due))
            shelf_all &= (mfg + it.shelf_life_days - check) >= it.shelf_life_days * it.min_remaining_shelf_life_pct / 100 - 1e-9
        per_demand[did] = round(ok.double().mean().item(), 4)
        all_ok &= ok
    cost = result.get("cost_usd", 0.0) + late_unit_days * u.late_penalty_usd_per_unit_day
    q = torch.quantile(cost.float().cpu(), torch.tensor([0.5, 0.95]))
    return {
        "n_samples": n, "device": str(dev), "seed": u.seed, "seconds": round(time.time() - t_start, 3),
        "p_all_on_time": round(all_ok.double().mean().item(), 4),
        "p_on_time_by_demand": per_demand,
        "p_shelf_ok": round(shelf_all.double().mean().item(), 4),
        "p_no_excursion": round(exc_free.double().mean().item(), 4),
        "expected_late_unit_days": round(late_unit_days.mean().item(), 3),
        "cost_mean_usd": round(cost.mean().item(), 2),
        "cost_p50_usd": round(q[0].item(), 2), "cost_p95_usd": round(q[1].item(), 2),
        "assumptions": "delay=max(0,N(mean,sd)) per leg by mode; missed connection waits for the next departure; later departures have unlimited capacity",
    }
