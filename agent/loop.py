"""Planner loop: goal -> plan -> tool calls -> observe -> re-plan -> final proposal.

Two tool protocols (same idea as autoresearch/agent_shim.py, measured 2026-09-23):
  native  — OpenAI `tools` / `tool_calls` (NIM, vLLM with --enable-auto-tool-choice)
  prompt  — the model writes ONE fenced ```tool block with a JSON call; we run it and
            feed the result back as the next user turn. Works on any chat endpoint.
  auto    — try native once; on HTTP 400 fall back to prompt for the run.

Env: LLM_BASE_URL (default http://127.0.0.1:8001/v1), LLM_MODEL (qwen38), LLM_API_KEY,
     TOOLS_URL (http://127.0.0.1:8090), TOOL_PROTOCOL (auto|native|prompt), MAX_TURNS (24).
Usage: python -m agent.loop scenarios/s1_hub_gdp/goal.json [--log logs/run.jsonl]
Every step is appended to the JSONL log: what was called, with what, what came back.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time

import httpx

from .manifest import BY_NAME, TOOLS

LLM_BASE = os.environ.get("LLM_BASE_URL", "http://127.0.0.1:8001/v1").rstrip("/")
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen38")
LLM_KEY = os.environ.get("LLM_API_KEY", "")
TOOLS_URL = os.environ.get("TOOLS_URL", "http://127.0.0.1:8090").rstrip("/")
PROTOCOL = os.environ.get("TOOL_PROTOCOL", "auto")
MAX_TURNS = int(os.environ.get("MAX_TURNS", "30"))
MAX_TOOL_CHARS = 9000
LLM_TIMEOUT = float(os.environ.get("LLM_TIMEOUT", "1500"))
LLM_RETRIES = int(os.environ.get("LLM_RETRIES", "3"))  # on 5xx / 429 / transport, backoff 2,4,8 s
# Extra JSON merged into every chat request, e.g. '{"chat_template_kwargs":{"enable_thinking":false}}'
LLM_EXTRA = json.loads(os.environ.get("LLM_EXTRA_JSON", "{}"))

SYSTEM = """You are a cargo disruption recovery planner for a freight forwarder's operations desk.
You receive a GOAL and a shipment list. You must PLAN, then CALL TOOLS to check facts
(airspace programs, weather, capacity, cost), then REVISE, and finally PROPOSE a recovery plan.
Rules:
- Never invent capacity, delays or prices: every number in the final plan must come from a tool result.
- Check the disruption first (nas_status, wx), then enumerate alternatives (schedule), then price them (cost).
- A plan is VALID only if every leg carries no more kg than that option's remaining capacity, arrives before cut-off,
  and ALL cargo reaches the final destination: kg arriving at the final destination must equal the total kg, and cargo
  flown to an intermediate hub must continue on an onward leg (nothing stranded). Pass final_dest and total_kg to cost.
  If a group does not fit one option, SPLIT it across options (pass each split as its own leg with option_id) and re-price.
  Never recommend a plan whose cost result says feasible=false; fix it first.
- Group AWBs by booked flight; keep groups together unless splitting is needed for capacity.
- The plan is a PROPOSAL for a human to approve. Do not claim anything was booked.
- Use allocate with ROUTES (chains such as truck feeder + flight) to assign AWBs; do not do packing arithmetic in prose. Its plan_legs go straight into cost and PLAN_JSON.
- Final answer format (markdown): 1) Situation (what tools showed) 2) Options considered with cost/arrival/cutoff
  3) Recommended plan per AWB group 4) Risks and what would change the decision 5) Tools called (list)
  6) The LAST line of the answer is one machine-readable line (this is NOT a tool call; it is required):
PLAN_JSON: {"cutoff": "<ISO>", "awb_count": <int>, "final_dest": "<IATA>", "total_kg": <kg>, "legs": [{"option_id": "<id>", "chargeable_kg": <kg>}, ...]}
  It must list EVERY leg of the recommended plan. The loop re-prices it with the cost tool; if it is infeasible or missing you will be asked to fix it.
