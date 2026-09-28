# 무인 개발 세션 상태 (cargo-recovery-agent v2)

갱신: 2026-09-28 저녁 (Opus 5.5, screen `cargo-dev`)

## 먼저 알아둘 것
- run 1·2 가 rc=1 로 끝난 것은 코드 문제가 아니다. 모델 측 안전장치가 첫 메시지를 거부했다(로그 dev/logs/run-1.log). run 3 부터 정상.
- 루트 디스크 여유가 4.5 GB 라 venv 를 <venv> 에 두었다(리포의 .venv 심링크). 실행은 `.venv/bin/python`.
- 이 서버 GPU 는 쓰지 않는다(지시). 몬테카를로는 CPU, cuOpt 는 설치·인터페이스만.

## 끝낸 것
- 단계 1: 계획 문법 plan/v1 (planner/grammar.py), 검증기(validate.py), 구조 해시(structure.py), 저널(engine/journal.py), CLI.
- 단계 2: 엔진 engine/ (options → lp(MILP, HiGHS/cuOpt) → verify(독립 재계산) → mc(torch) → pareto → run CLI).
  실행: `.venv/bin/python -m engine.run solve scenarios/examples/s1_base.json`

## 측정값
- S1(C 100개 A→B, 40일, 예산 60,000): 해상 8,900 USD(정시 30.6 %, 기대비용 53,706) / sea-air 21,400(99.9 %) / 항공 25,100(100 %). 31초.
- S2(A1·A2·A3→AA, 배치 3개): 200,131(정시 80.5 %) → 200,331(99.8 %) → 209,731 → 222,101(급행). 84초.
- 파손 스펙 12종 전부 거부, 기본 스펙 2종(S1·S2) 통과. `.venv/bin/python -m unittest tests.test_grammar -v` → 3/3 OK.

## 건너뛴 것과 이유
- HiGHS↔cuOpt 목적값 일치 검사: 이 서버 GPU 금지 + libnccl 없음. 테스트는 CARGO_ALLOW_GPU=1에서만 돈다.

## 다음 단계
- 단계 3: 시나리오 뱅크(S1·S2 각 4변형 사전등록) + 합성 생성기 + 기준선 2개.
