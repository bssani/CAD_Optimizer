# CLAUDE.md

> AI (Claude)와 협업할 때 매 세션 시작 시 참조하는 프로젝트 컨텍스트 파일.
> **버전**: v0.9 (2026-06-06, VR 실측 → plugin hypothesis 부정 → 정체성 재정의)

---

## 1. 프로젝트 개요

**이름**: CAD_Optimizer (내부명: GMTCK CAD Optimizer)
**저장소**: `C:\Git\MeshOptimization\Plugins\CAD_Optimizer`
**목적**: GM 차량 CAD 데이터를 PCVR 환경에서 다루기 위한 **진단/측정 + rendering setup 도구**.
(기존 목적 "draw call 감소" 는 VR 실측으로 효용 부정됨 — 2026-06-06 박제 참조)
**사용자**: GMTCK PQDQ 팀 + 다른 부서
**배포**: 사내 git 서버, plugin 형태로 UE 프로젝트에 drop-in
**현재 타겟**: PCVR 전용 (Nanite 활용). Web/standalone용 mesh 감량(decimation, LOD)은 향후 별도 트랙(Phase W, 미정)으로 검토.

**Plugin 진짜 가치 (재정의)**:
1. **차량 진단/측정 도구** — F2/F4/F5/F6/F7 한 번 실행해 차량 baseline 박제
2. **사용자 도메인 tag** (F8) — Nanite 가 모르는 정보 (movable, cull, keep)
3. **Rendering setup** (`Config/DefaultEngine.ini`) — VR/PCVR 영구 cvar 적용

## 2. 사람 소개

**담당자**: 최필립 (GMTCK PQDQ, Unreal Engine 개발자)
**배경**: Python 자동화·.exe 패키징 경험 있음. UE VR 개발 중. CAD 도메인 학습 중.
**협업 원칙**: "필립이 70% 일하고 Claude가 30% 가속". 학습 목표 병행.

## 3. 기술 스택

- **엔진**: Unreal Engine 5.5 (고정)
- **언어**: Python (UE 내장 3.11.x)
- **UI**: Editor Utility Widget (UMG)
- **C++**: 사용 안 함
- **외부 라이브러리**: Phase 1엔 없음. 외부 라이브러리 도입은 MIT 라이선스만 검토.
- **버전 관리**: 사내 git 서버 + GitHub mirror (main only + squash)
- **타겟 하드웨어**: RTX 5000 Ada 노트북 + Meta Quest 3 (via PCVR Link)
- **렌더링**: Deferred + Nanite + TSR
  (DLAA/DLSS 는 UE 5.5 VR stereo bug 로 사용 불가 — 2026-06-06 확정)
- **Long-running task**: `unreal.ScopedSlowTask` + batch processing (F0)

## 4. 핵심 결정사항

- **Nanite 켜고 간다**: Decimation 대신 Nanite 활용.
  → 실측 (2026-06-06): Nanite 만으로 drawcall 45,809 → 70 (VR) 자동 처리.
  Drawcall 정리 작업의 추가 효용 사실상 0.
- **Forward rendering 포기, Deferred 선택**: Nanite 사용 위해
- **PiXYZ 대체 자체 구축**: 라이선스 리스크 회피
- **Phase 1 (진단/측정 도구) ✅ 완료** — 이게 plugin 의 진짜 가치
- **Phase 2 (actor merging) / Phase 3 (visibility culling) — 효용 부정**:
  Nanite 가 이미 처리. 코드는 유지 (revert 안 함) but 새 작업/확장 안 함.
- **F0 infrastructure 우선**: 30,000 mesh 처리 freeze 방지 (Week 1 최우선)
- **F8 metadata tagging**: Phase 3 입력으로 설계되었지만 실 가치는 사용자 도메인 tag
  (movable / keep / cull) — Nanite 가 모르는 정보 보존
- **새 트랙 — Rendering / VR setup** (2026-06+):
  - `Config/DefaultEngine.ini` 의 [SystemSettings] cvar 영구 적용
  - VolCloud / RT / Lumen Reflections off + ScreenPercentage 80
  - 측정 효과: GPU 111ms → 65ms (VR, -46ms, 41% 절감)
  - 다음: baked lighting, Foveated Rendering, movable BP wrap

