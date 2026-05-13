# F8 Metadata Tagging — C1YC_2_MCM

> Phase 1 마지막 기능 첫 실차 측정. F4×F5×F6 cross-tab 가설을
> actor tag로 박제. Phase 3 visibility culling 입력 데이터 확보.

| 항목 | 값 |
|------|-----|
| 측정일 | 2026-05-13 |
| 차량 코드 | C1YC_2_MCM |
| 프로젝트 경로 | `C:\Users\BZLS01\Downloads\C1YC_2_MCM` |
| 레벨 | `L_C1YC_2_MCM` |
| Plugin commit | `f339316` (F8 squash) |
| Threshold | 0.5 cm (Tiny preset) |
| Tag prefix | `CADOpt_F8_` |

---

## 1. Tier 분포 (실측)

| Tier | 카운트 | 비중 | 조건 |
|------|--------|------|------|
| `CADOpt_F8_Cull_High` | 1,680 | 3.67% | small AND slot_empty AND nx_category ∈ {LATCH, BRACKET} |
| `CADOpt_F8_Cull_Mid` | 2,499 | 5.46% | small AND slot_empty (그 외 카테고리) |
| `CADOpt_F8_Review` | 2,959 | 6.46% | small AND (has_override OR no_slot) |
| `CADOpt_F8_Keep` (implicit) | 38,671 | 84.42% | not small (tag 부재) |
| **Total** | **45,809** | **100.00%** | |

산술 일관: 1,680 + 2,499 + 2,959 = 7,138 (Tagged) ✓
7,138 + 38,671 = 45,809 (Total) ✓

## 2. F7 § 9 preview ↔ F8 apply 일치 검증

F8 menu 실행 = F4 measurements 입력 + 4-tier dispatch. F7 § 9 preview =
같은 입력 + 같은 dispatch 함수 (mutation 0). 두 출력이 같아야 함 — end-to-end
idempotent.

| Tier | F7 § 9 preview | F8 apply (Run 1) | 일치 |
|------|----------------|------------------|------|
| Cull_High | 1,680 | 1,680 | ✅ |
| Cull_Mid | 2,499 | 2,499 | ✅ |
| Review | 2,959 | 2,959 | ✅ |
| Keep (implicit) | 38,671 | 38,671 | ✅ |
| Total | 45,809 | 45,809 | ✅ |

→ F7 preview = F8 apply. 같은 분류 함수 (`compute_tier`) 공유 보장.

## 3. Tier별 카테고리 breakdown (F5 cross-tab 재활용)

F4×F5 cross-tab (`@ 0.5 cm`) 기준:

| nx_category | small (n) | LATCH/BRACKET? | small ∩ slot_empty 분기 |
|-------------|-----------|----------------|--------------------------|
| FASTENER | 77 | No → Cull_Mid 후보 | Mid + Review |
| VALVE | 80 | No → Cull_Mid 후보 | Mid + Review |
| LATCH | 1,915 | **Yes** → Cull_High 후보 | High + Review |
| BRACKET | **0** | **Yes** but small 0개 | (영향 없음) |
| HOUSING | 362 | No → Cull_Mid 후보 | Mid + Review |
| TRIM | 14 | No → Cull_Mid 후보 | Mid + Review |
| WIRING | 2,035 | No → Cull_Mid 후보 | Mid + Review |
| ASSEMBLY | 1,753 | No → Cull_Mid 후보 | Mid + Review |
| UNCATEGORIZED | 902 | No → Cull_Mid 후보 | Mid + Review |

**Cull_High 1,680개의 출처**: LATCH small 1,915개 중 slot_empty인 것.
BRACKET small이 0이라 BRACKET 기여 0. **이 차종에선 Cull_High = 사실상 LATCH 단독**.

이론적 상한: LATCH 4,505 slot_empty × P(small | LATCH slot_empty). 실측
1,680 ≈ LATCH small의 87.7% (1,680/1,915). 즉 LATCH small 중 12.3%는
slot_empty 아님 → Review로 분류됨.

## 4. Idempotent 검증

Run 1 직후 Run 2 (입력 변경 없음) 실행 결과:

