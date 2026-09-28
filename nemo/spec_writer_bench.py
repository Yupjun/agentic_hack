"""NeMo Evaluator benchmark: can a model turn a planning request into the right plan spec?

Dataset: nemo/data/sft_test.jsonl (281 held-out requests after NeMo Curator; labels correct by
construction). A response is CORRECT when its JSON {"base", "params"} generates exactly the same
spec as the label (semantic match, not string match; same rule as eval/agent_eval.py).
Also reported: valid_json (parsable, known base) and applicable (the generator accepts the params).

  source ~/.config/nvidia/env && .venv/bin/nel eval run --bench nemo/spec_writer_bench.py:spec-writer \
     --model-url https://integrate.api.nvidia.com/v1 --model-id nvidia/nemotron-3-super-120b-a12b \
     --api-key "$NVIDIA_API_KEY" --max-problems 60 -o nemo/eval-out
The same benchmark scores a LoRA spec-writer later (NeMo AutoModel, not trained yet).
"""
from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from nemo_evaluator.environments.custom import benchmark, scorer  # noqa: E402
from nemo_evaluator.scoring import ScorerInput  # noqa: E402

from nemo.make_sft_data import SYSTEM  # noqa: E402

_BASES = {b: json.load(open(os.path.join(ROOT, "scenarios", "examples", f"{b}.json"))) for b in ("s1_base", "s2_base")}


def _rows() -> list[dict]:
    out = []
    for line in open(os.path.join(ROOT, "nemo", "data", "sft_test.jsonl"), encoding="utf-8"):
        m = json.loads(line)["messages"]
        out.append({"request": m[1]["content"], "target": m[2]["content"]})
    return out


def _parse(text: str):
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S)
    m = re.findall(r"\{.*\}", text, flags=re.S)
    if not m:
        return None
    for cand in (m[-1], m[0]):
        try:
            return json.loads(cand)
        except json.JSONDecodeError:
            continue
    return None


def _spec(d: dict):
    from scenarios.gen import generate
    return generate(_BASES[d["base"]], d.get("params") or {}, 0, new_id="x")


# SYSTEM contains literal JSON braces; they must be doubled or the {request} placeholder is never
# filled (found 2026-09-28: the first run sent "Request: {request}" verbatim and scored 0/40).
PROMPT = SYSTEM.replace("{", "{{").replace("}", "}}") + "\n\nRequest: {request}\nAnswer with the JSON only."
assert "{request}" in PROMPT.format(request="{request}")


@benchmark(name="spec-writer", dataset=_rows, prompt=PROMPT, target_field="target")
@scorer
def spec_writer_scorer(sample: ScorerInput) -> dict:
    got = _parse(sample.response)
    want = json.loads(sample.target)
    valid = isinstance(got, dict) and got.get("base") in _BASES
    applicable = correct = False
    if valid:
        try:
            g = _spec(got)
            applicable = True
            correct = g == _spec(want)
        except (ValueError, KeyError, TypeError):
            pass
    return {"correct": correct, "valid_json": valid, "applicable": applicable, "extracted": json.dumps(got, ensure_ascii=False)[:300] if got else None}