## 5. 절대 하지 말 것 (Lessons Learned)

상세는 `docs/lessons_learned/` 참조.

- ❌ **전체 차량 한꺼번에 decimation** — mesh 깨짐. Part별 개별 처리
- ❌ **Nanite 끄고 decimation** — self-sabotage
- ❌ **GPL/non-commercial 라이선스 라이브러리** (MeshLib 등) — 상용 리스크
- ❌ **glTF 경유 파이프라인** — Datasmith 네이티브 우회 시 정보 손실
- ❌ **UE Mesh Editor Simplify를 CAD mesh에 사용** — CAD 특성 대응 X
- ❌ **Progress/cancel 없이 대량 처리** — 에디터 freeze (F0이 해결)
- ❌ **Deprecated API 사용** (예: `EditorLevelLibrary` — UE 5.1에서 deprecated, `EditorActorSubsystem` 사용)
- ❌ **Subsystem 직접 생성자 호출** (예: `unreal.EditorActorSubsystem()`) — 5.2+ deprecated.
  반드시 `unreal.get_editor_subsystem(Cls)` 사용
- ❌ **검증 없이 AI 제안 UE API 사용** — 추정 오답률 높음.
  `dir()`로 존재 확인 + 한 줄 실험 후 반복문. 상세: `docs/lessons_learned/api_verification_first.md`
- ❌ **검증 없이 AI 제안 console cvar 사용** — `r.NGX.DLSS.Quality` 같은
  존재하지 않는 cvar 잘못 안내 사례. autocomplete (`r.NGX.DLSS.` 등) 또는
  `help` 명령으로 cvar 존재 확인 후 사용.
- ❌ **DLSS / Streamline plugin 그냥 enable** — UE 5.5 VR stereo path 와
  호환 안 됨 (right eye 검정). VR project 에선 plugin 자체 install 안 하거나,
  install 후 PIE viewports 체크박스 OFF.
- ❌ **drawcall 감소 작업으로 PCVR 성능 ↑ 가정** — Nanite 가 이미 처리.
  실 GPU 시간의 14% 만 Nanite mesh 비용. 진짜 GPU 비용은 post-process /
  lighting / atmospherics. 상세: `docs/measurements/vr_baseline_c1yc_2_mcm.md`

## 6. 작업 방식

### 코드 줄 때
- 먼저 **접근법**부터 (코드 아님)
- 코드엔 **핵심 아이디어 한 단락** + 주석
- 줄 단위 설명 가능해야 함
- 새 개념 나오면 짧게 설명
- **"variation 과제"** 1개씩 제안

### 정보 전달 시
- 확신 없으면 검색해서 확인 (라이선스, API 스펙, 버전 특히)
- **UE 버전별 deprecated API 주의** — 5.5 기준 맞는지 체크
- 틀렸다고 판단되면 솔직히 정정

### 의사결정 시
- 여러 옵션 → trade-off 명확히
- "이게 best" 단정 X
- Scope creep 경계 → "Phase 2 백로그로"

### 학습 지원
- 매 sub-task 후 **"방금 거 너 말로 정리해줘"**
- 못 설명하면 다시 짚기
- `docs/concepts/`에 기록 유도

## 7. Phase 현황

**현재**: **Plugin track 종결**. Rendering / VR setup track 진입.

### Phase 1 ✅ 완료 (2026-05-13)
- Week 1: **F0 (infrastructure)** + F1 (plugin 골격) ✅
- Week 2: F2 (mesh 통계) ✅
- Week 3: F3 (instance detection) ✅
- Week 4: F4 (small part culling) + F5 (NX naming classification) ✅
- Week 5: F6 (material consolidation) + F7 (리포트) + F8 (metadata tagging) ✅

→ **진단/측정 도구로서 가치 valid**. 새 차량 받을 때 재실행.
회고: `docs/phase1_retrospective.md`

### Phase 2 (actor merging) — 효용 부정 (2026-06-06 확정)
구현됨 (`actor_merger.py`, `BP_ISMHolder`) but **VR 실측으로 효과 0 확인**.
- 측정: 45,809 → 39,310 SMA, drawcall 6,196 ↓ — 그러나 Nanite 가
  이미 drawcall 360 → 70 (VR) 으로 처리 중
