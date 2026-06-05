# VR Baseline + Plugin Hypothesis 부정 — C1YC_2_MCM

> Phase 1~3 작업 후 첫 VR 실측. Plugin 의 main hypothesis
> ("drawcall 줄이면 PCVR 빨라진다") 가 이 측정으로 **부정됨**.
> Nanite + rendering settings 만으로 효과의 90%+ 가 나옴.

| 항목 | 값 |
|------|-----|
| 측정일 | 2026-06-05 ~ 06 |
| 차량 코드 | C1YC_2_MCM |
| 엔진 | UE 5.5 |
| GPU | RTX 5000 Ada (Ada Lovelace) |
| HMD | Meta Quest 3 via PCVR Link |
| Plugin commit | `Config/DefaultEngine.ini` 적용 후 |
| Level 상태 | Phase 2 머지 X, Phase 3 cull X (raw 45,809 SMA) |

---

## 1. Editor Viewport (초기 오인 측정)

대화 초기 "11 FPS" 보고 — Editor viewport 측정값으로 추정. PIE 진입 시
**50~55 FPS** 로 확인됨. Editor overhead (toolbar/outliner/asset thumbnail
갱신) 차이.

→ **lesson**: VR feasibility 판단은 항상 **PIE 또는 standalone build** 기준.
Editor viewport FPS 는 무관.

## 2. Desktop PIE (Nanite ON, default rendering)

```
stat unit
  Frame  19~20 ms     = 50~55 FPS
  Game   14~15 ms     ← CPU bound (actor Tick / Blueprint)
  Draw   18~19 ms     ← Render thread (Draw thread bound)
  RHIT   14~15 ms
  GPU    11 ms        ← 여유 있음
  draws  360          ← Nanite 가 합쳐서 매우 적음 ✅
  prims  527.7 k      ← Nanite cluster cull 후
```

→ **Drawcall 360**. 우리 plugin 의 Phase 2 actor merging (45,809 → 39,310
SMA, 6,196 drawcall 감소) 의 main 효용 = **이미 Nanite 가 internally 처리 중**.
실 drawcall 추가 감소 거의 없음.

## 3. VR Preview (default rendering, DLSS 시도 전)

```
stat unit
  Frame    140 ms     ← ~7 FPS
  Game     14.45 ms
  Draw     0.00 ms    (VR 모드 표시 통합)
  RHIT     2.82 ms
  CPU time 130 ms
  Input    273.30 ms  (60Hz 못 따라가 늘어남)
  draws    313
  prims    781 k      ← VR 양쪽 eye 합산

stat gpu
  TOTAL                        111.05 ms
  TemporalSuperResolution       23.88 ms (21%)
  LumenScreenProbeGather        16.85 ms (15%)
  VolumetricCloud               15.96 ms (14%)
  NaniteVisBuffer               12.62 ms (11%)
  LumenReflections               5.74 ms
  RenderDeferredLighting         4.92 ms
  LumenSceneLighting             4.19 ms
  Translucency                   4.06 ms
  ... 기타 ~24 ms

stat scenerendering
  Mesh draw calls                70  ← VR 양쪽 eye 합산 매우 적음
  Occluding instances          5,910

stat rhi
  Triangles drawn            789,747
  DrawPrimitive calls            380
  UAV Texture Memory          4,153 MB  ← VR 양쪽 eye render target
```

**핵심 finding**:
- GPU 111ms / frame 140ms — **GPU bound**
- Drawcall 70 — 진짜로 적음. Phase 2 머지 의미 없음 확정
- 진짜 비용: TSR / Lumen / VolCloud / Nanite 4개 = 69ms (62%)
- Nanite 비용은 16.6ms (전체의 14%) — 이미 효율적

## 4. Rendering Settings 조정 후 (실측)

`Config/DefaultEngine.ini` 의 `[SystemSettings]`:
```
r.VolumetricCloud=0
r.RayTracing.Enable=0
r.Lumen.HardwareRayTracing=0
r.Lumen.Reflections.Allow=0
r.ScreenPercentage=80
```

