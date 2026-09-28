"""Planner tools for the agent — plain functions, text in, JSON text out.

Framework-agnostic on purpose: NeMo Agent Toolkit registers them (agent/nat_planner),
the v1 loop can call them, tests call them directly. Each tool does one thing.
None of them books, orders or sends anything: the agent can only PROPOSE.

Errors are returned as {"error": ...} JSON with the reason (the model reads it),
never as an empty success.
"""
from __future__ import annotations

import json
import os
import time
import warnings

warnings.filterwarnings("ignore")
from engine import journal  # noqa: E402
from engine.mc import simulate  # noqa: E402
from engine.run import solve_spec  # noqa: E402
from planner.validate import validate  # noqa: E402
from scenarios.gen import generate  # noqa: E402
from scenarios.judge import derived  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASES = {"s1_base": "S1 transport-mode choice: stock of C at site A (Incheon area) to warehouse B (Frankfurt area); truck, air (passive / active container), ocean via Rotterdam, sea-air via Dubai, express parcel.",
         "s2_base": "S2 multi-site sourcing: materials a (site A1), b (A2), c and d (A3) to production site AA for batches B1-B3; each material has ONE approved site; standard or expedite production orders."}
PARAMS_DOC = ("generator params (all optional): due_days (S1 deadline, days after t0), budget_usd, shelf_life_days {item: days}, "
              "min_remaining_pct {item: pct at receipt/use}, max_exposure_hours, allowed_modes [truck|parcel|air|ocean], "
              "delay_mean_days {mode: days}, delay_scale {mode: factor}, lead_time_add_days {item: days}, moq {item: n}, "
              "capacity_per_week {item: n}, batch_shift_days (S2)")


def _dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def _spec_path(spec_id: str) -> str:
    for d in ("state/specs", "scenarios/specs"):
        p = os.path.join(ROOT, d, f"{spec_id}.json")
        if os.path.exists(p):
            return p
    return ""


def _base(name: str) -> dict:
    return json.load(open(os.path.join(ROOT, "scenarios", "examples", f"{name}.json"), encoding="utf-8"))


def list_bases() -> str:
    """List the base scenarios and the parameters a variant may change."""
    return _dump({"bases": BASES, "params": PARAMS_DOC})


