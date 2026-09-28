"""plan/v1 — the grammar of an order-and-transport plan request ("발주·운송 계획").

One grammar covers both scenario families because both are the same problem:
supply candidates (stock on hand, or a production order at an approved site) move
along qualified lanes and are allocated to demands (item, qty, place, due date,
minimum remaining shelf life at receipt).

  S1  transport-mode choice : fixed stock at A -> demand at B by a deadline, on a budget.
  S2  multi-site sourcing   : production orders at approved sites A1..An -> materials
                              at site AA before each production batch (BOM x batches).

Structure is checked by pydantic; meaning (references, time, reachability) by
validate.py. Neither ever raises on a bad spec: both return a list of problems.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SPEC_VERSION = "plan/v1"
MODES = ("truck", "parcel", "air", "ocean", "rail")
TEMP_BANDS = ("2-8C", "15-25C", "frozen", "ambient")
NODE_KINDS = ("site", "warehouse", "airport", "port", "hub", "customer")
OBJECTIVES = ("min_cost", "max_slack", "balanced")


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Item(Strict):
    kind: Literal["product", "material"]
    temp_band: Literal["2-8C", "15-25C", "frozen", "ambient"]
    shelf_life_days: float = Field(gt=0)
    min_remaining_shelf_life_pct: float = Field(ge=0, le=100)
    lot_size: int = Field(ge=1, default=1)
    unit_kg: float = Field(gt=0, default=1.0)
    unit_value_usd: float = Field(ge=0, default=0.0)


class Node(Strict):
    kind: Literal["site", "warehouse", "airport", "port", "hub", "customer"]
    name: str = ""
    lat: float | None = None
    lon: float | None = None
    min_connect_days: float = Field(ge=0, default=0.25)


class Schedule(Strict):
    first: str
    every_days: float = Field(gt=0)
    count: int = Field(ge=1, le=400)


class Lane(Strict):
    id: str
    mode: Literal["truck", "parcel", "air", "ocean", "rail"]
    frm: str = Field(alias="from")
    to: str
    carrier: str = ""
    transit_days: float = Field(gt=0)
    cost_fixed_usd: float = Field(ge=0, default=0.0)      # per departure used
    cost_per_unit_usd: float = Field(ge=0, default=0.0)
    capacity_units: int = Field(ge=1)                      # per departure
    temp_bands: list[Literal["2-8C", "15-25C", "frozen", "ambient"]]
    qualified: bool = True
    exposure_hours: float = Field(ge=0, default=0.0)       # time outside controlled temperature (hand-overs)
    schedule: Schedule

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Stock(Strict):
    """S1: finished stock already made (mfg_date) and available at a node."""
    item: str
    node: str
    qty: int = Field(ge=1)
    available_from: str
    mfg_date: str


class ProductionOption(Strict):
    name: Literal["standard", "expedite"]
    lead_time_days: float = Field(gt=0)
    premium_pct: float = Field(ge=0, default=0.0)


class Production(Strict):
    """S2: an APPROVED site that makes one material. No alternate sources exist."""
    item: str
    site: str
    unit_cost_usd: float = Field(ge=0)
    moq: int = Field(ge=1)
    options: list[ProductionOption] = Field(min_length=1)
    capacity_per_week: int = Field(ge=1)
    order_from: str
    order_to: str
    order_every_days: float = Field(gt=0, default=7)
    max_wait_days: float = Field(ge=0, default=7)   # goods may wait at the site at most this long after ready


class Demand(Strict):
    id: str
    item: str
    node: str
    qty: int = Field(ge=1)
    due: str


class Batch(Strict):
    id: str
    start: str
    qty: int = Field(ge=1)


class BomLine(Strict):
    material: str
    qty_per_unit: float = Field(gt=0)


class ProductionPlan(Strict):
    """S2: batches of the final product at the target site; demands are BOM x batches."""
    site: str
    product: str
    batches: list[Batch] = Field(min_length=1)
    bom: list[BomLine] = Field(min_length=1)
    mos_months: float = Field(ge=0, default=0.0)
    monthly_usage: dict[str, float] = {}


class Constraints(Strict):
    qualified_lanes_only: bool = True
    max_exposure_hours: float = Field(ge=0, default=24.0)
    allowed_modes: list[Literal["truck", "parcel", "air", "ocean", "rail"]] = list(MODES)
    max_legs: int = Field(ge=1, le=4, default=3)
    alt_connections: int = Field(ge=1, le=4, default=2)   # onward departures tried per later leg (1 = earliest only)


class ModeDelay(Strict):
    mean_days: float = Field(ge=0)
    sd_days: float = Field(ge=0)


class Uncertainty(Strict):
    n_samples: int = Field(ge=100, le=1_000_000, default=10_000)
    seed: int = 7
    delay: dict[str, ModeDelay] = {}
    excursion_prob_per_leg: dict[str, float] = {}
    late_penalty_usd_per_unit_day: float = Field(ge=0, default=0.0)


class Objective(Strict):
    primary: Literal["min_cost", "max_slack", "balanced"] = "balanced"
    pareto_points: int = Field(ge=2, le=40, default=8)


class PlanSpec(Strict):
    spec: Literal["plan/v1"]
    id: str
    family: Literal["S1", "S2"]
    t0: str
    budget_usd: float = Field(gt=0)
    objective: Objective = Objective()
    items: dict[str, Item] = Field(min_length=1)
    nodes: dict[str, Node] = Field(min_length=2)
    lanes: list[Lane] = Field(min_length=1)
    stock: list[Stock] = []
    production: list[Production] = []
    demand: list[Demand] = []
    production_plan: ProductionPlan | None = None
    constraints: Constraints = Constraints()
    uncertainty: Uncertainty = Uncertainty()
    hypothesis: str = ""
