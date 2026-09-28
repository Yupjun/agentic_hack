# Agent evaluation — NeMo Agent Toolkit + Nemotron 3 Super via NeMo Guardrails gateway

| scenario | base | params | recommended | verified | cost = bank | seconds | tools |
|---|---|---|---|---|---|---|---|
| s1-v1-tight-deadline | ok | ok `{"due_days": 11, "budget_usd": 60000}` | cost_optimal | ok | ok | 47.1 | list_bases > make_spec > solve_plan > plan_details |
| s1-v3-short-shelf-life | ok | WRONG `{"due_days": 40, "budget_usd": 60000, "shelf_life_days": {"C": 120}, "min_remaining_pct": {"C": 60}, "moq": {"C": 100}}` | time_optimal | ok | ok | 63.6 | list_bases > make_spec > solve_plan |
| s1-v4-low-exposure | ok | ok `{"due_days": 40, "budget_usd": 60000, "max_exposure_hours": 2}` | time_optimal | ok | ok | 54.9 | list_bases > make_spec > solve_plan > plan_details |
| s2-v1-site-delay | ok | ok `{"budget_usd": 250000, "lead_time_add_days": {"c": 10, "d": 10}}` | None | FAIL | no | 112.4 | list_bases > make_spec > solve_plan |
| s2-v2-moq-above-need | ok | ok `{"budget_usd": 250000, "moq": {"b": 15}}` | time_optimal | ok | ok | 152.7 | list_bases > make_spec > solve_plan |
| s2-v4-budget-cut | ok | ok `{"budget_usd": 205000}` | balanced | ok | ok | 60.6 | list_bases > make_spec > solve_plan |

base 6/6, params 5/6, verified recommendation 5/6, cost equals bank 5/6