(Lumen GI = `ScreenProbeGather` 는 유지 — 끄면 어두워짐 확인)

VR 결과:
```
Frame   72.39 ms     ← 14 FPS
Game    13.46 ms
GPU     65.38 ms     ← -46 ms (41% 절감)
Input  184.76 ms
```

→ frame 140ms → 72ms (절반).

## 5. DLSS 도입 시도 → 실패

NVIDIA DLSS UE plugin (Streamline 기반) 설치:
- DLSS / Streamline / StreamlineCore / StreamlineNGXCommon /
  StreamlineReflex / StreamlineDLSSG / StreamlineDeepDVC

### 5.1 발견 — `r.NGX.DLSS.Quality` cvar 존재 안 함

Console autocomplete 확인 결과 (`r.NGX.DLSS.` prefix 의 cvar 들):
- Enable, Preset, AutoExposure, DenoiserMode 등은 있음
- **Quality 는 없음**

DLSS Mode 선택 (Performance/Balanced/Quality/DLAA) 은:
- Project Settings GUI: **dropdown 없음** (Preset 만 있음 — model variant)
- BP node `Set DLSS Mode` 만 명시적 설정 가능
- 또는 plugin Auto Quality Setting

`Preset` 은 model variant (F/J/K/L/M) — quality 아님:
- K: DLAA/Balanced/Quality default (가벼움)
- L: UltraPerf default (sharp, ghosting 적음, 비쌈, RTX 40+ 최적)
- M: Performance default (RTX 40+ 최적)

→ Plugin 의 quality 통제 mechanism 이 console-only 가 아님.

### 5.2 VR stereo 깨짐

PIE → VR Preview 진입 시 **오른쪽 eye 검정 (left eye only)**.

진단:
- `r.NGX.DLSS.Enable 0` 해도 복구 안 됨 (plugin hook 단계)
- `r.ScreenPercentage 100` 해도 복구 안 됨
- Instanced Stereo Rendering 정상
- **DLSS plugin 전체 disable → stereo 정상 복구** ✅

→ NVIDIA DLSS plugin (현재 버전) 이 **UE 5.5 VR stereo path 와 호환 안 됨**.
DLSS / DLAA 모두 사용 불가 (같은 plugin path).

