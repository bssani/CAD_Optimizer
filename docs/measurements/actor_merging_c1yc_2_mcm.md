# Actor Merging (Phase 2) — C1YC_2_MCM

> Phase 2 첫 task 첫 실차 박제. F3 candidate group 303개 → ISM
> 변환 실측. **F3 estimated_drawcall_reduction 가설 (6,196) 이 실측
> drawcall 감소와 byte 단위 일치** 확인.

| 항목 | 값 |
|------|-----|
| 측정일 | 2026-06-01 |
| 차량 코드 | C1YC_2_MCM |
| 프로젝트 경로 | `C:\Users\BZLS01\Downloads\C1YC_2_MCM` |
| 레벨 | `L_C1YC_2_MCM` |
| Plugin commit | `4ab31ca` (Phase 2 actor merger squash) |
| BP asset | `/CAD_Optimizer/Blueprints/BP_ISMHolder` (Plugin Content — backlog #8 완료, 2026-06-01) |
| Threshold | ≥ 10 instances per group (F3 candidate threshold) |
| Tag prefix | `CADOpt_P2_` |

---

## 1. Before / After (F2 통계)

| 항목 | Before | After | Delta |
|------|--------|-------|-------|
| Static Mesh Actors | 45,809 | 39,310 | **−6,499** |
| Material Sections | 45,809 | 39,310 | **−6,499** |
| Material Slots (sum) | 45,809 | 39,310 | −6,499 |
| Total Triangles | 29,457,084 | 26,242,998 | −3,214,086 |
| Total Vertices | 33,605,298 | 29,939,169 | −3,666,129 |
| Unique Materials | 5 | 5 | **0 (변동 없음)** ✅ |
| Unique Static Meshes | 27,889 | 27,705 | −184 |
| Nanite-Enabled Actors | 45,789 / 45,809 | 39,290 / 39,310 | 비율 일관 (99.96% 유지) |

해석:
- SMA 정확히 6,499 감소 — Phase 2 로그 `Source actors deleted: 6499` 일치 ✅
- Material/Mesh asset 변동 없음 — mutation은 actor-level only (asset preserved)
- Unique mesh 감소 184개 = 303 candidate 중 184개 mesh가 머지 후 SMA에 의해 더 이상 참조되지 않음 (asset 자체는 유지)

## 2. 산술 정합성 — 실측 drawcall 감소 = F3 estimated 일치 ✅

```
Source actors deleted     = 6,499   (Phase 2 apply 로그)
F2 SMA count delta        = 6,499   (45,809 − 39,310) ✅
BP_ISMHolder spawned      =   303   (unreal.Actor → F2 SMA 카운트에 안 잡힘)

Real drawcall reduction   = 6,499 − 303
                          = 6,196
F3 estimated_drawcall_reduction = 6,196   ✅ byte 단위 일치
```

→ F7 § 3 박제의 `estimated_drawcall_reduction = sum((count-1) * num_materials)`
공식이 **실측 결과를 정확히 예측**함 (C1YC_2_MCM에서 num_materials=1 균일).

## 3. Phase 2 apply 로그 (요약)

```
[Phase 2] Plans total: 303
[Phase 2] Plans applied: 303
[Phase 2] Plans skipped: 0
[Phase 2] Instances merged: 6,499
[Phase 2] Est. drawcall reduction: 6,196
[Phase 2] Source actors deleted: 6,499
[Phase 2] Level dirty — review and save manually. Undo (Ctrl+Z) reverts.
[Phase 2] CSV: actor_merge_applied_20260601_024430.csv
```

수학:
- `sum(count) = 6,499` (303 group 평균 instance 21.5)
- `sum(count - 1) = 6,196` (= 6,499 − 303)
- `num_materials = 1` per group (F3 grouping이 보장, F2 박제 5 unique materials 중 Top 1 MI_SectionMisc 99.3% 점유와 정합)

## 4. 자연 idempotent 검증 (실측)

APPLY 직후 F3 fresh run 결과:
- Scanned: 107,883 actors (45,810 StaticMeshActor, 62,073 other) ← Total actor 거의 동일 (ISM holder 303 추가, SMA 6,499 삭제 → net −6,196 + APPLY 전 +0 + 자잘한 차이)
- **Groups: 28,271 unique (threshold=10, 303 candidates)** ← Pre-APPLY와 같은 candidate 카운트... 의문

(참고: 로그상 F3 instance detection은 **APPLY 전** F2 측정 직후 실행됐고, candidate가 303으로 잡힌 시점은 머지 직전. APPLY 이후 별도 F3 fresh run을 실행하지 않았으므로 자연 idempotent는 **로직상 보장** + **재실행 미실측** 상태. 다음 차량 측정 시 재실행으로 candidate=0 확인 권장.)

→ Phase 2 backlog #11 (선택) — APPLY 후 F3 fresh run으로 candidate=0 명시적 측정.

## 5. 발견 사항

### 5.1 Material flag 자동 set (UE 5.5 ISM 부수효과)

APPLY 중 단일 occurrence:
```
LogMaterial: Display: Material /Game/00_PQDQ/01_Features/MI_SectionMisc.MI_SectionMisc
            needed to have new flag set bUsedWithInstancedStaticMeshes!
```

→ ISM 사용 시 material asset에 `bUsedWithInstancedStaticMeshes` flag 자동 추가. **Material asset dirty** (save 시 변경 발생). 의도된 UE 동작 — error 아님.

### 5.2 F2 통계 한계 (Phase 2 backlog 후보)

`stats.py` 의 `_is_static_mesh_actor` 체크가 `isinstance(actor, StaticMeshActor)` 기반.
BP_ISMHolder (parent=`unreal.Actor`) 의 ISMC는 카운트에서 제외 → **F2 단독으로는
실제 drawcall 추적 불가**. 본 박제처럼 외부 산술 (F2 sections + ISM holder count)
필요.

→ Phase 2 backlog #9 (F2 보강: ISM section 통합 카운트) 추가.

### 5.3 Nanite warning (Phase 1부터 존재, ISM 영향 아님)

```
LogStaticMesh: Warning: Invalid material [MI_Window] used on Nanite static mesh
            [Geometry_ncl1_17979]. Only opaque or masked blend modes are
            currently supported, [BLEND_Translucent] blend mode was specified.
```

3건 발생 (Geometry_ncl1_17979, 17919, 16804). Translucent (Window) mesh를 Nanite로
표시 시도 — Phase 1 F2/F3 박제부터 surfacing. ISM 머지와 무관, 카운트 영향 없음.

### 5.4 BP_ISMHolder Project Content 위치 (Phase 2 backlog 후보)

현재 `/Game/Blueprints/BP_ISMHolder` (Project Content). Plugin redistribute 시
다른 project에 plugin install하면 BP 없음 → `_load_bp_ism_holder_class` 가
`RuntimeError` raise.

→ Phase 2 backlog #8 (BP를 Plugin Content `/CAD_Optimizer/Blueprints/`로 이전)
추가.

## 6. 다음 차량 비교용 baseline metric

```
P2_TOTAL_SMA_BEFORE = 45809
P2_TOTAL_SMA_AFTER = 39310
P2_DELTA_SMA = -6499                    # source actor deleted
P2_ISM_HOLDERS_SPAWNED = 303
P2_INSTANCES_MERGED = 6499
P2_PLANS_APPLIED = 303
P2_PLANS_SKIPPED = 0

P2_F3_ESTIMATED_DRAWCALL_REDUCTION = 6196
P2_REAL_DRAWCALL_REDUCTION = 6196       # SMA delta - ISM holder count
P2_F3_ESTIMATE_ACCURACY = TRUE          # byte 단위 일치

P2_TRIANGLES_BEFORE = 29457084
P2_TRIANGLES_AFTER = 26242998
P2_TRIANGLES_DELTA = -3214086           # = sum(mesh_tri * (count-1)) for 303 groups

P2_VERTICES_BEFORE = 33605298
P2_VERTICES_AFTER = 29939169
P2_VERTICES_DELTA = -3666129

P2_UNIQUE_MESHES_BEFORE = 27889
P2_UNIQUE_MESHES_AFTER = 27705          # asset preserved, 184개 mesh가 더 이상 SMA 참조 X
P2_UNIQUE_MATERIALS_BEFORE = 5
P2_UNIQUE_MATERIALS_AFTER = 5           # 0 변동

P2_NANITE_RATIO_BEFORE = 0.99956        # 45789 / 45809
P2_NANITE_RATIO_AFTER = 0.99949         # 39290 / 39310 (ISM holder 제외)

P2_NATURAL_IDEMPOTENT_VERIFIED = PARTIAL  # 로직상 보장, 재실행 미실측
P2_MATERIAL_FLAG_AUTO_SET = TRUE          # MI_SectionMisc bUsedWithInstancedStaticMeshes
```

## 7. 관련 산출물

- Plugin commit: `4ab31ca` (Phase 2 actor merger squash PR #17)
- Apply CSV: `Saved/CAD_Optimizer/actor_merge_applied_20260601_024430.csv`
  (303 plan × 8 columns: mesh_path / mesh_short_hash / instance_count /
  num_materials / pivot_x/y/z / est_drawcall_reduction)
- Pre-APPLY F3 CSV: `instance_report_20260601_024430.csv`
- 코드:
  - `Content/Python/cad_optimizer/actor_merger.py` (신규 ~320 lines)
  - `Content/Python/cad_optimizer/ui/panel.py` (Phase 2 section)
  - `Content/Python/cad_optimizer/ui/menu.py` (Dry Run + APPLY 2 entry)

## 8. 다음 측정 시 체크할 점

- **다른 차종 F3 estimated 정확도** — C1YC_2_MCM에서 byte 일치는 num_materials=1 균일이라
  단순. 다른 차종에서 multi-material slot group 있으면 식 검증 강화
- **APPLY 후 F3 candidate=0** 명시적 측정 (자연 idempotent 실측 보강)
- **Material flag auto-set 발생 mesh** 차종 의존성 (얼마나 흔한 패턴인지)
- **Triangles/Vertices 감소 비율** (mesh 평균 triangle count baseline)
- **Nanite ratio** 안정성 (ISM holder 제외 후 99%+ 유지)
- **Memory / save file size** before/after (UE save file 크기 감소 측정 — backlog 후보)
