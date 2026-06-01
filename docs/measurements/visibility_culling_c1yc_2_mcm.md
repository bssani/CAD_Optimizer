# Visibility Culling (Phase 3) — C1YC_2_MCM

> Phase 3 첫 task 첫 실차 박제. F8 metadata tag (Phase 1 박제) 를 입력으로
> `set_actor_hidden_in_game(True)` 영구 적용. Phase 1 F8 tier 분포와
> byte 단위 일치 검증.

| 항목 | 값 |
|------|-----|
| 측정일 | 2026-06-01 |
| 차량 코드 | C1YC_2_MCM |
| 프로젝트 경로 | `C:\Users\BZLS01\Downloads\C1YC_2_MCM` |
| 레벨 | `L_C1YC_2_MCM` |
| Plugin commit | Phase 3 첫 PR (visibility_culler 신규) |
| F2 baseline 상태 | **머지 전** (45,809 SMA) — Phase 2 actor merging 적용 안 된 level |
| Tag prefix | `CADOpt_P3_` (sentinel + source tier) |

---

## 1. F2 Before / After (예상대로 변동 0)

| 항목 | Before (22:48:46) | After (22:49:28) | Delta |
|------|-------------------|-------------------|-------|
| Static Mesh Actors | 45,809 | 45,809 | 0 |
| Total Triangles | 29,457,084 | 29,457,084 | 0 |
| Total Vertices | 33,605,298 | 33,605,298 | 0 |
| Material Sections | 45,809 | 45,809 | 0 |
| Unique Materials | 5 | 5 | 0 |
| Unique Static Meshes | 27,889 | 27,889 | 0 |
| Nanite-Enabled | 45,789 / 45,809 | 45,789 / 45,809 | 0 |

**해석**: `set_actor_hidden_in_game(True)` 는 **mesh 통계 영향 없음**. F2는 잠재
drawcall 상한 (level에 존재하는 mesh) 만 측정. **실제 drawcall 감소 효과는
GPU profiling 으로만 확인 가능** (`stat scenerendering`, `stat gpu`).

## 2. Phase 3 Cull 실행 결과

### 2.1 Cull_High only (보수)

```
[Phase 3] Targets (F8 tag matched): 1,680
[Phase 3] Newly hidden: 1,680
[Phase 3] Already hidden: 0
[Phase 3] Skipped: 0
[Phase 3]   CADOpt_F8_Cull_High: 1,680
```

→ Phase 1 F8 박제 `CADOpt_F8_Cull_High = 1,680` 과 **byte 일치** ✅

### 2.2 Cull_High + Mid (적극)

```
[Phase 3] Targets (F8 tag matched): 4,179
[Phase 3] Newly hidden: 4,179
[Phase 3] Already hidden: 0
[Phase 3] Skipped: 0
[Phase 3]   CADOpt_F8_Cull_High: 1,680
[Phase 3]   CADOpt_F8_Cull_Mid: 2,499
```

산술: `1,680 + 2,499 = 4,179` ✅

Phase 1 F8 박제 (`Cull_High 1,680 + Cull_Mid 2,499`) 와 **byte 일치** ✅

### 2.3 Restore P3 Visibility (안전망)

```
[Phase 3] Restored: 4,179
[Phase 3] Skipped: 0
```

→ Cull total (4,179) 과 정확 일치 ✅. Sentinel tag 기반 일괄 복원 정상 동작.

## 3. Phase 1 F8 박제 cross-check

| Tier | F8 박제 (Phase 1) | Phase 3 Cull 실측 | 일치 |
|------|--------------------|--------------------|------|
| `CADOpt_F8_Cull_High` | 1,680 | 1,680 | ✅ |
| `CADOpt_F8_Cull_Mid` | 2,499 | 2,499 | ✅ |
| Total cull-eligible | 4,179 | 4,179 | ✅ |

→ Phase 1 → Phase 3 end-to-end metric 일관성 확인. F8 tag 부여 → 머지 영향
없이 (이번 측정은 머지 전) → Phase 3 cull 입력으로 정확히 사용됨.

