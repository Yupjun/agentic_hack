"""API server (port 8091): guarded LLM gateway + read-only data for the dashboard.

  POST /llm/v1/chat/completions   OpenAI-compatible, NeMo Guardrails in the path (api/llm_gateway.py)
  GET  /api/health
  (dashboard routes are added in api/data.py)
"""
from __future__ import annotations

import os
import sys
import warnings

warnings.filterwarnings("ignore")
import logging  # noqa: E402
logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logging.getLogger("nemoguardrails.guardrails").setLevel(logging.INFO)   # "Tool call blocked: ..." lines are the evidence of a rail firing
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi import FastAPI  # noqa: E402

from api.llm_gateway import router as gateway  # noqa: E402

app = FastAPI(title="cargo-recovery-agent v2 API", version="0.2")
app.include_router(gateway)

try:
    from api.data import router as data  # noqa: E402
    app.include_router(data)
except ImportError:
    pass

from api.dag import router as dag  # noqa: E402
app.include_router(dag)


@app.get("/api/health")
def health():
    return {"ok": True, "nvidia_key_set": bool(os.environ.get("NVIDIA_API_KEY")), "guardrails_config": "agent/guardrails/config.yml"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("CARGO_API_PORT", "8091")))
