# Phase 1 회고

> **기간**: 2026-04-21 (Initial commit) ~ 2026-05-13 (F8 main merge)
> **약 3주 calendar time** (실작업은 condensed bursts)

---

## 1. 완료한 것

- F0 ~ F8 (9 feature) — Phase 1 scope 전체
- 실차 측정 1대 (C1YC_2_MCM) — 박제 5건
- Phase 2 backlog — 7 항목

| Feature | 모듈 | Week |
|---------|------|------|
| F0 | `slow_iter.py` + `batch_iter.py` (long-running task infra) | 1 |
| F1 | Plugin scaffold + menu | 1 |
| F2 | `stats.py` (mesh stats scan) | 2 |
| F3 | `instance_detector.py` (ISM 후보 탐지) | 3 |
| F4 | `small_part_detector.py` (bbox diagonal + Datasmith hierarchy) | 4 |
| F5 | `nx_naming.py` (NX category classifier, 순수 분류기) | 4 |
| F6 | `material_inventory.py` (3-value enum + multi-pattern category) | 5 |
| F7 | `integrated_report.py` (`unreal` 의존 0 aggregator) | 5 |
| F8 | `metadata_tagger.py` (4-tier dispatch + mutation, F-pattern 4번째) | 5 |

박제 (`docs/measurements/`):
- `f4_c1yc_2_mcm.md` — F4 baseline 형식 (Week 4)
- `f5_nx_distribution_c1yc_2_mcm.md` — F5 분포 + zone (Week 5)
- `integrated_report_c1yc_2_mcm.md` — F7 통합 + F8 가설 (Week 5)
- `f8_c1yc_2_mcm.md` — F8 tier 분포 + idempotent 검증 (Week 5)
- `material_analysis_c1yc_2_mcm.md` — F6 3-value enum 정의 (`docs/concepts/`)

---

## 2. 핵심 기술 결정 (변경 없이 유지된 것)

- **Nanite + DLAA + Deferred** (Forward 포기) — `CLAUDE.md` §4
- **Detection only** (Phase 2 mutation, Phase 3 visibility) — Phase 1 scope 원칙
- **F0 batch infrastructure 우선** — 30K mesh freeze 방지 (Week 1 최우선)
- **외부 라이브러리 0건** — Phase 1 자생. Phase 2+ MIT 라이선스 검토 가능
- **C++ 0줄** — Python only

---

## 3. 핵심 함정 3선

### 1. `\b` word boundary + underscore (Week 4 F5 V1)
- Python `\w` 에 `_` 포함 → `_LATCH_` 같은 underscore-bounded 토큰을 `\b` 가 못 잡음
- V1 regex: UNCATEGORIZED 44.4% (🔴 red)
- V2 우회: 명시적 `[_\-]` 경계 또는 anchor (`^`, `$`) → UNCATEGORIZED 22.91% (🟡 yellow)
- 박제: `docs/concepts/nx_naming_patterns.md`

### 2. Datasmith attach hierarchy ≠ folder_path (Week 4 F4)
- `folder_path` 거의 빈 셀 (`Name("None")`)
- 진짜 부품명 = `actor.get_attach_parent_actor().get_actor_label()`
- chain depth 평균 13 (RootNode + DatasmithSceneActor + assembly grouping + RotationPivot)
- noise filter 5종 (RootNode/_asmesh/_RotationPivot/MOVING/EXT) 으로 의미 있는 라벨만 남김
- 박제: `docs/measurements/f4_c1yc_2_mcm.md` § 4

### 3. F6 `override_status` 3-value enum (Week 5 F6 fix)
- 박제 작성 시점 (UE Python Console 1회 추출): `no_override 58.9%` 2-value
- F6 코드 실차 검증: `slot_empty` vs `no_slot` 구분 필요 → 3-value enum 도입
- **박제 self-correction 첫 사례** — `docs/concepts/material_analysis_c1yc_2_mcm.md` § 7 patch + § 8 신설

---

## 4. 핵심 패턴 3선

### 1. F-pattern (측정 / 분류 / 결합 분리)
- F4부터 정립, F8까지 유지
- 측정 = unreal 의존 (`small_part_detector`, `material_inventory`)
- 분류 = 순수 함수 (`nx_naming`, `compute_tier`)
- 결합 = `panel.py` (orchestration + UI)
- 모듈별 `import unreal` 0건 확인 → CI/Glean/단위 테스트 가능

### 2. 박제 의무 (`docs/measurements/`)
- 다음 차량 비교용 baseline metric 코드 블록 의무화
- `grep -F "F4_DIAG_P50_CM"` 같은 cross-vehicle 비교 가능
- self-correction patch 허용 (immutable 아님)

### 3. AI 추정 검증 우선 (CLAUDE.md §5)
- `dir()` + 한 줄 실험 후 본 구현
- Week 1부터 정립, F8 (PR #15) 까지 매번 적용
- 박제: `docs/lessons_learned/api_verification_first.md`

---

## 5. 페이스

- **Week 1** (2026-04-21~23): F0 + F1 — 계획대로 (1 feature / week)
- **Week 2** (2026-04-23~24): F2 — 계획대로
- **Week 3** (2026-05-04): F3 — 계획대로
- **Week 4** (2026-05-04): F4 + F5 — 1일에 2 feature (가속)
- **Week 5** (2026-05-10 + 2026-05-13): F6 + F7 + F8 + 박제 3건 = 8 task in 2일 (condensed)
- **평균**: 약 1주 / feature 유지, buffer 1주 사용
- 가속 구간: 실차 검증이 가능해진 Week 4부터 (가설 사이클 축소)

---

## 6. Phase 2 입력 (decision points)

1. **다음 차량 측정** (backlog #6) — 단일 차량 가정 검증. **1순위**
2. **ERP/PLM supplier-code lookup** (backlog #1) — UNCAT green zone 진입의 유일한 경로. **2순위**
3. **Actor merging** (`CLAUDE.md` §7 원래 계획, F3 결과 입력) — **3순위**
4. **BRACKET threshold 재검토** (backlog #7) — F8 발견, 다음 차량 측정과 묶음
5. **Polished GUI** — 4순위, Phase 2 후반 또는 Phase 3
6. **외부 라이브러리** — MIT 검토, 사내 pip 정책 확인 필요
7. **Phase W (Web)** — 별도 트랙, Phase 2 진행 중 VWV 진척 보면서

우선순위 최종 결정은 Phase 2 kickoff 시점.

---

## 7. 메타 — 회고를 회고하기

- 박제 self-correction (F6 fix) 가 **계획 미반영 추가 task** 였지만 박제 가치 입증
- F-pattern은 F4에서 우연히 발견 → F5/F6/F8까지 의식적으로 적용. **Phase 2 actor merging도 동일 분리 권장**
- 단일 차량 데이터 위험성 — Phase 2 진입 전 차량 1~2건 더 측정 필요 (가설 일반성 검증)
- AI 협업 70:30 비율 유지 — 필립 결정 70%, AI 가속 30%. Phase 2 진입 시 비율 조정 검토 (외부 라이브러리 + actor merging에서 AI 비중 늘릴 수 있음)