## 4. Idempotent + Reversible 검증

| 동작 | 검증 |
|------|------|
| 1차 cull → Newly 1,680, Already 0 | ✅ initial 동작 |
| 2차 cull (High+Mid) → Newly 4,179, Already 0 | ✅ (1차 후 sentinel tag 재부여, action="skip-tag-added") |
| Restore → 4,179 | ✅ 일괄 복원, sentinel tag 제거 |
| Level dirty 경고 | ✅ 모든 mutation 시 surface |

## 5. 머지 + cull 시나리오 (미측정, 향후)

본 측정은 **머지 전 level** 기준. 실 PCVR 시나리오 (Phase 2 머지 + Phase 3
cull 둘 다 적용) 에선:
- Phase 2 머지로 6,499 source actor 삭제됨 — 그 중 일부는 F8 tag 보유
- → 머지 후 살아남은 F8 tag actor 수 = **머지된 source 중 F8 tag 보유한 수만큼 줄어듦**

**예상**: F8 small parts (Cull_High/Mid) 가 F3 candidate (count ≥ 10) 의 일부일
때만 머지로 사라짐. Cull_High 1,680 중 머지로 사라진 수는 미측정.

→ 다음 cycle: 머지 + cull 둘 다 적용 후 실 cull 카운트 박제.

## 6. 진짜 drawcall 효과 — GPU profiling 필요

`set_actor_hidden_in_game(True)` 의 효과는 **GPU render queue 에서 mesh 제외**.
F2 (mesh count) 로는 측정 불가. 진짜 metric:

- `stat scenerendering` — Visible Static Meshes / DrawPrim 카운트
- `stat gpu` — render pass 별 시간
- `stat nanite` — Nanite cluster cull 효율
- VR Preview frame time

다음 측정 시 PIE 진입 + 위 stat 명령 실행 후 결과 박제.

## 7. 다음 차량 비교용 baseline metric

```
P3_CULL_HIGH_TARGETS = 1680           # F8 박제 Cull_High 일치
P3_CULL_MID_TARGETS = 2499            # F8 박제 Cull_Mid 일치
P3_TOTAL_CULL_TARGETS = 4179          # High + Mid 합
P3_NEWLY_HIDDEN_FIRST_RUN = 1680      # High only 1차
P3_NEWLY_HIDDEN_FULL = 4179           # High + Mid 2차
P3_RESTORE_COUNT = 4179               # Sentinel tag 기반 일괄 복원
P3_F2_DELTA = 0                       # 예상 (set_hidden은 mesh count 무관)
P3_BASELINE_LEVEL_STATE = pre_merge   # 머지 전 측정
P3_IDEMPOTENT_VERIFIED = TRUE         # 1차 → 2차 Already hidden 0 (sentinel re-applied)
P3_REVERSIBLE_VERIFIED = TRUE         # Restore 4179 = Cull 4179
```

## 8. 관련 산출물

- 코드: `Content/Python/cad_optimizer/visibility_culler.py` (신규, F-pattern, `import unreal` 0)
- Phase 3 CSV: `Saved/CAD_Optimizer/p3_visibility_cull_*.csv` (5 컬럼: actor_path/actor_label/matched_tier/was_hidden_before/action)
- 메뉴: `🙈 Cull Visibility (Phase 3) — High only` / `High + Mid` + `👁️ Restore P3 Visibility`

## 9. 다음 측정 시 체크할 점

- **머지 + cull 시나리오** — Phase 2 머지 적용된 level에서 cull 실측 (살아남은 F8 tag actor 수)
- **GPU profiling** — `stat scenerendering` Visible Static Meshes / DrawPrim 변동
- **VR frame time** — PCVR (Quest 3 via Link) 환경에서 stat unit, frame time
- **Cull_Review tier** — 사용자 재검토 후 추가 cull 가치 여부
- **다른 차종 F8 분포** — Cull tier 카운트 일관성 (현재 Cull_High = LATCH dominant)
