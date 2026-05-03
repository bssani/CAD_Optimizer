# NX Naming Patterns — F5 분류 근거

> **출처**: C1YC_2_MCM F4 측정 (2026-05-04, 45,805 parent labels)
> **목적**: F5 (naming filter)의 카테고리 regex 도출 근거 박제
> **상태**: Phase 1 초안 — 다음 차량 측정 후 정밀화 예정

---

## 1. 분석 데이터

- 입력: `Saved/CAD_Optimizer/small_part_report_20260504_020105.csv`
  (Philip 로컬 / 회사 머신 — repo 미동봉)
- 분석 대상: **45,805 labels** (전체 45,809에서 root-level 4개 제외)
- Plugin commit: `843e73b` (F4)
- 분석 실행 환경: 회사 머신의 Glean (사내 LLM, 사내 데이터 직접 접근 가능)

---

## 2. 빈출 토큰 — 첫 토큰 (split by `_`) Top 30

각 `parent_part_label`을 `_`로 split해 첫 토큰만 카운트.

| Rank | Token | Count | % |
|------|-------|-------|---|
| 1 | BDE09660 | 2,872 | 6.3% |
| 2 | 84815023 | 2,018 | 4.4% |
| 3 | 84815022 | 2,012 | 4.4% |
| 4 | BKF25249 | 781 | 1.7% |
| 5 | 13551254 | 735 | 1.6% |
| 6 | 12747161 | 658 | 1.4% |
| 7 | BKE11927 | 436 | 1.0% |
| 8 | BTK11914 | 421 | 0.9% |
| 9 | 84742085 | 354 | 0.8% |
| 10 | 13535098 | 339 | 0.7% |
| 11 | 11546843 | 330 | 0.7% |
| 12 | 26598724 | 329 | 0.7% |
| 13 | BTH67573 | 299 | 0.7% |
| 14 | BTK12488 | 289 | 0.6% |
| 15 | 12707959 | 283 | 0.6% |
| 16 | 11547581 | 276 | 0.6% |
| 17 | 13557529 | 245 | 0.5% |
| 18 | SCP02011 | 240 | 0.5% |
| 19 | 11611072 | 234 | 0.5% |
| 20 | BOU26193 | 223 | 0.5% |
| 21 | 13569973 | 220 | 0.5% |
| 22 | BTB06701 | 219 | 0.5% |
| 23 | BTH95812 | 217 | 0.5% |
| 24 | BOE75242 | 201 | 0.4% |
| 25 | BSH53769 | 193 | 0.4% |
| 26 | BOZ51612 | 190 | 0.4% |
| 27 | BTK08701 | 188 | 0.4% |
| 28 | 84763115 | 187 | 0.4% |
| 29 | BEZ01225 | 185 | 0.4% |
| 30 | 11547421 | 174 | 0.4% |

**관찰**: Top 30이 전부 GM internal part code (8자 영숫자 또는 숫자). 카테고리 추출엔 직접 가치 없음 — supplier/parts master lookup 필요 (Phase 2+ 백로그).

---

## 3. 빈출 토큰 — 영문 토큰 Top 30 (regex 도출의 핵심)

각 라벨을 `_` 와 `-` 양쪽으로 split (정규식 `[_\-]`), 순수 영문자 토큰만 카운트.

