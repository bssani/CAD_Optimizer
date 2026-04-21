# CLAUDE.md

> AI (Claude)와 협업할 때 매 세션 시작 시 참조하는 프로젝트 컨텍스트 파일.
> **버전**: v0.2 (2026-04-18, Gemini Pro 리뷰 반영)

---

## 1. 프로젝트 개요

**이름**: CAD_Optimizer (내부명: GMTCK CAD Optimizer)
**저장소**: `C:\Git\MeshOptimization\Plugins\CAD_Optimizer`
**목적**: GM 차량 CAD 데이터를 PCVR용으로 최적화하는 draw call 감소 도구
**사용자**: GMTCK PQDQ 팀 + 다른 부서
**배포**: 사내 git 서버, plugin 형태로 UE 프로젝트에 drop-in

## 2. 사람 소개

**담당자**: 최필립 (GMTCK PQDQ, Unreal Engine 개발자)
**배경**: Python 자동화·.exe 패키징 경험 있음. UE VR 개발 중. CAD 도메인 학습 중.
**협업 원칙**: "필립이 70% 일하고 Claude가 30% 가속". 학습 목표 병행.

## 3. 기술 스택

- **엔진**: Unreal Engine 5.5 (고정)
- **언어**: Python (UE 내장 3.11.x)
- **UI**: Editor Utility Widget (UMG)
- **C++**: 사용 안 함
- **외부 라이브러리**: Phase 1엔 없음. Phase 2+ 시 MIT 라이선스만 검토 (Open3D, trimesh, meshoptimizer 등)
- **버전 관리**: 사내 git 서버
- **타겟 하드웨어**: RTX 5000 Ada 노트북 + Meta Quest 3 (via PCVR Link)
- **렌더링**: Deferred + Nanite + DLAA
- **Long-running task**: `unreal.ScopedSlowTask` + batch processing (F0)

## 4. 핵심 결정사항

- **Nanite 켜고 간다**: Decimation 대신 Nanite 활용. Draw call/instance 정리가 핵심
- **Forward rendering 포기, Deferred 선택**: Nanite, DLSS/DLAA 사용 위해
- **PiXYZ 대체 자체 구축**: 라이선스 리스크 회피
- **Phase별 접근**: Phase 1 (core recipes + infra) → Phase 2 (UI + actor merging) → Phase 3 (visibility culling)
- **F0 infrastructure 우선**: 30,000 mesh 처리 freeze 방지 (Week 1 최우선)
- **F8 metadata tagging**: Phase 3 대비 Phase 1에서 미리 태깅

## 5. 절대 하지 말 것 (Lessons Learned)

상세는 `docs/lessons_learned/` 참조.

- ❌ **전체 차량 한꺼번에 decimation** — mesh 깨짐. Part별 개별 처리
- ❌ **Nanite 끄고 decimation** — self-sabotage
- ❌ **GPL/non-commercial 라이선스 라이브러리** (MeshLib 등) — 상용 리스크
- ❌ **glTF 경유 파이프라인** — Datasmith 네이티브 우회 시 정보 손실
- ❌ **UE Mesh Editor Simplify를 CAD mesh에 사용** — CAD 특성 대응 X
- ❌ **Progress/cancel 없이 대량 처리** — 에디터 freeze (F0이 해결)
- ❌ **Deprecated API 사용** (예: `EditorLevelLibrary` — UE 5.1에서 deprecated, `EditorActorSubsystem` 사용)

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

**현재**: Phase 1 시작 전 (환경 세팅 마무리 중)

**Phase 1 기능 (Week별)**:
- Week 1: **F0 (infrastructure)** + F1 (plugin 골격)
- Week 2: F2 (mesh 통계)
- Week 3: F3 (instance detection) ★
- Week 4: F4 (small part culling) + F5 (naming filter)
- Week 5: F6 (material consolidation) + F7 (리포트) + **F8 (metadata tagging)**

**Out of scope (Phase 1)**:
- Mesh decimation
- Static mesh actor merging (Phase 2)
- Texture atlas baking
- Visibility culling (Phase 3)
- Polished GUI
- C++ 코드
- 외부 라이브러리

## 8. 파일 위치 참조

| 무엇 | 어디 |
|------|------|
| 전체 계획 | `docs/Phase1_Kickoff.md` |
| 주차별 로그 | `docs/weekly_log/weekNN.md` |
| 의사결정 기록 | `docs/decisions/ADR_*.md` |
| 실패/함정 | `docs/lessons_learned/*.md` |
| 학습 노트 (필립 작성) | `docs/concepts/*.md` |
| Plugin 소스 | `Content/Python/cad_optimizer/` + `Content/EditorWidgets/` |

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

---

*마지막 업데이트: 2026-04-18*
