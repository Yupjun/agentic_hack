"""Guardrails policy is enforced by the rail, not by the prompt: a declared call passes,
an undeclared tool (book_shipment) and a schema-invalid call are blocked. No LLM call is made."""
import asyncio
import os
import unittest
import warnings

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = [{"type": "function", "function": {"name": "cargo_solve_plan", "description": "solve",
          "parameters": {"type": "object", "properties": {"spec_id": {"type": "string"}}, "required": ["spec_id"]}}}]


def check(name, args):
    from nemoguardrails import RailsConfig
    from nemoguardrails.guardrails.guardrails import Guardrails
    from nemoguardrails.types import ToolCall, ToolCallFunction
    os.environ.setdefault("NVIDIA_API_KEY", "not-used-by-this-test")
    g = Guardrails(RailsConfig.from_path(os.path.join(ROOT, "agent", "guardrails")), require_iorails=True)

    async def go():
        await g._ensure_started()
        r = await g.rails_engine.rails_manager.are_tool_calls_safe(
            [ToolCall(id="t", type="function", function=ToolCallFunction(name=name, arguments=args))], {"tools": TOOLS})
        return r.is_safe, str(getattr(r, "reason", ""))
    return asyncio.run(go())


class GuardrailPolicy(unittest.TestCase):
    def test_declared_call_allowed(self):
        self.assertEqual(check("cargo_solve_plan", {"spec_id": "s1"})[0], True)

    def test_booking_tool_blocked(self):
        ok, why = check("book_shipment", {"plan": "cost_optimal"})
        self.assertFalse(ok)
        self.assertIn("not an allowed tool", why)

    def test_schema_violation_blocked(self):
        ok, why = check("cargo_solve_plan", {"wrong": 1})
        self.assertFalse(ok)
        self.assertIn("schema", why)


if __name__ == "__main__":
    unittest.main(verbosity=2)