| Rank | Token | Count | % |
|------|-------|-------|---|
| 1 | ASM | 22,485 | 10.3% |
| 2 | SEAT | 7,901 | 3.6% |
| 3 | R | 6,897 | 3.2% |
| 4 | FRT | 6,663 | 3.1% |
| 5 | RH | 5,273 | 2.4% |
| 6 | LATCH | 4,522 | 2.1% |
| 7 | BOLT | 3,648 | 1.7% |
| 8 | WRG | 3,471 | 1.6% |
| 9 | CABLE | 3,211 | 1.5% |
| 10 | RTD | 2,973 | 1.4% |
| 11 | STRUT | 2,968 | 1.4% |
| 12 | SCREW | 2,966 | 1.4% |
| 13 | RR | 2,952 | 1.4% |
| 14 | S | 2,754 | 1.3% |
| 15 | HARNESS | 2,491 | 1.1% |
| 16 | MASTER | 2,198 | 1.0% |
| 17 | LH | 2,174 | 1.0% |
| 18 | D | 2,114 | 1.0% |
| 19 | INSTALLED | 2,114 | 1.0% |
| 20 | F | 2,010 | 0.9% |
| 21 | MODULE | 1,985 | 0.9% |
| 22 | NUT | 1,650 | 0.8% |
| 23 | CLIP | 1,505 | 0.7% |
| 24 | FASCIA | 1,351 | 0.6% |
| 25 | REINFORCEMENT | 1,328 | 0.6% |
| 26 | COVER | 1,142 | 0.5% |
| 27 | TRIM | 1,113 | 0.5% |
| 28 | LH1 | 1,081 | 0.5% |
| 29 | REINF | 1,066 | 0.5% |
| 30 | BACKING | 1,024 | 0.5% |

**관찰**:
- ASM(10.3%): assembly marker — `_ASM[-_]` 패턴으로 ASSEMBLY 카테고리에 매핑
- 직위/방향 토큰 (R, FRT, RH, RR, LH, F, D, S): 카테고리 키워드 아님 — 무시
- WRG/HARNESS/CABLE 합 ~6.6% → **WIRING** 신규 카테고리 정당화
- LATCH/BOLT/SCREW/MODULE/COVER/TRIM/NUT/CLIP은 초안 regex에 이미 포함
- FASCIA/REINF/REINFORCEMENT/BACKING → BRACKET/TRIM 확장 후보

---

## 4. 카테고리 regex (Phase 1 V2 — 최종)

```python
import re

NX_CATEGORY_PATTERNS = {
    "FASTENER":  re.compile(r'(?:^|[_\-])(BOLT|NUT|SCREW|CLIP|WASHER|RIVET)(?=[_\-]|$)', re.IGNORECASE),
    "VALVE":     re.compile(r'(?:^|[_\-])(VALVE|PMP)(?=[_\-]|$)', re.IGNORECASE),
    "LATCH":     re.compile(r'(?:^|[_\-])(LATCH|LOCK|HINGE)(?=[_\-]|$)', re.IGNORECASE),
    "BRACKET":   re.compile(r'(?:^|[_\-])(BRKT|BRACKET|SUPPORT|REINF|REINFORCEMENT)(?=[_\-]|$)', re.IGNORECASE),
    "HOUSING":   re.compile(r'(?:^|[_\-])(MODULE|HOUSING|CASE|CSE|ENCLOSURE)(?=[_\-]|$)', re.IGNORECASE),
    "TRIM":      re.compile(r'(?:^|[_\-])(SHUTTER|TRIM|COVER|SEAL|MOLDING|FASCIA|BACKING)(?=[_\-]|$)', re.IGNORECASE),
    "WIRING":    re.compile(r'(?:^|[_\-])(WRG|HARNESS|CABLE|WIRING)(?=[_\-]|$)', re.IGNORECASE),
    "ASSEMBLY":  re.compile(r'_ASM[-_]', re.IGNORECASE),
}
```

매칭 우선순위 규칙:
- dict 순서로 위에서 아래 첫 매칭에서 stop
- ASSEMBLY는 마지막 (다른 카테고리에 매칭 안 된 `*_ASM-` 라벨만 잡음)
- UNCATEGORIZED는 어느 패턴도 매칭 안 된 경우

### V1 → V2 변경 사항 (자기-정정 기록)

