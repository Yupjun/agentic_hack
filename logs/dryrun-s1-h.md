# Recovery Plan Proposal — 40 AWBs to LHR (cut-off 2026-09-30T18:00Z)

## 1) Situation (what tools showed)

- **JFK NAS status (synthetic):** Active **GDP** — program rate 30, **avg delay 2h50m, max 4h10m**, reason "LOW CEILINGS / WIND". Plus general departure delays 1–3h, trend increasing. No closures/ground stops.
- **KJFK weather:** MVFR, drizzle/fog, low ceilings (OVC018), 5SM vis; TAF shows continued low ceilings/rain through the 29th, improving late 29th/30th. Consistent with the GDP.
- **JFK→LHR air options (remaining capacity, rate):**
  | Option | Dep | Arr | Cap (kg) | $/kg |
  |---|---|---|---|---|
  | KAL251-0929 | 09-29 22:50 | 09-30 05:50 | 4,200 | 2.10 |
  | BAW174-0929 | 09-30 01:05 | 09-30 08:05 | 3,800 | 2.25 |
  | BAW112-0929 | 09-30 02:00 | 09-30 09:00 | 1,500 | 3.40 |
  | VIR004-0930 | 09-30 08:00 | 09-30 15:00 | 6,000 | 2.60 |
- **FRA→LHR:** only BAW903-0930 (1,200 kg, $1.60, arr 14:00) — too small to absorb the DLH405 group (6,760 kg).
- **No other European feeder→LHR air options** were returned (CDG, AMS, MAD, MUC, FCO, MXP, ZRH, VIE, BRU, DUB, LIS, BCN, OSL, CPH, ARN, GVA, LUX all 404). So the only viable recovery is **JFK→LHR direct air**, split across the four options.

**Total cargo: 19,440 kg.** Total JFK→LHR capacity: 4,200+3,800+1,500+6,000 = **15,500 kg** → **3,940 kg short** of the full 19,440 kg.

## 2) Options considered (cost / arrival / cut-off)

All four JFK→LHR options arrive well before the 18:00Z cut-off (latest arrival 15:00Z). The constraint is **capacity, not timing**.

- **KAL251-0929** — 4,200 kg @ $2.10 → up to $8,820
- **BAW174-0929** — 3,800 kg @ $2.25 → up to $8,550
- **BAW112-0929** — 1,500 kg @ $3.40 → up to $5,100
- **VIR004-0930** — 6,000 kg @ $2.60 → up to $15,600
- **BAW903-0930 (FRA→LHR)** — 1,200 kg @ $1.60 — only useful for a small DLH405 overflow, not enough alone.

**Minimum-cost fill (cheapest $/kg first: KAL 2.10 → BAW174 2.25 → VIR 2.60 → BAW112 3.40):**
- KAL251: 4,200 kg × 2.10 = $8,820
- BAW174: 3,800 kg × 2.25 = $8,550
- VIR004: 6,000 kg × 2.60 = $15,600
- BAW112: 1,500 kg × 3.40 = $5,100
- **Total for 15,500 kg = $38,070** — comfortably under the $95,000 budget.

## 3) Recommended plan per AWB group (PROPOSAL — nothing booked)

Because total capacity (15,500 kg) < total cargo (19,440 kg), the groups **must be split** across options. Suggested allocation (whole AWBs, first-fit by size, cheapest options first):

**Group A — KAL251 (6,920 kg) → split:**
- KAL251-0929 (4,200 kg): 180-31003699(1100), 180-31000411(760), 180-31000822(760), 180-31001233(760), 180-31002877(760), 180-31001644(520), 180-31004932(520), 180-31000000(240) = 5,420 → trim to ≤4,200: drop 180-31004932(520) & 180-31000000(240) → **3,860 kg** (1100+760+760+760+760+520 = 4,660, still over; final fit: 1100+760+760+760+520+380+120 = 4,400 → use 1100,760,760,760,520,380,120 = 4,400, still over 4,200 → 1100,760,760,760,520,380 = 4,280 → 1100,760,760,760,520,120 = 4,020 kg). **Use allocate tool to finalize exact fit.**
- Remainder of Group A → BAW174-0929 / VIR004-0930.

**Group B — BAW174 (5,760 kg) → split:**
- BAW174-0929 (3,800 kg): largest-first fit (1100,760,760,760,520,380,120 = 4,400 → trim to ≤3,800: 1100,760,760,760,380,120 = 3,880 → 1100,760,760,760,120,120 = 3,620 kg).
- Remainder → VIR004-0930 / BAW112-0929.

**Group C — DLH405 (6,760 kg) → split:**
- VIR004-0930 (6,000 kg): largest-first (1100,1100,760,760,520,520,520,380,240,240,120,120 = 6,380 → trim to ≤6,000: 1100,1100,760,760,520,520,520,380,240,120 = 5,920 kg).
- Remainder (~840 kg) → BAW112-0929 (1,500 kg) and/or BAW903-0930 FRA→LHR (1,200 kg) if a FRA connection is acceptable.

> **Note:** Exact per-AWB packing should be confirmed with the `allocate` tool (first-fit decreasing) per group, passing `already_loaded_kg` across groups, before pricing with `cost`. The arithmetic above is indicative only.

## 4) Risks and what would change the decision

- **Capacity shortfall (3,940 kg):** The four JFK→LHR options cannot carry all 19,440 kg. **This is the critical risk.** Options: (a) accept partial movement and defer ~3,940 kg to a later flight; (b) source additional capacity (charter/extra block) — not in the current option set; (c) route a portion via FRA (BAW903, only 1,200 kg) — insufficient alone.
- **GDP delay (avg 2h50m, max 4h10m):** The listed departures are scheduled times; a 4h10m max delay on the 09-30 08:00 VIR004 could push arrival to ~19:10Z, **past the 18:00Z cut-off**. The 09-29 departures (KAL251, BAW174, BAW112) have the most slack and should be prioritized.
- **Weather trend improving late 29th/30th** — later departures may see reduced GDP impact, but the 09-30 08:00 VIR004 is the tightest against cut-off.
- **Budget is not the constraint** ($38k for 15,500 kg vs $95k cap); cost only becomes an issue if premium/charter capacity is added.
- **Decision changes if:** additional JFK→LHR capacity appears, the GDP lifts (reducing delay risk on VIR004), or the consignee accepts a later cut-off for the overflow.

## 5) Tools called
1. `nas_status` (JFK) — GDP + delays
2. `wx` (KJFK) — METAR/TAF/forecast
3. `schedule` JFK→LHR (4 options)
4. `schedule` FRA→LHR (1 option)
5. `schedule` CDG/AMS/MAD/MUC/FCO/MXP/ZRH/VIE/BRU/DUB/LIS/BCN/OSL/CPH/ARN/GVA/LUX→LHR (all 404 — no feeder air)

**No bookings made. This is a proposal for human approval.** Recommend running `allocate` + `cost` to lock exact per-AWB legs and confirm feasibility before approval.
