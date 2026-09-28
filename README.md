# Cargo Planner — an order-and-transport planning agent

Give it a goal in your own words ("100 units of C from A to B within 30 days, 40,000 USD"; "site A3 is ten days
late on every order"). The agent turns the goal into a **plan spec** (data), a fixed engine solves it
(MILP + Monte Carlo), an independent verifier re-checks every plan, and the agent **proposes** one of four
verified plans — cost-optimal, time-optimal, balanced, risk-adjusted. It cannot book, order or send anything;
that is enforced by NeMo Guardrails, not by the prompt.

The goods are temperature-sensitive, short-shelf-life and high-value: lots, a minimum remaining shelf life at
receipt, temperature bands, qualified lanes, exposure time outside control, MOQ, months of supply, production
lead times, and approved (single) suppliers. All data is synthetic; public feeds (FAA NAS status,
aviationweather.gov, ADS-B, GDACS) are live.

## Stack

| Layer | What | NVIDIA |
|---|---|---|
| Agent | `agent/nat_planner` — `tool_calling_agent` workflow, 7 tools, LLM roles as data | **NeMo Agent Toolkit** (`nvidia-nat` 1.9) |
| Policy | `api/llm_gateway.py` + `agent/guardrails/` — OpenAI-compatible gateway, tool-call allowlist + schema check | **NeMo Guardrails** 0.24 (IORails) |
| Models | planner: Nemotron 3 Super 120B-A12B (build.nvidia.com); local fallback qwen38 (vLLM) | **Nemotron 3**, **NIM API** |
| Engine | `planner/` grammar + validator, `engine/` candidates → MILP → verify → Monte Carlo → Pareto | **cuOpt** backend via PuLP (GPU box), HiGHS on CPU |
| Data | `nemo/` synthetic goal→spec data, curation, benchmark | **NeMo Curator** 1.3, **NeMo Evaluator** 0.3 |
| Dashboard | `web/` Next.js 15, Signal on Paper tokens, design guard | |

## Run

```bash
dev/run-all.sh            # API :8091 (guarded gateway + data) and dashboard :3200
dev/run-all.sh --replay   # + re-solve the S1 scenarios and compare with the committed numbers
dev/run-all.sh --stop
```
Needs `.venv` (a symlink to `<venv>`, Python 3.13 with `--system-site-packages`) and the
NVIDIA key in `~/.config/nvidia/env` (`export NVIDIA_API_KEY=...`; never committed, never printed).

```bash
.venv/bin/python -m engine.run solve scenarios/examples/s1_base.json      # four verified plans for one spec
.venv/bin/python -m eval.compare_v2                                        # all 11 pre-registered scenarios vs rule baselines
.venv/bin/python -m agent.run_agent "C 제품 100개를 A에서 B로 30일 안에, 예산 4만 달러"   # one agent session
.venv/bin/python -m eval.agent_eval                                        # six goals, checked against the bank
.venv/bin/nel eval run nemo/eval_super.yaml                               # NeMo Evaluator spec-writer benchmark
CUDA_VISIBLE_DEVICES= .venv/bin/python -m nemo.curate                      # NeMo Curator pipeline (CPU)
.venv/bin/python -m unittest discover -s tests                             # grammar, verify, engine, guardrails, tools
```

## Layout

```
planner/    plan/v1 grammar (pydantic), validate() -> problems, structure_key, CLI
engine/     options (candidates), lp (MILP), verify (independent), mc (torch), pareto, run, journal
scenarios/  examples/ (hand-authored bases), gen.py (variant = base + params), bank/ (pre-registered), judge.py
agent/      planner_tools.py (plain tools), nat_planner/ (NAT plugin + planner.yml), guardrails/, run_agent.py
api/        app.py (:8091), llm_gateway.py (Guardrails), data.py (dashboard routes)
eval/       baseline_v2 (rules), compare_v2, agent_eval, rescore, replay_check; results *.md / *.json
nemo/       make_sft_data, curate (Curator), spec_writer_bench (Evaluator), eval_*.yaml
web/        dashboard; scripts/verify-design.mjs
dev/        run-all.sh, screenshots.py, STATUS.md (unattended session log)
docs/       screens/ (1512x982, 1920x1080), demo-script.md
v1 (kept):  tools/ (FastAPI public-feed tools on :8090), agent/loop.py, scenarios/s1_hub_gdp
```

## What is not done

- NeMo AutoModel LoRA of a small spec-writer: deferred (the data and the benchmark are ready).
- cuOpt: installed and wired (`CARGO_LP_BACKEND=cuopt`), not run — this server's GPUs are off-limits.
- NemoClaw / OpenShell sandbox: needs Docker or Podman, not available to this account.
- Login on the dashboard: both servers bind 127.0.0.1 only.
