# F4 Measurement — C1YC_2_MCM

> 첫 실 GM CAD 측정. Phase 1 exit criteria
> (`lessons_learned/sample_vs_real_data.md`) 첫 충족.

| 항목 | 값 |
|------|-----|
| 측정일 | 2026-05-04 |
| 차량 코드 | C1YC_2_MCM |
| 프로젝트 경로 | `C:\Users\BZLS01\Downloads\C1YC_2_MCM` |
| 레벨 | `L_C1YC_2_MCM` |
| Plugin commit | `843e73b` (F4 squash) |
| Threshold | 0.5 cm (Tiny preset) |

---

## 1. Scan 결과

- Scanned: **107,882 actors**
  - StaticMeshActor: 45,809
  - other: 62,073
- Skipped: 0 no-root, 0 no-mesh, 0 zero-bbox
- Root-level (no attach parent, measured): 4
- Measured: **45,809**

## 2. Diagonal 분포

| 백분위 | 값 |
|--------|-----|
| P10 | 0.2 cm |
| P50 | 2.7 cm |
| P90 | 18.2 cm |

→ Long-tail 정상 분포. CarConfigurator 샘플의 single-bucket
(P10=P50=P90=141.4cm)과 정성적으로 다름.

## 3. Multi-threshold simulation

| Threshold | Small parts | % of measured |
|-----------|-------------|---------------|
| 0.5 cm | 7,138 | 15.6% |
| 1.0 cm | 11,596 | 25.3% |
| 2.0 cm | 18,164 | 39.7% |
| 5.0 cm | 32,241 | 70.4% |
| 10.0 cm | 38,095 | 83.2% |

## 4. Hierarchy 가설 검증

이전 검증(C1YC_2_MCM 별도 UE 프로젝트, plugin 미장착)에서 세운 가설들이
F4 측정으로 사후 confirm됨:

| 가설 | 결과 |
|------|------|
| leaf actor_label 99%+ 가 `Geometry*` (자동 생성) | ✅ confirmed |
| folder_path 거의 빈 셀 | ✅ confirmed |
| 진짜 부품 식별 = immediate attach parent | ✅ confirmed |
| chain depth 6+ 일반적 | ✅ confirmed |
| Noise filter 5종 (RootNode/_asmesh/_RotationPivot/MOVING/EXT) 충분 | ✅ over-filter 없음 |
| Multi-leaf 부품 9.4% 전후 | ✅ smallest 10에 multi=2 surfacing |

## 5. Smallest 10 (실차 첫 surfacing)

Output Log 표시 기준 (diagonal은 2-decimal 반올림). 정확한 mm-단위 수치는 CSV(8번 항목) 참조.

> **2026-05-04 patch**: #3 multi 컬럼 "2" → "1" 정정. CSV 원본의
> `parent_leaf_count=1` / `is_multi_leaf=FALSE` 확인 결과 반영. 이전
> 박제는 Output Log 표시를 그대로 옮긴 cosmetic 오류.

| Rank | Diagonal | Parent (immediate attach parent label) | Mobility | parent_leaf_count |
|------|----------|----------------------------------------|----------|-------------------|
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

**Smallest 10 multi-leaf 비율: 2/10 (20%).** 전체 평균 9.4%(이전 hierarchy 분석)보다
높음 — "smallest 부품일수록 multi-leaf 비율 높을 수 있다"는 가설 신호. 다음 차량
측정 시 이 비율이 비슷하게 나오는지가 가설 강화/약화 신호.

### 5.1 Multi-leaf AABB union merged diagonal (Phase 2 backlog #3, 2026-06-01)

옵션 A (surfacing only, small 판정은 leaf 유지) 첫 iteration 실측:

| Rank | leaf diagonal | parent | merged diagonal | 해석 |
|------|--------------|--------|------------------|------|
| #1 | 0.001cm (Output Log 0.00cm) | VALVE_ASM_600913 | **2.46cm** | leaf는 collapsed (단축), VALVE 부품 진짜 크기 ~2.46cm |
| #2 | 0.001cm | VALVE_ASM_600254 | **2.46cm** | 동일 |
| #3~#10 | 0.00cm | LATCH/SHUTTER (single-leaf) | (merged = self) | multi-leaf 아님 |

**가설**:
- VALVE_ASM 부품엔 collapsed actor (한 축 0.001cm) 가 부착됨 (구조/기하학적 마커?)
- 진짜 부품 크기는 2.46cm
- 옵션 B (판정 = merged) 적용 시 #1, #2 가 small에서 빠짐 (0.5cm 초과)

**Backlog 연결**:
- #3 ✅ 본 박제 patch (merged metric surfacing)
- #4 (zero-bbox epsilon): leaf 0.001cm 한 축 collapsed → 정책 결정 입력
- #5 (collapsed actor 정책): VALVE_ASM에 collapsed 부착 — CAD 팀 확인 후보

## 6. 진단 신호로서의 0.00cm

Smallest 10의 #1~#10 모두 Output Log에서 ~0.00 cm로 표시 (CSV 3-decimal에선
0.001~0.010 cm 범위). Self-review #1 (한 축 collapsed actor)이 실제 surfacing됨.
zero-bbox 분기를 통과한 것은 의도된 동작:

- `extent.x=0, y=0, z=0` → `skipped_zero_bbox` (3축 모두 0인 경우만)
- `extent.x=0.001, y=0, z=0` → 측정됨, smallest로 분류

PCVR cull 후보 1순위로 정확한 surfacing. **버그 아닌 진단 신호로 confirmed.**

## 7. 미래 비교용 baseline metric

다음 차량 측정 시 비교할 핵심 수치:

```
TOTAL_ACTORS = 107882
STATIC_MESH_ACTORS = 45809
ROOT_LEVEL = 4
DIAG_P10_CM = 0.2
DIAG_P50_CM = 2.7
DIAG_P90_CM = 18.2
SMALL_AT_0.5_CM = 7138       # 15.6%
SMALL_AT_1.0_CM = 11596      # 25.3%
SMALL_AT_2.0_CM = 18164      # 39.7%
SMALL_AT_5.0_CM = 32241      # 70.4%
SMALL_AT_10.0_CM = 38095     # 83.2%
SMALLEST_10_MULTI_LEAF_RATIO = 0.30   # 3/10
```

## 8. 관련 산출물

- 원본 CSV: Philip 로컬 (`C:/Users/BZLS01/Downloads/C1YC_2_MCM/Saved/CAD_Optimizer/small_part_report_20260504_020105.csv`)
- F4 plugin commit: `843e73b`
- Lesson: `docs/lessons_learned/sample_vs_real_data.md`
- Hierarchy 검증 세션 노트: 이전 세션 컨텍스트, 별도 박제 없음

## 9. 다음 측정 시 체크할 것

- 다른 vehicle program (truck/SUV)에서 분포 모양이 비슷한가
- multi-leaf 비율(전체 9.4% vs smallest 10 30%)이 다른 차량에서도 유지되는가
- noise filter 5종이 다른 차량에서도 충분한가 (over-filter 발생 여부)
- chain depth 평균이 비슷한가 (Datasmith pipeline 일관성 지표)
- ROOT_LEVEL이 한 자릿수에 머무는가 (Datasmith 구조 변형 신호)
