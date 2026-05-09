# Material 실태 분석 — C1YC_2_MCM

> **출처**: UE Python Console 직접 추출 (F2는 CSV writer 부재 — Output Log only)
> **측정일**: 2026-05-09
> **목적**: F6 (material consolidation) 본 구현 전 선행 데이터 분석.
> **상태**: F6 spec 설계 입력 — 본 markdown 후 F6 prompt 작성.
> **Plugin commit**: e191201

---

## 1. 측정 환경

- Level: `L_C1YC_2_MCM` (107,882 actors, 45,809 StaticMeshActor)
- 측정 방법: UE Python Console + `Counter` 기반 빈도 분석
- StaticMeshActor: 45,809 (no-SMC 0, no-static_mesh 0, all measured)

---

## 2. Material asset 분포 — **충격적으로 작음**

- **Total unique material paths: 20** (45,809 actors 분산)
- F2 plugin이 보고한 "Unique Materials: 5"와 차이 — **둘 다 valid measurement, 측정 각도 다름**:
  - F2: `sm.static_materials` (mesh asset이 declare한 materials) → 5
  - 본 측정: `smc.get_material(i)` (component override 포함) → 20
  - 차이 15개는 component-level override로 재할당된 material (mesh default 아님)

### Top 20 most-used materials

| Rank | Path | Usage |
|------|------|-------|
| 1 | `/Game/00_PQDQ/01_Features/MI_SectionMisc.MI_SectionMisc` | **18,696** |
| 2 | `/Game/00_PQDQ/00_Material/02_Instance/CarPaint/MI_PNT_SummitWhite.MI_PNT_SummitWhite` | 52 |
| 3 | `/Game/00_PQDQ/00_Material/02_Instance/Metal/MI_MetalFrosted1.MI_MetalFrosted1` | 35 |
| 4 | `/Game/00_PQDQ/00_Material/02_Instance/Plastic/MI_PLS_Black.MI_PLS_Black` | 8 |
| 5 | `/Game/00_PQDQ/00_Material/02_Instance/Glass/MI_Window.MI_Window` | 8 |
| 6 | `/Game/00_PQDQ/00_Material/02_Instance/Glass/MI_WIndSheild.MI_WIndSheild` | 7 |
| 7 | `/Game/00_PQDQ/00_Material/02_Instance/CarPaint/MI_PNT_PianoBlack.MI_PNT_PianoBlack` | 4 |
| 8 | `/Game/00_PQDQ/00_Material/02_Instance/Rubber/MI_RubberClean.MI_RubberClean` | 3 |
| 9 | `/Game/00_PQDQ/00_Material/02_Instance/Metal/MI_BMF_Brt_Chrome_150Z.MI_BMF_Brt_Chrome_150Z` | 3 |
| 10 | `/Game/00_PQDQ/00_Material/02_Instance/Misc/Liquid/MI_Liquid_03.MI_Liquid_03` | 2 |
| 11 | `/Game/00_PQDQ/00_Material/02_Instance/Plastic/MI_EngineOil.MI_EngineOil` | 2 |
| 12 | `/Engine/EngineSky/M_SimpleSkyDome.M_SimpleSkyDome` | 1 |
| 13 | `/Engine/OpenWorldTemplate/LandscapeMaterial/MI_ProcGrid.MI_ProcGrid` | 1 |
| 14 | `/Game/00_PQDQ/01_Features/Data/M_Decal_Tire.M_Decal_Tire` | 1 |
| 15 | `/Engine/EngineMaterials/WorldGridMaterial.WorldGridMaterial` | 1 |
| 16 | `/Game/00_PQDQ/00_Material/02_Instance/Misc/Liquid/MI_Liquid_05.MI_Liquid_05` | 1 |
| 17 | `/Game/00_PQDQ/00_Material/02_Instance/00_InstanceMaster/MI_Carpet02.MI_Carpet02` | 1 |
| 18 | `/Game/00_PQDQ/00_Material/02_Instance/Glass/MI_WIndSheild_5Per.MI_WIndSheild_5Per` | 1 |
| 19 | `/Game/00_PQDQ/00_Material/02_Instance/Misc/Liquid/MI_Liquid_04.MI_Liquid_04` | 1 |
| 20 | `/Game/00_PQDQ/00_Material/02_Instance/Plastic/MI_BatteryCover.MI_BatteryCover` | 1 |

