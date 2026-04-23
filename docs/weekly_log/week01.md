# Week 1 — Plugin 골격 + F0 Infrastructure

> **기간**: 2026-04-18 ~ 2026-04-23
> **Phase**: 1 / Week 1 of 5
> **상태**: ✅ 완료

---

## 완료 Task

| # | Task | 핵심 산출물 | Commit |
|---|------|-----------|--------|
| 1 | Plugin 골격 | `CAD_Optimizer.uplugin`, `Content/Python/init_unreal.py`, 문서 재배치 | `38ab313`, `286b817` |
| 2 | Tools 메뉴 등록 | `ToolMenuEntry` + `set_string_command` 방식 | `4fb2600` |
| 3 | 빈 EUW | `Content/EditorWidgets/EUW_MainPanel.uasset` | `3538618` |
| 4 | F0 `SlowIter` | ScopedSlowTask RAII wrapper, 매 item cancel | `a0227ea` |
| 5 | F0 `BatchIter` | 고정 크기 chunking, batch 경계 cancel (transaction-safe) | `2d540df` |
| 6 | 메뉴 → EUW 연결 refactor | PythonCommand → `ToolMenuEntryScript` subclass, `ui/` 모듈 분리 | `33efaf8` |

---

**Variation**: 이번 Week 1 생략.

---

## 학습한 핵심 개념 3개

### 1. UE ToolMenus Registry
- 메뉴는 **위치가 아니라 이름**(`"LevelEditor.MainMenu.Tools"`)으로 식별.
- `ToolMenus.get().extend_menu(...)` → 해당 경로에 **대해 확장 의도 등록**. 실제 UI 갱신은 `refresh_all_widgets` 또는 다음 메뉴 오픈 시.
- Section 개념: 같은 메뉴 안 논리적 그룹 (현재 `"CADOptimizer"` 섹션 하나).

### 2. RAII (ScopedSlowTask)
- Python `with` 블록 = C++ RAII 생성자/소멸자 흉내. 진입 시 progress dialog 구성, 예외/리턴 시 자동 정리.
- UE에서 "짝 맞춰 시작/끝내야 하는 자원"은 거의 모두 RAII: `ScopedSlowTask`, `ScopedEditorTransaction`, `ScopedSlowTaskGroup` 등 → F3+에서 transaction 쓸 때 동일 패턴.
- 관련 문서: `docs/concepts/batch_iter.md`.

### 3. UClass 패턴 (`@unreal.uclass` / `@unreal.ufunction(override=True)`)
- `@unreal.uclass()`: Python class를 UE reflection에 등록 → C++이 이 타입을 **볼 수 있게 됨**. 없으면 no-op 객체.
- `@unreal.ufunction(override=True)`: base virtual UFunction을 Python에서 override. `override=True` 빠지면 별개 slot에 등록돼서 dispatch가 base 구현으로 감.
- **GC 함정**: UClass 인스턴스는 Python GC로 수거됨. 모듈 전역 list에 append해서 강한 레퍼런스 유지 필수 (`ui/menu.py`의 `_MENU_SCRIPTS`). 증상: 메뉴 클릭 시 dangling / cryptic 에러.

---

## 막혔던 점 + 해결

| 문제 | 증상 | 해결 |
|------|------|------|
| `__pycache__/*.pyc` 커밋 혼입 (Task 4) | Commit에 3개 .pyc 포함됨 | `.gitignore`에 `__pycache__/`, `*.pyc` 추가 + commit amend |
| 커밋 메시지 리터럴 escape (초반) | `\"...\"` 문자 그대로 박힘 | Amend로 clean한 `"..."` 로 교체 |
| Plugin content path 불명확 (Task 6 설계) | EUW asset 로드 경로 규칙 | `/<PluginName>/<Content 아래>/<파일명 ext 제외>` = `/CAD_Optimizer/EditorWidgets/EUW_MainPanel` |

---

## Week 2 진입 시 주의

1. **Python 모듈 reload 트랩**: `cad_optimizer/` 내부 수정 시 UE 에디터 **완전 재기동** 필수. `import` 캐시 무효화 안 되면 옛 코드가 계속 실행됨.
2. **F2는 읽기 작업** → `SlowIter` 사용. `BatchIter`는 transaction 필요한 쓰기 단계에서 등장 (F3+).
3. **메뉴 entry 추가 시 이미 정한 패턴 재사용**: `ui/menu.py`의 `ToolMenuEntryScript` subclass를 복사 + `execute` 본문만 변경. 각 subclass는 반드시 `_MENU_SCRIPTS`에 append.
4. **진행 속도 유지**: variation/concept 노트는 phase 말 몰아서. 단, 또 다른 "반드시 남길 함정" 만나면 `docs/lessons_learned/`에 짧게 기록.

---

## 다음 세션 시작 시 (CLAUDE.md §9)

- 이 문서 링크 첨부
- 현재: Phase 1 Week 2 진입 직전
- 목표: F2 mesh 통계 (StaticMeshActor 순회, polygon/material/draw call 집계 → widget 표시)
- 예상 첫 task: "StaticMeshActor 순회 + 집계 구조 설계"
