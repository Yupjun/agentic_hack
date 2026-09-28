"""Read-only data for the dashboard, plus one action: start an agent session.

Each route answers one question the dashboard asks:
  GET  /api/overview            what is the state of the bank, the runs and the agent?
  GET  /api/scenarios           which scenarios exist, what was predicted, what happened?
  GET  /api/scenarios/{id}      one scenario: spec parameters, predictions, plans, baselines
  GET  /api/runs                which solver runs exist?
  GET  /api/runs/{run_id}       one run: frontier and the four named plans
  GET  /api/sessions            which agent sessions ran, and did they end with a verified plan?
  GET  /api/sessions/{session}  the trace of one session: tool calls and guarded LLM calls in time order
  POST /api/agent/run           start one agent session in the background (one at a time)
  GET  /api/live/{airport}      live FAA airspace status + aviation weather (public feeds)
"""
from __future__ import annotations

import glob
import json
import os
import subprocess
import threading
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
router = APIRouter()
_lock = threading.Lock()
_current: dict = {}


def _journal() -> list[dict]:
    p = os.path.join(ROOT, "state", "journal.jsonl")
    if not os.path.exists(p):
        return []
    out = []
    for line in open(p, encoding="utf-8"):
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _load(path: str):
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else None


def _bank() -> list[dict]:
    rows = []
    for f in sorted(glob.glob(os.path.join(ROOT, "scenarios", "bank", "*.json"))):
        e = _load(f)
        if isinstance(e, dict) and "expected" in e:
            rows.append(e)
    return rows


def _results() -> dict:
    r = _load(os.path.join(ROOT, "eval", "scenarios-v2.json")) or []
    return {x["id"]: x for x in r}


def _sessions() -> list[dict]:
    j = _journal()
    starts = {r["session"]: r for r in j if r.get("event") == "agent_run_start"}
    ends = {r["session"]: r for r in j if r.get("event") == "agent_run_end"}
    out = []
    for s, st in starts.items():
        e = ends.get(s)
        rec = (e or {}).get("recommended") or {}
        out.append({"session": s, "goal": st.get("goal"), "started": st["ts"], "ended": e and e["ts"], "seconds": e and e.get("seconds"),
                    "status": "running" if e is None else ("verified" if rec.get("ok") else "failed"),
                    "plan": rec.get("plan"), "run_id": rec.get("run_id"), "cost_usd": rec.get("cost_usd"), "reason": rec.get("reason")})
    return sorted(out, key=lambda x: x["started"], reverse=True)


@router.get("/api/overview")
def overview():
    bank, res = _bank(), _results()
    j = _journal()
    sess = _sessions()
    agent_eval = _load(os.path.join(ROOT, "eval", "agent-eval.json")) or []
    return {
        "scenarios": len(bank),
        "judged": sum(1 for b in bank if b["id"] in res),
        "supported": sum(1 for b in bank if res.get(b["id"], {}).get("judge", {}).get("verdict") == "supported"),
        "pre_registered": sum(1 for b in bank if b.get("prediction_registered") == "before_run"),
        "runs": len(glob.glob(os.path.join(ROOT, "state", "runs", "*.json"))),
        "sessions": len(sess), "sessions_verified": sum(1 for s in sess if s["status"] == "verified"),
        "guardrail_blocks": sum(1 for r in j if r.get("event") == "guardrail_block"),
        "llm_calls": sum(1 for r in j if r.get("event") == "llm_call"),
        "tool_calls": sum(1 for r in j if r.get("event") == "tool_call"),
        "agent_eval": {"n": len(agent_eval), "params_ok": sum(1 for x in agent_eval if x.get("params_ok")),
                       "verified": sum(1 for x in agent_eval if (x.get("recommended") or {}).get("ok"))},
        "latest_session": sess[0] if sess else None,
        "agent_running": bool(_current.get("running")),
    }


@router.get("/api/scenarios")
def scenarios():
    res = _results()
    out = []
    for b in _bank():
        r = res.get(b["id"], {})
        rows = {x["plan"]: x for x in r.get("rows", [])}
        out.append({"id": b["id"], "family": b["family"], "status": b["status"], "registered": b.get("prediction_registered"),
                    "params": b.get("generator_params"), "rationale": b["rationale"], "falsifier": b["falsifier"],
                    "verdict": r.get("judge", {}).get("verdict"), "passed": r.get("judge", {}).get("passed"), "total": r.get("judge", {}).get("total"),
                    "cost_optimal": rows.get("cost_optimal"), "risk_adjusted": rows.get("risk_adjusted"), "rule_cheapest": rows.get("rule_cheapest"),
                    "seconds": r.get("seconds")})
    return out


