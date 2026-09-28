# Scenario 1 (JFK GDP, 40 AWBs, 19,440 kg, cutoff 09-30 18:00Z, cap 95,000 USD)

All rows priced by the same POST /cost call (awb_count=40, final_dest=LHR, total_kg=19440; handling per AWB per leg is crude but identical across rows).

| plan | total_usd (joint call) | final_arrival | cutoff_ok | slack_h | legs | all 19,440 kg delivered |
|---|---|---|---|---|---|---|
| do_nothing | 49,440 | 2026-09-30T22:00 | False | -4.0 | 4 | yes (but late) |
| rule_split_greedy | 72,938 | 2026-09-30T15:00 | True | 3.0 | 10 | yes |
| agent_nemotron3_super | 60,677 | 2026-09-30T15:00 | True | 3.0 | 8 | yes |
| agent_qwen38_run_O | 60,692 | 2026-09-30T15:00 | True | 3.0 | see log | yes |

- agent_nemotron3_super: logs/dryrun-s1-nemo-super3.jsonl — nvidia/nemotron-3-super-120b-a12b via build.nvidia.com, native tool calling, 12 turns, 10 tool calls, 309 s. Routes: 4 direct JFK-LHR flights + 2 truck-feeder chains via EWR (UAL16, BAW188). Verified by the loop (plan_check ok) and re-verified here.
- Local qwen38 (thinking off, prompt protocol): 15 runs, 1 complete plan (run O, logs/dryrun-s1-o.jsonl, after route-aware allocate + coverage check); 14 failed. Earlier row "agent_dryrun_D 55,712" was withdrawn: it delivered only 14,440 kg.
- Caveat: PLAN_JSON is kg-level per option. The AWB-by-AWB listing in the prose is NOT validated; the Nemotron answer lists some AWB numbers twice. Next step: AWB-level validation from allocate's assignment.
- Rule baseline (earliest-arrival greedy with splitting) is complete but 20 % dearer than the agent plan because it fills expensive early truck+air chains first.
