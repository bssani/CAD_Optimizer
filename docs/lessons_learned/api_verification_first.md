# Lesson Learned — API Verification First

> **생성일**: 2026-04-24 (Week 2 / F2 설계 단계)
> **원칙**: AI (Claude / Gemini)가 제안하는 UE API는 **실행 전에 반드시 검증**.
>          추정으로 답하는 비율이 체감상 50%를 넘는다.

---

## 원칙

1. 새 API 첫 사용 전 Python console에서 `dir(obj)` 또는 `help(cls)`로 존재 확인.
2. Subsystem은 `unreal.get_editor_subsystem(SubsystemClass)`만 사용 (5.2+ 직접 생성 deprecated).
3. Struct 속성은 직접 `.` 접근 안 되는 경우가 많음 → `get_editor_property('name')` 후보.
4. 메서드 시그니처 추정 금지: 파라미터 타입이 의외인 경우 많음 (예: `to_world`).
5. 반복문/대량 호출 전에 **한 줄 실험** 필수.

---

## 사례 1 (2026-04-24): F2 API 4라운드 검증 중 3/4 오답

F2 설계 초안에서 Claude/Gemini가 제안한 UE 5.5 API를 Python console에서 검증. 4개 중 **3개가 틀림**.

### 1-1. `EditorActorSubsystem` 직접 생성 — deprecated

제안:
```python
eas = unreal.EditorActorSubsystem()  # ❌
```

실행 시:
```
DeprecationWarning: Creating an instance of an Editor subsystem has been
deprecated since UE 5.2. Use unreal.get_editor_subsystem() instead.
```

교정:
```python
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)  # ✅
```

교훈: Subsystem은 **반드시** `get_editor_subsystem` 팩토리 경유. 직접 생성자는 5.2에서 deprecated, 5.6+에서 제거 가능성 높음.

### 1-2. `StaticMeshEditorSubsystem.get_num_triangles` — 존재 안 함

제안:
```python
smes = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
tris = smes.get_num_triangles(sm, 0)  # ❌ AttributeError
```

`dir(smes)` 로 확인 → `get_num_triangles` 없음. 대신 `get_number_verts`, `get_number_materials` 만 존재.

교정 (instance method):
```python
tris = sm.get_num_triangles(0)     # ✅ StaticMesh 본체
secs = sm.get_num_sections(0)      # ✅
```

교훈: "비슷한 이름의 서브시스템 메서드가 있을 것" 이란 추정 금지. `dir()` 출력에 실제 있는 이름만 쓴다. LOD 인자 유무도 메서드별로 다름 (`get_number_verts`는 LOD 인자 O, `get_number_materials`는 X).

### 1-3. `StaticMesh.nanite_settings` — 속성 직접 접근 불가

제안:
```python
if sm.nanite_settings.enabled:  # ❌ AttributeError
    ...
```

`dir(sm)` 확인 → `nanite_settings` 속성 노출 안 됨. UE reflection이 이 struct를 Python property로 자동 노출하지 않음.

교정:
```python
if sm.get_editor_property('nanite_settings').enabled:  # ✅
    ...
```

교훈: UStruct/FStruct 멤버는 Python에서 직접 접근 안 되는 경우가 일반적. `get_editor_property('snake_case_name')` 로 우회. 반환된 struct의 하위 필드는 그대로 `.` 접근 가능.

### 정답이었던 1개

- `actor.is_hidden_ed()` — bool 반환. 이건 맞았음.

### 정리

4라운드 검증 후 확정한 7개 API가 F2 `stats.py` 의 `_get_*` / `_is_*` helper 블록에 그대로 반영됨. "검증 완료" 라벨 붙이고 이후 구현 단계에선 이 리스트 벗어난 API 금지.

---

## 사례 2 (2026-04-24): `duplicate_actor` 파라미터 추정 실패

Claude가 AC3 검증용 10,000 actor 복제 스크립트 제안:

```python
eas.duplicate_actor(sm_actor, unreal.Vector(...))  # ❌
```

실행 시 에러:

```
TypeError: EditorActorSubsystem: Failed to convert parameter 'to_world'
Cannot nativize 'Vector' as 'ToWorld' (allowed Class type: 'World')
```

**원인**: `duplicate_actor`의 두 번째 인자는 `World` 타입, `Vector`가 아님. Claude가 직관적으로 "좌표 = Vector" 추정.

**해결**: `spawn_actor_from_object(sm, loc)` 사용.

```python
for i in range(10000):
    loc = unreal.Vector((i % 100) * 100, (i // 100) * 100, 0)
    eas.spawn_actor_from_object(sm, loc)  # ✅
```

**재확인된 원칙**: 검증 없이 제안된 API는 실행 전 `dir()` 또는 공식 문서로 확인.
새 API 첫 호출은 한 줄 실험 후 반복문에 투입.
