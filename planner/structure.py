"""canonical() and structure_key(): dedupe proposals that differ only in numbers.

structure_key hashes the SHAPE of a request (family, item temperature bands, the
set of lane mode/from/to, demand item/node, constraint switches, objective), not
its quantities, dates or prices — same idea as autoresearch's structure_key.
spec_hash hashes everything (exact identity of a run input).
"""
from __future__ import annotations

import hashlib
import json

from .grammar import PlanSpec


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def spec_hash(spec: dict) -> str:
    return hashlib.sha256(canonical(spec).encode()).hexdigest()[:16]


def structure_key(spec: dict) -> str:
    s = PlanSpec.model_validate(spec)
    shape = {
        "family": s.family,
        "items": sorted((k, v.kind, v.temp_band) for k, v in s.items.items()),
        "lanes": sorted({(l.mode, l.frm, l.to, l.qualified) for l in s.lanes}),
        "demand": sorted({(d.item, d.node) for d in s.demand}),
        "production": sorted({(x.item, x.site, tuple(sorted(o.name for o in x.options))) for x in s.production}),
        "bom": sorted({b.material for b in s.production_plan.bom}) if s.production_plan else [],
        "constraints": [s.constraints.qualified_lanes_only, sorted(s.constraints.allowed_modes), s.constraints.max_legs],
        "objective": s.objective.primary,
    }
    return hashlib.sha256(canonical(shape).encode()).hexdigest()[:16]


def complexity(spec: dict) -> int:
    s = PlanSpec.model_validate(spec)
    return len(s.lanes) + len(s.items) + len(s.demand) + len(s.production) + (len(s.production_plan.batches) if s.production_plan else 0)
