# Phase 1 Kickoff — GMTCK CAD Optimizer Plugin

> **프로젝트명**: CAD_Optimizer (내부명: GMTCK CAD Optimizer)
> **버전**: Phase 1 (v0.2)
> **타겟**: Unreal Engine 5.5
> **언어**: Python (UE Python API 기반)
> **형태**: UE Editor Plugin
> **작성일**: 2026-04-18
> **마지막 수정**: 2026-04-18 (Gemini Pro review 반영, F0/F8 추가)

---

## 1. 프로젝트 컨텍스트

GMTCK PQDQ 팀의 PCVR 평가 워크플로우에서 자동차 CAD 데이터 (4,000만 폴리곤, 30,000~40,000 mesh)를 그대로 Unreal Engine에 import하면 PCVR (Quest 3 + RTX 5000 Ada)에서 사용 가능한 frame rate가 나오지 않는다. PiXYZ 같은 상용 CAD 최적화 툴 라이선스 없이도 draw call을 줄이고 mesh 수를 정리하는 자동화 도구가 필요하다.

Datasmith가 import만 담당한다면, 우리 plugin은 **import 후의 정리/최적화**를 담당한다. PiXYZ의 80% 기능을 GM 환경에 특화된 형태로 구현한다.

---

## 2. Phase 1 목표

### 2.1 기능 목표

| # | 기능 | 설명 | Week |
|---|------|------|------|
| **F0** | **Infrastructure** | **ScopedSlowTask 기반 progress/cancel, batch processor, 공통 유틸** | **Week 1** |
| F1 | Plugin 골격 | UE 5.5에 enable하면 메뉴에 "CAD Optimizer" 등장 | Week 1 |
| F2 | Mesh 통계 리포트 | mesh/polygon/material count, draw call 추정 | Week 2 |
| F3 | Instance detection | Mesh hash 기반 동일 geometry 감지 → ISM/HISM 변환 | Week 3 |
| F4 | Small part culling | Bounding box threshold 기반 제거/분리 | Week 4 |
| F5 | Naming rule filter | GM NX naming convention 기반 분류 | Week 4 |
| F6 | Material consolidation | 속성 similarity 기반 material 통합 | Week 5 |
| F7 | Before/After 리포트 | 작업 전후 metric 비교 | Week 5 |
| **F8** | **Metadata tagging** | **각 actor에 bounding box, volume, category, nanite_compatible 등 tag 부여 (Phase 3 대비)** | **Week 5** |

### 2.2 비기능 목표

- 실제 GM 차량 CAD 데이터에서 **mesh count 50% 이상 감소**
- PQDQ 팀원이 **튜토리얼 없이 30분 내 사용법 익힘**
- 처리 결과 **재현 가능**
- **에디터 freeze 없이** progress 표시, cancel 가능 (F0)

### 2.3 학습 목표

- UE 5.5 Plugin 구조 (`.uplugin`, 폴더 구조)
- UE Python API 핵심 클래스 (`EditorActorSubsystem`, `StaticMesh`, `MaterialInterface`)
- `unreal.ScopedSlowTask`를 활용한 long-running 작업 처리
- Mesh data 접근 (vertex, triangle, transform, bounds)
- Editor Utility Widget 생성 및 Python 연결
- Mesh hashing (geometry signature)
- ISM/HISM 개념과 사용
- Actor tag 시스템

---

## 3. Out of Scope

- ❌ Visibility-based hidden geometry removal → **Phase 3**
- ❌ Mesh decimation → Datasmith 옵션 활용
- ❌ Static mesh actor merging (unique geometry 물리적 합치기) → **Phase 2**
- ❌ Texture atlas baking → **Phase 2 이후**
- ❌ Imposter generation → **Phase 3 이후**
- ❌ Polished GUI → **Phase 2**
- ❌ C++ 코드 → 필요 시 Phase 2 이후

---

## 4. 기술 스택

| 항목 | 결정 | 이유 |
|------|------|------|
| Plugin 언어 | Python only | 학습곡선 낮음, 필립 강점 |
| UI | Editor Utility Widget (UMG) | Python 연결 쉬움 |
| 버전 관리 | 사내 git 서버 | 사내 정책 |
| 의존성 | UE 5.5 내장 Python만 | 외부 pip 보류 |
| 테스트 데이터 | UE 기본 asset + 가짜 CAD 씬 | 실 차량 CAD 확보 전까지 |
| Long-running task | `unreal.ScopedSlowTask` + batch | 에디터 freeze 방지 (F0) |

---

## 5. Repository 구조

