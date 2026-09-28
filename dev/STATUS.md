# 무인 개발 세션 상태 (cargo-recovery-agent v2)

갱신: 2026-09-28 밤 (Opus 5.5, screen `cargo-dev`)

## 먼저 알아둘 것
- run 1·2가 rc=1로 끝난 것은 코드 문제가 아니다. 모델 쪽 안전장치가 첫 메시지를 거부했다(dev/logs/run-1.log). run 3부터 정상 진행.
- 이 서버 GPU는 쓰지 않았다(지시). 몬테카를로·Curator는 CPU, cuOpt는 설치·연결만.
- venv는 <venv> (리포의 .venv 심링크). NVIDIA 키는 ~/.config/nvidia/env에서만 읽는다.
- 지금 떠 있는 것: API :8091, 웹 :3200 (둘 다 127.0.0.1). 노트북에서 보려면 `ssh -L 3200:127.0.0.1:3200 <user>@<server>` 후 http://127.0.0.1:3200

## 끝낸 것 (v2 계획서 단계 1~6)
1. 계획 문법 plan/v1 + 검증기 + 구조 해시 + 저널 — 5b3e7c6
2. 엔진: 후보 열거 → MILP(PuLP/HiGHS, cuOpt 백엔드 연결) → 독립 검증 → torch 몬테카를로 → 파레토 4안 — 7e843df
3. 시나리오 뱅크 11개(예측을 실행 전 커밋 29b9a2e) + 판정기 + 규칙 기준선 — 21d6c68
4. NeMo Agent Toolkit 워크플로 + NeMo Guardrails 게이트웨이 — c8520e6
4b. NeMo Curator 정제 + NeMo Evaluator 벤치마크 (LoRA 학습은 보류) — 6ba7d7b
5. 대시보드 5화면 — 6ba7d7b
6. dev/run-all.sh(한 명령), --replay 재현 검사, README, docs/demo-script.md — 이번 커밋

## 측정값
- 시나리오 11/11 지지(기본 2개는 관찰 후 등록). S1: 해상 8,900 USD 정시 30.6 %(기대비용 91,866) / sea-air 21,400 99.9 % / 항공 25,100.
- S2: 엔진이 수요별 탐욕 규칙보다 1.4–8.6 % 쌈.
- 에이전트(자연어 목표 6개): 2회차 파라미터 6/6, 검증된 추천 6/6, 비용=뱅크 6/6 (1건은 판정기 수정으로 통과 — reasoning-log 참고).
- 가드레일: 모델이 없는 예약 도구를 지어낸 2회 모두 차단.
- 재현: 새 셸에서 run-all --replay 1분 49초, 36개 안 차이 0.
- 화면: 14장 콘솔 0, 12px 미만 0, 표 열 밀림 0.
- NeMo Evaluator(목표→스펙): docs/submission-draft 4절과 eval 로그 참고(API 한도로 느림).

## 건너뛴 것과 이유
- NeMo AutoModel LoRA: 사용자 결정으로 보류(데이터·벤치마크 준비됨).
- cuOpt 실행: 서버 GPU 금지 + libnccl 없음. 테스트는 CARGO_ALLOW_GPU=1에서만.
- NemoClaw/OpenShell: Docker/Podman 권한 없음. 원격 설치 스크립트는 무인으로 돌리지 않았다.
- 대시보드 로그인: 127.0.0.1만 바인드해서 미구현.

## 실행이 드러낸 결함 (전부 고침, reasoning-log에 경위)
validate 도달성 필터 누락 · 가장 이른 연결편 가정 · 미수렴 MILP · 지배된 안 선택 · knee 동점 · 생성기가 파라미터를 조용히 무시 ·
게이트웨이 재시도 없음 · 스트리밍 422 · 판정기 파서/문자 비교 · 몬테카를로가 수령 거부를 비용에 안 넣음(에이전트가 발견) ·
표 열 밀림 · 차트 라벨 겹침 · Evaluator 템플릿 치환 실패(0/40) · 실행기 파이프 점유

## 다음 단계 (사용자 결정 필요)
- LoRA 학습 시점과 장소(해커톤 박스?).
- 주최 측에 "NeMo Framework 활용" 인정 범위 확인(Curator·Evaluator 실사용, Agent Toolkit·Guardrails는 에이전트 층).
- 해커톤 박스에서: cuOpt 동등성 테스트, OpenShell 샌드박스.