"""


def prompt_protocol_text() -> str:
    lines = ["", "# Tools", "You have these tools:"]
    for t in TOOLS:
        lines.append(f"- {t['name']}: {t['description']} args schema: {json.dumps(t['parameters']['properties'])}")
    lines += ["To call one, reply with ONLY a fenced block and nothing after it:", "```tool", '{"tool": "nas_status", "args": {"airport": "JFK"}}', "```",
              "One tool call per reply. The result comes back as the next user message starting with TOOL RESULT.",
              "When you have what you need, write the final proposal with no tool block.",
              f"Budget: at most {MAX_TURNS} replies in total, tool calls included."]
    return "\n".join(lines)


def call_tool(name: str, args: dict) -> tuple[int, str]:
    t = BY_NAME.get(name)
    if not t:
        return 400, json.dumps({"error": f"unknown tool {name}", "known": list(BY_NAME)})
    try:
        with httpx.Client(timeout=120) as c:
            if t["method"] == "GET":
                r = c.get(TOOLS_URL + t["path"], params={k: v for k, v in args.items() if v is not None})
            else:
                r = c.post(TOOLS_URL + t["path"], json=args)
        body = r.text
        if len(body) > MAX_TOOL_CHARS:
            body = body[:MAX_TOOL_CHARS] + f'... [truncated {len(r.text) - MAX_TOOL_CHARS} chars]'
        return r.status_code, body
    except Exception as e:  # noqa: BLE001
        return 599, json.dumps({"error": f"{type(e).__name__}: {e}"})


def chat(messages: list[dict], use_native: bool) -> dict:
    payload: dict = {"model": LLM_MODEL, "messages": messages, "max_tokens": int(os.environ.get("LLM_MAX_TOKENS", "6000")), "temperature": 0.2}
    payload.update(LLM_EXTRA)
    if use_native:
        payload["tools"] = [{"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}} for t in TOOLS]
        payload["tool_choice"] = "auto"
    headers = {"Content-Type": "application/json"}
    if LLM_KEY:
        headers["Authorization"] = f"Bearer {LLM_KEY}"
    last = None
    for attempt in range(LLM_RETRIES + 1):
        try:
            with httpx.Client(timeout=LLM_TIMEOUT) as c:
                r = c.post(LLM_BASE + "/chat/completions", json=payload, headers=headers)
        except Exception as e:  # noqa: BLE001 — transport failures are reported, not raised bare
            last = RuntimeError(f"LLM transport {type(e).__name__}: {e}")
        else:
            if r.status_code == 200:
                return r.json()
            last = RuntimeError(f"LLM HTTP {r.status_code}: {r.text[:300]}")
            if r.status_code < 500 and r.status_code != 429:
                raise last  # 4xx (other than 429) will not get better by retrying
        if attempt < LLM_RETRIES:
            time.sleep(2 ** (attempt + 1))
    raise last


_FENCE = re.compile(r"```tool\s*(\{.*?\})\s*```", re.S)
_PLAN = re.compile(r"PLAN_JSON:\s*(\{.*\})", re.M)
MAX_REPEATS = int(os.environ.get("MAX_REPEATS", "2"))
MAX_PLAN_FIXES = int(os.environ.get("MAX_PLAN_FIXES", "2"))


def parse_prompt_call(text: str) -> tuple[str, dict] | None:
    m = _FENCE.findall(text or "")
    if not m:
        return None
    try:
        d = json.loads(m[-1])
    except json.JSONDecodeError:
        return None
    return d.get("tool"), d.get("args") or {}


def shipments_summary(awbs: list[dict]) -> str:
    """Per booked flight: count, total chargeable kg, destination, cutoff, and the AWB numbers.
    Compact on purpose: the planner reasons in groups; the raw list only inflates the context."""
    groups: dict[str, list[dict]] = {}
    for a in awbs:
        groups.setdefault(a["booked_flight"], []).append(a)
    lines = []
    for fl, rows in groups.items():
        kg = sum(r["chargeable_kg"] for r in rows)
        lines.append(f"- {fl} {rows[0]['origin']}->{rows[0]['dest']} (final {rows[0]['final_dest']}): {len(rows)} AWBs, {kg} kg, cutoff {rows[0]['cutoff']}, largest single AWB {max(r['chargeable_kg'] for r in rows)} kg")
        lines.append("  AWBs: " + ", ".join(f"{r['awb']}({r['chargeable_kg']}kg)" for r in rows))
    return "\n".join(lines)


def check_plan(text: str, final_dest: str | None = None, total_kg: float | None = None) -> tuple[bool, str, dict | None]:
    """Re-price the ```plan block with the cost tool. Returns (ok, message, cost_result)."""
    m = _PLAN.findall(text or "")
    if not m:
        return False, "final answer has no PLAN_JSON line", None
    try:
        plan = json.loads(m[-1])
    except json.JSONDecodeError as e:
        return False, f"PLAN_JSON is not valid JSON: {e}", None
    if final_dest:
        plan.setdefault("final_dest", final_dest)
        plan.setdefault("total_kg", total_kg)
    status, body = call_tool("cost", plan)
    if status != 200:
        return False, f"cost tool rejected the plan: HTTP {status} {body[:400]}", None
    res = json.loads(body)
    if not res.get("feasible"):
        return False, f"plan is infeasible: {json.dumps({k: res.get(k) for k in ('capacity_violations', 'final_arrival', 'meets_cutoff', 'delivered_kg_to_final_dest', 'required_kg', 'stranded_kg_by_node')})}", res
    return True, "ok", res


def run(goal_path: str, log_path: str) -> int:
    with open(goal_path, encoding="utf-8") as f:
        goal = json.load(f)
    use_native = PROTOCOL in ("auto", "native")
    log = open(log_path, "a", encoding="utf-8")

    def rec(kind: str, **kw):
        kw.update(kind=kind, ts=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        log.write(json.dumps(kw, ensure_ascii=False) + "\n")
        log.flush()

    system = SYSTEM + ("" if use_native else prompt_protocol_text())
    user = f"GOAL: {goal['goal']}\nHUB: {goal['hub']} ({goal['hub_icao']})\nSHIPMENTS ({len(goal['awbs'])} AWBs), grouped by booked flight:\n" + shipments_summary(goal["awbs"])
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    rec("start", goal=goal_path, model=LLM_MODEL, base=LLM_BASE, protocol=PROTOCOL)
    calls = 0
    fixes = 0
    repeats = 0
    last_key, last_result = None, None
    for turn in range(1, MAX_TURNS + 1):
        if turn == MAX_TURNS:
            messages.append({"role": "user", "content": "Budget exhausted. Write the final proposal now with what you have. No tool calls. End with the PLAN_JSON line."})
        try:
            resp = chat(messages, use_native)
        except RuntimeError as e:
            if use_native and PROTOCOL == "auto" and "400" in str(e):
                rec("protocol_fallback", reason=str(e)[:200])
                use_native = False
                messages[0]["content"] = SYSTEM + prompt_protocol_text()
                continue
            rec("error", error=str(e))
            print("ERROR", e, file=sys.stderr)
            return 1
        msg = resp["choices"][0]["message"]
        content = msg.get("content") or ""
        rec("llm", turn=turn, finish_reason=resp["choices"][0].get("finish_reason"), usage=resp.get("usage"),
            content_chars=len(content), reasoning_chars=len(msg.get("reasoning_content") or msg.get("reasoning") or ""))
        tool_calls = msg.get("tool_calls") or []
        if use_native and tool_calls:
            messages.append(msg)
            for tc in tool_calls:
                fn = tc["function"]
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                status, body = call_tool(fn["name"], args)
                calls += 1
                rec("tool", turn=turn, tool=fn["name"], args=args, status=status, result=body[:2000])
                messages.append({"role": "tool", "tool_call_id": tc["id"], "content": f"HTTP {status}\n{body}"})
            continue
        pc = parse_prompt_call(content) if not use_native else None
        if pc and pc[0]:
            name, args = pc
            messages.append({"role": "assistant", "content": content})
            key = json.dumps([name, args], sort_keys=True)
            if key == last_key:
                status, body = last_result
                repeats += 1
                rec("tool_repeat", turn=turn, tool=name, status=status, repeats=repeats)
                if repeats >= MAX_REPEATS:
                    messages.append({"role": "user", "content": f"You have repeated the identical {name} call {repeats} times; the result will not change. STOP calling tools. Write the final proposal now, ending with the PLAN_JSON line."})
                else:
                    messages.append({"role": "user", "content": f"TOOL RESULT {name} HTTP {status} (IDENTICAL call repeated — result unchanged; change the arguments or move on)\n{body}"})
                continue
            repeats = 0
            status, body = call_tool(name, args)
            calls += 1
            last_key, last_result = key, (status, body)
            rec("tool", turn=turn, tool=name, args=args, status=status, result=body[:2000])
            messages.append({"role": "user", "content": f"TOOL RESULT {name} HTTP {status}\n{body}"})
            continue
        ok, why, priced = check_plan(content, goal["awbs"][0]["final_dest"], sum(a["chargeable_kg"] for a in goal["awbs"]))
        rec("plan_check", turn=turn, ok=ok, why=why, priced=priced)
        if not ok and fixes < MAX_PLAN_FIXES and turn < MAX_TURNS:
            fixes += 1
            messages.append({"role": "assistant", "content": content})
            messages.append({"role": "user", "content": f"PLAN CHECK FAILED: {why}\nRevise: call allocate/cost as needed, then give the full final answer again with a corrected ```plan block."})
            continue
        rec("final", turn=turn, tool_calls=calls, plan_ok=ok, plan_priced=priced, answer=content)
        print(content)
        print(f"\n[plan_ok={ok} {why}]", file=sys.stderr)
        print(f"\n[turns={turn} tool_calls={calls} protocol={'native' if use_native else 'prompt'} log={log_path}]", file=sys.stderr)
        return 0
    rec("error", error="no final answer within budget")
    return 1


if __name__ == "__main__":
    a = sys.argv[1:]
    goal = a[0] if a else "scenarios/s1_hub_gdp/goal.json"
    logp = a[a.index("--log") + 1] if "--log" in a else f"logs/run-{int(time.time())}.jsonl"
    sys.exit(run(goal, logp))
