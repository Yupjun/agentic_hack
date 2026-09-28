"""Stage-1 gate: every broken spec below must be refused with a matching problem,
and both base specs must pass. Broken specs are derived from the real base specs
(one mutation each), not hand-written from scratch."""
import copy
import json
import os
import unittest

from planner.structure import spec_hash, structure_key
from planner.validate import validate

EX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scenarios", "examples")
S1 = json.load(open(os.path.join(EX, "s1_base.json")))
S2 = json.load(open(os.path.join(EX, "s2_base.json")))


def mut(base, fn):
    s = copy.deepcopy(base)
    fn(s)
    return s


BROKEN = [
    ("unknown top-level key", S1, lambda s: s.update(foo=1), "structure"),
    ("bad mode", S1, lambda s: s["lanes"][0].update(mode="teleport"), "structure"),
    ("negative qty", S1, lambda s: s["demand"][0].update(qty=-5), "structure"),
    ("lane to unknown node", S1, lambda s: s["lanes"][0].update(to="ZZZ"), "ref: lane"),
    ("non-ISO due", S1, lambda s: s["demand"][0].update(due="next tuesday"), "time:"),
    ("due before t0", S1, lambda s: s["demand"][0].update(due="2026-09-01T00:00:00Z"), "due at or before t0"),
    ("deadline shorter than fastest route", S1, lambda s: s["demand"][0].update(due="2026-10-02T12:00:00Z"), "earliest possible arrival"),
    ("no lane carries the band", S1, lambda s: s["items"]["C"].update(temp_band="frozen"), "temp: no lane"),
    ("S1 with production", S1, lambda s: s.update(production=copy.deepcopy(S2["production"][:1])), "family: S1 must not"),
    ("alternate supplier for a material", S2, lambda s: s["production"].append(dict(copy.deepcopy(s["production"][0]), site="A2")), "no alternate suppliers"),
    ("BOM material without source", S2, lambda s: s["production_plan"]["bom"].append({"material": "AA", "qty_per_unit": 1}), "no approved production source"),
    ("all lanes unqualified", S1, lambda s: [l.update(qualified=False) for l in s["lanes"]], "reach: no usable lane path"),
]


class GrammarGate(unittest.TestCase):
    def test_base_specs_pass(self):
        self.assertEqual(validate(S1), [])
        self.assertEqual(validate(S2), [])

    def test_broken_specs_refused(self):
        for name, base, fn, needle in BROKEN:
            with self.subTest(name):
                probs = validate(mut(base, fn))
                self.assertTrue(probs, f"{name}: accepted")
                self.assertTrue(any(needle in p for p in probs), f"{name}: problems {probs} lack {needle!r}")

    def test_structure_key_ignores_numbers(self):
        a = mut(S1, lambda s: s["demand"][0].update(qty=200))
        self.assertEqual(structure_key(a), structure_key(S1))
        self.assertNotEqual(spec_hash(a), spec_hash(S1))
        b = mut(S1, lambda s: s["constraints"].update(allowed_modes=["truck", "air"]))
        self.assertNotEqual(structure_key(b), structure_key(S1))


if __name__ == "__main__":
    unittest.main(verbosity=2)