| 항목 | V1 (초안) | V2 (최종) | 사유 |
|------|----------|----------|------|
| Word boundary | `\b` 사용 | `(?:^\|[_\-])` + `(?=[_\-]\|$)` lookaround | Python regex의 `\w`에 underscore 포함 → `\bLATCH\b`는 `_LATCH_`를 못 잡음. 명시적 경계로 우회. |
| WIRING 카테고리 | 없음 | 추가 (WRG/HARNESS/CABLE/WIRING) | alpha tokens 분석에서 합 ~6.6% 차지 — 별도 카테고리 정당 |
| BRACKET 키워드 | BRKT/BRACKET/SUPPORT | + REINF, REINFORCEMENT | 합 2,394개 (1.1%), 구조적 지지 의미 부합 |
| HOUSING 키워드 | MODULE/HOUSING/CASE/ENCLOSURE | + CSE | UNCATEGORIZED 샘플에서 자주 발견된 CASE 약어 |
| TRIM 키워드 | SHUTTER/TRIM/COVER/SEAL/MOLDING | + FASCIA, BACKING | 합 2,375개 (1.1%), 외장 trim |

### V1 vs V2 효과 (V1 버그 영향 가시화)

| Category | V1 | V2 | 증가 |
|----------|------|------|------|
| FASTENER | 2,215 (4.8%) | 7,439 (16.2%) | +5,224 |
| VALVE | 7 (0.0%) | 481 (1.1%) | +474 |
| LATCH | 5 (0.0%) | 4,811 (10.5%) | +4,806 |
| BRACKET | 464 (1.0%) | 1,284 (2.8%) | +820 |
| HOUSING | 97 (0.2%) | 2,238 (4.9%) | +2,141 |
| TRIM | 396 (0.9%) | 1,240 (2.7%) | +844 |
| WIRING | (n/a) | 6,086 (13.3%) | (new) |
| ASSEMBLY | 22,297 (48.7%) | 11,734 (25.6%) | -10,563 |
| UNCATEGORIZED | 20,324 (44.4%) | 10,492 (22.9%) | **-9,832** |

ASSEMBLY 감소는 V1에서 LATCH/HOUSING/TRIM 등이 `\b` 버그로 매칭 실패 → ASSEMBLY 우선순위에 흡수됐던 것이 V2에서 정상 분류로 복구된 결과. 의도된 동작.

---

## 5. 매칭 결과 (V2, 45,805 labels)

| Category | Count | % |
|----------|-------|---|
| FASTENER | 7,439 | 16.24% |
| VALVE | 481 | 1.05% |
| LATCH | 4,811 | 10.50% |
| BRACKET | 1,284 | 2.80% |
| HOUSING | 2,238 | 4.89% |
| TRIM | 1,240 | 2.71% |
| WIRING | 6,086 | 13.29% |
| ASSEMBLY | 11,734 | 25.62% |
| UNCATEGORIZED | 10,492 | 22.91% |
| **Total** | **45,805** | **100.00%** |

Sanity: Total (45,805) = 분석 대상 (45,809 - root 4 = 45,805) ✓

---

## 6. UNCATEGORIZED 분석

비율: **22.91%** (acceptance: <10% green / 10–30% **yellow** / >30% red)

상위 30개 샘플 (빈도 순):

| Rank | Sample label | Count |
|------|--------------|-------|
| 1 | `BTH93574_001_0002-C1YX_ICE_GEAR_LOA4_6295` | 7 |
| 2 | `BOQ28188_001_22685` | 7 |
| 3 | `BSB47865_001-24055547_001-ACCUMULATOR-A_TRNS_AUX_FLUID_21360` | 7 |
| 4 | `BOQ28188_001_226855214` | 7 |
| 5 | `BSH53769_002_0001-C1YC-BAOLUO_DYNAMIC_OF_26565433_291607` | 6 |
| 6 | `BOQ28188_001_226851218` | 6 |
| 7 | `BSH53769_002_0001-C1YC-BAOLUO_LOA4_6206_290129` | 6 |
| 8 | `BOQ28188_001_226851182` | 6 |
| 9 | `BOQ28188_001_226851230` | 5 |
| 10 | `BOQ28188_001_226851247` | 5 |
| 11 | `BOQ28188_001_226851196` | 5 |
| 12 | `BOQ28188_001_226851414` | 5 |
| 13 | `BOQ28188_001_226851581` | 5 |
| 14 | `BOQ28188_001_226851353` | 5 |
| 15 | `BOQ28188_001_226851162` | 5 |
| 16 | `BOQ28188_001_226851609` | 5 |
| 17 | `BOQ28188_001_226851575` | 5 |
| 18 | `BOQ28188_001_226851616` | 5 |
| 19 | `BOQ28188_001_226851368` | 5 |
| 20 | `BOQ28188_001_226851443` | 5 |
| 21 | `BOQ28188_001_226851276` | 5 |
| 22 | `BOQ28188_001_226851688` | 5 |
| 23 | `BOQ28188_001_226851661` | 5 |
| 24 | `BOQ28188_001_226851292` | 5 |
| 25 | `BOQ28188_001_226851333` | 5 |
| 26 | `BOQ28188_001_226851441` | 5 |
| 27 | `BOQ28188_001_226851647` | 5 |
| 28 | `BOQ28188_001_226851263` | 5 |
| 29 | `BOQ28188_001_226851508` | 5 |
| 30 | `BOQ28188_001_226851466` | 5 |

