# cargo-recovery-agent

Hackathon prototype: an agent that takes a cargo goal ("get these shipments to the
consignee before cut-off under a spend cap"), watches the disruption sources
(FAA NAS status, aviation weather, ADS-B, AIS, hazards), enumerates recovery options
(later flight, truck to a neighbouring hub, sea-air switch), prices them and proposes
a plan. It proposes; a human approves. Nothing is booked.

Not connected to any company system or data. All feeds are public; capacity and
rates are synthetic scenario files.

## Layout
- `tools/` one small HTTP service per tool (FastAPI). `python -m tools.serve` mounts all on :8090.
- `agent/` planner loop (`python -m agent.loop scenarios/s1_hub_gdp/goal.json`) — OpenAI-compatible chat endpoint, native or prompt tool protocol.
- `scenarios/` goal + synthetic shipments/options/rates + optional NAS override for replay.
- `logs/` JSONL trace of every run (what was called, with what, what came back).

## Run
```bash
export SCENARIO_DIR=$PWD/scenarios/s1_hub_gdp NAS_OVERRIDE_FILE=$PWD/scenarios/s1_hub_gdp/nas_override.json
python -m tools.serve &            # :8090
python -m agent.loop scenarios/s1_hub_gdp/goal.json
```
Model endpoint: `LLM_BASE_URL` (default `http://127.0.0.1:8001/v1`), `LLM_MODEL` (default `qwen38`).
For an NVIDIA NIM: `LLM_BASE_URL=http://<nim>:8000/v1 LLM_MODEL=<nemotron id> TOOL_PROTOCOL=native`.

## Keys (optional, loud 503 without them)
- `AISSTREAM_API_KEY` — vessel positions (aisstream.io, free registration)
- `FAA_NOTAM_CLIENT_ID` / `FAA_NOTAM_CLIENT_SECRET` — NOTAMs (api.faa.gov, registration)