- → 머지의 GPU 영향 측정 noise floor 아래
- 코드 유지 (revert 안 함). 새 작업/확장 안 함.

### Phase 3 (visibility culling) — 효용 부정 (2026-06-06 확정)
구현됨 (`visibility_culler.py`) but Nanite VisBuffer 12ms 의 작은 일부 (~1~2ms)
영향만 추정.
- F8 tag → set_hidden 자체는 idempotent + reversible 확인
- 코드 유지. 새 작업/확장 안 함.

### Phase 4 — Rendering / VR setup (현재 트랙, 2026-06+)

**Verdict**: 진짜 효과는 rendering settings 에 있음 (VR GPU 111 → 65ms 실측).

작업 입력:
- ✅ `Config/DefaultEngine.ini` 초기 적용 (PR #26 + #27 hotfix)
- 다음 후보 (우선순위 순):
  1. **Baked lighting (Lightmass)** — Lumen GI off → -22ms 잠재 (Lightmap UV 변수)
  2. **Foveated Rendering** — Quest 3 호환 plugin 검토
  3. **차량 두 번째 측정** — plugin 효용 부정 finding 일관성 검증
  4. **Movable BP wrap** — 도어/트렁크/본넷 (F5 NX naming 확장으로 식별)
  5. **DLSS 향후 재검토** — UE 5.5 VR stereo bug 패치 또는 다른 path

**박제**: `docs/measurements/vr_baseline_c1yc_2_mcm.md`

### Out of scope (현재 모든 트랙)
- Mesh decimation (Nanite 가 처리 — Phase W 도 사실상 불요)
- Polished GUI
- C++ 코드
- DLSS / DLAA 도입 (UE 5.5 VR bug)

## 8. 파일 위치 참조

| 무엇 | 어디 |
|------|------|
| 전체 계획 | `docs/Phase1_Kickoff.md` |
| 주차별 로그 | `docs/weekly_log/weekNN.md` |
| 의사결정 기록 | `docs/decisions/ADR_*.md` |
| 실패/함정 | `docs/lessons_learned/*.md` |
| 학습 노트 (필립 작성) | `docs/concepts/*.md` |
| 실차 측정 박제 | `docs/measurements/*.md` |
| **VR 실측 + plugin hypothesis 부정** | `docs/measurements/vr_baseline_c1yc_2_mcm.md` ⭐ |
| Phase 2 backlog (효용 부정으로 obsolete) | `docs/phase2_backlog.md` |
| Phase 회고 | `docs/phase{N}_retrospective.md` |
| Plugin 소스 | `Content/Python/cad_optimizer/` + `Content/EditorWidgets/` |
| **VR rendering cvar 영구 적용** | `Config/DefaultEngine.ini` ⭐ |

## 9. 세션 시작 시 권장 절차

Claude와 새 대화 시작할 때:

1. 이 `CLAUDE.md` 첫 메시지에 포함 (또는 핵심 섹션)
2. **현재 주차와 진행 중 task** 명시
3. 최근 `weekly_log/weekNN.md` 요약
4. 특정 파일 다룰 거면 해당 파일 내용 포함

예:
> "현재 Phase 1 Week 2, F2 구현 중. 어제 StaticMeshActor 순회 완료.
> 오늘은 polygon count 집계 시작 예정. 어제 코드: [첨부]"

## 10. 업데이트 규칙

- Phase 이동 시 (Phase 1 → Phase 2)
- 기술 스택 변경 시
- 새 lesson learned 생겼을 때
- 주요 결정 번복 시

상세 내용은 다른 파일 링크. 이 파일은 index 역할.

---

## 11. 변경 이력

- **2026-04-18 (v0.1)**: 초안
- **2026-04-18 (v0.2)**: Gemini Pro 리뷰 반영
  - F0 (infrastructure) 추가 → long-running task freeze 방지
  - F8 (metadata tagging) 추가 → Phase 3 대비
  - Lessons learned에 deprecated API 경고 추가
  - Repo 경로 명시 (`C:\Git\MeshOptimization\Plugins\CAD_Optimizer`)
- **2026-04-23 (v0.3)**: Week 1 완료 반영 (§7 상태 업데이트)
- **2026-04-23 (v0.4)**: §1에 타겟 범위 명시 — PCVR 전용, decimation/LOD는 Phase W 별도 트랙
- **2026-04-24 (v0.5)**: Week 2 발견 사항 반영 — subsystem 생성 규칙, AI API 검증 원칙 §5 편입
- **2026-04-24 (v0.6)**: Week 3 완료 반영 — §7 상태 업데이트
- **2026-05-04 (v0.7)**: Week 4 완료 반영
  - §7 상태 업데이트 (Week 4 ✅, Week 5 진입 직전)
  - §8에 신규 산출물 reference 추가: `docs/measurements/`, `docs/phase2_backlog.md`
  - 신규 박제: `docs/measurements/f4_c1yc_2_mcm.md` (실차 첫 측정),
    `docs/concepts/nx_naming_patterns.md` (V2 regex 박제),
    `docs/phase2_backlog.md` (Phase 2 입력 문서)
  - F4 Datasmith hierarchy 발견 — leaf actor_label 99%+ Geometry*, attach
    parent에서 부품명 식별 (실차 검증으로 확정)
  - F5 분리 원칙 — 측정 (`small_part_detector.py`)과 분류 (`nx_naming.py`)
    모듈 분리, panel이 결합. 향후 F-pattern으로 재사용 가능.
- **2026-05-13 (v0.8)**: **Phase 1 종료 반영**
  - §7 Phase 1 완료 마킹 (2026-05-13 F8 main merge) + Phase 2 진입 대기 항목 명시
  - §8 Phase 회고 파일 위치 추가 (`docs/phase{N}_retrospective.md`)
  - 신규 박제: `docs/phase1_retrospective.md`, `docs/weekly_log/week05.md`,
    `docs/measurements/f5_nx_distribution_c1yc_2_mcm.md`,
    `docs/measurements/integrated_report_c1yc_2_mcm.md`,
    `docs/measurements/f8_c1yc_2_mcm.md`,
    `docs/concepts/material_analysis_c1yc_2_mcm.md`
  - F-pattern 4번째 검증 (F8 mutation도 분리 원칙 유지 — `metadata_tagger.py`
    `import unreal` 0건, actor duck-typed)
  - F6 박제 self-correction 패턴 정립 (3-value enum: `no_slot` /
    `slot_empty` / `has_override`)
  - F8 BRACKET small=0 발견 → Phase 2 backlog #7 추가 (tier schema 차종
    의존 검증 필요)
  - End-to-end idempotent 검증 첫 사례 — F7 § 9 preview ↔ F8 apply 산술
    일치 (1,680 / 2,499 / 2,959 / 38,671)