**구조적 관찰**:
- Top 30 중 **22개가 `BOQ28188_001_226851xxx` 패턴** — 단일 supplier 코드의 일련번호식 부품들. 영문 키워드 0개 → keyword regex로 영원히 못 잡음.
- 잡힐 수 있는 영문 토큰을 가진 샘플은 ACCUMULATOR(1), GEAR(1), DYNAMIC(1) 등 — V3에 powertrain 카테고리 추가 시 잡히지만 누적 ~30개 라벨 추가 분류에 그침 (UNCAT의 0.3%).
- 따라서 **V2 (UNCAT 22.91%)가 keyword regex 접근의 사실상 천장**. 그 이하로 낮추려면 supplier-code → category lookup table 필요 (Phase 2+).

다음 차량 측정 시 검증할 점:
- UNCATEGORIZED 비율이 22.91%와 비슷한가
- BOQ28188 같은 supplier-code 무영문 라벨 비율이 비슷한가 (Datasmith export 일관성 신호)
- 새 차량에서 category 키워드 새로 등장하는가 (예: BATTERY, MOTOR — EV 차량)

---

## 7. F5 import 형태

F5 구현 시 다음과 같이 import:

```python
from cad_optimizer.nx_naming import NX_CATEGORY_PATTERNS, classify_label

category = classify_label(measurement.parent_part_label)
# returns one of: FASTENER / VALVE / LATCH / BRACKET / HOUSING / TRIM /
#                 WIRING / ASSEMBLY / UNCATEGORIZED
```

Phase 1 F5 구현 시 `cad_optimizer/nx_naming.py` 신규 모듈로 박제. 본 markdown은 그 regex의 도출 근거 + V1 버그 자기-정정 기록.

`classify_label` 표준 구현:

```python
def classify_label(label: str) -> str:
    if not label:
        return "UNCATEGORIZED"
    for category, pattern in NX_CATEGORY_PATTERNS.items():
        if pattern.search(label):
            return category
    return "UNCATEGORIZED"
```

---

## 8. 한계 + 다음 단계

- **차량 1대 (C1YC_2_MCM) 데이터로 도출** → 차량 의존성 미검증. 다음 차량 측정 시 본 markdown patch (Section 5의 카운트 갱신, regex는 변경 없으면 그대로).
- **Supplier-code 무영문 라벨 (UNCAT의 다수)** → keyword 접근 불가. ERP/PLM master data와 join하는 lookup table이 효과적이지만 Phase 2+ 백로그.
- **ASSEMBLY 카테고리는 sub-classification 안 됨** (LATCH_ASM- 와 SEAT_ASM- 미구분, V2에서는 LATCH가 우선 매칭되어 분리됨) — 더 세분화는 Phase 2 정밀화.
- **Powertrain 키워드 (ACCUMULATOR/GEAR/SHAFT/DYNAMIC)** 추가는 1% 미만의 추가 분류 효과 — V3 가치 미미. 다음 차량 측정 후 기여도 누적되면 재검토.
- **BDM*/BKE*/BRU* 같은 GM 내부 코드는 의미 미파악** → UNCATEGORIZED 잠재적 다수. 사내 parts master 접근 가능 시 prefix → category 매핑 시도.

