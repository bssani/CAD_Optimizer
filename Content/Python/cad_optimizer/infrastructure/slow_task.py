from typing import Iterable, Iterator, TypeVar

import unreal

T = TypeVar("T")


class SlowIter(Iterable[T]):
    """Iterate with UE ScopedSlowTask progress dialog + cancel."""

    def __init__(
        self,
        items: Iterable[T],
        description: str,
        *,
        can_cancel: bool = True,
    ) -> None:
        self._items = list(items)
        self._description = description
        self._can_cancel = can_cancel
        self.was_cancelled: bool = False

    def __iter__(self) -> Iterator[T]:
        total = len(self._items)
        if total == 0:
            return

        with unreal.ScopedSlowTask(total, self._description) as task:
            task.make_dialog(self._can_cancel)
            for item in self._items:
                if self._can_cancel and task.should_cancel():
                    self.was_cancelled = True
                    return
                task.enter_progress_frame(1)
                yield item
