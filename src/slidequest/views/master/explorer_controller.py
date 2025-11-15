from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from slidequest.models.slide import SlideData


class ExplorerViewModel(Protocol):
    def create_slide(self, layout_id: str, *, group: str) -> SlideData: ...

    def delete_slide(self, index: int) -> SlideData | None: ...

    def update_metadata(self, title: str, subtitle: str, group: str) -> None: ...

    def reorder_slides(self, order: list[int]) -> None: ...

    def select_slide(self, index: int) -> None: ...

    @property
    def current_slide(self) -> SlideData | None: ...


@dataclass
class ExplorerController:
    viewmodel: ExplorerViewModel

    def create_slide(self, layout_id: str, group: str) -> SlideData:
        return self.viewmodel.create_slide(layout_id, group=group)

    def delete_slide(self, index: int) -> SlideData | None:
        return self.viewmodel.delete_slide(index)

    def update_metadata(self, title: str, subtitle: str, group: str) -> None:
        self.viewmodel.update_metadata(title, subtitle, group)

    def reorder(self, order: list[int]) -> None:
        self.viewmodel.reorder_slides(order)

    def select(self, index: int) -> SlideData | None:
        self.viewmodel.select_slide(index)
        return self.viewmodel.current_slide
