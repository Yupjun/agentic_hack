# Recovery Plan Proposal — 40 AWBs to LHR (cut-off 2026-09-30T18:00Z)

## 1) Situation (what the tools showed)
- **JFK NAS status:** Active **GDP** (synthetic) — program rate 30, **avg delay 2h50m, max 4h10m**; general departure delays 1–3h, trend *increasing*. No closures/ground stops.
- **KJFK weather:** MVFR, low ceilings (BKN011/OVC018), drizzle/brk, 5SM; TAF shows continued low cigs/precip through the night, improving late 29th. This is the driver of the GDP.
- **Direct JFK→LHR capacity (all legs):** KAL251-0929 (4,200 kg, arr 05:50), BAW174-0929 (3,800 kg, arr 08:05), BAW112-0929 (1,500 kg, arr 09:00), VIR004-0930 (6,000 kg, arr 15:00). **Total = 15,500 kg.**
- **JFK→FRA→LHR route:** DLH405-0929 (5,000 kg, arr FRA 09:40) + BAW903-0930 (1,200 kg, arr LHR 14:00) + TRK-FRA-LHR (20,000 kg, arr LHR 22:00).
- **Total cargo = 19,440 kg.** Direct LHR capacity (15,500) + FRA air (5,000) = 20,500 kg, so all cargo *can* be moved, but the FRA→LHR air leg (BAW903) only holds 1,200 kg.

## 2) Options considered (cost / arrival / cut-off)
| Plan | Legs (kg) | Total USD | Final arrival | Meets 18:00Z cut-off? |
|---|---|---|---|---|
| A — all air, FRA split 1,200 air + 560 truck | KAL 4200 / BAW174 3800 / BAW112 1500 / VIR 6000 / DLH 5000 / BAW903 1200 / TRK 560 | **61,736** | 22:00Z | **NO (−4h)** |
| B — all air, FRA 1,760 on BAW903 | same but BAW903 1760 | 61,436 | 15:00Z | YES, but **capacity violation** (1,760 > 1,200) → invalid |
| C — all air, FRA 1,200 air + 560 truck (same as A) | — | 61,736 | 22:00Z | NO |

**Key finding:** Every plan that keeps all 40 AWBs on schedule **before 18:00Z** requires the 560 kg FRA overflow to fly BAW903, which exceeds its 1,200 kg capacity (violation). The only capacity-clean way to move that 560 kg is the FRA→LHR **truck**, which arrives **22:00Z — 4h after cut-off**.

## 3) Recommended plan per AWB group (PROPOSAL — nothing booked)
Because no capacity-clean plan meets the 18:00Z cut-off for all 40 AWBs, I recommend the **lowest-cost, capacity-clean plan (A, $61,736)** and flag the 560 kg shortfall for a decision:

- **KAL251 group (14 AWBs, 6,920 kg):** 4,200 kg on **KAL251-0929** (arr 05:50Z); remaining 2,720 kg rebooked to **VIR004-0930** (arr 15:00Z).
- **BAW174 group (13 AWBs, 5,760 kg):** 3,800 kg on **BAW174-0929** (arr 08:05Z); remaining 1,960 kg to **VIR004-0930** (arr 15:00Z).
- **DLH405 group (13 AWBs, 6,760 kg):** 5,000 kg on **DLH405-0929** → FRA (arr 09:40Z); 1,200 kg on **BAW903-0930** → LHR (arr 14:00Z); **560 kg on TRK-FRA-LHR** (arr 22:00Z).
- VIR004-0930 total load = 2,720 + 1,960 = 4,680 kg ≤ 6,000 kg ✓.

**Total: $61,736 (within $95,000 budget).** 39 of 40 AWB-groups' cargo arrives before cut-off; the 560 kg FRA truck overflow arrives 22:00Z.

## 4) Risks and what would change the decision
- **Cut-off breach (primary risk):** 560 kg arrives 22:00Z, 4h late. If the consignee hard-requires 18:00Z, this plan fails for that portion.
- **GDP escalation:** avg 2h50m / max 4h10m and *increasing* trend. If the GDP extends into the 30th, VIR004-0930 (dep 08:00Z) and BAW903 could slip past cut-off. **Mitigation:** prioritize loading the 560 kg overflow and the BAW903 cargo first; monitor NAS feed.
- **What would change the decision:**
  - If a **second FRA→LHR air leg** (or a later BAW903 with ≥560 kg) becomes available, move the 560 kg to air → all 40 AWBs meet cut-off (cost rises modestly, still well under $95k).
  - If the consignee **accepts a 22:00Z delivery** for the 560 kg, plan A stands as-is.
  - If the **GDP clears by the 30th**, the direct LHR legs (esp. VIR004) gain reliability and the FRA truck overflow could be re-routed direct.
  - If **budget were the only constraint** (not cut-off), plan A is already the cheapest capacity-clean option.

## 5) Tools called
1. `nas_status` (JFK) — GDP + delays
2. `wx` (KJFK) — METAR/TAF/forecast
3. `schedule` (JFK→LHR)
4. `schedule` (JFK→FRA)
5. `schedule` (FRA→LHR)
6. `schedule` (JFK, all legs)
7. `schedule` (EWR→LHR)
8. `schedule` (BOS→LHR)
9. `cost` (multiple candidate plans)

**Note:** This is a proposal for human approval — no bookings were made. The 560 kg FRA→LHR overflow is the single item that cannot meet the 18:00Z cut-off on current capacity; please confirm whether to (a) accept the 22:00Z truck arrival, (b) source additional FRA→LHR air capacity, or (c) re-route that 560 kg direct to LHR.
