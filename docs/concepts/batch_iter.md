# BatchIter — 학습 포인트

> F0 infrastructure, Week 1 Task 5. `cad_optimizer/infrastructure/batch.py`.

---

## 1. Ceil division idiom: `(a + b - 1) // b`

Python에서 a를 b로 나눈 결과를 **올림**하고 싶을 때 쓰는 정수 연산 관용구.

```python
batch_count = (total + self._size - 1) // self._size
```

2150 items / size=100 → `(2150 + 99) // 100` = `2249 // 100` = **22**.

### 왜 `math.ceil(a / b)` 대신?

| 방법 | 비교 |
|------|------|
| `math.ceil(a / b)` | `import math` 필요, float 연산 (부동소수점 오차 리스크) |
| `(a + b - 1) // b` | import 불필요, 순수 integer 연산, 더 빠름 |

대규모 수에선 float 변환에서 정밀도 손실이 생길 수 있음. `(30_000 + 99) // 100` 같이 모두 정수로 끝나면 항상 정확.

### 대체 표현 (Python 3.8+)

```python
-(-total // self._size)  # double negation idiom
```

가독성은 `(a + b - 1) // b`가 낫다. 현재 코드는 의도 드러내는 쪽 선택.

---

## 2. Cancel 시점 설계 결정: batch 사이에서만

### 의도

BatchIter는 **쓰기 작업 (actor 삭제, 속성 변경, ISM 변환 등)**에 쓰이는 도구. 쓰기는 보통 `unreal.ScopedEditorTransaction`으로 감싸서 undo 가능한 단위로 묶는다. Transaction 중간에 cancel되면 절반만 적용된 상태로 남을 수 있어 위험.

그래서 BatchIter의 cancel 체크는 **`yield` 직전 batch 경계**에서만 일어남:

```python
for start in range(0, total, self._size):
    if self._can_cancel and task.should_cancel():   # ← 여기만
        self.was_cancelled = True
        return
    task.enter_progress_frame(1)
    yield self._items[start : start + self._size]   # caller가 이 batch를 transaction으로 감쌈
```

Caller 쪽 패턴:

```python
for batch in BatchIter(actors, 100, "Remove small parts"):
    with unreal.ScopedEditorTransaction("Remove small parts"):
        for actor in batch:
            ...  # 이 안에서 cancel 안 됨 → transaction 안전
```

### SlowIter vs BatchIter 차이

| | SlowIter | BatchIter |
|---|---|---|
| 용도 | 읽기 작업 (mesh 메타데이터 조회 등) | 쓰기 작업 (actor 수정/삭제) |
| Cancel 체크 주기 | 매 item | 매 batch |
| Transaction 안전성 | 필요 없음 (읽기만) | 보장됨 (batch 단위 원자성) |
| Progress step 수 | item 수 | batch 수 |

### Trade-off

**비용**: 사용자가 Cancel 버튼을 눌러도 최대 1 batch 처리 시간만큼 응답이 지연됨.
- size=100, batch당 0.5초 걸리면 → 최악 0.5초 지연
- size=1000, batch당 5초 걸리면 → 최악 5초 지연

이 비용이 수용 가능한 이유: batch size를 caller가 정하므로, "응답성이 중요하면 size를 줄여라"로 tuning 가능. 현재 권장값(100~500)은 대부분의 UE editor 작업에서 cancel 지연이 체감되지 않는 범위.

### Phase 2 재검토 여지

Phase 2에서 UX 개선할 때 다음 옵션 검토 가능:
- Batch 내부에서도 cancel flag만 set하고 transaction 끝난 후 break
- 큰 transaction을 자동으로 더 작은 sub-transaction으로 쪼개기

현재는 단순함 우선.

---

## 참고

- 검증: 2150 items / size=100 → 22 batches. Cancel 시 processed가 항상 100의 배수로 나옴 확인 (800, 1000 등).
- 구현 파일: `Content/Python/cad_optimizer/infrastructure/batch.py`