---

## 9. 분석 스크립트 (재현용)

회사 머신에서 실행. CSV 경로만 갱신.

```python
"""
F4 CSV의 parent_part_label 패턴 분석 → F5 카테고리 regex 검증.
"""
import csv
import re
from collections import Counter

CSV_PATH = r"<path-to>/small_part_report_YYYYMMDD_HHMMSS.csv"

NX_CATEGORY_PATTERNS = {
    "FASTENER":  re.compile(r'(?:^|[_\-])(BOLT|NUT|SCREW|CLIP|WASHER|RIVET)(?=[_\-]|$)', re.IGNORECASE),
    "VALVE":     re.compile(r'(?:^|[_\-])(VALVE|PMP)(?=[_\-]|$)', re.IGNORECASE),
    "LATCH":     re.compile(r'(?:^|[_\-])(LATCH|LOCK|HINGE)(?=[_\-]|$)', re.IGNORECASE),
    "BRACKET":   re.compile(r'(?:^|[_\-])(BRKT|BRACKET|SUPPORT|REINF|REINFORCEMENT)(?=[_\-]|$)', re.IGNORECASE),
    "HOUSING":   re.compile(r'(?:^|[_\-])(MODULE|HOUSING|CASE|CSE|ENCLOSURE)(?=[_\-]|$)', re.IGNORECASE),
    "TRIM":      re.compile(r'(?:^|[_\-])(SHUTTER|TRIM|COVER|SEAL|MOLDING|FASCIA|BACKING)(?=[_\-]|$)', re.IGNORECASE),
    "WIRING":    re.compile(r'(?:^|[_\-])(WRG|HARNESS|CABLE|WIRING)(?=[_\-]|$)', re.IGNORECASE),
    "ASSEMBLY":  re.compile(r'_ASM[-_]', re.IGNORECASE),
}


def load_labels(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        lines = [ln for ln in f if not ln.startswith("#")]
    reader = csv.reader(lines)
    header = next(reader)
    idx = header.index("parent_part_label")
    out = []
    for row in reader:
        if len(row) <= idx:
            continue
        label = row[idx].strip()
        if label:
            out.append(label)
    return out


def classify(label):
    for cat, pat in NX_CATEGORY_PATTERNS.items():
        if pat.search(label):
            return cat
    return "UNCATEGORIZED"


def main():
    labels = load_labels(CSV_PATH)
    n = len(labels)
    print(f"Total labels analyzed: {n}\n")

    print("## Top 30 first tokens")
    first = Counter(l.split("_", 1)[0] for l in labels)
    for tok, cnt in first.most_common(30):
        print(f"  {tok:20s} {cnt:>6d} {cnt/n*100:5.1f}%")

    print("\n## Top 30 alpha tokens")
    alpha = Counter()
    for label in labels:
        for tok in re.split(r"[_\-]", label):
            if tok and tok.isalpha():
                alpha[tok] += 1
    for tok, cnt in alpha.most_common(30):
        print(f"  {tok:20s} {cnt:>6d} {cnt/n*100:5.1f}%")

    print("\n## Category match counts")
    cat = Counter(classify(l) for l in labels)
    total = 0
    for c in list(NX_CATEGORY_PATTERNS) + ["UNCATEGORIZED"]:
        total += cat[c]
        print(f"  {c:15s} {cat[c]:>6d} {cat[c]/n*100:5.2f}%")
    print(f"  {'Total':15s} {total:>6d}  (sanity: == {n}? {total==n})")

    print("\n## UNCATEGORIZED top 30")
    uncat = Counter(l for l in labels if classify(l) == "UNCATEGORIZED")
    for lab, cnt in uncat.most_common(30):
        print(f"  {cnt:>4d}  {lab}")


if __name__ == "__main__":
    main()
```