→ `.ini` 의 DLSS cvar 2줄 제거 (PR #27).

## 6. 진짜 finding — Plugin Hypothesis 부정

### 6.1 가설 vs 실측

| 가설 (Phase 1~3 출발점) | 실측 결과 |
|------------------------|-----------|
| "45K mesh = drawcall 폭주 → VR 느림" | Drawcall 70 (VR), 360 (desktop). 진짜 적음 |
| "Actor merging 으로 6,196 drawcall ↓ → VR ↑" | 실 GPU 영향 거의 0 (이미 Nanite 처리 중) |
| "Set_hidden cull 로 GPU 절감" | NaniteVisBuffer 12ms 의 작은 일부 (~1~2ms 추정) |
| "DLSS 로 -15~18ms 절감" | UE 5.5 + 이 plugin 버전 에선 사용 불가 |

### 6.2 진짜 GPU 비용 분포 (VR, baseline)

```
TSR                23.88 ms (21%)   ← post-process
Lumen GI           16.85 ms (15%)   ← lighting
Volumetric Cloud   15.96 ms (14%)   ← atmospherics ← 차량에 불필요
Nanite VisBuffer   12.62 ms (11%)   ← mesh rendering
나머지            ~42    ms (38%)
```

→ **Mesh rendering (Nanite + drawcall) 은 GPU 의 11~14% 만 차지**.
나머지는 post-process / lighting / atmospherics.
Plugin 의 drawcall 감소 작업이 GPU 4ms 도 못 줄임.

### 6.3 효과 입증된 작업

| 작업 | 효과 |
|------|------|
| **`Config/DefaultEngine.ini` rendering tuning** | GPU 111 → 65ms (**-46ms**, 41% 절감) |
| **VolCloud off** | -16ms |
| **Lumen Reflections off** | -6ms |
| **RT off** | -2~5ms |
| **ScreenPercentage 80** | -13ms 추정 |
| **Phase 2 actor merging** | 측정 불가능 (effect < noise floor) |
| **Phase 3 set_hidden cull** | NaniteVisBuffer 의 일부 (미미) |

## 7. Plugin 정체성 재정의

**기존 (Phase 1~3 기간)**: "Drawcall 줄여 PCVR 빠르게"  
**새 (Phase 4+)**: "차량 진단 + rendering tuning + movable 부품 식별"

### 7.1 Plugin 의 진짜 가치 (유지)

- **F2 mesh stats** — 새 차량 받을 때 baseline 측정
- **F4 small parts** — 진단 (어떤 부품이 작은지)
- **F5 NX naming** — 분류 (어떤 카테고리인지)
- **F6 material consolidation** — 진단
- **F7 integrated report** — 차량 종합 보고
- **F8 metadata tagging** — 도메인 지식 입력 (Nanite 가 모름)

→ **한 번 측정 박제로 가치 추출**. 매 차량 자동화는 필요 시.

### 7.2 Plugin 에서 stop (효용 부정됨)

- **Phase 2 actor merging** — drawcall 이미 적음 → 효과 0
- **Phase 3 set_hidden cull** — Nanite VisBuffer 의 작은 일부

→ 코드 유지 (revert 안 함, 사용 안 함). 다음 차종 측정 시 호출 안 함.

### 7.3 새 트랙 — Rendering / VR setup

- `Config/DefaultEngine.ini` — 이미 작업 시작
- **Baked lighting** (Lightmass) — Lumen GI off → -22ms 잠재
- **Foveated Rendering** plugin — Quest 3 주변부 ↓
- **Movable 분류** (도어/트렁크) — F5 NX naming 확장 (선택)
- **VR plugin 호환성** — DLSS 향후 재검토

## 8. 다음 차량 비교용 metric

```
PLUGIN_MAIN_HYPOTHESIS_VERDICT = REJECTED  # drawcall ↓ ≠ VR FPS ↑
VR_BASELINE_GPU_MS = 111                   # default rendering
VR_TUNED_GPU_MS = 65                       # VolCloud/RT/LumenRefl off + SP80
VR_DRAWCALL = 70                           # 양쪽 eye, Nanite 처리됨
NANITE_GPU_SHARE_PCT = 14                  # Nanite 가 전체 GPU 의 14% 만 차지
TOP_GPU_COSTS = [TSR, LumenGI, VolCloud, Nanite]
DLSS_VR_USABLE = FALSE                     # UE 5.5 + 현재 plugin 버전
PHASE_2_MERGE_REAL_GPU_DELTA = ~0          # below measurement noise
PHASE_3_CULL_REAL_GPU_DELTA = ~1_2         # Nanite VisBuffer 일부
RENDERING_TUNING_REAL_GPU_DELTA = -46      # 실측 절감
```

## 9. 관련 산출물

- 코드: `Config/DefaultEngine.ini` (PR #26 + #27 hotfix)
- 박제: 이 file (`vr_baseline_c1yc_2_mcm.md`)
- 종합 보고: `docs/measurements/integrated_report_c1yc_2_mcm.md` (Phase 1)
- 회고: `docs/phase1_retrospective.md`
- Backlog: `docs/phase2_backlog.md` — 효용 부정으로 사실상 obsolete

## 10. 다음 cycle 후보 (입력)

순서:
1. **Baked lighting (Lightmass)** 시도 — Lumen GI off → -22ms 잠재.
   Lightmap UV 필요 (CAD mesh 변수). Production quality build 1회.
2. **Foveated Rendering** — Quest 3 호환 plugin 검토.
3. **차량 두 번째 측정** — Plugin 효용 부정 finding 일관성 검증.
4. **Movable 부품 식별** (F5 NX naming 확장) — 도어/트렁크 BP wrap 입력.
5. **DLSS 향후 재검토** — plugin 패치 또는 다른 path.
