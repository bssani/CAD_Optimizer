# F5 NX Category Distribution — C1YC_2_MCM

> **출처**: F4+F5 통합 CSV (post-F5 plugin 재생성, 17 columns)
> **측정일**: 2026-05-09
> **목적**: F5 분류기의 실차 분포 박제 + V2 regex 회귀 검증.
> **Plugin commit**: e191201 (Week 4 cleanup, F5 포함)

---

## 1. 측정 개요

- Total measured: **45,809**
- Plugin commit: e191201
- Source CSV column: `nx_category` (post-F5 schema)
- 분석 도구: 회사 머신 Glean (사내 LLM, CSV 직접 접근)

Sanity check ✓:
- 9 카테고리만 발생 (예상 외 카테고리 0)
- Total = 45,809 (입력 row 수와 일치)
- `parent_part_label` 빈 행 4개 (root-level mesh) 모두 UNCATEGORIZED 분류

---

## 2. 카테고리 분포 (9 categories)

| nx_category | Count | % |
|-------------|-------|---|
| FASTENER | 7,439 | 16.24% |
| VALVE | 481 | 1.05% |
| LATCH | 4,811 | 10.50% |
| BRACKET | 1,284 | 2.80% |
| HOUSING | 2,238 | 4.89% |
| TRIM | 1,240 | 2.71% |
| WIRING | 6,086 | 13.29% |
| ASSEMBLY | 11,734 | 25.62% |
| UNCATEGORIZED | 10,496 | 22.91% |
| **Total** | **45,809** | **100.00%** |

ASSEMBLY가 최대 (25.62%), 그 다음 UNCATEGORIZED (22.91%) → keyword regex 천장.

---

## 3. nx_category × is_small (Tiny @ 0.5 cm) 교차표

| nx_category | small | not small | total | % small |
|-------------|-------|-----------|-------|---------|
| FASTENER | 77 | 7,362 | 7,439 | 1.04% |
| VALVE | 80 | 401 | 481 | 16.63% |
| LATCH | 1,915 | 2,896 | 4,811 | **39.80%** |
| BRACKET | 0 | 1,284 | 1,284 | 0.00% |
| HOUSING | 362 | 1,876 | 2,238 | 16.18% |
| TRIM | 14 | 1,226 | 1,240 | 1.13% |
| WIRING | 2,035 | 4,051 | 6,086 | 33.44% |
| ASSEMBLY | 1,753 | 9,981 | 11,734 | 14.94% |
| UNCATEGORIZED | 902 | 9,594 | 10,496 | 8.59% |

**관찰**:
- LATCH 39.80% small — 카테고리 내 small 비율 최고. 의미상 부합 (LATCH 부속 부품은 작은 metal 핀/스프링이 많음).
- BRACKET 0% small — bracket은 정의상 구조 지지 부품이라 작을 수 없음. F5 분류 정합성 확인.
- WIRING 33.44% small — 케이블 connector / clip 작은 부품 surfacing.
- FASTENER 1.04%만 small — 흥미로움. BOLT/NUT 등이 expected small이지만 bbox diagonal은 head 부피 포함이라 0.5cm 넘는 경우 다수. M2~M5 fastener 형상 확인 필요.

---

## 4. Small parts top 5 by category (절대 카운트)

| Rank | nx_category | small parts |
|------|-------------|-------------|
| 1 | WIRING | 2,035 |
| 2 | LATCH | 1,915 |
| 3 | ASSEMBLY | 1,753 |
| 4 | UNCATEGORIZED | 902 |
| 5 | HOUSING | 362 |

PCVR 최적화 우선순위: WIRING + LATCH + ASSEMBLY 합 = 5,703 (76% of all small parts).

---

## 5. UNCATEGORIZED zone 판정

| 지표 | 값 |
|------|-----|
| Count | 10,496 |
| % of 45,809 | 22.91% |
| Zone | 🟡 **yellow** (10–30%) |

Acceptance 기준: `<10% green / 10-30% yellow / >30% red`.
22.91%는 yellow zone — keyword regex 접근의 사실상 천장 (`docs/concepts/nx_naming_patterns.md` Section 8 참조). green 진입은 ERP/PLM supplier-code lookup 도입 필요 (Phase 2 backlog #1).

---

## 6. 회귀 검증 — nx_naming_patterns.md 박제 vs F5 실측

| Source | UNCATEGORIZED | Total | % |
|--------|---------------|-------|---|
| nx_naming_patterns.md (PR #5, parent_part_label 단독 분석) | 10,492 | 45,805 | 22.91% |
| F5 expected (root-level 4 추가 → 모두 UNCATEGORIZED) | 10,496 | 45,809 | 22.91% |
| F5 measured (이번 측정) | 10,496 | 45,809 | 22.91% |

**검증 결과: ✅ PASS** — measured와 expected 차이 = **0 actor**. F5 코드(`nx_naming.py`)와 V2 regex 박제가 글자 단위 일치 확인. 코드↔박제 mismatch 0건.

(주: 박제 prompt에서 expected를 "22.92%"로 표기했지만 정확한 값은 10,496/45,809 = 22.9107…% → 2 decimal 반올림 시 22.91%. 동일 값.)

---

## 7. 다음 차량 비교용 baseline metric

```
F5_TOTAL = 45809
F5_FASTENER = 7439          # 16.24%
F5_VALVE = 481              # 1.05%
F5_LATCH = 4811             # 10.50%
F5_BRACKET = 1284           # 2.80%
F5_HOUSING = 2238           # 4.89%
F5_TRIM = 1240              # 2.71%
F5_WIRING = 6086            # 13.29%
F5_ASSEMBLY = 11734         # 25.62%
F5_UNCATEGORIZED = 10496    # 22.91%
F5_UNCAT_PCT = 22.91

# Cross-tab — small parts by category
F5_SMALL_LATCH_PCT = 39.80      # in-category, 카테고리 내 small 비율 최고
F5_SMALL_WIRING_ABS = 2035      # absolute, top across categories
F5_SMALL_TOP3_SUM = 5703        # WIRING + LATCH + ASSEMBLY = 76% of all small
F5_SMALL_BRACKET_PCT = 0.00     # 정의상 sanity check
```

---

## 8. 다음 차량 측정 시 체크할 점

- **UNCATEGORIZED 비율 일관성**: 22.91% 가 차량 간 안정적인가, 또는 모델별 (truck/SUV/EV) 큰 변동이 있는가
- **ASSEMBLY 비중 (25.62%)**: 분포가 차량 간 안정적이면 Phase 2 ASSEMBLY sub-classification (backlog #2) 우선순위 결정 근거
- **회귀 검증 PASS/FAIL 재확인**: F5 코드와 V2 regex 박제 정합성을 매 측정마다 검증
- **BRACKET 0% small** 정합성: 다른 차량에서도 bracket이 정의상 작지 않은가
- **LATCH small 비율 39.80%** 일반성: 작은 latch component가 차량 공통 패턴인지
- **신규 categories 후보**: alpha tokens 분포가 크게 바뀌면 V3 regex 검토 (현재 V2 안정)
