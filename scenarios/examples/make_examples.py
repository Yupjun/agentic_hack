"""Write the two hand-authored base specs (S1, S2). All numbers are synthetic.

These are the seeds that scenarios/gen.py perturbs. They are written by hand on
purpose: the plan grammar is new, so the spec itself is the source of truth for
the rules (see CLAUDE.md "new rules have no answer in code").
"""
import json
import os

HERE = os.path.dirname(__file__)
BANDS_COLD = ["2-8C", "15-25C"]


def sched(first, every, count):
    return {"first": first, "every_days": every, "count": count}


s1 = {
    "spec": "plan/v1", "id": "s1-base", "family": "S1", "t0": "2026-10-01T00:00:00Z", "budget_usd": 60000,
    "objective": {"primary": "balanced", "pareto_points": 8},
    "items": {"C": {"kind": "product", "temp_band": "2-8C", "shelf_life_days": 180, "min_remaining_shelf_life_pct": 60,
                    "lot_size": 10, "unit_kg": 12, "unit_value_usd": 9000}},
    "nodes": {
        "A": {"kind": "site", "name": "Plant A (Incheon area)", "lat": 37.46, "lon": 126.44},
        "ICN": {"kind": "airport", "name": "Incheon Intl", "lat": 37.46, "lon": 126.44, "min_connect_days": 0.25},
        "PUS": {"kind": "port", "name": "Busan New Port", "lat": 35.08, "lon": 128.83, "min_connect_days": 1.0},
        "DXB": {"kind": "hub", "name": "Dubai sea-air hub (Jebel Ali / DWC)", "lat": 24.98, "lon": 55.06, "min_connect_days": 1.0},
        "RTM": {"kind": "port", "name": "Rotterdam", "lat": 51.95, "lon": 4.14, "min_connect_days": 1.0},
        "FRA": {"kind": "airport", "name": "Frankfurt", "lat": 50.04, "lon": 8.56, "min_connect_days": 0.25},
        "B": {"kind": "warehouse", "name": "Distribution centre B (Frankfurt area)", "lat": 50.1, "lon": 8.7},
    },
    "lanes": [
        {"id": "T-A-ICN", "mode": "truck", "from": "A", "to": "ICN", "carrier": "reefer truck", "transit_days": 0.3, "cost_fixed_usd": 400, "cost_per_unit_usd": 5, "capacity_units": 300, "temp_bands": BANDS_COLD, "exposure_hours": 0.5, "schedule": sched("2026-10-02T06:00:00Z", 1, 60)},
        {"id": "AIR-ICN-FRA-STD", "mode": "air", "from": "ICN", "to": "FRA", "carrier": "belly, passive shipper", "transit_days": 0.6, "cost_fixed_usd": 1500, "cost_per_unit_usd": 180, "capacity_units": 40, "temp_bands": BANDS_COLD, "exposure_hours": 3.0, "schedule": sched("2026-10-02T14:00:00Z", 1, 60)},
        {"id": "AIR-ICN-FRA-ACT", "mode": "air", "from": "ICN", "to": "FRA", "carrier": "freighter, active container", "transit_days": 0.6, "cost_fixed_usd": 2500, "cost_per_unit_usd": 260, "capacity_units": 60, "temp_bands": BANDS_COLD, "exposure_hours": 0.5, "schedule": sched("2026-10-03T02:00:00Z", 2, 30)},
        {"id": "T-FRA-B", "mode": "truck", "from": "FRA", "to": "B", "carrier": "reefer truck", "transit_days": 0.3, "cost_fixed_usd": 300, "cost_per_unit_usd": 4, "capacity_units": 300, "temp_bands": BANDS_COLD, "exposure_hours": 0.5, "schedule": sched("2026-10-02T06:00:00Z", 0.5, 120)},
        {"id": "T-A-PUS", "mode": "truck", "from": "A", "to": "PUS", "carrier": "reefer truck", "transit_days": 0.4, "cost_fixed_usd": 600, "cost_per_unit_usd": 4, "capacity_units": 400, "temp_bands": BANDS_COLD, "exposure_hours": 0.5, "schedule": sched("2026-10-02T06:00:00Z", 1, 60)},
        {"id": "OCN-PUS-RTM", "mode": "ocean", "from": "PUS", "to": "RTM", "carrier": "reefer container, via Cape", "transit_days": 34, "cost_fixed_usd": 6500, "cost_per_unit_usd": 3, "capacity_units": 400, "temp_bands": BANDS_COLD, "exposure_hours": 1.0, "schedule": sched("2026-10-04T00:00:00Z", 7, 8)},
        {"id": "T-RTM-B", "mode": "truck", "from": "RTM", "to": "B", "carrier": "reefer truck", "transit_days": 0.8, "cost_fixed_usd": 700, "cost_per_unit_usd": 4, "capacity_units": 400, "temp_bands": BANDS_COLD, "exposure_hours": 0.5, "schedule": sched("2026-10-02T06:00:00Z", 1, 90)},
        {"id": "OCN-PUS-DXB", "mode": "ocean", "from": "PUS", "to": "DXB", "carrier": "reefer container", "transit_days": 16, "cost_fixed_usd": 4500, "cost_per_unit_usd": 3, "capacity_units": 400, "temp_bands": BANDS_COLD, "exposure_hours": 1.0, "schedule": sched("2026-10-06T00:00:00Z", 7, 8)},
        {"id": "AIR-DXB-FRA", "mode": "air", "from": "DXB", "to": "FRA", "carrier": "sea-air onward, active container", "transit_days": 0.4, "cost_fixed_usd": 1800, "cost_per_unit_usd": 110, "capacity_units": 50, "temp_bands": BANDS_COLD, "exposure_hours": 1.5, "schedule": sched("2026-10-02T20:00:00Z", 1, 70)},
        {"id": "PCL-A-B", "mode": "parcel", "from": "A", "to": "B", "carrier": "express courier, passive box", "transit_days": 3, "cost_fixed_usd": 0, "cost_per_unit_usd": 420, "capacity_units": 20, "temp_bands": BANDS_COLD, "exposure_hours": 6.0, "schedule": sched("2026-10-02T09:00:00Z", 1, 60)},
    ],
    "stock": [{"item": "C", "node": "A", "qty": 100, "available_from": "2026-10-02T00:00:00Z", "mfg_date": "2026-09-10T00:00:00Z"}],
    "demand": [{"id": "B-C-100", "item": "C", "node": "B", "qty": 100, "due": "2026-11-10T18:00:00Z"}],
    "constraints": {"qualified_lanes_only": True, "max_exposure_hours": 4, "allowed_modes": ["truck", "parcel", "air", "ocean"], "max_legs": 3},
    "uncertainty": {"n_samples": 10000, "seed": 7,
                    "delay": {"truck": {"mean_days": 0.05, "sd_days": 0.2}, "parcel": {"mean_days": 0.3, "sd_days": 0.8},
                              "air": {"mean_days": 0.3, "sd_days": 0.7}, "ocean": {"mean_days": 3.0, "sd_days": 4.0}},
                    "excursion_prob_per_leg": {"truck": 0.002, "parcel": 0.03, "air": 0.01, "ocean": 0.004},
                    "late_penalty_usd_per_unit_day": 150},
    "hypothesis": "Ocean is cheapest and still meets the 40-day deadline with >=60% shelf life; sea-air via DXB should sit between ocean and air on both cost and lead time.",
}

