"""verify must catch every defect class v1 hit, on a real LP result mutated once.
The LP result is produced by the engine (not hand-written), then broken."""
import copy
import json
import os
import unittest
import warnings

warnings.filterwarnings("ignore")
from planner.grammar import PlanSpec  # noqa: E402
from engine.options import build  # noqa: E402
from engine.lp import solve  # noqa: E402
from engine.verify import verify  # noqa: E402

EX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scenarios", "examples")
S1 = json.load(open(os.path.join(EX, "s1_base.json")))
R1 = solve(build(PlanSpec.model_validate(S1)), slack=5.0)   # sea-air split 50+50, 21,400 USD


def broken(fn):
    r = copy.deepcopy(R1)
    fn(r)
    return r


def overload(r):          # one shipment takes all 100 units onto one 50-unit flight
    r["shipments"][0]["qty"] = 100
    r["shipments"].pop(1)
    for a in r["allocations"]:
        a["shipment"] = r["shipments"][0]["id"]


CASES = [
    ("capacity (v1: 6,920 kg on a 4,200 kg flight)", overload, "capacity:"),
    ("coverage (v1: 14,440 of 19,440 kg delivered)", lambda r: r["allocations"].pop(), "coverage:"),
    ("late (v1: arrival after cut-off)", lambda r: [g.update(depart="2026-11-20T00:00:00Z", arrive="2026-11-20T09:36:00Z") for g in r["shipments"][0]["legs"][-1:]], "late:"),
    ("claimed cost differs", lambda r: r.update(cost_usd=r["cost_usd"] - 1000), "cost: plan claims"),
    ("unscheduled departure", lambda r: r["shipments"][0]["legs"][1].update(depart="2026-10-07T03:00:00Z"), "no scheduled departure"),
    ("lot multiple", lambda r: r["shipments"][0].update(qty=55), "multiple of lot"),
    ("stranded mid-route (ends at FRA)", lambda r: r["shipments"][0].update(legs=r["shipments"][0]["legs"][:-1]), "ends at FRA"),
]


class VerifyGate(unittest.TestCase):
    def test_clean_plan_passes(self):
        v = verify(S1, R1)
        self.assertTrue(v["ok"], v["problems"])
        self.assertEqual(v["metrics"]["cost_usd"], R1["cost_usd"])

    def test_defects_caught(self):
        for name, fn, needle in CASES:
            with self.subTest(name):
                v = verify(S1, broken(fn))
                self.assertFalse(v["ok"], f"{name}: passed")
                self.assertTrue(any(needle in p for p in v["problems"]), f"{name}: {v['problems']}")

    def test_shelf_life(self):
        spec = copy.deepcopy(S1)
        spec["items"]["C"]["min_remaining_shelf_life_pct"] = 80   # max age at receipt 36 d; sea-air arrives ~day 51-52 after mfg
        v = verify(spec, R1)
        self.assertTrue(any(p.startswith("shelf:") for p in v["problems"]), v["problems"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
