"""Run one agent session end to end and check its answer.

  python -m agent.run_agent "<goal>" [--config agent/nat_planner/planner.yml]

- tags the session (CARGO_SESSION) so tool calls land in the journal under it
- runs the NeMo Agent Toolkit workflow (`nat run`) as a subprocess
- parses the final "RECOMMENDED: <run_id> <plan>" line and checks that the run
  exists and the plan passed engine/verify.py; an answer that names an unverified
  or unknown plan is recorded as failed (fail noisily)
Writes one agent_run_start and one agent_run_end journal row and logs/nat/<session>.log.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from engine import journal  # noqa: E402

REC = re.compile(r"RECOMMENDED:\s*(\S+)\s+(cost_optimal|time_optimal|balanced|risk_adjusted)")


def run(goal: str, config: str, timeout: int = 900) -> dict:
    session = f"agent-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    env = dict(os.environ, CARGO_SESSION=session)
    journal.append("agent_run_start", session=session, goal=goal, config=os.path.relpath(config, ROOT))
    t = time.time()
    os.makedirs(os.path.join(ROOT, "logs", "nat"), exist_ok=True)
    logp = os.path.join(ROOT, "logs", "nat", f"{session}.log")
    try:
        p = subprocess.run([os.path.join(ROOT, ".venv", "bin", "nat"), "run", "--config_file", config, "--input", goal],
                           cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)
        out = p.stdout + "\n" + p.stderr
        rc = p.returncode
    except subprocess.TimeoutExpired as e:
        out, rc = (e.stdout or "") + "\n" + (e.stderr or "") + "\nTIMEOUT", -1
    open(logp, "w").write(out)
    m = out.split("Workflow Result:", 1)
    answer = re.sub(r"\x1b\[[0-9;]*m", "", m[1]).split("\n-----", 1)[0].strip() if len(m) == 2 else ""
    rec = REC.findall(answer)
    check = {"found": bool(rec)}
    if rec:
        run_id, plan = rec[-1]
        rp = os.path.join(ROOT, "state", "runs", f"{run_id}.json")
        if not os.path.exists(rp):
            check.update(ok=False, reason=f"run {run_id} does not exist")
        else:
            r = json.load(open(rp))
            pl = r.get("plans", {}).get(plan)
            check.update(run_id=run_id, plan=plan, ok=bool(pl and pl.get("verify_ok")), cost_usd=pl and pl["cost_usd"],
                         reason=None if pl and pl.get("verify_ok") else "plan missing or not verified")
    else:
        check.update(ok=False, reason="no RECOMMENDED line in the answer")
    res = {"session": session, "rc": rc, "seconds": round(time.time() - t, 1), "answer": answer, "recommended": check, "log": os.path.relpath(logp, ROOT)}
    journal.append("agent_run_end", **{k: v for k, v in res.items() if k != "answer"}, answer=answer[:4000])
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("goal")
    ap.add_argument("--config", default=os.path.join(ROOT, "agent", "nat_planner", "planner.yml"))
    a = ap.parse_args()
    r = run(a.goal, a.config)
    print(r["answer"])
    print(json.dumps({k: v for k, v in r.items() if k != "answer"}, ensure_ascii=False))
    sys.exit(0 if r["recommended"].get("ok") else 1)
