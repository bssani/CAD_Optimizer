# Week 5 — F6 + F7 + F8 (Phase 1 종료)

> **기간**: 2026-05-10 ~ 2026-05-13 (실작업 2일, 사이 buffer 3일)
> **Phase**: 1 / Week 5 of 5 — **Phase 1 마지막 주**
> **상태**: ✅ 완료

---

## 완료 Task

| # | Task | 핵심 산출물 | Commit/PR |
|---|------|-----------|-----------|
| 1 | F5 NX distribution 박제 + F6 material analysis prep | `f5_nx_distribution_c1yc_2_mcm.md` (신규), `material_analysis_c1yc_2_mcm.md` (prep) | PR #9 |
| 2 | F6 1차 구현 (material inventory) | `material_inventory.py` 신규 + panel/menu wiring | PR #10 |
| 3 | F6 fix (3-value enum + category regex + 박제 patch) | `override_status` 3-value enum, multi-pattern category, `material_analysis` § 7+8 patch | PR #11 |
| 4 | F7 spec + 구현 (integrated report aggregator) | `integrated_report.py` 신규 (`unreal` 의존 0) + panel/menu wiring | PR #12 |
| 5 | F7 fix (default threshold Tiny + label 정리) | `run_integrated_report` 기본값, § 7 헤더 hardcode 제거 | PR #13 |
| 6 | F7 실차 검증 + 박제 | `integrated_report_c1yc_2_mcm.md` (신규), F8 가설 § 12 박제 | PR #14 |
| 7 | F8 spec + 구현 (metadata_tagger + F7 § 9 patch) | `metadata_tagger.py` 신규, 4-tier dispatch, F7 § 9 preview | PR #15 |
| 8 | F8 실차 검증 + 박제 + Phase 2 backlog #7 | `f8_c1yc_2_mcm.md`, BRACKET small=0 발견 | PR #15 |

### 측정 결과 (C1YC_2_MCM, F4~F8 통합 — Tiny @ 0.5 cm baseline)

```
F4 Total measured: 45,809
F4 Small (Tiny @ 0.5cm): 7,138 (15.6%)
F5 NX category: 8 + UNCATEGORIZED 22.91% (🟡 yellow)
F6 override_status: no_slot 0 / slot_empty 26,980 (58.90%) / has_override 18,829 (41.10%)
F6 unique primary materials: 20 (Top 1 99.3% 점유)
F7 integrated report: PR #14 박제 (F8 가설 § 12 포함)
F8 tier 분포: Cull_High 1,680 / Cull_Mid 2,499 / Review 2,959 / Keep 38,671 (implicit)
F8 BRACKET small = 0 → Cull_High 사실상 LATCH 단독 기여
```

