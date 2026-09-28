"""python -m planner.cli validate <spec.json> [...]   -> problems per spec, exit 1 if any."""
from __future__ import annotations

import json
import sys

from .structure import spec_hash, structure_key
from .validate import validate


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] != "validate":
        print(__doc__.strip(), file=sys.stderr)
        return 2
    bad = 0
    for path in argv[1:]:
        spec = json.load(open(path, encoding="utf-8"))
        probs = validate(spec)
        if probs:
            bad += 1
            print(f"{path}: INVALID ({len(probs)})")
            for p in probs:
                print(f"  - {p}")
        else:
            print(f"{path}: ok spec_hash={spec_hash(spec)} structure_key={structure_key(spec)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