| Tier | Run 1 | Run 2 | 일치 |
|------|-------|-------|------|
| Cull_High | 1,680 | 1,680 | ✅ |
| Cull_Mid | 2,499 | 2,499 | ✅ |
| Review | 2,959 | 2,959 | ✅ |
| Keep (implicit) | 38,671 | 38,671 | ✅ |

→ 두 번째 run에서 actor.modify() skip (fast-path: current_f8 == target_f8).
Tag prefix filter (`CADOpt_F8_*`)로 기존 F8 tag만 제거 후 재부여하는
구조라 재실행 안전.

## 5. 비-F8 tag 보존 검증

사전 actor 1개 (`SM_SkySphere`)에 임시 `UserTag_Preserve_Test` 부여 후 F8 실행:

```
PRESERVED on SM_SkySphere: ['UserTag_Preserve_Test']
```

→ prefix 비매칭 tag 보존. F8 작업이 사용자 또는 다른 도구의 actor tag를
파괴하지 않음 확인.

## 6. 발견 — BRACKET small = 0

**가설** (F8 spec):
- Cull_High = small AND slot_empty AND nx_category ∈ {LATCH, BRACKET}
- 추정: BRACKET (체결/지지부)도 LATCH와 함께 PCVR 최우선 cull 후보

**실측 (C1YC_2_MCM)**:
- BRACKET 총 1,284개 — F5 cross-tab에서 small@0.5cm = 0개
- 즉 0.5cm Tiny preset에선 BRACKET이 Cull_High 분류에 전혀 기여하지 않음
- Cull_High 1,680개는 사실상 LATCH 단독 (BRACKET 0)

**해석**:
- BRACKET은 정의상 "구조 지지 부품"이라 작은 ones가 적을 수 있음
- 또는 (이 차종 한정) BRACKET 부품 자체가 큰 것들만 모델링됨
- 차량 1대 데이터로 단정 불가 — Phase 2 backlog #7로 박제 (다음 차종 검증)

## 7. 다음 차량 비교용 baseline metric

```
F8_TOTAL = 45809
F8_TAGGED = 7138
F8_IMPLICIT_KEEP = 38671
F8_CULL_HIGH = 1680            # 3.67%
F8_CULL_MID = 2499             # 5.46%
F8_REVIEW = 2959               # 6.46%
F8_KEEP_PCT = 84.42
F8_BRACKET_SMALL = 0           # 가설 검증 키
F8_CULL_HIGH_LATCH_DOM = TRUE  # LATCH 단독 기여 (BRACKET 0)
F8_IDEMPOTENT_VERIFIED = TRUE
F8_NON_F8_TAG_PRESERVED = TRUE
```

## 8. 관련 산출물

- Plugin commit: `f339316` (F8 squash)
- F8 CSV: `Saved/CAD_Optimizer/f8_metadata_20260513_100653.csv` (Philip 로컬)
- F7 integrated report: `Saved/CAD_Optimizer/integrated_report_20260513_103623.md`
- 코드:
  - `Content/Python/cad_optimizer/metadata_tagger.py` (신규, unreal 의존 0)
  - `Content/Python/cad_optimizer/ui/panel.py` (메뉴 entry wiring)
  - `Content/Python/cad_optimizer/ui/menu.py` (메뉴 등록)
  - `Content/Python/cad_optimizer/integrated_report.py` (§ 9 preview)

## 9. 다음 측정 시 체크할 점

- **BRACKET small 비율** 다른 차종에서도 0%인지 (Phase 2 backlog #7 핵심 입력)
- **Cull_High = LATCH 단독** 차종 일반성 — 다른 차종에서 BRACKET 합류 여부
- **Tier 비중 안정성** — 3.67% / 5.46% / 6.46% / 84.42% 가 차종 간 유사한지
- **not_found_in_level 카운트** (F4 측정 시점과 F8 실행 시점 사이 actor 삭제 등 stale ref 발생 빈도)
- **Implicit Keep 비중 84.42%** 가 다른 차종에서도 80%+ 유지되는지 — Phase 3 visibility culling 효과 예상치 안정성