MAT = ["2-8C", "15-25C", "frozen"]
s2 = {
    "spec": "plan/v1", "id": "s2-base", "family": "S2", "t0": "2026-10-01T00:00:00Z", "budget_usd": 250000,
    "objective": {"primary": "balanced", "pareto_points": 8},
    "items": {
        "AA": {"kind": "product", "temp_band": "2-8C", "shelf_life_days": 365, "min_remaining_shelf_life_pct": 0},
        "a": {"kind": "material", "temp_band": "15-25C", "shelf_life_days": 365, "min_remaining_shelf_life_pct": 50, "lot_size": 1, "unit_kg": 20, "unit_value_usd": 1200},
        "b": {"kind": "material", "temp_band": "2-8C", "shelf_life_days": 40, "min_remaining_shelf_life_pct": 50, "lot_size": 1, "unit_kg": 8, "unit_value_usd": 2600},
        "c": {"kind": "material", "temp_band": "15-25C", "shelf_life_days": 540, "min_remaining_shelf_life_pct": 60, "lot_size": 1, "unit_kg": 5, "unit_value_usd": 4000},
        "d": {"kind": "material", "temp_band": "frozen", "shelf_life_days": 120, "min_remaining_shelf_life_pct": 50, "lot_size": 1, "unit_kg": 10, "unit_value_usd": 3100},
    },
    "nodes": {
        "A1": {"kind": "site", "name": "Site A1 (Basel area)", "lat": 47.56, "lon": 7.59},
        "A2": {"kind": "site", "name": "Site A2 (Cork area)", "lat": 51.9, "lon": -8.47},
        "A3": {"kind": "site", "name": "Site A3 (Singapore)", "lat": 1.35, "lon": 103.82},
        "ZRH": {"kind": "airport", "name": "Zurich", "lat": 47.46, "lon": 8.55, "min_connect_days": 0.25},
        "DUB": {"kind": "airport", "name": "Dublin", "lat": 53.43, "lon": -6.25, "min_connect_days": 0.25},
        "FRA": {"kind": "airport", "name": "Frankfurt hub", "lat": 50.04, "lon": 8.56, "min_connect_days": 0.5},
        "RTM": {"kind": "port", "name": "Rotterdam", "lat": 51.95, "lon": 4.14, "min_connect_days": 1.0},
        "SIN": {"kind": "airport", "name": "Singapore Changi", "lat": 1.36, "lon": 103.99, "min_connect_days": 0.25},
        "SGP": {"kind": "port", "name": "Singapore port", "lat": 1.26, "lon": 103.84, "min_connect_days": 1.0},
        "ICN": {"kind": "airport", "name": "Incheon", "lat": 37.46, "lon": 126.44, "min_connect_days": 0.25},
        "PUS": {"kind": "port", "name": "Busan", "lat": 35.08, "lon": 128.83, "min_connect_days": 1.0},
        "AA": {"kind": "site", "name": "Site AA (final production)", "lat": 37.39, "lon": 126.64},
    },
    "lanes": [
        {"id": "T-A1-ZRH", "mode": "truck", "from": "A1", "to": "ZRH", "transit_days": 0.2, "cost_fixed_usd": 300, "cost_per_unit_usd": 2, "capacity_units": 100, "temp_bands": MAT, "exposure_hours": 0.5, "schedule": sched("2026-10-01T06:00:00Z", 1, 150)},
        {"id": "AIR-ZRH-ICN", "mode": "air", "from": "ZRH", "to": "ICN", "transit_days": 0.6, "cost_fixed_usd": 1800, "cost_per_unit_usd": 90, "capacity_units": 30, "temp_bands": MAT, "exposure_hours": 2.0, "schedule": sched("2026-10-02T12:00:00Z", 2, 75)},
        {"id": "T-A1-RTM", "mode": "truck", "from": "A1", "to": "RTM", "transit_days": 1.0, "cost_fixed_usd": 900, "cost_per_unit_usd": 3, "capacity_units": 200, "temp_bands": ["15-25C", "2-8C"], "exposure_hours": 0.5, "schedule": sched("2026-10-01T06:00:00Z", 1, 150)},
        {"id": "OCN-RTM-PUS", "mode": "ocean", "from": "RTM", "to": "PUS", "transit_days": 36, "cost_fixed_usd": 5500, "cost_per_unit_usd": 4, "capacity_units": 300, "temp_bands": ["15-25C", "2-8C"], "exposure_hours": 1.0, "schedule": sched("2026-10-03T00:00:00Z", 7, 20)},
        {"id": "T-A2-DUB", "mode": "truck", "from": "A2", "to": "DUB", "transit_days": 0.2, "cost_fixed_usd": 250, "cost_per_unit_usd": 2, "capacity_units": 100, "temp_bands": MAT, "exposure_hours": 0.5, "schedule": sched("2026-10-01T06:00:00Z", 1, 150)},
        {"id": "AIR-DUB-FRA", "mode": "air", "from": "DUB", "to": "FRA", "transit_days": 0.2, "cost_fixed_usd": 700, "cost_per_unit_usd": 25, "capacity_units": 40, "temp_bands": ["2-8C", "15-25C"], "exposure_hours": 1.5, "schedule": sched("2026-10-01T15:00:00Z", 1, 150)},
        {"id": "AIR-FRA-ICN", "mode": "air", "from": "FRA", "to": "ICN", "transit_days": 0.6, "cost_fixed_usd": 1800, "cost_per_unit_usd": 70, "capacity_units": 40, "temp_bands": MAT, "exposure_hours": 2.0, "schedule": sched("2026-10-02T13:00:00Z", 1, 150)},
        {"id": "T-A3-SIN", "mode": "truck", "from": "A3", "to": "SIN", "transit_days": 0.1, "cost_fixed_usd": 200, "cost_per_unit_usd": 1, "capacity_units": 100, "temp_bands": MAT, "exposure_hours": 0.5, "schedule": sched("2026-10-01T06:00:00Z", 1, 150)},
        {"id": "AIR-SIN-ICN", "mode": "air", "from": "SIN", "to": "ICN", "transit_days": 0.3, "cost_fixed_usd": 1200, "cost_per_unit_usd": 45, "capacity_units": 40, "temp_bands": MAT, "exposure_hours": 1.5, "schedule": sched("2026-10-01T23:00:00Z", 1, 150)},
        {"id": "T-A3-SGP", "mode": "truck", "from": "A3", "to": "SGP", "transit_days": 0.2, "cost_fixed_usd": 300, "cost_per_unit_usd": 1, "capacity_units": 200, "temp_bands": ["15-25C", "2-8C"], "exposure_hours": 0.5, "schedule": sched("2026-10-01T06:00:00Z", 1, 150)},
        {"id": "OCN-SGP-PUS", "mode": "ocean", "from": "SGP", "to": "PUS", "transit_days": 7, "cost_fixed_usd": 2500, "cost_per_unit_usd": 2, "capacity_units": 300, "temp_bands": ["15-25C", "2-8C"], "exposure_hours": 1.0, "schedule": sched("2026-10-02T00:00:00Z", 7, 20)},
        {"id": "T-ICN-AA", "mode": "truck", "from": "ICN", "to": "AA", "transit_days": 0.2, "cost_fixed_usd": 200, "cost_per_unit_usd": 1, "capacity_units": 200, "temp_bands": MAT, "exposure_hours": 0.5, "schedule": sched("2026-10-01T06:00:00Z", 0.5, 300)},
        {"id": "T-PUS-AA", "mode": "truck", "from": "PUS", "to": "AA", "transit_days": 0.4, "cost_fixed_usd": 500, "cost_per_unit_usd": 2, "capacity_units": 300, "temp_bands": ["15-25C", "2-8C"], "exposure_hours": 0.5, "schedule": sched("2026-10-01T06:00:00Z", 1, 150)},
    ],
    "production": [
        {"item": "a", "site": "A1", "unit_cost_usd": 1200, "moq": 8, "capacity_per_week": 20, "order_from": "2026-10-01T00:00:00Z", "order_to": "2027-01-10T00:00:00Z", "order_every_days": 7,
         "options": [{"name": "standard", "lead_time_days": 21}, {"name": "expedite", "lead_time_days": 10, "premium_pct": 35}]},
        {"item": "b", "site": "A2", "unit_cost_usd": 2600, "moq": 10, "capacity_per_week": 15, "order_from": "2026-10-01T00:00:00Z", "order_to": "2027-01-10T00:00:00Z", "order_every_days": 7,
         "options": [{"name": "standard", "lead_time_days": 14}, {"name": "expedite", "lead_time_days": 7, "premium_pct": 40}]},
        {"item": "c", "site": "A3", "unit_cost_usd": 4000, "moq": 5, "capacity_per_week": 10, "order_from": "2026-10-01T00:00:00Z", "order_to": "2027-01-10T00:00:00Z", "order_every_days": 7,
         "options": [{"name": "standard", "lead_time_days": 28}, {"name": "expedite", "lead_time_days": 14, "premium_pct": 30}]},
        {"item": "d", "site": "A3", "unit_cost_usd": 3100, "moq": 6, "capacity_per_week": 12, "order_from": "2026-10-01T00:00:00Z", "order_to": "2027-01-10T00:00:00Z", "order_every_days": 7,
         "options": [{"name": "standard", "lead_time_days": 21}, {"name": "expedite", "lead_time_days": 10, "premium_pct": 35}]},
    ],
    "production_plan": {
        "site": "AA", "product": "AA",
        "batches": [{"id": "B1", "start": "2026-11-20T00:00:00Z", "qty": 1}, {"id": "B2", "start": "2026-12-18T00:00:00Z", "qty": 1}, {"id": "B3", "start": "2027-01-15T00:00:00Z", "qty": 1}],
        "bom": [{"material": "a", "qty_per_unit": 5}, {"material": "b", "qty_per_unit": 10}, {"material": "c", "qty_per_unit": 2}, {"material": "d", "qty_per_unit": 5}],
        "mos_months": 1, "monthly_usage": {"a": 5, "c": 2},
    },
    "constraints": {"qualified_lanes_only": True, "max_exposure_hours": 4, "allowed_modes": ["truck", "air", "ocean"], "max_legs": 3},
    "uncertainty": {"n_samples": 10000, "seed": 7,
                    "delay": {"truck": {"mean_days": 0.05, "sd_days": 0.2}, "air": {"mean_days": 0.3, "sd_days": 0.7}, "ocean": {"mean_days": 3.0, "sd_days": 4.0}},
                    "excursion_prob_per_leg": {"truck": 0.002, "air": 0.01, "ocean": 0.004}, "late_penalty_usd_per_unit_day": 500},
    "hypothesis": "Material b (40-day shelf life, 50% remaining at receipt) cannot be bought once for three batches; it needs one order per batch. MOQ 8 on a forces overbuy on the first order.",
}

for name, spec in (("s1_base.json", s1), ("s2_base.json", s2)):
    with open(os.path.join(HERE, name), "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=1, ensure_ascii=False)
print("wrote s1_base.json s2_base.json")
