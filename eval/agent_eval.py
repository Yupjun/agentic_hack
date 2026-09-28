"""Agent evaluation: natural-language goals that mean the same as banked scenarios.

For each goal the agent (NAT + guarded Nemotron) must (1) choose the right base,
(2) translate the goal into the same generator parameters as the banked scenario,
(3) end with a RECOMMENDED plan that exists and passed verify. Because the engine is
deterministic, the agent's plan costs must then equal the banked scenario's.
Writes eval/agent-eval.json and eval/agent-eval.md. Runs goals one at a time.
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from agent.run_agent import run  # noqa: E402
from engine import journal  # noqa: E402

GOALS = [
    ("s1-v1-tight-deadline", "s1_base", {"due_days": 11}, "C 제품 100개를 A에서 B로 11일 안에 보내야 해. 예산은 6만 달러야. 계획을 제안해줘."),
    ("s1-v3-short-shelf-life", "s1_base", {"shelf_life_days": {"C": 120}}, "이번 C 제품 로트는 유통기한이 120일이야. 수령 시 60% 이상 남아 있어야 하는 건 그대로고, 100개를 A에서 B로 40일 안에, 예산 6만 달러로 보내야 해."),
    ("s1-v4-low-exposure", "s1_base", {"max_exposure_hours": 2.0}, "C 제품 100개 A에서 B로, 기한 40일, 예산 6만 달러. 고객이 온도 통제 밖 노출을 합계 2시간 이내로 요구했어."),
    ("s2-v1-site-delay", "s2_base", {"lead_time_add_days": {"c": 10, "d": 10}}, "AA 사이트 배치 3개용 원료 발주 계획이 필요해. A3 사이트가 모든 발주에서 10일씩 늦어진대. 예산 25만 달러."),
    ("s2-v2-moq-above-need", "s2_base", {"moq": {"b": 15}}, "AA 배치 3개용 원료 계획을 짜줘. A2 사이트가 원료 b의 최소 발주량을 15개로 올렸어. 예산 25만 달러."),
    ("s2-v4-budget-cut", "s2_base", {"budget_usd": 205000}, "AA 배치 3개용 원료 발주·운송 계획. 예산이 20만 5천 달러로 깎였어."),
]
DEFAULTS = {"s1_base": {"due_days": 40, "budget_usd": 60000}, "s2_base": {"budget_usd": 250000}}


def params_match(got: dict, want: dict, base: str) -> bool:
    """Same meaning: every wanted key equal; extra keys allowed only if they restate the base default."""
    for k, v in want.items():
        if got.get(k) != v and not (isinstance(v, float) and got.get(k) == int(v)):
            return False
    for k, v in got.items():
        if k not in want and DEFAULTS.get(base, {}).get(k) != v:
            return False
    return True


def main() -> int:
    bank = {r["id"]: r for r in json.load(open(os.path.join(ROOT, "eval", "scenarios-v2.json")))}
    rows = []
    for sid, base, want, goal in GOALS:
        r = run(goal, os.path.join(ROOT, "agent", "nat_planner", "planner.yml"))
        calls = [json.loads(l) for l in open(os.path.join(ROOT, "state", "journal.jsonl")) if f'"session": "{r["session"]}"' in l]
        mk = [c for c in calls if c.get("event") == "tool_call" and c["tool"] == "make_spec"]
        got_base = mk[-1]["args"][0] if mk else None
        try:
            got = json.loads(mk[-1]["args"][1]) if mk else {}
        except (json.JSONDecodeError, IndexError):
            got = {"_unparsed": mk[-1]["args"][1] if mk else None}
        rec = r["recommended"]
        bank_costs = {x["plan"]: x["cost_usd"] for x in bank.get(sid, {}).get("rows", []) if not x["plan"].startswith("rule")}
        row = {"scenario": sid, "goal": goal, "seconds": r["seconds"], "tool_calls": [c["tool"] for c in calls if c.get("event") == "tool_call"],
               "base_ok": got_base == base, "params": got, "params_ok": params_match(got, want, base), "recommended": rec,
               "cost_matches_bank": rec.get("ok") and bank_costs.get(rec.get("plan")) == rec.get("cost_usd"),
               "bank_cost": bank_costs.get(rec.get("plan")), "session": r["session"]}
        rows.append(row)
        print(f"{sid:24s} base {row['base_ok']} params {row['params_ok']} {got} rec {rec.get('plan')} ok {rec.get('ok')} cost {rec.get('cost_usd')} bank {row['bank_cost']} {r['seconds']}s", flush=True)
    json.dump(rows, open(os.path.join(ROOT, "eval", "agent-eval.json"), "w"), indent=1, ensure_ascii=False)
    L = ["# Agent evaluation — NeMo Agent Toolkit + Nemotron 3 Super via NeMo Guardrails gateway", "",
         "| scenario | base | params | recommended | verified | cost = bank | seconds | tools |", "|---|---|---|---|---|---|---|---|"]
    for x in rows:
        L.append(f"| {x['scenario']} | {'ok' if x['base_ok'] else 'WRONG'} | {'ok' if x['params_ok'] else 'WRONG'} `{json.dumps(x['params'], ensure_ascii=False)}` | "
                 f"{x['recommended'].get('plan')} | {'ok' if x['recommended'].get('ok') else 'FAIL'} | {'ok' if x['cost_matches_bank'] else 'no'} | {x['seconds']} | {' > '.join(x['tool_calls'])} |")
    n = len(rows)
    L += ["", f"base {sum(x['base_ok'] for x in rows)}/{n}, params {sum(x['params_ok'] for x in rows)}/{n}, "
          f"verified recommendation {sum(bool(x['recommended'].get('ok')) for x in rows)}/{n}, cost equals bank {sum(bool(x['cost_matches_bank']) for x in rows)}/{n}"]
    open(os.path.join(ROOT, "eval", "agent-eval.md"), "w").write("\n".join(L) + "\n")
    journal.append("agent_eval", n=n, base_ok=sum(x["base_ok"] for x in rows), params_ok=sum(x["params_ok"] for x in rows),
                   verified=sum(bool(x["recommended"].get("ok")) for x in rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
