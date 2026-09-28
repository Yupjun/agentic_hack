"""Stage-2 gate on S1: three named plans exist and verify, the non-dominated frontier
is monotone (more slack costs more), Monte Carlo is seed-reproducible, and the
HiGHS/cuOpt objective match is checked where cuOpt can run (skipped otherwise)."""
import json
import os
import unittest
import warnings

warnings.filterwarnings("ignore")
from planner.grammar import PlanSpec  # noqa: E402
from engine.lp import solve  # noqa: E402
from engine.mc import simulate  # noqa: E402
from engine.options import build  # noqa: E402
from engine.run import solve_spec  # noqa: E402
from engine.verify import verify  # noqa: E402

EX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scenarios", "examples")
S1 = json.load(open(os.path.join(EX, "s1_base.json")))
RES = solve_spec(S1, points=6)


def cuopt_usable() -> bool:
    if os.environ.get("CARGO_ALLOW_GPU") != "1":
        return False
    try:
        import cuopt  # noqa: F401
        return True
    except Exception:
        return False


class EngineGate(unittest.TestCase):
    def test_named_plans_verify(self):
        self.assertEqual(RES["status"], "ok")
        for k in ("cost_optimal", "time_optimal", "balanced", "risk_adjusted"):
            with self.subTest(k):
                p = RES["plans"][k]
                v = verify(S1, p)
                self.assertTrue(v["ok"], v["problems"])
                self.assertEqual(v["metrics"]["units_required"], 100)
                self.assertEqual(v["metrics"]["units_left_over"], 0)

    def test_frontier_monotone(self):
        nd = sorted([p for p in RES["frontier"] if p.get("verify_ok") and not p.get("dominated")], key=lambda p: p["metrics"]["min_slack_days"])
        self.assertGreaterEqual(len(nd), 2)
        for a, b in zip(nd, nd[1:]):
            self.assertLess(a["cost_usd"], b["cost_usd"])

    def test_cost_vs_time_differ(self):
        self.assertLess(RES["plans"]["cost_optimal"]["cost_usd"], RES["plans"]["time_optimal"]["cost_usd"])
        self.assertLess(RES["plans"]["cost_optimal"]["metrics"]["min_slack_days"], RES["plans"]["time_optimal"]["metrics"]["min_slack_days"])

    def test_mc_reproducible(self):
        p = RES["plans"]["cost_optimal"]
        a, b = simulate(S1, p), simulate(S1, p)
        a.pop("seconds"), b.pop("seconds")
        self.assertEqual(a, b)

    @unittest.skipUnless(cuopt_usable(), "cuOpt not runnable here (GPU off-limits on this server; set CARGO_ALLOW_GPU=1 on a GPU box)")
    def test_highs_cuopt_same_objective(self):
        prob = build(PlanSpec.model_validate(S1))
        h = solve(prob, slack=5.0, backend="highs")
        c = solve(prob, slack=5.0, backend="cuopt")
        self.assertAlmostEqual(h["cost_usd"], c["cost_usd"], delta=max(1.0, 1e-4 * h["cost_usd"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
