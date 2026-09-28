export type LT = { min: number; likely: number; max: number };
export type Opt = { id: string; supplier: string; site: string; lat?: number | null; lon?: number | null; approved?: boolean; capacity_per_day: number;
  lead_time_days: LT; unit_cost_usd: number; fixed_cost_usd: number; moq: number; lot_size: number; shelf_life_days?: number | null;
  min_remaining_pct?: number; expedite?: { lead_time_cut_days: number; premium_pct: number } | null };
export type DNode = { id: string; task: string; qty_per_unit: number; after: string[]; join: "all" | "any"; options: Opt[] };
export type DStep = { id: string; name: string; nodes: DNode[] };
export type DagSpec = { spec: "dag/v1"; id: string; title: string; hypothesis: string; objective: string;
  demand: { qty: number; unit: string; deadline_days: number; budget_usd: number; product_age_at_start_days: number; shelf_life_days?: number | null; min_remaining_pct_at_delivery: number };
  inventory: { mos_target_months: number; monthly_usage: number; on_hand: number };
  uncertainty: { n_samples: number; seed: number; late_penalty_usd_per_day: number }; steps: DStep[] };
export type NodeRow = { option: string; supplier: string; expedite: boolean; need: number; order_qty: number; overbuy: number; cost_usd: number;
  duration_days: number; lead_time_days: number; ES: number; EF: number; LS: number; slack: number; critical: boolean };
export type Plan = { key: string; cost_usd: number; makespan_days: number; slack_days: number; critical_path: string[]; nodes: Record<string, NodeRow>;
  shelf_problems: string[]; mos_after_months: number | null;
  mc: { p_on_time: number; makespan_p10: number; makespan_p50: number; makespan_p90: number; expected_cost_usd: number;
        histogram: { lo: number; width: number; counts: number[] }; criticality: Record<string, number> } };
export type Result = { status: string; problems?: string[]; n_plans?: number; n_feasible?: number; required_units?: number; objective?: string; hint?: string;
  closest?: Plan; pareto?: { cost_usd: number; makespan_days: number; p_on_time: number; expected_cost_usd: number; key: string }[];
  named?: Record<string, string>; plans?: Record<string, Plan>; recommended?: string; seconds?: number;
  crashing?: { node: string; days_saved: number; extra_cost_usd: number; usd_per_day: number; within_budget: boolean }[];
  flow?: { units_by_deadline: number; demand_units: number; bottleneck: string[]; node_capacity_units: Record<string, number>; method: string; enough: boolean };
  cloud?: { cost_usd: number; makespan_days: number }[] };
export const OBJ: [string, string, string][] = [
  ["min_cost", "최저 비용", "비용이 가장 낮은 안"],
  ["min_time", "최단 기간", "가장 빨리 끝나는 안"],
  ["balanced", "균형", "비용·기간 파레토의 무릎점"],
  ["max_on_time", "정시 확률 최대", "몬테카를로 정시 확률이 가장 높은 안"],
  ["risk", "위험 조정", "지연 벌금 포함 기대비용이 가장 낮은 안"],
];
export const usd = (v?: number | null) => (v == null ? "-" : Math.round(v).toLocaleString("en-US"));
