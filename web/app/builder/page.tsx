import { Builder } from "../../components/builder/Builder";

export const metadata = { title: "Plan Builder — Cargo Planner" };

export default function Page() {
  return (
    <div className="grid gap-5">
      <div>
        <div className="kicker">Plan Builder</div>
        <h1 className="text-h1 font-semibold">가설을 스펙으로 적고, 실행하고, 결과를 봅니다</h1>
        <p className="mt-1 max-w-[900px] text-body text-muted">
          단계 → 작업 → 승인 공급처를 트리로 적습니다. 엔진은 모든 공급처·급행 조합을 풀어 CPM 주공정, PERT 몬테카를로 정시 확률,
          최대 유량 병목, 크래싱 비용을 계산하고, 고른 목표에 맞는 안을 추천합니다.
        </p>
      </div>
      <Builder />
    </div>
  );
}