def make_spec(base: str, params_json: str = "{}", new_id: str = "") -> str:
    """Create a plan spec from a base scenario plus parameter overrides; validate it and save it."""
    if base not in BASES:
        return _dump({"error": f"unknown base {base!r}", "known": list(BASES)})
    try:
        params = json.loads(params_json or "{}")
    except json.JSONDecodeError as e:
        return _dump({"error": f"params_json is not JSON: {e}"})
    sid = new_id or f"{base}-agent-{int(time.time())}"
    try:
        spec = generate(_base(base), params, 0, new_id=sid)
    except (KeyError, TypeError, ValueError) as e:
        return _dump({"error": f"cannot apply params: {e}", "params": PARAMS_DOC,
                      "hint": "remove or correct the listed parameters and call make_spec again"})
    probs = validate(spec)
    os.makedirs(os.path.join(ROOT, "state", "specs"), exist_ok=True)
    json.dump(spec, open(os.path.join(ROOT, "state", "specs", f"{sid}.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    journal.append("agent_make_spec", spec_id=sid, base=base, params=params, problems=probs)
    dem = [{"id": d["id"], "item": d["item"], "qty": d["qty"], "due": d["due"]} for d in spec.get("demand", [])]
    if spec.get("production_plan"):
        dem = [{"batch": b["id"], "start": b["start"]} for b in spec["production_plan"]["batches"]]
    return _dump({"spec_id": sid, "valid": not probs, "problems": probs, "family": spec["family"], "budget_usd": spec["budget_usd"],
                  "demand": dem, "constraints": spec.get("constraints"), "lanes": len(spec["lanes"])})


def solve_plan(spec_id: str) -> str:
    """Solve a saved spec: returns the cost-optimal, time-optimal, balanced and risk-adjusted plans (all verified)."""
    p = _spec_path(spec_id)
    if not p:
        return _dump({"error": f"no spec {spec_id!r}; create one with make_spec"})
    spec = json.load(open(p, encoding="utf-8"))
    res = solve_spec(spec, time_limit=90)
    run_id = f"{spec_id}-{res['spec_hash']}"
    os.makedirs(os.path.join(ROOT, "state", "runs"), exist_ok=True)
    json.dump(res, open(os.path.join(ROOT, "state", "runs", f"{run_id}.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    journal.append("agent_solve", spec_id=spec_id, run_id=run_id, status=res["status"], seconds=res.get("seconds"))
    if res["status"] != "ok":
        return _dump({"run_id": run_id, "status": res["status"], "problems": res.get("problems"),
                      "hint": "the request is infeasible as stated: say so and propose which constraint to relax (deadline, budget, exposure)"})
    plans = {}
    for k, v in res["plans"].items():
        d = derived(v)
        plans[k] = {"cost_usd": v["cost_usd"], "min_slack_days": v["metrics"]["min_slack_days"], "latest_arrival": v["metrics"]["latest_arrival"],
                    "p_all_on_time": v["mc"]["p_all_on_time"], "expected_cost_usd": v["mc"]["cost_mean_usd"], "cost_p95_usd": v["mc"]["cost_p95_usd"],
                    "p_shelf_ok": v["mc"]["p_shelf_ok"], "expected_shelf_loss_usd": v["mc"].get("expected_shelf_loss_usd"), "p_no_excursion": v["mc"]["p_no_excursion"],
                    "routes": d["route_classes"], "expedite_items": d["expedite_items"], "units_left_over": v["metrics"]["units_left_over"],
                    "shipments": len(v["shipments"]), "verified": v["verify_ok"]}
    return _dump({"run_id": run_id, "status": "ok", "backend": res["backend"], "seconds": res["seconds"],
                  "frontier_points": sum(1 for f in res["frontier"] if f.get("verify_ok") and not f.get("dominated")), "plans": plans,
                  "note": "every plan here passed the independent verifier; costs are USD; p_* come from 10,000 Monte Carlo samples"})


def _run(run_id: str) -> dict | None:
    p = os.path.join(ROOT, "state", "runs", f"{run_id}.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


def plan_details(run_id: str, plan: str) -> str:
    """Show the shipments of one named plan (cost_optimal | time_optimal | balanced | risk_adjusted)."""
    r = _run(run_id)
    if r is None:
        return _dump({"error": f"no run {run_id!r}"})
    p = r.get("plans", {}).get(plan)
    if p is None:
        return _dump({"error": f"no plan {plan!r} in run", "plans": list(r.get("plans", {}))})
    rows = [{"item": s["item"], "qty": s["qty"], "option": s["option"], "made": s["mfg"][:10],
             "route": " > ".join(f"{g['mode']} {g['from']}-{g['to']}" for g in s["legs"]),
             "depart": s["legs"][0]["depart"][:16], "arrive": s["legs"][-1]["arrive"][:16]} for s in p["shipments"]]
    return _dump({"run_id": run_id, "plan": plan, "cost_usd": p["cost_usd"], "shipments": rows})


def stress_test(run_id: str, plan: str, delay_mean_days_json: str = "{}") -> str:
    """What-if: re-run Monte Carlo for one plan with different mean delays per mode, e.g. {"ocean": 6.06}."""
    r = _run(run_id)
    if r is None:
        return _dump({"error": f"no run {run_id!r}"})
    p = r.get("plans", {}).get(plan)
    if p is None:
        return _dump({"error": f"no plan {plan!r}"})
    try:
        over = json.loads(delay_mean_days_json or "{}")
    except json.JSONDecodeError as e:
        return _dump({"error": f"not JSON: {e}"})
    spec = json.load(open(_spec_path(r["spec_id"]), encoding="utf-8"))
    for m, v in over.items():
        if m in spec.get("uncertainty", {}).get("delay", {}):
            spec["uncertainty"]["delay"][m]["mean_days"] = float(v)
    mc = simulate(spec, p)
    return _dump({"run_id": run_id, "plan": plan, "delay_mean_days": over, "p_all_on_time": mc["p_all_on_time"],
                  "expected_cost_usd": mc["cost_mean_usd"], "cost_p95_usd": mc["cost_p95_usd"], "baseline_p_all_on_time": p["mc"]["p_all_on_time"]})


EXPLAINER_MODEL = os.environ.get("CARGO_EXPLAINER_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b")


def _numbers(text: str) -> list[str]:
    import re
    return [n.replace(",", "") for n in re.findall(r"\d[\d,]*\.?\d*", text)]


def explain_plan(run_id: str, plan: str) -> str:
    """Write a short Korean brief of one verified plan for the approver, with a second, smaller model
    (Nemotron 3.5 Lightning, reasoning off). Every number in the brief is checked against the plan data;
    numbers that do not appear there are listed as unverified (the brief is not silently trusted)."""
    import httpx
    r = _run(run_id)
    if r is None:
        return _dump({"error": f"no run {run_id!r}"})
    p = r.get("plans", {}).get(plan)
    if p is None:
        return _dump({"error": f"no plan {plan!r}", "plans": list(r.get("plans", {}))})
    facts = {"plan": plan, "cost_usd": p["cost_usd"], "min_slack_days": p["metrics"]["min_slack_days"], "latest_arrival": p["metrics"]["latest_arrival"],
             "p_all_on_time": p["mc"]["p_all_on_time"], "expected_cost_usd": p["mc"]["cost_mean_usd"], "units_left_over": p["metrics"]["units_left_over"],
             "shipments": [{"item": s["item"], "qty": s["qty"], "option": s["option"], "route": " > ".join(f"{g['mode']} {g['from']}-{g['to']}" for g in s["legs"]),
                            "depart": s["legs"][0]["depart"][:10], "arrive": s["legs"][-1]["arrive"][:10]} for s in p["shipments"]]}
    key = os.environ.get("NVIDIA_API_KEY")
    if not key:
        return _dump({"error": "NVIDIA_API_KEY not set"})
    body = {"model": EXPLAINER_MODEL, "max_tokens": 700, "temperature": 0.2, "chat_template_kwargs": {"enable_thinking": False},
            "messages": [{"role": "system", "content": "승인자에게 보낼 발주·운송 계획 요약을 한국어로 5문장 이내로 쓴다. 아래 JSON에 있는 숫자만 쓴다. 숫자를 새로 계산하거나 지어내지 않는다."},
                         {"role": "user", "content": json.dumps(facts, ensure_ascii=False)}]}
    last = None
    for attempt in range(4):
        try:
            resp = httpx.post("https://integrate.api.nvidia.com/v1/chat/completions", json=body, headers={"Authorization": f"Bearer {key}"}, timeout=120)
            if resp.status_code == 200:
                text = resp.json()["choices"][0]["message"]["content"] or ""
                source = _numbers(json.dumps(facts, ensure_ascii=False))
                pct = [f"{v * 100:.1f}".rstrip("0").rstrip(".") for v in (facts["p_all_on_time"],)]
                unverified = [n for n in _numbers(text) if not any(n == s or s.startswith(n) or n in s for s in source + pct)]
                return _dump({"model": EXPLAINER_MODEL, "brief": text.strip(), "unverified_numbers": unverified,
                              "note": "unverified_numbers lists numbers in the brief that do not appear in the plan data"})
            last = f"HTTP {resp.status_code}: {resp.text[:200]}"
            if resp.status_code < 500 and resp.status_code != 429:
                break
        except httpx.HTTPError as e:
            last = f"{type(e).__name__}: {e}"
        time.sleep(2 ** (attempt + 1))
    return _dump({"error": f"explainer failed: {last}"})


def airspace_status(airport: str) -> str:
    """Live FAA airspace status for a US airport (ground delay programs, ground stops, closures)."""
    try:
        from tools.nas_status import nas
        return _dump(nas(airport))
    except Exception as e:  # noqa: BLE001 - report the upstream failure to the model
        return _dump({"error": f"{type(e).__name__}: {getattr(e, 'detail', e)}"})


def aviation_weather(icao: str) -> str:
    """Live aviation weather (METAR, TAF, SIGMET nearby) for an ICAO station."""
    try:
        from tools.wx import wx
        d = json.loads(json.dumps(wx(icao), default=str))
        d.pop("surface_forecast_24h", None)
        return _dump(d)
    except Exception as e:  # noqa: BLE001
        return _dump({"error": f"{type(e).__name__}: {getattr(e, 'detail', e)}"})


def _traced(fn):
    """Journal every tool call (name, args, seconds, result size, error?) so the dashboard
    can show the agent's trace independent of the agent framework."""
    import functools

    @functools.wraps(fn)
    def wrap(*args, **kwargs):
        t = time.time()
        out = fn(*args, **kwargs)
        err = None
        try:
            err = json.loads(out).get("error")
        except (ValueError, AttributeError):
            pass
        journal.append("tool_call", tool=fn.__name__, args=[str(a)[:300] for a in args], kwargs={k: str(v)[:300] for k, v in kwargs.items()},
                       seconds=round(time.time() - t, 3), result_chars=len(out), error=err, session=os.environ.get("CARGO_SESSION", ""))
        return out
    return wrap


list_bases, make_spec, solve_plan, plan_details, stress_test, explain_plan, airspace_status, aviation_weather = (
    _traced(f) for f in (list_bases, make_spec, solve_plan, plan_details, stress_test, explain_plan, airspace_status, aviation_weather))
TOOLS = [list_bases, make_spec, solve_plan, plan_details, stress_test, explain_plan, airspace_status, aviation_weather]
