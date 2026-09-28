# Recovery Plan Proposal — 40 AWBs to LHR (cutoff 2026-09-30T18:00Z, budget ≤ $95,000)

> **Status: PROPOSAL for human approval. Nothing has been booked.**
> Note: the `cost` tool returned HTTP 500 on every attempt, so all dollar figures below are **derived from schedule rates × kg** (rate × chargeable kg), not from a cost-tool confirmation. Treat totals as estimates pending a working cost check.

## 1) Situation (what the tools showed)
- **JFK NAS status (synthetic):** Active **GDP** — "LOW CEILINGS / WIND, PROGRAM RATE 30", **avg delay 2h50m, max 4h10m**. Plus general departure delays 1–3h, trend *increasing*. No closures/ground stops.
- **KJFK weather:** METAR MVFR (BR, 6SM, OVC027). TAF shows **rain + low ceilings through ~2912Z**, improving to P6SM/OVC025 by 2905Z and P6SM/OVC035 by 2911Z. No SIGMET/AIRMET. → The GDP is weather-driven and expected to ease late 29th/early 30th.
- **JFK→LHR air options (remaining capacity / rate):**
  - KAL251-0929: dep 29T22:50Z → arr 30T05:50Z, **4,200 kg @ $2.10**
  - BAW174-0929: dep 30T01:05Z → arr 30T08:05Z, **3,800 kg @ $2.25**
  - BAW112-0929: dep 30T02:00Z → arr 30T09:00Z, **1,500 kg @ $3.40**
  - VIR004-0930: dep 30T08:00Z → arr 30T15:00Z, **6,000 kg @ $2.60**
- **JFK→FRA:** DLH405-0929 dep 30T01:40Z → arr 30T09:40Z, **5,000 kg @ $1.95**.
- **FRA→LHR:** BAW903-0930 dep 30T12:00Z → arr 30T14:00Z, **1,200 kg @ $1.60** (only 1,200 kg — far short of the 6,760 kg DLH group).

## 2) Options considered (cost / arrival / cutoff)
| Option | Arrival LHR | Cutoff 18:00Z? | Est. cost (rate×kg) |
|---|---|---|---|
| KAL251-0929 (4,200 kg) | 30T05:50Z | ✅ 12h10m slack | 4,200×2.10 = **$8,820** |
| BAW174-0929 (3,800 kg) | 30T08:05Z | ✅ 9h55m slack | 3,800×2.25 = **$8,550** |
| BAW112-0929 (1,500 kg) | 30T09:00Z | ✅ 9h00m slack | 1,500×3.40 = **$5,100** |
| VIR004-0930 (6,000 kg) | 30T15:00Z | ✅ 3h00m slack | 6,000×2.60 = **$15,600** |
| DLH405→FRA + BAW903→LHR | 30T14:00Z | ✅ 4h00m slack | but FRA→LHR cap only 1,200 kg vs 6,760 kg needed → **infeasible for full group** |

Total direct JFK→LHR capacity = 4,200+3,800+1,500+6,000 = **15,500 kg**, vs **19,440 kg** total. **Shortfall ≈ 3,940 kg** that cannot be moved direct by the cutoff.

## 3) Recommended plan per AWB group
**Group A — KAL251 (14 AWBs, 6,920 kg):**
- Load **4,200 kg** on **KAL251-0929** (arr 05:50Z).
- Remaining **2,720 kg** → **VIR004-0930** (arr 15:00Z).
- Keep group together where possible; split only because KAL251 capacity (4,200) < group weight (6,920).

**Group B — BAW174 (13 AWBs, 5,760 kg):**
- Load **3,800 kg** on **BAW174-0929** (arr 08:05Z).
- Remaining **1,960 kg** → **VIR004-0930** (arr 15:00Z).

**Group C — DLH405 (13 AWBs, 6,760 kg):**
- Load **5,000 kg** on **DLH405-0929** to FRA (arr 09:40Z).
- FRA→LHR BAW903-0930 has only **1,200 kg** → move **1,200 kg** to LHR (arr 14:00Z).
- **Remaining 5,560 kg cannot reach LHR by 18:00Z via the only FRA→LHR option.** → **Escalate to human:** need an additional FRA→LHR (or FRA→LHR via another carrier) capacity, or re-route the residual direct JFK→LHR on VIR004-0930 if space allows (VIR004 has 6,000 kg; after Groups A+B residual 4,680 kg, only ~1,320 kg left — still short).

**Estimated total spend (direct legs only, excl. unresolved residual):**
- KAL251 4,200×2.10 = $8,820
- BAW174 3,800×2.25 = $8,550
- VIR004 4,680×2.60 = $12,168
- DLH405 5,000×1.95 = $9,750
- BAW903 1,200×1.60 = $1,920
- **Subtotal ≈ $41,208** — well under $95,000, leaving headroom for premium/spot capacity to close the ~3,940 kg gap.

## 4) Risks and what would change the decision
- **GDP max delay 4h10m:** KAL251 (29T22:50Z) and BAW174 (30T01:05Z) departures could slip; if KAL251 slips past ~30T06:00Z arrival, its 12h slack absorbs it, but BAW112/VIR004 slack is thinner. **If the GDP extends past 2912Z (TAF improvement), re-check departures before committing.**
- **VIR004-0930 is the single largest lever (6,000 kg, arr 15:00Z, only 3h slack):** any >3h delay breaches cutoff. **If VIR004 is at risk, shift its load earlier to BAW112-0929 (1,500 kg @ $3.40) and/or secure earlier FRA→LHR capacity.**
- **Capacity shortfall (~3,940 kg):** the plan as priced does NOT move all 40 AWBs by cutoff. **Decision changes if:** (a) additional FRA→LHR capacity is confirmed, or (b) a premium direct JFK→LHR option appears, or (c) the consignee accepts a partial late delivery for the residual.
- **Cost tool unavailable (HTTP 500):** all totals are rate×kg estimates; **re-run `cost` before approval** to confirm totals and `meets_cutoff`/`slack_hours`.
- **Largest single AWB 1,100 kg** (in each group): ensure no per-piece/ULD limit blocks it on the chosen flight.

## 5) Tools called
- `nas_status` (JFK) — GDP + delays confirmed
- `wx` (KJFK) — METAR/TAF, weather-driven GDP, improving late 29th
- `schedule` (JFK→LHR air) — 4 options
- `schedule` (FRA→LHR air) — 1 option (1,200 kg)
- `schedule` (JFK→FRA air) — 1 option (5,000 kg)
- `cost` — **failed (HTTP 500) on all attempts**; no cost-tool confirmation obtained

**Bottom line:** Direct JFK→LHR capacity covers ~15,500 of 19,440 kg within budget and cutoff. **Approve the direct legs now, and I need a human decision on the ~3,940 kg residual** (extra FRA→LHR capacity, premium direct, or partial late delivery) before this is a complete recovery.
