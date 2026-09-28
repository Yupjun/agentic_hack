# Recovery Plan Proposal — 40 AWBs to LHR (cut-off 2026-09-30T18:00Z, budget ≤ $95,000)

## 1) Situation (what the tools showed)
- **JFK NAS (synthetic):** Active **GDP** — program rate 30, **avg delay 2h50m, max 4h10m** (low ceilings/wind). General departure delays 1–3h, trend *increasing*. No closures/ground stops.
- **KJFK weather:** MVFR, drizzle/br, 5SM; TAF shows rain and low ceilings through the night, improving after ~22:00Z. Consistent with the GDP.
- **Capacity reality:** The three originally-booked flights (KAL251, BAW174, DLH405) are the only direct/origin options, and their remaining capacity (4,200 / 3,800 / 5,000 kg) is **less than the cargo each group was booked on** (6,920 / 5,760 / 6,760 kg). So every group must be **split** across the option set.
- **Only LHR-arriving options before cut-off:** KAL251-0929 (arr 05:50Z), BAW174-0929 (08:05Z), BAW112-0929 (09:00Z), VIR004-0930 (15:00Z). The FRA route (DLH405→FRA 09:40Z) only reaches LHR via **BAW903-0930 (arr 14:00Z, 1,200 kg cap)** or **TRK-FRA-LHR (arr 22:00Z — misses cut-off)**.

## 2) Options considered (cost / arrival / cut-off)
| Option | Route | Arrive LHR | Cap (kg) | $/kg | Meets 18:00Z? |
|---|---|---|---|---|---|
| KAL251-0929 | JFK→LHR | 05:50Z | 4,200 | 2.10 | ✅ |
| BAW174-0929 | JFK→LHR | 08:05Z | 3,800 | 2.25 | ✅ |
| BAW112-0929 | JFK→LHR | 09:00Z | 1,500 | 3.40 | ✅ |
| VIR004-0930 | JFK→LHR | 15:00Z | 6,000 | 2.60 | ✅ (3h slack) |
| DLH405-0929 | JFK→FRA | 09:40Z (FRA) | 5,000 | 1.95 | needs 2nd leg |
| BAW903-0930 | FRA→LHR | 14:00Z | 1,200 | 1.60 | ✅ (4h slack) |
| TRK-FRA-LHR | FRA→LHR | 22:00Z | 20,000 | 0.35 | ❌ (−4h) |

## 3) Recommended plan per AWB group
**Group A — KAL251 (14 AWBs, 6,920 kg):**
- KAL251-0929: 4,140 kg (5 AWBs: 31003699, 31000411, 31000822, 31001233, 31002877)
- BAW174-0929: 2,780 kg (9 AWBs: 31001644, 31004932, 31002055, 31002466, 31004521, 31000000, 31003288, 31004110, 31005343)

**Group B — BAW174 (13 AWBs, 5,760 kg):**
- BAW174-0929: 1,000 kg (2 AWBs: 31000959, 31003425)
- BAW112-0929: 1,480 kg (2 AWBs: 31004247, 31002603)
- VIR004-0930: 3,280 kg (9 AWBs: 31001781, 31002192, 31003014, 31003836, 31005069, 31000137, 31000548, 31001370, 31004658)

**Group C — DLH405 (13 AWBs, 6,760 kg):**
- DLH405-0929 → FRA: 5,000 kg (7 AWBs: 31001096, 31004384, 31001507, 31003973, 31002329, 31003562, 31002740)
- VIR004-0930 (direct JFK→LHR): 1,760 kg (6 AWBs: 31005206, 31000274, 31003151, 31004795, 31000685, 31001918)

**Option-level totals:** KAL251 4,140/4,200 · BAW174 3,780/3,800 · BAW112 1,480/1,500 · VIR004 5,040/6,000 · DLH405 5,000/5,000. **No capacity violations; all 40 AWBs placed.**

**Cost (direct-LHR legs only, 34 AWBs):** $60,135 — well under $95,000.

## 4) Risks and what would change the decision
- **The 7 AWBs on DLH405 (5,000 kg) are the problem.** They land at FRA 09:40Z, but the only FRA→LHR air leg (BAW903) caps at **1,200 kg**, and the FRA→LHR truck arrives **22:00Z (misses cut-off by 4h)**. The cost tool confirms: any plan routing these 5,000 kg via FRA is **feasible=false / meets_cutoff=false** (final arrival 22:00Z).
- **Decision point for the human:**
  1. **Preferred (keeps all 40 on-time, within budget):** Move the 7 DLH405 AWBs off FRA onto **VIR004-0930 direct JFK→LHR**. VIR004 has 6,000 kg cap; current plan uses 5,040 kg, so it can absorb up to ~960 kg more — **not enough for all 5,000 kg**. So this requires either (a) additional VIR004/next-day LHR capacity, or (b) accepting that ~4,000 kg of Group C cannot make 18:00Z on the current option set.
  2. **If FRA routing is kept:** only 1,200 kg can follow BAW903 to LHR by 14:00Z; the remaining 3,800 kg would need a later LHR arrival (truck 22:00Z) → **cut-off breach**.
- **GDP risk:** avg 2h50m / max 4h10m delays at JFK. VIR004-0930 (dep 08:00Z, arr 15:00Z) has only **3h slack** — a max GDP delay could push it past 18:00Z. KAL251/BAW174/BAW112 depart earlier and have more buffer.
- **What changes the decision:** (a) confirmation of extra LHR capacity on VIR004 or a 2nd LHR flight; (b) a later FRA→LHR air leg with ≥3,800 kg; (c) consignee agreeing to a 22:00Z dock slot for the FRA-truck portion; (d) GDP lifting (weather improves after ~22:00Z per TAF).

## 5) Tools called
nas_status (JFK) · wx (KJFK) · schedule (JFK→LHR) · schedule (JFK→FRA) · schedule (JFK all) · schedule (FRA→LHR) · allocate (×3, per group) · cost (multiple).

> **Note:** This is a **proposal** for approval — nothing has been booked. The 34 AWBs on direct LHR legs are fully costed and feasible ($60,135, all before cut-off). The 7 DLH405 AWBs (5,000 kg) **cannot** be confirmed to LHR before 18:00Z on the current option set and require a human decision (extra LHR capacity vs. FRA routing vs. cut-off exception).
