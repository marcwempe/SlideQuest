from __future__ import annotations

from slidequest.views.master.explorer_controller import ExplorerController


class _DummyVM:
    def __init__(self) -> None:
        self.created: list[tuple[str, str]] = []
        self.deleted: list[int] = []
        self.updated: list[tuple[str, str, str]] = []
        self.reordered: list[list[int]] = []
        self.selected: list[int] = []
        self._slide = object()

    @property
    def current_slide(self):
        return self._slide

    def create_slide(self, layout_id: str, *, group: str):
        self.created.append((layout_id, group))
        return self._slide

    def delete_slide(self, index: int):
        self.deleted.append(index)
        return self._slide

    def update_metadata(self, title: str, subtitle: str, group: str) -> None:
        self.updated.append((title, subtitle, group))

    def reorder_slides(self, order: list[int]) -> None:
        self.reordered.append(order)

    def select_slide(self, index: int) -> None:
        self.selected.append(index)


def test_explorer_controller_delegates_to_viewmodel() -> None:
    vm = _DummyVM()
    controller = ExplorerController(vm)

    slide = controller.create_slide("layout", "A")
    assert slide is vm.current_slide
    assert vm.created == [("layout", "A")]

    controller.delete_slide(2)
    assert vm.deleted == [2]

    controller.update_metadata("a", "b", "c")
    assert vm.updated == [("a", "b", "c")]

    controller.reorder([1, 0])
    assert vm.reordered == [[1, 0]]

    selected = controller.select(1)
    assert selected is vm.current_slide
    assert vm.selected == [1]
