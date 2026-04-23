from typing import Iterable, Iterator, List, TypeVar

import unreal

T = TypeVar("T")


class BatchIter(Iterable[List[T]]):
    """Chunk an iterable into fixed-size batches with progress + cancel.

    Each yielded value is a list of up to ``size`` items. Progress advances
    per batch, not per item — with ``size=100`` and 30,000 items the user
    sees 300 progress steps. Cancel is checked between batches, so a
    caller's ``unreal.ScopedEditorTransaction`` wrapping one batch is
    never interrupted mid-write.

    Write-path caller pattern (F3+)::

        for batch in BatchIter(actors, 100, "Removing small parts"):
            with unreal.ScopedEditorTransaction("Remove small parts"):
                for actor in batch:
                    ...  # delete / modify

    Recommended sizes:
        - Actor deletion / tagging: 100~500
        - ISM/HISM conversion: 50~200
        - Cheap per-item work that still needs cancel: 1000+
    """

    def __init__(
        self,
        items: Iterable[T],
        size: int,
        description: str,
        *,
        can_cancel: bool = True,
    ) -> None:
        if size <= 0:
            raise ValueError(f"size must be positive, got {size}")
        self._items = list(items)
        self._size = size
        self._description = description
        self._can_cancel = can_cancel
        self.was_cancelled: bool = False

    def __iter__(self) -> Iterator[List[T]]:
        total = len(self._items)
        if total == 0:
            return

        batch_count = (total + self._size - 1) // self._size

        with unreal.ScopedSlowTask(batch_count, self._description) as task:
            task.make_dialog(self._can_cancel)
            for start in range(0, total, self._size):
                if self._can_cancel and task.should_cancel():
                    self.was_cancelled = True
                    return
                task.enter_progress_frame(1)
                yield self._items[start : start + self._size]
