# Phase 2 Backlog

> Phase 1 진행 중 발견된, Phase 1 scope 밖이라 의도적으로 미룬 항목.
> Phase 2 진입 시 본 문서가 입력. 각 항목은 "발견 → 미룬 이유 → Phase 2 액션" 구조.
> ADR과 다름 — ADR은 결정 기록, 본 문서는 미결정 미해결 항목 모음.

---

## 1. ERP/PLM supplier-code → category lookup

**출처**: `docs/concepts/nx_naming_patterns.md` (PR #5)

**발견 정황**:
- C1YC_2_MCM의 NX naming V2 regex 적용 시 UNCATEGORIZED 22.91%
- UNCATEGORIZED 상위 30개 중 22개가 단일 supplier 일련번호 패턴 (`BOQ28188_001_226851xxx`). 영문 키워드 0개라 keyword regex로는 분류 불가
- → keyword 기반 분류의 천장. ERP/PLM에 supplier code → 부품 카테고리 매핑이 있으면 회수 가능

**미룬 이유**:
- ERP/PLM 접근 권한 / API 미파악
- Phase 1 = core recipes 정신과 어긋남 (외부 시스템 의존)

**Phase 2 액션**:
- ERP/PLM 접근 가능 여부 확인
- 가능하면 supplier code lookup 함수 추가 → keyword regex 매칭 실패 시 fallback
- UNCATEGORIZED 비율 재측정 (목표: <10% green zone)

---

## 2. ASSEMBLY sub-classification

**출처**: `docs/concepts/nx_naming_patterns.md`

**발견 정황**:
- 현재 ASSEMBLY 카테고리는 `*_ASM-*` 패턴만 잡음. LATCH_ASM-, VALVE_ASM-, SEAT_ASM-, MODULE_ASM- 모두 ASSEMBLY로 묶임
- PCVR 평가 관점에서 LATCH assembly와 SEAT assembly는 시각적 비중 다름

**미룬 이유**:
- Phase 1 = 거친 카테고리화 (8개) 우선. 데이터 1대로 sub-classification 정밀화 못 함

**Phase 2 액션**:
- 다음 차량 측정 후 ASSEMBLY 내부 분포 보고 sub-pattern 도출
- LATCH > LATCH_ASM, VALVE > VALVE_ASM 같은 priority rule (LATCH 카테고리가 ASSEMBLY보다 우선)이 이미 도입된 상태 — Phase 2는 잔여 ASSEMBLY 분해

---

## 3. F4 disjoint mesh — multi-leaf 부품 N leaf bbox 합산

**출처**: F4 spec (`small_part_detector.py` docstring), `docs/measurements/f4_c1yc_2_mcm.md`

**발견 정황**:
- C1YC_2_MCM에서 multi-leaf (한 부품이 N leaf로 split) 비율 약 9.4%
- 현재는 `is_multi_leaf` 플래그로 surfacing만 하고 측정은 leaf 단위 — disjoint 부품의 한쪽만 작아도 small part로 잘못 분류 가능
- VALVE_ASM 케이스가 smallest top 1, 2에 떴음 (multi=2)

**미룬 이유**:
- 합산 정의 모호 (axis-aligned union? oriented? convex hull?). 단순 union은 거대 bbox 양산 → false positive
- Phase 1 = detection only 원칙. 합산은 actor 의미 변경 (둘을 한 단위로 봄) — measurement가 아니라 modeling 결정

**Phase 2 액션**:
- 합산 알고리즘 결정 (axis-aligned union 우선 권장 — 단순)
- 합산 bbox와 leaf bbox 둘 다 CSV에 박제 (사용자가 비교 가능)
- false positive/negative 비율 재측정

---

## 4. F4 zero-bbox epsilon

**출처**: F4 1차 검증 self-review #1, `docs/measurements/f4_c1yc_2_mcm.md` Section 6

**발견 정황**:
- 현재 zero-bbox 분기는 `extent.x == 0 and y == 0 and z == 0` (3축 모두 정확히 0)
- C1YC_2_MCM smallest 10의 #1~8이 0.001 cm — extent.x=0.001, y=0, z=0 같은 한 축 collapsed actor
- 이게 zero-bbox 분기를 통과하여 measurement에 포함됨 (의도된 동작 — 진단 신호로 surfacing)

**미룬 이유**:
- Phase 1에서 "진단 신호 surfacing"으로 판단. 실제 PCVR cull 후보 1순위로 정확
- epsilon 도입은 정책 결정 (어디까지 0으로 볼 것인가) — 데이터 더 보고 결정

**Phase 2 액션**:
- 0.001 cm 같은 collapsed actor를 어떻게 처리할지 정책 결정 (다음 항목 5와 묶음)
- epsilon 값 결정 후 zero-bbox 분기 보강 vs 별도 카운터 (`skipped_collapsed`) 추가

---

## 5. F4 한 축 collapsed actor 처리 정책

**출처**: 위 4와 동반 발견

**발견 정황**:
- 한 축 collapsed actor (예: extent x=0.001, y=0, z=0)는 의미상 면/선/점 — 시각적 비중 0
- 현재는 small part로 정확히 surfacing되어 사용자가 인지함

**미룬 이유**:
- 처리 정책 (cull / re-import / 무시) 미결정. CAD pipeline 상류에서 발생한 import 결함일 가능성 — 처리 위치가 F4가 아닐 수 있음
- Phase 1 = detection only

**Phase 2 액션**:
- collapsed actor가 import 결함인지 의도된 데이터인지 Design Center 확인
- 결함이면 import 단계에서 처리 (Datasmith reimport / source CAD fix)
- 의도된 데이터면 별도 카테고리 (`COLLAPSED`) 부여하여 PCVR cull 후보로 명시

---

## 6. (열린 항목) 다음 차량 측정

본 backlog는 차량 1대 (C1YC_2_MCM) 데이터로 도출됨. 다음 차량 측정 시 본 문서의 가정이 유효한지 재검증:
- multi-leaf 9.4% 비율 일반성
- UNCATEGORIZED 22.91% 일반성
- ASSEMBLY 내부 분포
- collapsed actor 발생 여부
- **BRACKET small@0.5cm = 0 일반성** (항목 7 참조)

다음 차량 측정 결과는 `docs/measurements/f4_<차량코드>.md`에 박제하고 본 backlog patch.

---

## 7. BRACKET small threshold 재검토

**출처**: F8 C1YC_2_MCM 첫 측정 (`docs/measurements/f8_c1yc_2_mcm.md` § 6)

**발견 정황**:
- F8 tier schema 가설: `Cull_High = small AND slot_empty AND nx_category ∈ {LATCH, BRACKET}`
- C1YC_2_MCM 실측: BRACKET small@0.5cm = **0개** (전체 BRACKET 1,284 중) → Cull_High 사실상 LATCH 단독 기여
- BRACKET은 정의상 "구조 지지 부품"이라 0.5cm Tiny preset 통과 불가능할 가능성
- 즉 Tier schema의 BRACKET 포함 자체가 (이 차종에서) dead branch

**미룬 이유**:
- 차량 1대 데이터로 일반화 불가. 다른 차종 (truck/SUV/EV)에서도 BRACKET small 0%인지 검증 필요
- 일관되면 schema에서 BRACKET 제거 (Cull_High = LATCH only)
- 일관되지 않으면 유지 (또는 BRACKET 전용 threshold 도입)
- Phase 1 = 가설 박제, 정밀화는 Phase 2

**Phase 2 액션**:
- 다음 차량 2~3대 측정 후 BRACKET small 비율 박제
- 0% 일관 → tier schema 정정 (LATCH 단독)
- 변동 있음 → BRACKET 전용 threshold (예: 2cm) 도입 검토, 또는 BRACKET을 별도 tier로 분리

**관련 backlog**: 본 항목 + #6 (다음 차량 측정)이 동반 진행

---

## 8. ✅ BP_ISMHolder → Plugin Content 이전 (완료 2026-06-01)

**출처**: Phase 2 actor merger 구현 (`docs/measurements/actor_merging_c1yc_2_mcm.md` § 5.4)

**해결**:
- BP 이전: `/Game/Blueprints/BP_ISMHolder` → `/CAD_Optimizer/Blueprints/BP_ISMHolder` (Plugin Content)
- `panel.py:_BP_ISMHOLDER_PATH` 갱신
- Plugin redistribute 시 .uasset 동봉됨 → 다른 project에서 즉시 사용 가능
- Project Content (`/Game/`) 의 기존 reference는 사용자가 UE Editor에서 직접 Move (auto fix-up)

**잔여 (선택)**:
- 다른 빈 project에서 plugin install 후 smoke test (single vehicle 검증으로 충분, redistribute 직전 검토)

---

## 9. ✅ F2 보강 — ISM section 통합 카운트 (완료 2026-06-01)

**출처**: Phase 2 actor merger 박제 §5.2

**해결**:
- `MeshStatsReport` 3 field 추가:
  - `ism_holder_actor_count`
  - `ism_total_instances`
  - `ism_material_sections`
- `collect_mesh_stats` non-SMA branch에서 ISMC 측정 (Phase 2 sentinel tag 의존성 없음)
- `panel.py:_log_report` 에 ISM block + `Real Drawcall (SMA+ISM)` 통합 행

**실측 검증 (C1YC_2_MCM 머지 후)**: Real Drawcall = 39,613 → Pre-APPLY 45,809 − 39,613 = 6,196 (Phase 2 estimated 일치). 박제 §5.2 갱신.

---

## 10. ✅ APPLY 후 F3 candidate=0 명시적 검증 (완료 2026-06-01)

**출처**: Phase 2 박제 § 4

**해결**:
- BP relocate PR Dry Run 실행 시 자연스럽게 검증됨
- Pre-APPLY: 28,271 groups, **303 candidates**, est. reduction 6,196
- Post-APPLY: 27,968 groups, **0 candidates**, est. reduction 0
- → 자연 idempotent 실측 PASS. 박제 § 4 갱신.

---

## 11. Actor merging multi-material slot 검증

**출처**: Phase 2 박제 § 2

**발견 정황**:
- C1YC_2_MCM 303 candidate 모두 num_materials=1 (Top 1 MI_SectionMisc 99.3% 점유)
- F3 `estimated_drawcall_reduction = sum((count-1) * num_materials)` 가 byte 일치
- num_materials > 1 그룹에서 같은 식이 정확한지 미검증

**Phase 2 액션**:
- 다른 차종 (multi-section material 흔한 차종) 측정으로 multi-slot 검증
- 불일치 시 식 보강 또는 grouping 정책 재검토
