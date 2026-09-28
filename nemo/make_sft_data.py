"""Synthetic training data for a small "spec writer" model: user goal -> {"base", "params"}.

Labels are correct by construction: the parameters are sampled FIRST from the
generator vocabulary (scenarios/gen.py) and the sentence is rendered from them,
in Korean or English, from several phrasings. Every label is also checked by
applying it with scenarios.gen.generate (unknown keys would raise).

  python -m nemo.make_sft_data --n 3000 --seed 11
Writes nemo/data/raw.jsonl. Curation (dedup, filters) is nemo/curate.py (NeMo Curator).
"""
from __future__ import annotations

import argparse
import json
import os
import random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Parameter SHAPES are part of the task (first version listed names only and models answered
# shelf_life_days: 90 instead of {"C": 90}; found by the NeMo Evaluator run on 2026-09-28).
SYSTEM = ("You translate an order-and-transport planning request into JSON {\"base\": \"s1_base\"|\"s2_base\", \"params\": {...}}. "
          "Params (omit any the request does not change): due_days: int (S1 deadline, days from now); budget_usd: number; "
          "shelf_life_days: {item: days}; min_remaining_pct: {item: percent}; max_exposure_hours: number; "
          "allowed_modes: [truck|parcel|air|ocean] (the modes still allowed); delay_mean_days: {mode: days}; "
          "lead_time_add_days: {material: days} (a late site delays every material it makes); moq: {material: n}; "
          "capacity_per_week: {material: n}; batch_shift_days: int (S2, negative = earlier). "
          "s1_base: move 100 units of product C from site A to warehouse B (defaults: due 2026-11-10T18:00Z = 40.75 days, budget 60,000 USD; restating a default changes nothing only if exact). "
          "s2_base: materials a (made only at site A1), b (A2), c and d (A3) for three batches at site AA (default 250,000 USD).")
SITE_ITEMS = {"A1": ["a"], "A2": ["b"], "A3": ["c", "d"]}
MODES_KO = {"ocean": "해상", "air": "항공", "parcel": "택배", "truck": "트럭"}


def s1(rng: random.Random) -> tuple[dict, str]:
    p, ko, en = {}, [], []
    if rng.random() < 0.7:
        d = rng.choice([8, 10, 11, 12, 14, 18, 20, 25, 30, 35, 45, 50, 60])
        p["due_days"] = d
        ko.append(rng.choice([f"{d}일 안에 도착해야 해", f"기한은 {d}일이야", f"{d}일 내 납품"]))
        en.append(rng.choice([f"it must arrive within {d} days", f"the deadline is {d} days", f"deliver in {d} days"]))
    if rng.random() < 0.6:
        b = rng.choice([12000, 15000, 20000, 25000, 30000, 40000, 50000, 80000])
        p["budget_usd"] = b
        ko.append(rng.choice([f"예산은 {b:,}달러", f"쓸 수 있는 돈은 {b:,} USD", f"비용 한도 {b:,}달러"]))
        en.append(rng.choice([f"budget is {b:,} USD", f"we can spend at most ${b:,}", f"cost cap {b:,} USD"]))
    if rng.random() < 0.3:
        sl = rng.choice([90, 100, 120, 150])
        p["shelf_life_days"] = {"C": sl}
        ko.append(f"이 로트는 유통기한이 {sl}일이야")
        en.append(f"this lot has a {sl}-day shelf life")
    if rng.random() < 0.2:
        pct = rng.choice([50, 70, 75, 80])
        p["min_remaining_pct"] = {"C": pct}
        ko.append(f"수령 시 유통기한이 {pct}% 이상 남아야 해")
        en.append(f"at least {pct}% shelf life must remain at receipt")
    if rng.random() < 0.25:
        h = rng.choice([1.5, 2.0, 3.0])
        p["max_exposure_hours"] = h
        ko.append(f"온도 통제 밖 노출은 합계 {h:g}시간 이내")
        en.append(f"total time outside temperature control must stay under {h:g} hours")
    if rng.random() < 0.2:
        m = rng.choice(["ocean", "parcel"])
        allowed = [x for x in ["truck", "parcel", "air", "ocean"] if x != m]
        p["allowed_modes"] = allowed
        ko.append(f"{MODES_KO[m]}은 쓰지 마")
        en.append(f"do not use {m}")
    if rng.random() < 0.2:
        v = rng.choice([4.0, 5.0, 6.06, 8.0])
        p["delay_mean_days"] = {"ocean": v}
        ko.append(f"요즘 해상 지연이 평균 {v:g}일이래")
        en.append(f"ocean delays average {v:g} days these days")
    if not p:
        return s1(rng)
    head_ko = rng.choice(["C 제품 100개를 A에서 B로 보내야 해.", "A 사이트 재고 C 100개를 B 창고로 옮겨야 해.", "C 100개 A→B 운송 계획."])
    head_en = rng.choice(["Ship 100 units of C from A to B.", "We need to move 100 units of product C from site A to warehouse B.", "Plan transport of 100 C from A to B."])
    return p, (head_ko + " " + ", ".join(ko) + ".") if rng.random() < 0.6 else (head_en + " " + "; ".join(en) + ".")


def s2(rng: random.Random) -> tuple[dict, str]:
    p, ko, en = {}, [], []
    if rng.random() < 0.5:
        site = rng.choice(list(SITE_ITEMS))
        d = rng.choice([5, 7, 10, 14])
        p["lead_time_add_days"] = {it: d for it in SITE_ITEMS[site]}
        ko.append(f"{site} 사이트가 모든 발주에서 {d}일씩 늦어진대")
        en.append(f"site {site} is running {d} days late on every order")
    if rng.random() < 0.35:
        it = rng.choice(["a", "b", "c", "d"])
        m = rng.choice([8, 10, 12, 15, 20])
        p["moq"] = {it: m}
        ko.append(f"원료 {it}의 최소 발주량이 {m}개로 바뀌었어")
        en.append(f"the minimum order quantity for material {it} is now {m}")
    if rng.random() < 0.4:
        b = rng.choice([200000, 205000, 210000, 220000, 240000, 300000])
        p["budget_usd"] = b
        ko.append(f"예산은 {b:,}달러")
        en.append(f"budget is {b:,} USD")
    if rng.random() < 0.25:
        it = rng.choice(["b", "d"])
        sl = rng.choice([30, 45, 60, 90])
        p["shelf_life_days"] = {it: sl}
        ko.append(f"원료 {it} 유통기한이 {sl}일로 짧아졌어")
        en.append(f"material {it} now has a {sl}-day shelf life")
    if rng.random() < 0.2:
        sh = rng.choice([-7, 7, 14])
        p["batch_shift_days"] = sh
        ko.append(f"배치 일정이 {abs(sh)}일 {'앞당겨졌어' if sh < 0 else '미뤄졌어'}")
        en.append(f"all batches move {abs(sh)} days {'earlier' if sh < 0 else 'later'}")
    if rng.random() < 0.15:
        it = rng.choice(["a", "b", "c", "d"])
        c = rng.choice([8, 10, 12])
        p["capacity_per_week"] = {it: c}
        ko.append(f"원료 {it} 주간 생산능력이 {c}개로 줄었어")
        en.append(f"weekly capacity for {it} dropped to {c}")
    if not p:
        return s2(rng)
    head_ko = rng.choice(["AA 사이트 배치 3개용 원료 발주 계획이 필요해.", "원료 a, b, c, d를 승인된 사이트에서 받아 AA 배치 3개를 돌려야 해.", "AA 생산용 발주·운송 계획을 짜줘."])
    head_en = rng.choice(["Plan material orders for the three AA batches.", "We need materials a-d from the approved sites for three batches at AA.", "Build the order-and-transport plan for AA production."])
    return p, (head_ko + " " + ", ".join(ko) + ".") if rng.random() < 0.6 else (head_en + " " + "; ".join(en) + ".")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=3000)
    ap.add_argument("--seed", type=int, default=11)
    a = ap.parse_args()
    import sys
    sys.path.insert(0, ROOT)
    from scenarios.gen import generate
    bases = {b: json.load(open(os.path.join(ROOT, "scenarios", "examples", f"{b}.json"))) for b in ("s1_base", "s2_base")}
    rng = random.Random(a.seed)
    out = open(os.path.join(ROOT, "nemo", "data", "raw.jsonl"), "w", encoding="utf-8")
    for i in range(a.n):
        base = "s1_base" if rng.random() < 0.5 else "s2_base"
        params, text = (s1 if base == "s1_base" else s2)(rng)
        generate(bases[base], params, 0)   # the label must be applicable
        label = json.dumps({"base": base, "params": params}, ensure_ascii=False, sort_keys=True)
        out.write(json.dumps({"id": f"g{i:05d}", "text": text, "label": label, "base": base,
                              "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": text}, {"role": "assistant", "content": label}]},
                             ensure_ascii=False) + "\n")
    out.close()
    print(f"wrote {a.n} rows to nemo/data/raw.jsonl")


if __name__ == "__main__":
    main()
