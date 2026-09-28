"""Agent tools without a model: errors are loud JSON, invalid requests are refused with a reason."""
import json
import unittest
import warnings

warnings.filterwarnings("ignore")
from agent import planner_tools as T  # noqa: E402


class Tools(unittest.TestCase):
    def test_unknown_base(self):
        self.assertIn("error", json.loads(T.make_spec("nope", "{}")))

    def test_bad_json(self):
        self.assertIn("error", json.loads(T.make_spec("s1_base", "{not json")))

    def test_impossible_deadline_refused(self):
        r = json.loads(T.make_spec("s1_base", '{"due_days": 1}', "test-impossible"))
        self.assertFalse(r["valid"])
        self.assertTrue(any("earliest possible arrival" in p for p in r["problems"]))

    def test_unknown_spec_and_run(self):
        self.assertIn("error", json.loads(T.solve_plan("does-not-exist")))
        self.assertIn("error", json.loads(T.plan_details("does-not-exist", "balanced")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
