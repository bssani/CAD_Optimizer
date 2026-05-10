# F7 Integrated Report — C1YC_2_MCM

> **출처**: F7 통합 리포트 (실차 첫 박제, fix #13 반영 — Tiny @ 0.5 cm)
> **측정일**: 2026-05-10
> **목적**: Phase 1 6 modules 통합 측정 결과 박제. 다음 차량 측정 시
>           baseline diff 가능. F4/F5/F6 박제와 baseline 일치 (모두 0.5 cm).
> **Plugin commit**: e8daf1c (F7 PR #12) + d9b53e1 (fix PR #13)
> **회귀 검증**: ✅ LATCH × small = 1,915 (39.80%) — F5 박제 byte 일치

---

## 1. 측정 개요

| 항목 | 값 |
|------|-----|
| 차량 코드 | `C1YC_2_MCM` |
| 레벨명 | `L_C1YC_2_MCM` |
| 측정일 | 2026-05-10 23:51:54 |
| Plugin commit | `d9b53e1` |
| F4 threshold | 0.50 cm (Tiny) |

---

## 2. F2 — Mesh Stats

| 항목 | 값 |
|------|-----|
| StaticMeshActor 수 | 45,809 |
| Unique static meshes | 27,889 |
| Total triangles | 29,457,084 |
| Total vertices | 33,605,298 |
| Material sections (potential draw calls) | 45,809 |
| Total material slots (mesh-level sum) | 45,809 |
| Unique materials (mesh-level) | 5 |
| Nanite-enabled actors | 45,789 / 45,809 (99.96%) |

---

## 3. F3 — Instance Detection

- Total groups (unique mesh + materials + mobility): **28,271**
- Duplicate groups (count > 1): **7,070**
- Candidate groups (count ≥ 10): **303**
- Est. drawcall reduction (ISM 변환 시): **6,196** (추정치)

### Top 10 most-instanced groups

| Rank | Count | Mesh path | Mobility |
|------|-------|-----------|----------|
| 1 | 93 | `/Game/_PQDQ/03_Mesh/FBX/NON_MOVING_C1YC-2_MCM_asmesh/Geometries/Geometry_ncl1_9143` | STATIC |
| 2 | 93 | `/Game/_PQDQ/03_Mesh/FBX/NON_MOVING_C1YC-2_MCM_asmesh/Geometries/Geometry_ncl1_9142` | STATIC |
| 3 | 71 | `/Game/_PQDQ/03_Mesh/FBX/NON_MOVING_C1YC-2_MCM_asmesh/Geometries/Geometry_ncl1_7334` | STATIC |
| 4 | 71 | `/Game/_PQDQ/03_Mesh/FBX/NON_MOVING_C1YC-2_MCM_asmesh/Geometries/Geometry_ncl1_7333` | STATIC |
| 5 | 71 | `/Game/_PQDQ/03_Mesh/FBX/NON_MOVING_C1YC-2_MCM_asmesh/Geometries/Geometry_ncl1_7332` | STATIC |
| 6 | 59 | `/Game/_PQDQ/03_Mesh/FBX/NON_MOVING_C1YC-2_MCM_asmesh/Geometries/Geometry_ncl1_9456` | STATIC |
| 7 | 54 | `/Game/_PQDQ/03_Mesh/FBX/NON_MOVING_C1YC-2_MCM_asmesh/Geometries/Geometry_ncl1_17800` | STATIC |
| 8 | 54 | `/Game/_PQDQ/03_Mesh/FBX/NON_MOVING_C1YC-2_MCM_asmesh/Geometries/Geometry_ncl1_17799` | STATIC |
| 9 | 52 | `/Game/_PQDQ/03_Mesh/FBX/NON_MOVING_C1YC-2_MCM_asmesh/Geometries/Geometry_ncl1_8424` | STATIC |
| 10 | 52 | `/Game/_PQDQ/03_Mesh/FBX/MOVING_C1YC-2_MCMasmesh/Geometries/Geometry_ncl1_1329` | STATIC |

→ Top 1 = 93× (CarConfigurator의 10,000× Plane과 정성적으로 다름 — 실 CAD는 mid-tier 분포).

---

## 4. F4 — Small Parts

- Total measured: **45,809**
- Skipped: 0 no-root, 0 no-mesh, 0 zero-bbox
- Root-level (no attach parent, measured): 4

### Diagonal 분포

| Percentile | Value (cm) |
|-----------|------------|
| P10 | 0.23 |
| P50 | 2.71 |
| P90 | 18.21 |

### Threshold preset 카운트

| Threshold | Small parts |
|-----------|-------------|
| 0.5 cm (Tiny) | 7,138 |
| 1.0 cm (Small) | 11,596 |
| 5.0 cm (Medium) | 32,241 |

### Smallest 10 (by diagonal)

| Rank | Diagonal | Parent (immediate attach parent) | Mobility | parent_leaf_count |
|------|----------|----------------------------------|----------|-------------------|
| 1 | 0.00 cm | `12696637_008-VALVE_ASM-O_PMP_FLOW_CONT_SOL_600913` | STATIC | 2 |
| 2 | 0.00 cm | `12696637_008-VALVE_ASM-O_PMP_FLOW_CONT_SOL_600254` | STATIC | 2 |
| 3 | 0.00 cm | `84815023_001-_LATCH_ASM-R_SEAT_27798932391` | STATIC | 1 |
| 4 | 0.00 cm | `84815023_001-_LATCH_ASM-R_SEAT_277989` | STATIC | 1 |
| 5 | 0.00 cm | `84815022_001-_LATCH_ASM-R_SEAT_17196633991` | STATIC | 1 |
| 6 | 0.00 cm | `84815022_001-_LATCH_ASM-R_SEAT_171966` | STATIC | 1 |
| 7 | 0.00 cm | `84815022_001-_LATCH_ASM-R_SEAT_17451534045` | STATIC | 1 |
| 8 | 0.00 cm | `84815022_001-_LATCH_ASM-R_SEAT_174515` | STATIC | 1 |
| 9 | 0.00 cm | `BRU57682_009-SHUTTER_-FRT_BPR_1975275` | STATIC | 1 |
| 10 | 0.00 cm | `BRU57682_009-SHUTTER_-FRT_BPR_1975274` | STATIC | 1 |

→ `docs/measurements/f4_c1yc_2_mcm.md` Section 5와 동일 (multi-leaf 정정 후 일치).

---

## 5. F5 — NX Category Distribution

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
| UNCATEGORIZED | 10,496 | 22.91% |
| **Total** | **45,809** | **100.00%** |

**UNCATEGORIZED zone**: 🟡 yellow (22.91%)
기준: <10% 🟢 green / 10-30% 🟡 yellow / >30% 🔴 red.

→ `docs/measurements/f5_nx_distribution_c1yc_2_mcm.md` Section 2와 byte 일치 (회귀 PASS).

---

## 6. F6 — Material Inventory

- Total unique materials (per-actor primary slot): **20**

### Override status 분포 (3-value enum)

| Status | Count | % | 의미 |
|--------|-------|---|------|
| `no_slot` | 0 | 0.00% | `smc.get_num_materials() == 0` |
| `slot_empty` | 26,980 | 58.90% | slot 존재, asset None → mesh default fallback (typical Datasmith CAD) |
| `has_override` | 18,829 | 41.10% | slot + asset 둘 다 |

### Top 10 materials (by per-actor primary slot usage)

| Rank | Path | Usage |
|------|------|-------|
| 1 | `/Game/00_PQDQ/01_Features/MI_SectionMisc.MI_SectionMisc` | 18,696 |
| 2 | `/Game/00_PQDQ/00_Material/02_Instance/CarPaint/MI_PNT_SummitWhite` | 52 |
| 3 | `/Game/00_PQDQ/00_Material/02_Instance/Metal/MI_MetalFrosted1` | 35 |
| 4 | `/Game/00_PQDQ/00_Material/02_Instance/Plastic/MI_PLS_Black` | 8 |
| 5 | `/Game/00_PQDQ/00_Material/02_Instance/Glass/MI_Window` | 8 |
| 6 | `/Game/00_PQDQ/00_Material/02_Instance/Glass/MI_WIndSheild` | 7 |
| 7 | `/Game/00_PQDQ/00_Material/02_Instance/CarPaint/MI_PNT_PianoBlack` | 4 |
| 8 | `/Game/00_PQDQ/00_Material/02_Instance/Rubber/MI_RubberClean` | 3 |
| 9 | `/Game/00_PQDQ/00_Material/02_Instance/Metal/MI_BMF_Brt_Chrome_150Z` | 3 |
| 10 | `/Game/00_PQDQ/00_Material/02_Instance/Plastic/MI_EngineOil` | 2 |

### Material category breakdown (unique assets)

| Category | Unique materials | % of 20 |
|----------|------------------|---------|
| CarPaint | 2 | 10.00% |
| Metal | 2 | 10.00% |
| Plastic | 3 | 15.00% |
| Glass | 3 | 15.00% |
| Rubber | 1 | 5.00% |
| Misc | 3 | 15.00% |
| Features | 2 | 10.00% |
| UNKNOWN | 4 | 20.00% |

→ `docs/concepts/material_analysis_c1yc_2_mcm.md` § 8 박제와 일관 (no_slot 0, slot_empty 58.9%, has_override 41.1%).

---

## 7. F4 × F5 Cross-tab — nx_category × is_small (@ 0.5 cm)

| nx_category | small | not small | total | % small |
|-------------|-------|-----------|-------|---------|
| FASTENER | 77 | 7,362 | 7,439 | 1.04% |
| VALVE | 80 | 401 | 481 | 16.63% |
| **LATCH** | **1,915** | 2,896 | 4,811 | **39.80%** |
| BRACKET | 0 | 1,284 | 1,284 | 0.00% |
| HOUSING | 362 | 1,876 | 2,238 | 16.18% |
| TRIM | 14 | 1,226 | 1,240 | 1.13% |
| WIRING | 2,035 | 4,051 | 6,086 | 33.44% |
| ASSEMBLY | 1,753 | 9,981 | 11,734 | 14.94% |
| UNCATEGORIZED | 902 | 9,594 | 10,496 | 8.59% |

→ **회귀 검증 PASS**: F5 박제 (`docs/measurements/f5_nx_distribution_c1yc_2_mcm.md` Section 3) 와 byte 일치.

---

## 8. F4 × F6 Cross-tab — nx_category × override_status (신규 데이터)

| nx_category | no_slot | slot_empty | has_override | total | slot_empty % |
|-------------|---------|------------|--------------|-------|--------------|
| FASTENER | 0 | 4,137 | 3,302 | 7,439 | 55.6% |
| VALVE | 0 | 194 | 287 | 481 | 40.3% |
| **LATCH** | 0 | **4,505** | 306 | 4,811 | **93.6%** |
| BRACKET | 0 | 954 | 330 | 1,284 | 74.3% |
| HOUSING | 0 | 1,168 | 1,070 | 2,238 | 52.2% |
| TRIM | 0 | 754 | 486 | 1,240 | 60.8% |
| WIRING | 0 | 1,875 | 4,211 | 6,086 | 30.8% |
| ASSEMBLY | 0 | 6,973 | 4,761 | 11,734 | 59.4% |
| UNCATEGORIZED | 0 | 6,420 | 4,076 | 10,496 | 61.2% |

본 cross-tab은 박제 없는 첫 측정 (F4 × F6은 F7에서 처음 surfacing).

---

## 9. F8 — Metadata Tags

박제 시점에 미구현 (Phase 1 Week 5 마지막 task). § 12 가설 참조.

---

## 10. 다음 차량 비교용 baseline metric

```
# F2
F2_TOTAL_ACTORS = 45809
F2_UNIQUE_MESHES = 27889
F2_TOTAL_TRIANGLES = 29457084
F2_TOTAL_VERTICES = 33605298
F2_NANITE_ENABLED = 45789

# F3
F3_TOTAL_GROUPS = 28271
F3_DUPLICATE_GROUPS = 7070
F3_CANDIDATE_GROUPS = 303
F3_EST_DRAWCALL_REDUCTION = 6196

# F4
F4_TOTAL_MEASURED = 45809
F4_DIAG_P10_CM = 0.227
F4_DIAG_P50_CM = 2.712
F4_DIAG_P90_CM = 18.209
F4_SMALL_AT_0_5_CM = 7138
F4_SMALL_AT_1_0_CM = 11596
F4_SMALL_AT_5_0_CM = 32241

# F5
F5_FASTENER = 7439
F5_VALVE = 481
F5_LATCH = 4811
F5_BRACKET = 1284
F5_HOUSING = 2238
F5_TRIM = 1240
F5_WIRING = 6086
F5_ASSEMBLY = 11734
F5_UNCATEGORIZED = 10496
F5_UNCAT_PCT = 22.91

# F6 (per-actor primary slot)
F6_NO_SLOT = 0
F6_SLOT_EMPTY = 26980
F6_HAS_OVERRIDE = 18829
F6_UNIQUE_PRIMARY_MATERIALS = 20

# F4 × F5 cross-tab @ 0.5 cm (small parts by category)
CT_FASTENER_SMALL = 77
CT_VALVE_SMALL = 80
CT_LATCH_SMALL = 1915
CT_BRACKET_SMALL = 0
CT_HOUSING_SMALL = 362
CT_TRIM_SMALL = 14
CT_WIRING_SMALL = 2035
CT_ASSEMBLY_SMALL = 1753
CT_UNCATEGORIZED_SMALL = 902

# F4 × F6 cross-tab (slot_empty count by category)
CT_LATCH_SLOT_EMPTY = 4505
CT_LATCH_SLOT_EMPTY_PCT = 93.6
CT_ASSEMBLY_SLOT_EMPTY = 6973
CT_WIRING_HAS_OVERRIDE = 4211
```

---

## 11. 관련 산출물 (Philip 로컬, repo 미동봉)

**Primary**: `Saved/CAD_Optimizer/integrated_report_20260510_235154.md` (F7 출력)

**Supporting CSVs** (동일 측정 시점):
- F4 per-actor (master per-actor data — F5 + F6 통합):
  `Saved/CAD_Optimizer/small_part_report_20260510_235153.csv`
- F6 inventory (per-material asset, multi-slot/asset-level):
  `Saved/CAD_Optimizer/material_inventory_20260510_235154.csv`
- F3 instance detection (per-group):
  `Saved/CAD_Optimizer/instance_report_20260510_235149.csv`

### 박제 reference

- `docs/measurements/f4_c1yc_2_mcm.md` — F4 baseline 형식
- `docs/measurements/f5_nx_distribution_c1yc_2_mcm.md` — F5 분포 + zone
- `docs/concepts/material_analysis_c1yc_2_mcm.md` — F6 3-value enum 정의
- `docs/concepts/nx_naming_patterns.md` — V2 regex 출처
- `docs/phase2_backlog.md` — Phase 2 미결정 항목

---

## 12. 관찰 (Variation 회수: F4 × F6 cross-tab의 PCVR 신호)

§ 8 cross-tab에서 카테고리별 mesh default fallback 의존도 (slot_empty 비율) 정렬:

| Rank | 카테고리 | slot_empty % | total | PCVR 함의 |
|------|---------|--------------|-------|-----------|
| 1 | **LATCH** | **93.6%** | 4,811 | 절대 다수 fallback |
| 2 | BRACKET | 74.3% | 1,284 | high fallback |
| 3 | UNCATEGORIZED | 61.2% | 10,496 | mid-high (supplier serial 다수) |
| 4 | TRIM | 60.8% | 1,240 | mid-high |
| 5 | ASSEMBLY | 59.4% | 11,734 | mid (절반 이상 fallback) |
| 6 | FASTENER | 55.6% | 7,439 | mid |
| 7 | HOUSING | 52.2% | 2,238 | mid (균형) |
| 8 | VALVE | 40.3% | 481 | low (override 우세) |
| 9 | **WIRING** | **30.8%** | 6,086 | **lowest** (has_override 4,211 우세) |

### 가설 (F8 입력)

1. **LATCH × slot_empty × small@0.5cm**:
   - LATCH × small = 1,915 actors (39.80%)
   - LATCH × slot_empty = 4,505 actors (93.6%)
   - 두 조건 교집합은 ≈ **1,800+** (LATCH × small의 거의 전부 가정 시)
   - → **PCVR cull 1순위 후보 라벨링**: 작고 + mesh default fallback 의존하는 latch 부품. F8 metadata tag 우선순위.

2. **WIRING은 다른 정책 필요**:
   - WIRING × slot_empty = 1,875 (30.8%, 최저)
   - WIRING × has_override = 4,211 (override 우세)
   - WIRING × small = 2,035 (33.44%, LATCH 다음으로 높음)
   - → 작은 WIRING actor는 has_override 비중이 더 큼 → 시각적으로 의미 있는 경우 가능. cull보다 LOD/시각 디테일 검토.

3. **PCVR cull 우선순위 라벨링 (F8 후보 schema)**:
   ```
   tag.pcvr_cull_priority = "high"  if (small AND slot_empty AND category in [LATCH, BRACKET])
   tag.pcvr_cull_priority = "mid"   if (small AND slot_empty)
   tag.pcvr_cull_priority = "review" if (small AND has_override)
   tag.pcvr_cull_priority = "keep"   otherwise
   ```

### Cross-tab regression 검증

§ 7 LATCH × small @ 0.5cm = **1,915** (39.80%) — F5 박제 byte 일치 ✓
§ 7 BRACKET × small @ 0.5cm = **0** — sanity ✓ (bracket은 정의상 작지 않음)
§ 7 합계 = 7,138 = F4 박제 multi-threshold table의 `0.5 cm: 7,138` 일치 ✓

→ F7 cross-tab logic 회귀 검증 완료. F4 measurements 단일 소스 + nx_naming + material_inventory 결합 정합성 확인.

---

## 13. 다음 차량 측정 시 체크할 점

- **F2/F4/F5/F6 baseline 일관성**: § 10 metric block과 다음 차량 metric block을 diff. 큰 차이는 차량별 패턴 신호.
- **F3 분포**: 28,271 groups / 303 candidates / 6,196 drawcall reduction이 차량 간 안정적인가. CarConfigurator의 single-bucket과 달리 mid-tier 분포 (Top 1 = 93×) — 실 CAD 일반 패턴인지 다음 차량으로 검증.
- **LATCH × slot_empty 93.6%**: 차량 공통 패턴 (Datasmith CAD 일반)인지, GM-specific인지. 다른 차량에서 90%+ 유지되면 일반화 가능.
- **F5 UNCATEGORIZED 22.91% (yellow)**: 일관성. supplier serial 비중이 차량별 다를 수 있음.
- **F4 P10/P50/P90 long-tail 분포**: long-tail 형태 유지되는가, P50이 어느 cm 대인가.
- **F4 × F6 cross-tab의 LATCH/WIRING 패턴**: 다른 차량에서 LATCH가 여전히 fallback 최고, WIRING이 override 최고인지.
- **F6 unique materials 20개**: 다른 차량은 더 많을 수 있음. consolidation 표면적 확인.
- **회귀 검증**: F5 박제와 F7 § 7 cross-tab byte 일치 매번 재확인 (코드↔박제 mismatch 가드).