박제 5건 + Phase 2 backlog 1 항목 추가 (#7).

---

## 학습한 핵심 개념 3개

### 1. F-pattern 4번째 검증 — F8 mutation에도 분리 원칙 유지
- F4 (`small_part_detector`) / F5 (`nx_naming`) / F6 (`material_inventory`): 측정/분류 분리
- F8 (`metadata_tagger`): 분류 (`compute_tier` 순수 함수) + 적용 (`apply_tags_to_level` duck-typed) + 결합 (`panel`)
- **`metadata_tagger.py` 에 `import unreal` 0건** — actor 객체는 duck typing으로 받음
- mutation 기능에도 동일 패턴 적용 가능. Phase 2 actor merging도 같은 분리 예상

### 2. End-to-end idempotent 검증 — F7 § 9 preview ↔ F8 apply 산술 일치
- F7이 `compute_tiers_for_report` 호출 → preview 표 생성 (mutation 0)
- F8 메뉴 실행 → 같은 함수로 분류 후 actor tag 부여
- 실차 (C1YC_2_MCM): 1,680 / 2,499 / 2,959 / 38,671 글자 단위 일치
- **가설 → 박제 → 검증 → 일치 완전 사이클** 첫 사례 (이전엔 가설 박제만)

### 3. F6 측정 각도 차이 — 박제 self-correction 패턴
- F6 구현 전 박제 작성 시점: UE Python Console 1회 추출 → `no_override 58.9%` 2-value 가정
- F6 코드 실차 검증: `slot_empty` vs `no_slot` 구분 필요 → **3-value enum 도입**
- `material_analysis_c1yc_2_mcm.md` § 7 patch + § 8 신설 (enum 정의 + regex 정정)
- **"박제는 immutable 아님, patch로 진화"** 원칙 확립 — 박제 self-correction이 코드 안정성 신호

---

## 막혔던 점 + 해결

| 문제 | 증상 | 해결 |
|------|------|------|
| F6 박제 시 `override_status` 2-value 가정 | UE Python Console 1회 추출이 `slot_empty` ≡ `no_slot` 합쳐 분류 | F6 코드 작성 시 3-value enum 도입 + 박제 § 8 patch (PR #11) |
| F6 박제 시 카테고리 regex 단일 패턴 | Top 1 `MI_SectionMisc` (99.3%)가 `/01_Features/` 밑이라 UNKNOWN으로 잘못 분류 | F6 `_parse_category` multi-pattern + `Features` 카테고리 추가 (PR #11) |
| F7 spec 가정 오류 — F6 inventory CSV가 per-actor라 가정 | 실제는 per-material asset → actor join 불가 | F7 산출물 단순화: markdown 1개만, F4 CSV는 이미 통합 형태 (PR #12) |
| F7 default threshold mismatch (Small 1.0cm) | F4/F5 박제 baseline (Tiny 0.5cm) 와 불일치 → cross-tab 카운트 어긋남 | `run_integrated_report` 기본값 Tiny 변경 + § 7 헤더 hardcode 제거 (PR #13) |
| F7 § 9 placeholder 보존 vs patch | F8 가설 데이터가 § 12에 박제됐는데 § 9 비어있음 = silo | F8 PR (#15)에 § 9 patch 포함 (F7 책임 read-only 유지하면서 surfacing) |
| F8 stacked PR 의존 (F6 fix 미머지 상태에서 F7/F8 작업) | F7 검증 시 F6 fix 코드 의존 | F6 fix main merge 먼저 → F8 새 브랜치 (PR #11 → #12 → ... → #15 순차) |
| F8 BRACKET small = 0 발견 | tier schema 가설 (LATCH ∪ BRACKET) 중 BRACKET 기여 0 — 차종 의존 가능성 | Phase 2 backlog #7 신규 + 다음 차량 측정 후 정밀화 (PR #15) |

---

## Week 5 vs 초기 계획 차이

- **계획 (CLAUDE.md §7)**: Week 5 = F6 + F7 + F8 (3 task)
- **실제**: F6 + F6 fix + F7 + F7 fix + 박제 3건 (F5/F6 prep, F7, F8) + F8 + F8 검증 = **8 task in 2 days**
- 페이스 buffer (계획 1주, 실제 2일) 의도였지만 박제 self-correction (F6 fix, F7 fix)이 추가 task 발생
- 결론: 박제 의무가 일정 push back 발생시키지만, 발견된 misalign이 코드/박제 정합성이라 박제 가치 입증

---

## Phase 1 → Phase 2 진입 시 주의

1. **다음 차량 측정 1~2건 먼저** (`docs/phase2_backlog.md` #6) — C1YC_2_MCM 단일 데이터로 도출된 가정 (UNCAT 22.91%, BRACKET small 0%, multi-leaf 9.4% 등) 일반성 미검증
2. **Phase 2 첫 task 결정**: backlog #1 (ERP/PLM supplier-code lookup) — UNCATEGORIZED green zone 진입의 유일한 경로
3. **F-pattern 분리 원칙 유지** — Phase 2 actor merging도 측정/분류/적용 셋으로 쪼개기. mutation 비중이 Phase 2에서 커짐
4. **외부 라이브러리 검토 가능** (CLAUDE.md §3) — Phase 2+ 시 MIT 라이선스. 사내 pip install 정책 확인 필요
5. **Phase W (Web 트랙) 별도 결정** — Phase 2 진행 중 VWV 진척 보면서 진입 시점 검토

---

## 다음 세션 시작 시 (CLAUDE.md §9)

- 이 문서 + CLAUDE.md (v0.8) + `docs/phase1_retrospective.md` + `docs/phase2_backlog.md` 첨부
- 현재: **Phase 1 ✅ 완료. Phase 2 진입 검토 대기**
- 다음 결정: Phase 2 진입 vs 다른 차량 측정 vs VWV 우선 (3-way trade-off)
