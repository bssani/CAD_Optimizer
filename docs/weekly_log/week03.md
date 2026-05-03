# Week 3 — F3 Instance Detection

> **기간**: 2026-04-24 ~ 2026-04-24 (1일 완료)
> **Phase**: 1 / Week 3 of 5
> **상태**: ✅ 완료

---

## 완료 Task

| # | Task | 핵심 산출물 | Commit |
|---|------|-----------|--------|
| 1 | F3 설계 결정 6개 | Scope (detection only) / grouping key `(mesh, materials, mobility)` / ISM 기본 권장 / threshold 기본 10 / CSV + Top 10 Log / `stats.py` 재사용 금지 (독립 모듈) | (설계 단계) |
| 2 | API 검증 4건 | `smc.get_material(i)` (override auto-fallback), `rc.mobility` + `ComponentMobility.STATIC`, `sm.get_num_sections(0)`, `unreal.Paths.project_saved_dir` 모두 직접 속성 또는 `get_editor_property` 패턴 확인 | (검증 단계) |
| 3 | Gemini Pro cross-check | 6개 피드백 → 4 전체 반영 / 2 부분 반영 / 2 거부 (premature optim + hierarchy scope creep) | (리뷰 단계) |
| 4 | `instance_detector.py` 구현 | Pure module, 249 lines. `InstanceGroupKey` / `InstanceGroup` / `InstanceDetectionReport` + `detect_instance_groups` callback-driven | `4ea0717` |
| 5 | `ui/panel.py` `run_detect_instances` 추가 | 2-phase ScopedSlowTask, CSV writer (UTF-8 BOM, Excel 한글 대비), top-10 Output Log | `4ea0717` |
| 6 | `ui/menu.py` "Detect Instances (F3)" 엔트리 | 세 번째 `ToolMenuEntryScript` subclass, F2 패턴 재사용 | `4ea0717` |
| 7 | Slot mismatch counter 수정 | 5회 cap 이후 check 자체 skip → silent failure. `mismatch_count` 필드 추가 + log cap과 분리 | `9b286fd` |
| 8 | 실 레벨 테스트 | CarConfigurator 샘플 10,107 actors, 21 unique groups, top 1 Plane 10,000× | (에디터 검증) |

### 테스트 결과 (CarConfigurator 10,107 actors)

```
Scanned: 10,107 actors (10,070 StaticMeshActor, 37 other)
Skipped: 0 no-mesh, 0 no-component, 6 non-static
Groups: 21 unique (threshold=10, 2 candidates)
Est. drawcall reduction: 10,015 (추정치)
Slot mismatches: 0
  #1  10,000x  /Engine/BasicShapes/Plane [STATIC]
  #2  17x      /Game/.../SM_BGMountain_3 [STATIC]
```

CSV: `{project_saved_dir}/CAD_Optimizer/instance_report_*.csv`

---

**Variation**: 이번 Week 3 생략 (실 CAD 레벨 재측정이 더 가치 있는 다음 스텝).

---

## 학습한 핵심 개념 3개

### 1. Detection-only 원칙 (dry-run)
- Phase 1은 **측정/리포트만**, 수정은 Phase 2. Scope creep 방지.
- F3는 레벨/actor를 전혀 수정 안 함. CSV 리포트만 생성.
- 이 경계를 명확히 하면 Phase 2에서 변환 로직만 **추가**하면 됨 (교체 아닌 확장).
- `instance_detector.py` 공개 API는 `detect_instance_groups` 하나뿐 — 이름에서부터 "detect"만 한다는 계약.

### 2. Pure function + Callback injection 패턴 재사용
- F2 `stats.py`에서 확립한 패턴이 F3 `instance_detector.py`에 그대로 적용됨.
- `detect_instance_groups(actors, threshold, should_cancel, on_progress)` — `unreal` 외 의존 0.
- 새 F 구현 시 Claude/Gemini에게 **"이 패턴 따르라"** 고 한 줄 지시로 일관성 확보.
- F4~F7에도 동일 템플릿 적용 예상. 반복 가능해진 시점에서 Phase 1의 코드 품질 기조가 안정됨.

### 3. Label 지연 취득 (lazy label resolution)
- `actor.get_actor_label()` 10,107회 호출은 수 초 단위 비용 (editor-side Python↔C++ round-trip).
- 그룹핑 중엔 actor 참조만 유지, report 단계에서 **top N + CSV 행**에 필요한 만큼만 호출.
- `InstanceGroup.get_labels(limit=3)` property 패턴 — O(N) cost가 `limit` 만큼으로 cap됨.
- Gemini 피드백 중 가장 실효적인 하나. 대규모 레벨 스캔의 체감 속도 차이가 큼.

---

## 막혔던 점 + 해결

| 문제 | 증상 | 해결 |
|------|------|------|
| Material slot mismatch cap이 silent failure 유발 | 5회 warning 후 check 자체 skip → 실제 mismatch 총수가 리포트 어디에도 안 찍힘 | Claude Code self-review로 감지. `material_slot_mismatch_count` 필드 추가 + log cap과 분리 (commit `9b286fd`) |
| `importlib.reload` Python Console 멀티라인 IndentationError | 콘솔에서 재로드 스크립트 붙여넣다 indent 깨짐 | 실제로는 plugin 자동 로드로 reload 불필요 — Editor 재기동만으로 충분 |
| Stacked PR 복잡도 | F2 merge 전엔 F3 단독 리뷰 어려움 (F2 코드도 diff에 섞임) | F2 merge → `git rebase main` → F3 clean diff 대기 중 |

---

## Week 4 진입 시 주의

1. **실 CAD 레벨에서 F3 재측정 필요** — 샘플 레벨(CarConfigurator)의 `10000×` / `17×` 극단 분포는 실제 차량 CAD와 다를 것. Threshold 10의 적정성은 실 CAD에서 확정.
2. **Material slot mismatch 0** — 샘플에선 발생 안 함. 실 CAD에서 다시 측정해야 의미 있는 숫자. CAD import에서 slot/section 불일치는 흔한 현상.
3. **F4 (small part culling) + F5 (naming filter) 킥오프 준비됨** — bbox 계산 + regex 기반 분류.
4. **Pure function + callback 패턴 유지** — F4 구현 시 동일 템플릿. 입력은 actor 리스트, 출력은 리포트 dataclass.
5. **Stacked PR 체인**: F2 merge → rebase → F3 clean diff → F4 branch 시작. 체인 2단 이상 쌓이기 전에 merge 치고 가는 쪽 추천.

---

## 다음 세션 시작 시 (CLAUDE.md §9)

- 이 문서 + CLAUDE.md + `docs/weekly_log/week02.md` 첨부
- 현재: Phase 1 Week 4 진입 직전, F2/F3 PR merge 대기
- 목표: F4 (small part culling — bbox threshold 기반 제거/분리) + F5 (naming filter — GM NX regex)
- 예상 첫 task: "bbox 계산 + threshold 결정 기준 설계 (volume? diagonal?)"
