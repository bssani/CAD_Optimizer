# Week 4 — F4 + F5

> **기간**: 2026-05-04 ~ 2026-05-04 (1일 완료)
> **Phase**: 1 / Week 4 of 5
> **상태**: ✅ 완료

---

## 완료 Task

| # | Task | 핵심 산출물 | Commit/PR |
|---|------|-----------|-----------|
| 1 | F4 1차 구현 (small part detection v2) | bbox diagonal + threshold preset (Tiny/Small/Medium) + multi-threshold simulation + CSV | (이전 세션, F4 branch 작업) |
| 2 | F4 실 CAD hierarchy 검증 (별도 UE 프로젝트) | C1YC_2_MCM 107K actors 분석 — leaf actor_label 99%+ Geometry*, parent 식별, chain depth 13 평균, multi-leaf 9.4% | (검증 단계, plugin 미장착) |
| 3 | F4 보강 (옵션 2) — ISMA 제거 + hierarchy 컬럼 4개 | parent_part_label / parent_chain_path / parent_leaf_count / is_multi_leaf, skipped_no_attach_parent 신규 | PR #3 (squash) |
| 4 | F2/F3/F4 stacked PR 정리 | F2 일반 merge + cherry-pick / F3 rebase + squash / F4 rebase + squash | PR #1, #2, #3 |
| 5 | F4 실차 첫 측정 + 박제 | C1YC_2_MCM 45,809 measured, P10/P50/P90 = 0.2/2.7/18.2cm, Tiny@0.5cm 7,138 (15.6%) | PR #4 |
| 6 | NX naming patterns 분석 + 박제 | V2 regex 8 카테고리, UNCATEGORIZED 22.91% (yellow), `\b` word boundary 함정 V1→V2 우회 | PR #5 |
| 7 | Phase 2 backlog 박제 | 5 항목 + 1 열린 항목 — supplier code lookup / ASSEMBLY sub / disjoint mesh / zero-bbox epsilon / collapsed actor 정책 | PR #6 |
| 8 | F5 NX naming classification 구현 | nx_naming.py 신규 (순수 분류기, unreal 의존 0), panel.py에 nx_category 컬럼 + Output Log block 결합. small_part_detector / menu 변경 0건 | PR #7 |

### 측정 결과 (C1YC_2_MCM, F4 단독)

```
Scanned: 107,882 actors (45,809 StaticMeshActor)
Measured: 45,809
Tiny preset (<0.5cm): 7,138 (15.6%)
Diagonal P10/P50/P90: 0.2 / 2.7 / 18.2 cm
NX category distribution: (F5 통합 측정은 다음 차량/세션에 박제)
```

→ F4 + F5 통합 측정은 다음 차량 측정 시 박제. 본 week log는 구현 진행만 기록.

---

**Variation**: 이번 Week 4 생략 (실차 검증 + 박제 비중이 큼).

---

## 학습한 핵심 개념 3개

### 1. 측정과 분류 책임 분리 (F4 / F5 모듈 분리)
- F4 = measurement (`small_part_detector.py`)
- F5 = classification (`nx_naming.py`, 순수 분류기)
- 결합 = `panel.py` (UI/orchestration 레이어)
- F5는 `unreal` import 0건 → 단위 테스트 가능, 다른 환경 (CI/Glean) 에서 동작
- F-pattern 재사용 가능: 향후 F6/F7도 같은 분리 적용

### 2. Datasmith CAD hierarchy = attach 기반 (folder 아님)
- folder_path는 거의 빈 셀 (`Name("None")`)
- 진짜 부품명 = `actor.get_attach_parent_actor().get_actor_label()`
- chain depth 평균 13 (RootNode + DatasmithSceneActor + assembly grouping + RotationPivot)
- noise filter 5종 (RootNode/_asmesh/_RotationPivot/MOVING/EXT)으로 의미 있는 라벨만 남김
- → F6/F7도 actor hierarchy 보려면 같은 가정 적용

### 3. Python `\b` word boundary 함정 (NX V1 → V2)
- `\w`에 underscore 포함 → `_LATCH_` 같은 underscore-bounded 토큰을 `\b`가 못 잡음
- 우회: 명시적 `[_\-]` 경계 또는 anchor (`^`, `$`)
- V1: UNCATEGORIZED 44.4% → V2: 22.91%
- 미래 regex 작성 시 동일 함정 주의 (lessons learned 박제 안 됨, 본 week log + nx_naming_patterns.md에 캡처)

---

## 막혔던 점 + 해결

| 문제 | 증상 | 해결 |
|------|------|------|
| F2 PR이 일반 merge로 처리됨 (squash 아님) | 4 commit이 leftover, F3 rebase 시 섞임 | F2 follow-up cherry-pick → main 동기화 후 F3/F4 정상 squash |
| F4 ISMA 로직이 잘못된 가정 | `unreal.InstancedStaticMeshActor` 클래스 자체 부재. 1차 구현의 isinstance 체크는 noop | 보강 (옵션 2)에서 ISMA 코드 완전 제거 + Datasmith hierarchy 컬럼 4개 추가 |
| `\b` word boundary가 underscore-bounded 못 잡음 | V1 regex로 UNCATEGORIZED 44.4% (red zone) | V2에서 명시적 `[_\-]` 경계로 우회. 22.91% (yellow) |
| 실 CAD 데이터 외부 반출 금지 | Claude Code가 CSV 직접 못 읽음 | 회사 머신 Glean 우회 — 분석 prompt 넣고 결과 표만 chat 복붙 |

---

## Week 5 진입 시 주의

1. **F6 (material consolidation)도 F4/F5와 같은 분리 패턴**: measurement 모듈 + classification 모듈 + panel 결합. 메뉴 단일화.
2. **F7 (report)이 F2/F3/F4/F5 산출물 통합** — 각 모듈의 CSV/Report 객체를 받아서 하나의 통합 report. 모듈 간 join key 결정 필요 (actor_label? parent_part_label? mesh_path?).
3. **F8 (metadata tagging) Phase 3 대비** — Tag 형식 / 어떤 actor에 어떤 tag 부여할지 설계 우선.
4. **실차 측정은 F-별 1회 + Week 5 끝 통합 검증 1일** (이전 결정 — 페이스 buffer).
5. **F5 실차 측정 미실행** — F5 구현은 끝났지만 실차 데이터로 NX category distribution 측정은 미박제. Week 5 중 F6/F7과 묶어서 한 번 박제.
6. **Output Log #1 multi 마커 누락 (저번 세션 미해결)** — F4 Output Log smallest 10 표시에서 #1 multi=N 마커가 잘림. CSV는 정확. panel.py format string 정렬 이슈 가능. F6 시작 전 30분 fix 권장.

---

## 다음 세션 시작 시 (CLAUDE.md §9)

- 이 문서 + CLAUDE.md (v0.7) + `docs/measurements/f4_c1yc_2_mcm.md` + `docs/phase2_backlog.md` 첨부
- 현재: Phase 1 Week 5 진입 직전, F2~F5 PR merge 완료, main only
- 목표: F6 (material consolidation) + F7 (리포트) + F8 (metadata tagging)
- 예상 첫 task: "F6 spec 설계 — material slot 분석 vs material asset 분석 vs 둘 다"