- **2026-06-06 (v0.9)**: **VR 실측 → Plugin hypothesis 부정 → 정체성 재정의**
  - §1 목적 정정: "drawcall 감소" → "진단/측정 + rendering setup"
  - §3 렌더링 표기: DLAA → TSR (DLSS plugin UE 5.5 VR stereo bug)
  - §4 핵심 결정 갱신: Phase 2/3 효용 부정, 새 트랙 (rendering) 명시
  - §5 lessons learned 추가:
    * console cvar 검증 (autocomplete + help)
    * DLSS plugin VR 호환성 (right eye 검정)
    * drawcall 감소 → PCVR 성능 ↑ 가정 부정
  - §7 Phase 현황 전면 갱신: Phase 1 valid / Phase 2/3 stop / Phase 4 (rendering) 진입
  - §8 신규 산출물 reference:
    * `docs/measurements/vr_baseline_c1yc_2_mcm.md` ⭐ (main finding)
    * `Config/DefaultEngine.ini` ⭐ (rendering tuning)
  - 신규 박제: `docs/measurements/vr_baseline_c1yc_2_mcm.md`
  - 신규 코드: `Config/DefaultEngine.ini` (PR #26 + #27 hotfix)
  - 핵심 metric: VR GPU 111ms → 65ms (-46ms, 41% 절감, rendering tuning).
    Phase 2 merge / Phase 3 cull 의 실 GPU delta = ~0 (noise floor 아래).

---

*마지막 업데이트: 2026-06-06*
