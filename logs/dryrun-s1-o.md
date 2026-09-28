# Recovery Plan Proposal — JFK GDP Disruption (40 AWBs → LHR)

## 1) Situation (what tools showed)
- **JFK NAS status**: Active **GDP** (synthetic) — program rate 30, **avg delay 2h50m, max 4h10m**; general departure delays 1–3h, trend increasing. No closures/ground stops.
- **KJFK weather**: MVFR, drizzle, low ceilings (OVC012); TAF shows continued low ceilings/precip through 29th, improving late 29th. This is the driver of the GDP.
- **Capacity reality**: The three originally-booked flights (KAL251, BAW174, DLH405) cannot carry all 19,440 kg to LHR in time. DLH405 goes to **FRA** (not LHR) and its only onward LHR legs (BAW903 1,200 kg air; TRK-FRA-LHR truck arriving **22:00Z — after the 18:00Z cut-off**) cannot move the 6,760 kg group in time. So the DLH405 group must be re-routed.
- **Alternative options found** (all arrive before 18:00Z cut-off): direct JFK→LHR (KAL251, BAW174, BAW112, VIR004) plus **truck feeder JFK→EWR** (20,000 kg) connecting to EWR→LHR (UAL16, BAW188). EWR is not under the JFK GDP, so the feeder+air route is the key recovery lever.

## 2) Options considered (cost / arrival / cut-off)
| Option | Route | Cap (kg) | Rate | Arrive LHR | vs 18:00Z |
|---|---|---|---|---|---|
| KAL251-0929 | JFK→LHR | 4,200 | $2.10 | 05:50Z | ✓ |
| BAW174-0929 | JFK→LHR | 3,800 | $2.25 | 08:05Z | ✓ |
| BAW112-0929 | JFK→LHR | 1,500 | $3.40 | 09:00Z | ✓ |
| VIR004-0930 | JFK→LHR | 6,000 | $2.60 | 15:00Z | ✓ (3h slack) |
| TRK-JFK-EWR + UAL16-0929 | JFK→EWR→LHR | 2,600 (bottleneck) | $0.08+$2.35 | 04:00Z | ✓ |
| TRK-JFK-EWR + BAW188-0929 | JFK→EWR→LHR | 2,200 (bottleneck) | $0.08+$2.55 | 08:00Z | ✓ |
| TRK-JFK-BOS + BAW214-0929 | JFK→BOS→LHR | 3,000 | $0.22+$2.40 | 06:00Z | ✓ (not needed) |
| DLH405-0929 + BAW903-0930 | JFK→FRA→LHR | 1,200 | $1.95+$1.60 | 14:00Z | ✓ (too small) |
| DLH405-0929 + TRK-FRA-LHR | JFK→FRA→LHR | 5,000 | $1.95+$0.35 | **22:00Z** | ✗ **misses cut-off** |

## 3) Recommended plan per AWB group (PROPOSAL — nothing booked)
All 40 AWBs / 19,440 kg placed; **total $60,692.40** (≤ $95,000 ✓); final arrival 15:00Z, **3.0h slack** to cut-off; no stranded cargo, no capacity violations.

- **KAL251-0929 (JFK→LHR, 4,180 kg, 5 AWB)**: 180-31003699(1100), 180-31004247(1100), 180-31001096(1100), 180-31000411(760), 180-31003288(120)
- **BAW174-0929 (JFK→LHR, 3,760 kg, 5 AWB)**: 180-31004384(1100), 180-31000822(760), 180-31001233(760), 180-31002877(760), 180-31002055(380)
- **VIR004-0930 (JFK→LHR, 6,000 kg, 10 AWB)**: 180-31000959, 180-31001781, 180-31002192, 180-31001507, 180-31003973 (760 each), 180-31001644, 180-31004932, 180-31003014, 180-31002329 (520 each), 180-31004110(120)
- **BAW112-0929 (JFK→LHR, 1,420 kg, 3 AWB)**: 180-31003562(520), 180-31005206(520), 180-31002466(380)
- **TRK-JFK-EWR + UAL16-0929 (2,520 kg, 7 AWB)**: 180-31004521, 180-31002603, 180-31003836, 180-31005069, 180-31000274, 180-31003151 (380 each), 180-31000000(240)
- **TRK-JFK-EWR + BAW188-0929 (1,560 kg, 10 AWB)**: 180-31003425, 180-31002740, 180-31004795 (240 each), 180-31005343, 180-31000137, 180-31000548, 180-31001370, 180-31004658, 180-31000685, 180-31001918 (120 each)

Note: the original DLH405 (JFK→FRA) group is fully re-routed off FRA onto the direct/feeder options above, since no FRA→LHR leg clears the 18:00Z cut-off for its weight.

## 4) Risks and what would change the decision
- **GDP max delay 4h10m**: KAL251 (dep 22:50Z) and BAW174 (dep 01:05Z) are the tightest. A 4h slip on KAL251 pushes arrival to ~09:50Z — still inside cut-off, but it erodes slack. If the GDP extends past ~14:00Z on the 30th, VIR004 (dep 08:00Z, arr 15:00Z) becomes the binding constraint; consider shifting more weight to the EWR feeder (which departs JFK by truck at 14:00Z on the 29th, ahead of the worst of the GDP).
- **VIR004 is full (6,000/6,000)**: any added weight must go to the EWR feeder or BAW112.
- **EWR feeder truck departs 29th 14:00Z**: if that truck is delayed, UAL16 (dep 21:00Z) and BAW188 (dep 01:00Z) connections are at risk; BAW188 has 640 kg headroom and BAW214 (BOS) is the fallback.
- **Cost headroom is large** ($34k under budget): if a direct flight is cancelled, we can absorb the pricier BAW112 ($3.40/kg) or the BOS feeder without breaching $95,000.
- **Decision triggers**: (a) GDP avg delay > 4h or a ground stop → move more to EWR feeder; (b) any JFK→LHR flight cancelled → re-run allocate with remaining options; (c) cut-off pulled earlier than 18:00Z → drop reliance on VIR004 (15:00Z arrival).

## 5) Tools called
nas_status(JFK), wx(KJFK), schedule(JFK→LHR), schedule(JFK→FRA), schedule(JFK all), schedule(FRA→LHR), schedule(EWR→LHR), schedule(BOS→LHR), allocate(40 AWBs, 9 routes), cost(8 legs).

PLAN_JSON: {"cutoff": "2026-09-30T18:00:00Z", "awb_count": 40, "final_dest": "LHR", "total_kg": 19440, "legs": [{"option_id": "KAL251-0929", "chargeable_kg": 4180}, {"option_id": "BAW174-0929", "chargeable_kg": 3760}, {"option_id": "VIR004-0930", "chargeable_kg": 6000}, {"option_id": "BAW112-0929", "chargeable_kg": 1420}, {"option_id": "TRK-JFK-EWR", "chargeable_kg": 2520}, {"option_id": "UAL16-0929", "chargeable_kg": 2520}, {"option_id": "TRK-JFK-EWR", "chargeable_kg": 1560}, {"option_id": "BAW188-0929", "chargeable_kg": 1560}]}
