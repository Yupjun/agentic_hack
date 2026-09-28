# Recovery Plan Proposal — 40 AWBs to LHR (cutoff 2026-09-30T18:00Z, budget ≤ $95,000)

## 1) Situation (what tools showed)
- **JFK NAS (synthetic):** Active **GDP** — program rate 30, **avg delay 2h50m, max 4h10m**, reason "LOW CEILINGS / WIND". General departure delays 1–3h, trend **Increasing**. No closures/ground stops.
- **KJFK weather:** METAR MVFR (4SM, -DZ BR, OVC026). TAF: rain/low ceilings through ~2817Z, improving to P6SM OVC015 by 2822Z, OVC025–035 on the 29th. No SIGMET/AIRMET.
- **Implication:** Booked flights KAL251 / BAW174 / DLH405 (all departing JFK) are exposed to the GDP. The schedule feed already lists **revised/next-day departures** (KAL251-0929, BAW174-0929, DLH405-0929) plus alternates (BAW112, VIR004) and FRA→LHR connections.

## 2) Options considered (cost / arrival / cutoff)
| Option | Route | Arrive LHR | Meets cutoff | Cost |
|---|---|---|---|---|
| A | KAL251-0929 (JFK→LHR) | 09-30 05:50Z | ✅ 12.2h slack | $15,162 |
| B | BAW174-0929 (JFK→LHR) | 09-30 08:05Z | ✅ 9.9h slack | $13,545 |
| C1 | DLH405-0929 + **truck** FRA→LHR | 09-30 22:00Z | ❌ −4h | $16,458 |
| C2 | DLH405-0929 + **air** BAW903 FRA→LHR | 09-30 14:00Z | ✅ 4h slack | $25,168 |
| C3 | **VIR004-0930** (JFK→LHR direct) | 09-30 15:00Z | ✅ 3h slack | $18,161 |

## 3) Recommended plan per AWB group
- **Group 1 — KAL251 (14 AWBs, 6,920 kg):** Rebook on **KAL251-0929** (JFK→LHR, dep 09-29 22:50Z, arr 09-30 05:50Z). Fits 4,200 kg cap? **No — 6,920 kg > 4,200 kg cap.** ⚠️ See Risks. Cost basis $15,162 (14 AWBs).
- **Group 2 — BAW174 (13 AWBs, 5,760 kg):** Rebook on **BAW174-0929** (JFK→LHR, dep 09-30 01:05Z, arr 08:05Z). 5,760 kg > 3,800 kg cap. ⚠️ See Risks. Cost basis $13,545.
- **Group 3 — DLH405 (13 AWBs, 6,760 kg):** Move **direct on VIR004-0930** (JFK→LHR, dep 09-30 08:00Z, arr 15:00Z) — **$18,161**, meets cutoff with 3h slack. Cheaper than the FRA air-connection ($25,168) and the only FRA option that meets cutoff. (Truck FRA→LHR misses cutoff by 4h — rejected.)

**Total (recommended): $15,162 + $13,545 + $18,161 = $46,868** — well under the $95,000 budget.

## 4) Risks and what would change the decision
- **Capacity shortfall (primary risk):** KAL251-0929 cap 4,200 kg < 6,920 kg; BAW174-0929 cap 3,800 kg < 5,760 kg. As-is, ~2,720 kg (Group 1) and ~1,960 kg (Group 2) have no confirmed space. **Mitigation:** split the overflow onto **VIR004-0930** (6,000 kg cap, $2.6/kg) or **BAW112-0929** (1,500 kg cap, $3.4/kg). This raises cost but stays far under budget. **Decision changes if** the carrier confirms uplift of the full group weight on the named flights.
- **GDP persistence:** If the JFK GDP (avg 2h50m / max 4h10m) extends past the 09-30 08:00Z VIR004 departure, Group 3's 3h slack erodes. **Decision changes if** NAS shows the GDP still active at 09-30 06:00Z → pull Group 3 earlier onto BAW174-0929/KAL251-0929 space or add BAW112.
- **Largest single AWB (1,100 kg):** must fit within a single flight's per-piece/ULD limits — confirm with carrier; if not, that AWB may need its own allocation.
- **Weather:** improving by 09-29; no SIGMET. Low risk of a full closure, but a ground stop would reset all JFK departures.

## 5) Tools called
1. `nas_status` (JFK) — GDP + delays
2. `wx` (KJFK) — METAR/TAF/forecast
3. `schedule` (JFK→LHR) — 4 options
4. `schedule` (JFK→FRA) — 1 option
5. `schedule` (FRA→LHR) — 2 options
6. `cost` (KAL251-0929, 14 AWB) — $15,162
7. `cost` (BAW174-0929, 13 AWB) — $13,545
8. `cost` (DLH405 + truck FRA→LHR) — $16,458, misses cutoff
9. `cost` (DLH405 + air BAW903) — $25,168
10. `cost` (VIR004-0930 direct, 13 AWB) — $18,161

**This is a PROPOSAL for human approval — nothing has been booked.** Recommend confirming carrier uplift capacity for Groups 1 & 2 before finalizing.