@router.get("/api/scenarios/{sid}")
def scenario(sid: str):
    b = next((x for x in _bank() if x["id"] == sid), None)
    if b is None:
        raise HTTPException(404, f"no scenario {sid}")
    return {"entry": b, "result": _results().get(sid)}


@router.get("/api/runs")
def runs():
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, "state", "runs", "*.json")), key=os.path.getmtime, reverse=True):
        r = _load(f) or {}
        plans = r.get("plans") or {}
        out.append({"run_id": os.path.basename(f)[:-5], "spec_id": r.get("spec_id"), "family": r.get("family"), "status": r.get("status"),
                    "seconds": r.get("seconds"), "modified": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(os.path.getmtime(f))),
                    "costs": {k: v.get("cost_usd") for k, v in plans.items()}})
    return out


@router.get("/api/runs/{run_id}")
def run(run_id: str):
    r = _load(os.path.join(ROOT, "state", "runs", f"{os.path.basename(run_id)}.json"))
    if r is None:
        raise HTTPException(404, f"no run {run_id}")
    spec = None
    for d in ("state/specs", "scenarios/specs"):
        spec = spec or _load(os.path.join(ROOT, d, f"{r.get('spec_id')}.json"))
    return {"run": r, "spec": spec}


@router.get("/api/sessions")
def sessions():
    return _sessions()


@router.get("/api/sessions/{session}")
def session(session: str):
    j = _journal()
    st = next((r for r in j if r.get("event") == "agent_run_start" and r.get("session") == session), None)
    if st is None:
        raise HTTPException(404, f"no session {session}")
    en = next((r for r in j if r.get("event") == "agent_run_end" and r.get("session") == session), None)
    t0, t1 = st["ts"], (en or {}).get("ts", "9999")
    steps = []
    for r in j:
        if not (t0 <= r["ts"] <= t1):
            continue
        if r.get("event") == "tool_call" and r.get("session") == session:
            steps.append({"ts": r["ts"], "kind": "tool", "name": r["tool"], "args": r.get("args"), "seconds": r.get("seconds"), "error": r.get("error")})
        elif r.get("event") == "llm_call":
            steps.append({"ts": r["ts"], "kind": "llm", "name": ", ".join(r.get("tool_calls") or []) or "answer", "seconds": r.get("seconds"),
                          "blocked": r.get("blocked_rails"), "ok": r.get("ok")})
        elif r.get("event") == "guardrail_block":
            steps.append({"ts": r["ts"], "kind": "block", "name": ", ".join(r.get("rails") or []), "content": r.get("content")})
    return {"start": st, "end": en, "steps": steps}


class RunReq(BaseModel):
    goal: str


def _bg(goal: str):
    try:
        subprocess.run([os.path.join(ROOT, ".venv", "bin", "python"), "-W", "ignore", "-m", "agent.run_agent", goal], cwd=ROOT,
                       capture_output=True, text=True, timeout=1200)
    finally:
        _current["running"] = False


@router.post("/api/agent/run")
def agent_run(req: RunReq):
    if not req.goal.strip():
        raise HTTPException(422, "goal is empty")
    if not os.environ.get("NVIDIA_API_KEY"):
        raise HTTPException(503, "NVIDIA_API_KEY is not set for the API process")
    with _lock:
        if _current.get("running"):
            raise HTTPException(429, "an agent session is already running; wait for it to finish")
        _current["running"] = True
    threading.Thread(target=_bg, args=(req.goal,), daemon=True).start()
    return {"started": True, "note": "the new session appears in /api/sessions within a few seconds"}


@router.get("/api/live/{airport}")
def live(airport: str):
    from agent.planner_tools import airspace_status, aviation_weather
    a = airport.upper()
    icao = a if len(a) == 4 else "K" + a
    return {"airspace": json.loads(airspace_status(a if len(a) == 3 else a[1:])), "weather": json.loads(aviation_weather(icao))}
