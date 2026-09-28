# Agent evaluation — NeMo Agent Toolkit + Nemotron 3 Super via NeMo Guardrails gateway

| scenario | base | params | recommended | verified | cost = bank | seconds | tools |
|---|---|---|---|---|---|---|---|
| s1-v1-tight-deadline | ok | ok `{"due_days": 11, "budget_usd": 60000}` | cost_optimal | ok | ok | 31.8 | list_bases > make_spec > solve_plan |
| s1-v3-short-shelf-life | ok | WRONG `{"due_days": 40, "budget_usd": 60000, "shelf_life_days": {"C": 120}, "min_remaining_pct": {"C": 60}}` | None | FAIL | no | 70.7 | list_bases > make_spec > solve_plan |
| s1-v4-low-exposure | ok | ok `{"due_days": 40, "budget_usd": 60000, "max_exposure_hours": 2}` | time_optimal | ok | ok | 43.3 | list_bases > make_spec > solve_plan |
| s2-v1-site-delay | ok | ok `{"budget_usd": 250000, "lead_time_add_days": {"c": 10, "d": 10}}` | balanced | ok | ok | 106.9 | list_bases > make_spec > solve_plan |
| s2-v2-moq-above-need | ok | ok `{"moq": {"b": 15}, "budget_usd": 250000}` | balanced | ok | ok | 146.8 | list_bases > make_spec > solve_plan |
| s2-v4-budget-cut | ok | ok `{"budget_usd": 205000}` | time_optimal | ok | ok | 51.9 | list_bases > make_spec > solve_plan |

base 6/6, params 5/6, verified recommendation 5/6, cost equals bank 5/6
