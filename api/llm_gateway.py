"""OpenAI-compatible LLM gateway with NeMo Guardrails (IORails) in the path.

    agent (NAT tool_calling_agent) --> POST /llm/v1/chat/completions --> Guardrails IORails --> Nemotron (NIM API)
                                                                        |  tool call validation:
                                                                        |  only declared tools, schema-valid args
The agent does not know Guardrails exists; policy sits in one place (Rule of Separation).
Every request and every block is journaled (event llm_call / guardrail_block).
Configuration: agent/guardrails/config.yml. Key: NVIDIA_API_KEY in the environment.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
import uuid

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from engine import journal

router = APIRouter()
RETRIES = int(os.environ.get("CARGO_GATEWAY_RETRIES", "3"))
_G = None
CFG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agent", "guardrails")


async def _guardrails():
    global _G
    if _G is None:
        from nemoguardrails import RailsConfig
        from nemoguardrails.guardrails.guardrails import Guardrails
        _G = Guardrails(RailsConfig.from_path(CFG), require_iorails=True)
    return _G


def _args_str(a) -> str:
    return a if isinstance(a, str) else json.dumps(a or {}, ensure_ascii=False)


@router.post("/llm/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    stream = bool(body.get("stream"))   # answered AFTER all rails ran: one SSE chunk, then [DONE]
    if not os.environ.get("NVIDIA_API_KEY"):
        raise HTTPException(status_code=503, detail="NVIDIA_API_KEY is not set for the gateway process")
    g = await _guardrails()
    t = time.time()
    tools = body.get("tools") or []
    llm_params = {k: body[k] for k in ("tools", "tool_choice", "max_tokens", "temperature", "top_p") if k in body}
    msgs = []
    for m in body.get("messages", []):
        m = dict(m)
        if m.get("tool_calls"):
            m["tool_calls"] = [{**tc, "function": {**tc["function"], "arguments": json.loads(tc["function"]["arguments"]) if isinstance(tc["function"].get("arguments"), str) and tc["function"]["arguments"] else (tc["function"].get("arguments") or {})}} for tc in m["tool_calls"]]
        msgs.append(m)
    r, last = None, None
    for attempt in range(RETRIES + 1):   # transient upstream 5xx/429: retry with backoff (found 2026-09-28: one HTTP 500 ended a session)
        try:
            r = await g.generate_async(messages=msgs, options={"llm_params": llm_params, "log": {"activated_rails": True}})
            break
        except Exception as e:  # noqa: BLE001 — upstream failure is reported, not hidden
            last = e
            transient = any(code in str(e) for code in ("HTTP 500", "HTTP 502", "HTTP 503", "HTTP 504", "HTTP 429", "Timeout", "timed out"))
            journal.append("llm_call", ok=False, attempt=attempt, transient=transient, error=f"{type(e).__name__}: {str(e)[:300]}", seconds=round(time.time() - t, 3))
            if not transient or attempt == RETRIES:
                raise HTTPException(status_code=502, detail=f"guarded upstream failed after {attempt + 1} attempt(s): {type(e).__name__}: {str(e)[:300]}")
            await asyncio.sleep(2 ** (attempt + 1))
    content = ""
    if getattr(r, "response", None):
        content = r.response[-1].get("content") or ""
    tcs = getattr(r, "tool_calls", None) or []
    # Which rail stopped the turn: IORails' generation log names it (type input / output / tool_output, stop=True).
    # Fallback when no log: the fixed refusal text means a block (iorails._blocked_message).
    from nemoguardrails.guardrails import iorails as _io
    blocked = []
    log = getattr(r, "log", None)
    for ar in (getattr(log, "activated_rails", None) or []):
        if getattr(ar, "stop", False):
            blocked.append(f"{getattr(ar, 'type', '?')}: {getattr(ar, 'name', '?')}")
    if not blocked and content and content in {getattr(_io, "REFUSAL_MESSAGE", None), getattr(_io, "INTERNAL_ERROR_MESSAGE", None)}:
        blocked.append("unknown rail (refusal text)")
    msg = {"role": "assistant", "content": content or None}
    if tcs:
        msg["tool_calls"] = [{"id": tc.get("id") or f"call_{uuid.uuid4().hex[:12]}", "type": "function",
                              "function": {"name": tc["function"]["name"], "arguments": _args_str(tc["function"].get("arguments"))}} for tc in tcs]
    finish = "tool_calls" if tcs else "stop"
    names = [tc["function"]["name"] for tc in tcs]
    journal.append("llm_call", ok=True, model=body.get("model"), n_messages=len(msgs), n_tools_declared=len(tools), tool_calls=names,
                   blocked_rails=blocked, seconds=round(time.time() - t, 3), session=os.environ.get("CARGO_SESSION", ""))
    if blocked:
        journal.append("guardrail_block", rails=blocked, content=(content or "")[:300])
    cid, created, model = f"chatcmpl-{uuid.uuid4().hex[:16]}", int(time.time()), body.get("model", "guarded")
    if stream:
        delta = {"role": "assistant", "content": msg["content"] or ""}
        if tcs:
            delta["tool_calls"] = [{"index": i, **tc} for i, tc in enumerate(msg["tool_calls"])]

        def sse():
            yield "data: " + json.dumps({"id": cid, "object": "chat.completion.chunk", "created": created, "model": model,
                                         "choices": [{"index": 0, "delta": delta, "finish_reason": None}]}, ensure_ascii=False) + "\n\n"
            yield "data: " + json.dumps({"id": cid, "object": "chat.completion.chunk", "created": created, "model": model,
                                         "choices": [{"index": 0, "delta": {}, "finish_reason": finish}]}) + "\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(sse(), media_type="text/event-stream")
    return {"id": cid, "object": "chat.completion", "created": created, "model": model,
            "choices": [{"index": 0, "message": msg, "finish_reason": finish}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}}
