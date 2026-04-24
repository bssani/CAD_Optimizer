# Week 2 — F2 Mesh 통계 리포트

> **기간**: 2026-04-24 ~ 2026-04-24 (1일 완료)
> **Phase**: 1 / Week 2 of 5
> **상태**: ✅ 완료

---

## 완료 Task

| # | Task | 핵심 산출물 | Commit |
|---|------|-----------|--------|
| 1 | API 검증 (4라운드) | 7개 UE 5.5 API 확정, `api_verification_first.md` lesson 생성 | (검증 단계, commit 없음) |
| 2 | CLAUDE.md v0.4 | §1 PCVR 타겟 명시, §5 deprecated subsystem 경고 | (산출물 2 PR) |
| 3 | `stats.py` 구현 | `MeshStatsReport` dataclass + `collect_mesh_stats` pure function | `1e8b12e` |
| 4 | `ui/panel.py` 구현 | `run_scan_level` + ScopedSlowTask + 콜백 주입 | `1e8b12e` |
| 5 | `ui/menu.py` 수정 | Tools 메뉴 "Scan Level (Mesh Stats)" 엔트리 | `1e8b12e` |
| 6 | EUW Blueprint 구성 | 버튼 + 체크박스 + 라벨 12개 + Branch wiring | (asset, commit 아님) |
| 7 | Acceptance Criteria 검증 | 8/9 통과 + 1 실질 통과 | PR body 참조 |

---

**Variation**: Top 5 heaviest actors 제안됨 (PR body 참조). 이번 Week 미포함.

---

## 학습한 핵심 개념 3개

### 1. API Verification First 원칙
- AI (Claude, Gemini) 둘 다 UE API를 **추정으로 답한다**는 사실 직접 체감.
- F2 설계 단계 API 검증 4라운드에서 **4개 중 3개가 틀림**:
  - `EditorActorSubsystem()` 직접 생성 → deprecated since 5.2
  - `smes.get_num_triangles` → 메서드 없음 (실제는 `sm.get_num_triangles(0)`)
  - `sm.nanite_settings.enabled` → 속성 없음 (실제는 `get_editor_property('nanite_settings').enabled`)
- 대응: `dir()`로 먼저 검증, `get_editor_subsystem()` 강제 사용, struct는 `get_editor_property` 후보.
- 문서화: `docs/lessons_learned/api_verification_first.md`

### 2. Pure Function + Callback Injection 패턴
- `stats.py`는 `unreal` 외 의존 금지 원칙.
- 기존 `SlowIter` 객체 주입 대신 `should_cancel: Callable[[], bool]`, `on_progress: Callable[[], None]` 콜백 2개로 분리.
- 효과:
  - 로직 단위 테스트 가능 (더미 `lambda: False`, `lambda: None` 주입)
  - 순수성 유지 (stats는 SlowIter/ScopedSlowTask 모름)
  - `ui/panel.py`가 ScopedSlowTask 직접 사용 + lambda 2개로 주입
- Gemini Pro 피드백 직접 반영 사례.

### 3. Blueprint → Python 값 전달 (Execute Python Command 한계)
- `Execute Python Command` 노드는 **문자열만 실행**. Blueprint 변수 자동 binding 없음.
- 해결: `Is Checked` (bool) → `Select` (True/False 문자열) → `Format Text` (스크립트 조립) → `Execute Python Command`.
- 핑크 Text→String 자동 변환 노드는 정상 (손대면 X).
- 대안 Branch 구조도 가능 (2개의 고정 문자열 Python Command).

---

## 막혔던 점 + 해결

| 문제 | 증상 | 해결 |
|------|------|------|
| Subsystem 직접 생성 deprecated 경고 | `DeprecationWarning: Creating an instance of an Editor subsystem has been deprecated since UE 5.2` | `unreal.get_editor_subsystem(unreal.XxxSubsystem)` 로 교체. CLAUDE.md §5 + lesson learned 추가 |
| `StaticMeshEditorSubsystem.get_num_triangles` 존재 X | `AttributeError` | `sm.get_num_triangles(0)` (instance method)로 이동 확인 via `dir()` |
| Nanite 속성 접근 경로 | `AttributeError: 'StaticMesh' has no attribute 'nanite_settings'` | `sm.get_editor_property('nanite_settings').enabled` 사용 |
| `EditorActorSubsystem.duplicate_actor` 파라미터 오류 | `Cannot nativize 'Vector' as 'ToWorld'` | `spawn_actor_from_object(sm, loc)` 사용으로 전환. 2차 lesson learned 추가 (아래) |
| Blueprint 체크박스 값 Python에 전달 안 됨 | EUW 버튼 사용 시 `skip_hidden` 값 무시됨 | Branch + Select + Format Text로 문자열 동적 조립 |

---

## Week 3 진입 시 주의

1. **F3 Instance Detection 킥오프 준비됨**: 10,070 / 21 unique meshes 데이터가 구체적 ROI 근거.
2. **`spawn_actor_from_object` 재검증 이미 완료**: 합성 대량 레벨 필요 시 그대로 사용 가능.
3. **CLAUDE.md §5 deprecated 경고 추가됨**: 새 API 사용 전 반드시 `dir()` 검증.
4. **Pure function + callback injection 패턴**: F3 구현 시에도 동일하게 유지. `collect_mesh_stats` 재사용 가능성 높음 (grouping by mesh path).

---

## 다음 세션 시작 시 (CLAUDE.md §9)

- 이 문서 + CLAUDE.md 첨부
- 현재: Phase 1 Week 3 진입
- 목표: F3 Instance Detection (중복 StaticMeshActor 찾기 → ISM 변환 제안)
- 예상 첫 task: "같은 StaticMesh를 참조하는 actor 그룹핑 로직 설계"
