# Week 2 — F2 Mesh Statistics

> **기간**: 2026-04-24 ~ 2026-04-30 (진행 중)
> **Phase**: 1 / Week 2 of 5
> **상태**: 🟡 PR 진행 중 (`feature/f2-mesh-stats`)

---

## 완료 Task

| # | Task | 핵심 산출물 |
|---|------|-----------|
| 1 | F2 stats module (pure) | `cad_optimizer/stats.py` — `MeshStatsReport`, `collect_mesh_stats` |
| 2 | EUW panel glue + ScopedSlowTask wiring | `cad_optimizer/ui/panel.py` — `run_scan_level(widget, skip_hidden)` |
| 3 | Tools 메뉴에 "Scan Level" 엔트리 추가 | `cad_optimizer/ui/menu.py` — 2nd ToolMenuEntryScript subclass |

---

**Variation**: PR 본문에 1개 제안 (생략 여부는 병합 시점에 결정).

---

## 학습한 핵심 개념 2개

### 1. Callback injection — 코어 모듈을 UI 프레임워크와 분리
- `stats.collect_mesh_stats`는 `should_cancel`/`on_progress` 콜백만 받음. `SlowIter`/`ScopedSlowTask`/EUW 전부 모름.
- 이점:
  - **테스트 용이**: UE runtime 없이도 람다 2개 넘겨서 단위 테스트 가능 (Phase 2+ 고려).
  - **재사용**: F7 리포트 생성이 stats 재실행 필요할 때 UI 없이 호출 가능.
  - **F0 pattern 유지**: panel.py가 `ScopedSlowTask`를 직접 쓰고 콜백으로 브리지.
- 비용: 호출 쪽이 두 줄 짜리 closure 작성. 허용 범위.

### 2. UE API isolation layer — deprecation 내성 확보
- `stats.py`의 모든 `unreal.*` 호출은 파일 상단 `_get_*`/`_is_*` helper에 격리.
  예: `_get_triangles(sm, lod=0)` → `sm.get_num_triangles(lod)` 한 줄.
- UE 5.6+에서 API가 renamed/deprecated 되면 **이 블록 하나만** 수정하면 됨. `collect_mesh_stats` 본문은 변경 X.
- CLAUDE.md §5 "deprecated API 사용 금지"를 구조적으로 강제하는 방법.

---

## 막혔던 점 + 해결

| 문제 | 해결 |
|------|------|
| `.uasset` (EUW_MainPanel)은 Python 스크립트로 편집 불가 — Blueprint 편집기 수동 조작 필수 | PR 본문에 단계별 Blueprint 편집 가이드 포함. 병합 전 수동 체크리스트 통과 필요. |
| Acceptance criteria 9개 중 실행 검증은 에디터 내부에서만 가능 (Claude Code는 에디터 구동 X) | PR 본문에 verification procedure 명시. Philip이 테스트 후 본문 체크. |
| `stats.py`에서 `SlowIter` 직접 쓰면 "순수 모듈" 제약 위배. SlowIter는 iterable이라 should_cancel/advance 분리 노출 안 됨 | panel.py에서 `ScopedSlowTask` 직접 사용 + lambda 2개로 stats에 주입. SlowIter는 refactor 없이 유지. |

---

## Week 3 진입 시 주의

1. **F3는 쓰기 작업** → `BatchIter` 사용 + 각 batch를 `unreal.ScopedEditorTransaction`으로 감싸기.
2. **Instance detection hash 함수**는 geometry 기반 (vertex/triangle) — stats.py 재활용 어려움. 별도 `utils/mesh_hashing.py` 필요.
3. **ISM/HISM 변환**은 undo-able 해야 함 → transaction 경계 = batch 경계 (F0 BatchIter 설계 원칙 유효).
4. **Dry-run 모드**: F3부터 적용 (실제 변환 안 하고 "몇 개 그룹, 몇 개 감소 예상"만 리포트).

---

## 다음 세션 시작 시 (CLAUDE.md §9)

- 이 문서 + CLAUDE.md 첨부
- 현재: Week 2 PR 리뷰/병합 단계 또는 Week 3 시작
- Week 3 목표: F3 instance detection (mesh hashing → ISM/HISM 변환, dry-run)
