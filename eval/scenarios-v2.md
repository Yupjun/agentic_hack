# Scenario bank v2 — engine vs rule baselines

All plans re-checked by engine/verify.py (independent recomputation) and scored by engine/mc.py (10,000 samples, seed 7, CPU).
p_on_time = probability every demand is met by its due date; mean cost includes the late penalty.

| scenario | verdict | plan | cost USD | min slack d | verify | p_on_time | mean cost USD | left over | routes | expedite |
|---|---|---|---|---|---|---|---|---|---|---|
| s1-base | supported 5/5 (post-hoc) | cost_optimal | 8,900 | 1.70 | ok | 0.306 | 53,706 | 0 | ocean | - |
|  |  | risk_adjusted | 21,400 | 15.20 | ok | 0.999 | 21,411 | 0 | sea-air | - |
|  |  | balanced | 21,400 | 15.20 | ok | 0.999 | 21,411 | 0 | sea-air | - |
|  |  | time_optimal | 25,100 | 33.20 | ok | 1.000 | 25,100 | 0 | air | - |
|  |  | rule_cheapest | 8,900 | 1.70 | ok | 0.306 | 53,706 | 0 | ocean | - |
|  |  | rule_fastest | 28,700 | 36.70 | ok | 1.000 | 28,700 | 0 | air | - |
| s1-v1-tight-deadline | supported 4/4 | cost_optimal | 25,100 | 4.95 | ok | 1.000 | 25,100 | 0 | air | - |
|  |  | risk_adjusted | 25,100 | 4.95 | ok | 1.000 | 25,100 | 0 | air | - |
|  |  | balanced | 27,000 | 5.45 | ok | 1.000 | 27,000 | 0 | air | - |
|  |  | time_optimal | 28,400 | 6.95 | ok | 1.000 | 28,400 | 0 | air | - |
|  |  | rule_cheapest | 25,100 | 4.95 | ok | 1.000 | 25,100 | 0 | air | - |
|  |  | rule_fastest | 28,700 | 6.95 | ok | 1.000 | 28,700 | 0 | air | - |
| s1-v2-tight-budget | supported 4/4 | cost_optimal | 8,900 | 1.70 | ok | 0.306 | 53,706 | 0 | ocean | - |
|  |  | risk_adjusted | 8,900 | 1.70 | ok | 0.306 | 53,706 | 0 | ocean | - |
|  |  | balanced | 8,900 | 1.70 | ok | 0.306 | 53,706 | 0 | ocean | - |
|  |  | time_optimal | 8,900 | 1.70 | ok | 0.306 | 53,706 | 0 | ocean | - |
|  |  | rule_cheapest | 8,900 | 1.70 | ok | 0.306 | 53,706 | 0 | ocean | - |
|  |  | rule_fastest | 28,700 | 36.70 | FAIL | 1.000 | 28,700 | 0 | air | - |
| s1-v3-short-shelf-life | supported 3/3 | cost_optimal | 21,400 | 15.70 | ok | 0.999 | 21,411 | 0 | sea-air | - |
|  |  | risk_adjusted | 21,400 | 15.70 | ok | 0.999 | 21,411 | 0 | sea-air | - |
|  |  | balanced | 21,400 | 15.70 | ok | 0.999 | 21,411 | 0 | sea-air | - |
|  |  | time_optimal | 25,100 | 33.20 | ok | 1.000 | 25,100 | 0 | air | - |
|  |  | rule_cheapest | 21,400 | 15.70 | ok | 0.999 | 21,411 | 0 | sea-air | - |
|  |  | rule_fastest | 28,700 | 36.70 | ok | 1.000 | 28,700 | 0 | air | - |
| s1-v4-low-exposure | supported 5/5 | cost_optimal | 8,900 | 1.70 | ok | 0.306 | 53,706 | 0 | ocean | - |
|  |  | risk_adjusted | 32,900 | 33.20 | ok | 1.000 | 32,900 | 0 | air | - |
|  |  | balanced | 32,900 | 33.20 | ok | 1.000 | 32,900 | 0 | air | - |
|  |  | time_optimal | 32,900 | 33.20 | ok | 1.000 | 32,900 | 0 | air | - |
|  |  | rule_cheapest | 8,900 | 1.70 | ok | 0.306 | 53,706 | 0 | ocean | - |
|  |  | rule_fastest | 32,900 | 35.20 | ok | 1.000 | 32,900 | 0 | air | - |
| s1-v5-ocean-delay-2026 | supported 3/3 | cost_optimal | 8,900 | 1.70 | ok | 0.104 | 89,896 | 0 | ocean | - |
|  |  | risk_adjusted | 21,400 | 15.20 | ok | 0.990 | 21,504 | 0 | sea-air | - |
|  |  | balanced | 21,400 | 15.20 | ok | 0.990 | 21,504 | 0 | sea-air | - |
|  |  | time_optimal | 25,100 | 33.20 | ok | 1.000 | 25,100 | 0 | air | - |
|  |  | rule_cheapest | 8,900 | 1.70 | ok | 0.104 | 89,896 | 0 | ocean | - |
|  |  | rule_fastest | 28,700 | 36.70 | ok | 1.000 | 28,700 | 0 | air | - |
| s2-base | supported 4/4 (post-hoc) | cost_optimal | 200,131 | 2.05 | ok | 0.804 | 200,550 | 0 | air | - |
|  |  | risk_adjusted | 200,331 | 3.05 | ok | 0.998 | 200,332 | 0 | air | - |
|  |  | balanced | 209,731 | 8.05 | ok | 1.000 | 209,731 | 0 | air | c |
|  |  | time_optimal | 222,101 | 15.05 | ok | 1.000 | 222,101 | 0 | air | a,c,d |
|  |  | rule_cheapest | 203,478 | 3.05 | ok | 0.998 | 203,479 | 1 | air | - |
|  |  | rule_fastest | 240,838 | 15.05 | ok | 1.000 | 240,838 | 1 | air | a,c,d |
| s2-v1-site-delay | supported 3/3 | cost_optimal | 209,731 | 0.05 | ok | 0.001 | 220,143 | 0 | air | c |
|  |  | risk_adjusted | 216,241 | 6.05 | ok | 1.000 | 216,241 | 0 | air | c,d |
|  |  | balanced | 216,241 | 6.05 | ok | 1.000 | 216,241 | 0 | air | c,d |
|  |  | time_optimal | 216,441 | 7.05 | ok | 1.000 | 216,441 | 0 | air | c,d |
|  |  | rule_cheapest | 229,513 | 0.05 | ok | 0.219 | 230,977 | 6 | air | c |
|  |  | rule_fastest | 234,328 | 7.05 | ok | 1.000 | 234,328 | 1 | air | a,c,d |
| s2-v2-moq-above-need | supported 3/3 | cost_optimal | 240,601 | 0.05 | ok | 0.001 | 251,174 | 15 | air | - |
|  |  | risk_adjusted | 240,801 | 3.05 | ok | 0.997 | 240,803 | 15 | air | - |
|  |  | balanced | 240,801 | 3.05 | ok | 0.997 | 240,803 | 15 | air | - |
|  |  | time_optimal | 240,801 | 3.05 | ok | 0.997 | 240,803 | 15 | air | - |
|  |  | rule_cheapest | 243,948 | 3.05 | ok | 0.998 | 243,949 | 16 | air | - |
|  |  | rule_fastest | 281,308 | 15.05 | FAIL | 1.000 | 281,308 | 16 | air | a,c,d |
| s2-v3-short-shelf-d | supported 3/3 | cost_optimal | 210,972 | 0.05 | ok | 0.002 | 219,534 | 3 | air | - |
|  |  | risk_adjusted | 211,172 | 3.05 | ok | 0.980 | 211,208 | 3 | air | - |
|  |  | balanced | 220,572 | 8.05 | ok | 1.000 | 220,572 | 3 | air | c |
|  |  | time_optimal | 232,942 | 15.05 | ok | 1.000 | 232,942 | 3 | air | a,c,d |
|  |  | rule_cheapest | 211,172 | 3.05 | ok | 0.998 | 211,173 | 3 | air | - |
|  |  | rule_fastest | 250,902 | 15.05 | FAIL | 1.000 | 250,902 | 3 | air | a,c,d |
| s2-v4-budget-cut | supported 4/4 | cost_optimal | 200,131 | 2.05 | ok | 0.818 | 200,515 | 0 | air | - |
|  |  | risk_adjusted | 200,331 | 3.05 | ok | 0.998 | 200,332 | 0 | air | - |
|  |  | balanced | 200,331 | 3.05 | ok | 0.998 | 200,332 | 0 | air | - |
|  |  | time_optimal | 200,331 | 3.05 | ok | 0.998 | 200,332 | 0 | air | - |
|  |  | rule_cheapest | 203,478 | 3.05 | ok | 0.998 | 203,479 | 1 | air | - |
|  |  | rule_fastest | 240,838 | 15.05 | FAIL | 1.000 | 240,838 | 1 | air | a,c,d |

## Failed checks

- s1-v2-tight-budget rule_fastest verify: budget: cost 28700 > budget 15000
- s2-v2-moq-above-need rule_fastest verify: budget: cost 281308 > budget 250000
- s2-v3-short-shelf-d rule_fastest verify: budget: cost 250902 > budget 250000
- s2-v4-budget-cut rule_fastest verify: budget: cost 240838 > budget 205000