```
CAD_Optimizer/                              (git repo root)
├── CLAUDE.md
├── README.md
├── CAD_Optimizer.uplugin
├── Content/
│   ├── Python/                            ★ UE PythonScriptPlugin auto-discovery 경로
│   │   ├── init_unreal.py                 ← editor startup 시 자동 실행
│   │   └── cad_optimizer/                 ← namespace package (이름 충돌 방지)
│   │       ├── __init__.py
│   │       ├── infrastructure/            # F0
│   │       │   ├── __init__.py
│   │       │   ├── slow_task.py
│   │       │   ├── batch_processor.py
│   │       │   └── logger.py
│   │       ├── core/
│   │       │   ├── __init__.py
│   │       │   ├── mesh_stats.py          # F2
│   │       │   ├── instance_detector.py   # F3
│   │       │   ├── small_part_filter.py   # F4
│   │       │   ├── naming_filter.py       # F5
│   │       │   ├── material_consolidator.py  # F6
│   │       │   ├── reporter.py            # F7
│   │       │   └── metadata_tagger.py     # F8
│   │       ├── utils/
│   │       │   ├── __init__.py
│   │       │   ├── mesh_hashing.py
│   │       │   └── ue_helpers.py
│   │       └── ui/
│   │           ├── __init__.py
│   │           └── widget_handlers.py
│   ├── EditorWidgets/
│   │   └── EUW_MainPanel.uasset
│   └── Icons/
├── Resources/
│   └── Icon128.png
├── docs/
│   ├── Phase1_Kickoff.md
│   ├── concepts/                          # 학습 노트
│   ├── decisions/                         # ADR
│   ├── lessons_learned/                   # 실패/함정
│   └── weekly_log/                        # 주차별
└── tests/
    └── sample_scenes/
```

---

## 6. 주차별 계획 (5주, 주 10시간)

### Week 1 — Plugin 골격 + F0 Infrastructure
- [ ] 빈 plugin 만들고 UE 5.5 enable
- [ ] 메뉴에 "CAD Optimizer" 등장
- [ ] 빈 Editor Utility Widget 띄우기
- [ ] **F0**: ScopedSlowTask wrapper (progress + cancel)
- [ ] **F0**: Batch processor (N개씩 처리)
- [ ] Hello World Python → widget 버튼 연결
- 산출물: `docs/concepts/plugin_structure.md`, `scoped_slow_task.md`

### Week 2 — F2 Mesh 통계
- [ ] StaticMeshActor 순회 (F0 batch 사용)
- [ ] Mesh/polygon/material count 집계
- [ ] Draw call 추정
- [ ] Widget 표시
- 산출물: `docs/concepts/ue_static_mesh_api.md`

### Week 3 — F3 Instance Detection ★
- [ ] Mesh hashing 구현
- [ ] Hash 기반 그룹화
- [ ] ISM/HISM 변환 (F0 batch + progress)
- [ ] Dry-run 모드
- 산출물: `docs/concepts/mesh_hashing.md`, `ism_hism.md`

### Week 4 — F4, F5 Filtering
- [ ] Bounding box 계산 (F8에서 재사용)
- [ ] Threshold UI
- [ ] Naming pattern matching (regex)
- [ ] "제거" vs "분리" 옵션
- 산출물: `docs/concepts/ue_actor_manipulation.md`

### Week 5 — F6, F7, F8 + 마무리
- [ ] **F6**: Material similarity → 통합
- [ ] **F7**: Before/After 리포트 자동 생성
- [ ] **F8**: Metadata tagging
  - bounding_box_size, bounding_box_volume
  - world_position
  - nanite_compatible
  - material_count
  - category
- [ ] 통합 테스트
- [ ] **Phase 1 완료 보고서 작성**

---

## 7. Working Pattern

### 매 task 시작
1. 필립이 컨텍스트 짧게 공유
2. Claude가 **접근법 먼저** (코드 아님)
3. 필립 이해/동의
4. 코드 초안

### 코드 받은 후
- 줄 단위로 "왜?" 질문
- 일부 바꿔보고 동작 변화 관찰
- `docs/concepts/`에 자기 언어로 정리

### 막혔을 때
- "X일 거라고 예상했는데 Y가 나왔어" 형태로

### 매주 끝
- `weekly_log/weekNN.md` 작성

---

## 8. 성공 기준

1. ✅ Plugin이 UE 5.5에서 안정 로드, F0~F8 모두 동작
2. ✅ 실 CAD 데이터에서 mesh count 50% 이상 감소
3. ✅ 30,000+ mesh 처리 시 에디터 freeze 없음, cancel 가능
4. ✅ 필립이 plugin 코드 자기 말로 설명 가능
5. ✅ `Phase1_Completion_Report.md` 작성 완료

---

## 9. 위험 요소

| 위험 | 대응 |
|------|------|
| GM CAD naming convention 비일관 | Week 4 전 샘플 검토 |
| UE Python API 일부 제한 | Blueprint 노출 후 호출 우회 |
| **30,000 mesh 처리 시 freeze** | **F0: ScopedSlowTask + batch (Week 1 최우선)** |
| Phase 3 visibility culling 시 metadata 부족 | **F8: Phase 1에서 미리 태깅** |
| 일정 미끄러짐 | Scope 축소 OK, 일정 무리 X |
| 외부 pip 불가 가능성 | UE 내장 Python만 사용 |

---

## 10. Phase 2 미리보기

- F9: Polished GUI (drag&drop)
- F10: Recipe save/load (JSON)
- F11: Batch (여러 level/asset)
- F12: Static mesh actor merging
- F13: Texture atlas baking
- F14: 성능 개선 (필요 시 C++ 일부)

---

## 11. 변경 이력

- **2026-04-18 (v0.1)**: 초안
- **2026-04-18 (v0.2)**: Gemini Pro 외부 리뷰 반영
  - F0 추가 (Infrastructure — ScopedSlowTask, batch processor)
  - F8 추가 (Metadata tagging — Phase 3 대비)
  - Out of scope에 static mesh actor merging 명시 (Phase 2로)
