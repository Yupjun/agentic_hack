"""NeMo Agent Toolkit registration of the planner tools.

Each NAT function is a thin wrapper around one plain function in
agent/planner_tools.py (the mechanism lives there; this file only adapts it to
NAT). The repository root is put on sys.path explicitly because this package is
installed in editable mode from agent/nat_planner.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from nat.builder.builder import Builder  # noqa: E402
from nat.builder.function_info import FunctionInfo  # noqa: E402
from nat.cli.register_workflow import register_function  # noqa: E402
from nat.data_models.function import FunctionBaseConfig  # noqa: E402

from agent import planner_tools as T  # noqa: E402


class ListBasesConfig(FunctionBaseConfig, name="cargo_list_bases"):
    """List base scenarios and the parameters a variant may change."""


class MakeSpecConfig(FunctionBaseConfig, name="cargo_make_spec"):
    """Create and validate a plan spec from a base plus parameter overrides."""


class SolvePlanConfig(FunctionBaseConfig, name="cargo_solve_plan"):
    """Solve a spec; returns four verified plans with cost, slack and Monte Carlo risk."""


class PlanDetailsConfig(FunctionBaseConfig, name="cargo_plan_details"):
    """Shipments of one named plan."""


class StressTestConfig(FunctionBaseConfig, name="cargo_stress_test"):
    """Monte Carlo what-if with different mean delays per mode."""


class AirspaceConfig(FunctionBaseConfig, name="cargo_airspace_status"):
    """Live FAA airspace status for a US airport."""


class WeatherConfig(FunctionBaseConfig, name="cargo_aviation_weather"):
    """Live aviation weather for an ICAO station."""


@register_function(config_type=ListBasesConfig)
async def cargo_list_bases(config: ListBasesConfig, builder: Builder):
    async def _fn(query: str = "") -> str:
        """List the base scenarios (s1_base, s2_base) and the generator parameters a variant may change. Call this first."""
        return T.list_bases()
    yield FunctionInfo.from_fn(_fn, description=_fn.__doc__)


@register_function(config_type=MakeSpecConfig)
async def cargo_make_spec(config: MakeSpecConfig, builder: Builder):
    async def _fn(base: str, params_json: str = "{}", new_id: str = "") -> str:
        """Create a plan spec from a base scenario (s1_base or s2_base) and a JSON object of parameter overrides,
        e.g. {"due_days": 20, "budget_usd": 30000}. Returns spec_id, valid, and problems. If not valid, explain the problems."""
        return T.make_spec(base, params_json, new_id)
    yield FunctionInfo.from_fn(_fn, description=_fn.__doc__)


@register_function(config_type=SolvePlanConfig)
async def cargo_solve_plan(config: SolvePlanConfig, builder: Builder):
    async def _fn(spec_id: str) -> str:
        """Solve a saved spec with the MILP engine. Returns run_id and four independently verified plans
        (cost_optimal, time_optimal, balanced, risk_adjusted) with cost, minimum slack, on-time probability and expected cost."""
        return T.solve_plan(spec_id)
    yield FunctionInfo.from_fn(_fn, description=_fn.__doc__)


@register_function(config_type=PlanDetailsConfig)
async def cargo_plan_details(config: PlanDetailsConfig, builder: Builder):
    async def _fn(run_id: str, plan: str) -> str:
        """Show the shipments (item, qty, option, route, depart, arrive) of one plan: cost_optimal, time_optimal, balanced or risk_adjusted."""
        return T.plan_details(run_id, plan)
    yield FunctionInfo.from_fn(_fn, description=_fn.__doc__)


@register_function(config_type=StressTestConfig)
async def cargo_stress_test(config: StressTestConfig, builder: Builder):
    async def _fn(run_id: str, plan: str, delay_mean_days_json: str = "{}") -> str:
        """What-if: re-run Monte Carlo for one plan with other mean delays per mode, e.g. {"ocean": 6.06}. Returns on-time probability and expected cost."""
        return T.stress_test(run_id, plan, delay_mean_days_json)
    yield FunctionInfo.from_fn(_fn, description=_fn.__doc__)


@register_function(config_type=AirspaceConfig)
async def cargo_airspace_status(config: AirspaceConfig, builder: Builder):
    async def _fn(airport: str) -> str:
        """Live FAA National Airspace System status for a US airport (FAA id such as JFK): ground delay programs, ground stops, closures."""
        return T.airspace_status(airport)
    yield FunctionInfo.from_fn(_fn, description=_fn.__doc__)


@register_function(config_type=WeatherConfig)
async def cargo_aviation_weather(config: WeatherConfig, builder: Builder):
    async def _fn(icao: str) -> str:
        """Live aviation weather for an ICAO station (e.g. EDDF, RKSI, OMDB): METAR, TAF and SIGMET/AIRMET nearby."""
        return T.aviation_weather(icao)
    yield FunctionInfo.from_fn(_fn, description=_fn.__doc__)