(전체 20개 — Top 30 요청했으나 unique=20이라 모두 표시)

**핵심 관찰**:
- Top 1 (`MI_SectionMisc`)이 **18,696 사용 = 99.4% of slot count** (18,696 / 18,829 = 99.3% of actors with slots).
- 2~4위 합 95개. 5~20위 합 합쳐도 ~38개.
- **"Material consolidation"의 전통적 의미 (중복 통합) 표면적 거의 없음** — 이미 극도로 통합된 상태.

---

## 3. Long-tail

- **Used only once**: 9 materials (45%)
- **Used ≤5 times**: 14 materials (70%)
- 빈출 분포 = 1 dominant + 19 long-tail

Long-tail 9개를 통합한다 해도 영향 미미 (≤9 actors). 통합 가치 낮음.

---

## 4. Per-actor material slot 분포

| Slot count | Actor count | % of 45,809 |
|------------|-------------|-------------|
| 0 | **26,980** | **58.90%** |
| 1 | 18,829 | 41.10% |
| 2-5 | 0 | 0.00% |
| 6+ | 0 | 0.00% |

Max slot count: **1**.

**핵심 관찰**: 58.90% actors가 component slot 0개. 즉 SMC가 material override를 0개 보유. 렌더링은 정상 (UE는 component slot 0이면 mesh asset's default material로 fallback). 하지만 component-level API (`smc.get_material()`)만 보면 "material 없음"으로 보임.

---

## 5. Slot mismatch (재측정)

- F3 결과 (CarConfigurator 샘플): **0 mismatches**
- 실차 (C1YC_2_MCM): **26,980 mismatches**
- Mismatch 정의: `sm.get_num_sections(0)` ≠ `len(materials from smc.get_material())`

### Samples (first 5)

| Actor | Expected sections (mesh) | Material slots (component) |
|-------|--------------------------|---------------------------|
| `RH_Strut_Upper_Target_C1YC-2_MCM` | 1 | 0 |
| `LH_Strut_Upper_Target_C1YC-2_MCM` | 1 | 0 |
| `Geometry6` | 1 | 0 |
| `Geometry5` | 1 | 0 |
| `Geometry4` | 1 | 0 |

**진단**:
- 26,980 mismatches는 모두 동일 패턴: mesh asset에 1 section 있는데 component slot은 0.
- 이건 **결함이 아니라 자연 상태** — Datasmith가 component override를 안 만들고 mesh default에 의존.
- F3에서 0 mismatches였던 건 측정 각도가 달랐기 때문. F3는 `len(materials) != sections` 비교했지만 measurements를 수집하는 actors도 다르고 정의도 미묘하게 차이.
- **F6에서 이걸 "mismatch"로 카운트하면 misleading**. 진짜 anomaly가 아니라 정상 상태.

---

## 6. Material naming Top 30 tokens

| Rank | Token | Count |
|------|-------|-------|
| 1 | MI | 17 |
| 2 | Liquid | 3 |
| 3 | M | 2 |
| 4 | PNT | 2 |
| 5 | WIndSheild | 2 |
| 6 | SimpleSkyDome | 1 |
| 7 | ProcGrid | 1 |
| 8 | Decal | 1 |
| 9 | Tire | 1 |
| 10 | SummitWhite | 1 |
| 11 | WorldGridMaterial | 1 |
| 12 | SectionMisc | 1 |
| 13 | PLS | 1 |
| 14 | Black | 1 |
| 15 | Window | 1 |
| 16 | EngineOil | 1 |
| 17 | MetalFrosted1 | 1 |
| 18 | Carpet02 | 1 |
| 19 | RubberClean | 1 |
| 20 | 5Per | 1 |
| 21 | BatteryCover | 1 |
| 22 | PianoBlack | 1 |
| 23 | BMF | 1 |
| 24 | Brt | 1 |
| 25 | Chrome | 1 |
| 26 | 150Z | 1 |

(26개 token만 — material 자체가 20개라 token 수 적음)

**관찰**:
- Material path는 매우 구조적: `/Game/00_PQDQ/00_Material/02_Instance/<category>/MI_*` 또는 `M_*`.
- Categories: CarPaint / Metal / Plastic / Glass / Rubber / Misc.
- "MI" prefix = Material Instance (UE 표준), "M_" = base Material.
- NX과 달리 supplier-code 잡음 없음 — 모두 의미 있는 영문 token.
- Token 빈도 분포는 평탄 (대부분 1번 등장) — material 수 자체가 적어서.

---

## 7. F6 scope 설계 입력 (관찰 → 결정)

### 7.1 Consolidation candidate 정의 (재정의 필요)

전통적 F6 = "다른 path지만 같은 텍스처/속성인 material 찾아 통합"이지만 **본 데이터에 거의 적용 불가**:
- 20개만 존재 → 표면적 작음
- Top 1이 99.3% 점유 → 이미 극도 통합 상태
- Long-tail 14개도 의미 있는 차이 (예: `MI_Window` vs `MI_WIndSheild` vs `MI_WIndSheild_5Per` — 의도된 variation)

→ **F6 scope pivot 필요**. 후보 방향:

#### Option A: Material slot reality 진단 (권장)
- 측정 각도: `sm.static_materials` (mesh-level) vs `smc.get_material()` (component-level)
- 26,980 actors가 component slot 0 → "mesh default fallback" 상태 보고
- F2 측정 (5 unique)과 component 측정 (20 unique)의 의미 차이를 actor별로 가시화

#### Option B: Material category breakdown (간단)
- Path의 `/02_Instance/<category>/` 부분 추출 → CarPaint/Metal/Plastic/... 분류
- 각 카테고리별 actor count + bbox stats
- F5의 mini 버전 (regex 단순)

#### Option C: 둘 다 + F4/F5 join
- F4 measurement에 `material_path` (component-level), `material_count` (slot count) 컬럼 추가
- F5의 nx_category와 join하여 cross-tab 가능 (예: "FASTENER 카테고리 actor의 material 분포")

### 7.2 측정 vs consolidation 분리 (F4/F5 패턴 유지)

- F6는 detection only (어떤 material이 어떻게 쓰이는지 리포트)
- 실제 consolidation은 Phase 2 (이미 거의 다 통합된 상태라 Phase 2 가치도 낮음)

### 7.3 Slot mismatch 처리

- 26,980 mismatches는 정상 상태 (component override 부재 + mesh default fallback)
- **F6 별도 카운터로 추가하지 말 것** — misleading. "mismatch"가 아닌 "no override / default fallback" 같은 중립 표현.
- 또는 F6 scope에서 제외 (F3와 의미 다르므로 카운트 의미 모호).

### 7.4 Material naming 분류 (F5 패턴 재활용 검토)

- Material naming이 매우 단순 (path에 `/MI_*` 또는 `/<category>/`).
- **F5 keyword regex보다 path-based 단순 split이 더 적합**:
  - `/02_Instance/<category>/` 추출 = category 분류 (CarPaint/Metal/Plastic/...)
  - `MI_*` vs `M_*` prefix = instance vs base material 구분
- F5 regex 같은 복잡도 불필요. supplier-code 잡음도 없음.

---

## 8. F6 spec 설계 다음 단계

본 markdown 박제 완료 후:

1. **F6 spec 결정**: 위 7.1의 Option A/B/C 중 선택 (또는 hybrid)
2. **F6 prompt 작성** (Claude planner): 결정된 scope 기반
3. **Claude Code 구현**: F4/F5 패턴 따름 (`material_inventory.py` 또는 유사 신규 모듈, panel.py 결합, menu/EUW 신규 X)
4. **실차 측정 후 박제**: `docs/measurements/f6_<vehicle>.md`

### 권장 F6 scope 요약 (Option A + 단순화)

- 신규 모듈 `cad_optimizer/material_inventory.py` (순수 분석기, unreal+stdlib만)
- 출력: per-actor material info (path, slot count, override 여부) → CSV column 추가 또는 별도 CSV
- F4 CSV에 join: actor 단위 material context 노출
- 기존 F4 메뉴 재사용 (신규 entry X)
- F6 핵심 가치: "이 차량의 material 사용 reality 한 화면 진단" — duplicate 통합이 아닌 inventory + override 상태.
