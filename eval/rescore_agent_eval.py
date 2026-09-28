"""Re-score a finished agent-eval run from what is already recorded (journal answers and
make_spec calls) with the current parser and the semantic parameter check. Changes the
JUDGE only; the agent's behaviour is exactly what was recorded.
  python -m eval.rescore_agent_eval eval/agent-eval-run1.json
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from agent.run_agent import check_answer  # noqa: E402
from eval.agent_eval import GOALS, params_match  # noqa: E402

rows = json.load(open(sys.argv[1]))
ends = {}
for l in open(os.path.join(ROOT, "state", "journal.jsonl")):
    d = json.loads(l)
    if d.get("event") == "agent_run_end":
        ends[d["session"]] = d
want = {g[0]: (g[1], g[2]) for g in GOALS}
bank = {r["id"]: r for r in json.load(open(os.path.join(ROOT, "eval", "scenarios-v2.json")))}
out = []
for x in rows:
    base, w = want[x["scenario"]]
    rec = check_answer(ends[x["session"]].get("answer", ""))
    bank_costs = {r["plan"]: r["cost_usd"] for r in bank[x["scenario"]]["rows"] if not r["plan"].startswith("rule")}
    out.append({"scenario": x["scenario"], "params_ok": params_match(x["params"], w, base), "verified": bool(rec.get("ok")),
                "plan": rec.get("plan"), "cost_matches_bank": bool(rec.get("ok")) and bank_costs.get(rec.get("plan")) == rec.get("cost_usd"),
                "reason": rec.get("reason"), "old_params_ok": x["params_ok"], "old_verified": bool((x.get("recommended") or {}).get("ok"))})
for o in out:
    print(o)
n = len(out)
print(f"params {sum(o['params_ok'] for o in out)}/{n} (was {sum(o['old_params_ok'] for o in out)}), verified {sum(o['verified'] for o in out)}/{n} (was {sum(o['old_verified'] for o in out)}), cost=bank {sum(o['cost_matches_bank'] for o in out)}/{n}")
json.dump(out, open(sys.argv[1].replace(".json", "-rescored.json"), "w"), indent=1, ensure_ascii=False)
