from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class LayoutItem:
    title: str
    subtitle: str
    layout: str
    group: str
    preview: Path | None = None
    images: dict[int, str] = None

    def __post_init__(self) -> None:
        if self.images is None:
            self.images = {}


LAYOUT_ITEMS: tuple[LayoutItem, ...] = (
    LayoutItem("Einspaltig", "Vollflächige Anzeige", "1S|100/1R|100", "Standard"),
    LayoutItem("Zweispaltig", "Balance 60/40", "2S|60:40/1R:100/1R:100", "Standard"),
    LayoutItem("Dreispaltig", "Seitenleisten links/rechts", "3S|20:60:20/1R:100/1R:100/1R:100", "Standard"),
    LayoutItem("Moderator Panel", "Breite Bühne mit vier Slots", "2S|75:25/1R|100/4R|25:25:25:25", "Show"),
    LayoutItem("Fokus 3-1-3", "Zentrale Bühne mit Sidebars", "3S|20:60:20/2R|50:50/1R|100/2R|50:50", "Show"),
    LayoutItem("Matrix 3-1-3", "Drei Spalten mit 3/1/3 Reihen", "3S|12.5:75:12.5/3R|34:33:33/1R|100/3R|34:33:33", "Show"),
)


@dataclass
class LayoutCell:
    x: float
    y: float
    width: float
    height: float
    area_id: int = 0


@dataclass
class RatioSpec:
    ratio: float = 0.0
    area_id: int = 0
    has_explicit_id: bool = False


def _parse_ratios(segment: str) -> list[float]:
    parts = [part.strip() for part in segment.split(":") if part.strip()]
    if not parts:
        return []
    ratios: list[float] = []
    wildcard_indices: list[int] = []
    remaining = 1.0
    for index, component in enumerate(parts):
        if component == "*":
            ratios.append(0.0)
            wildcard_indices.append(index)
            continue
        try:
            value = float(component)
        except ValueError:
            return []
        value /= 100.0
        ratios.append(value)
        remaining -= value
    if remaining < 0:
        remaining = 0.0
    if wildcard_indices:
        per = remaining / len(wildcard_indices) if wildcard_indices else 0.0
        for idx in wildcard_indices:
            ratios[idx] = per
    total = sum(ratios)
    if total <= 0:
        return []
    return [value / total for value in ratios]


def _parse_ratio_specs(segment: str) -> list[RatioSpec]:
    parts = [part.strip() for part in segment.split(":") if part.strip()]
    if not parts:
        return []
    specs: list[RatioSpec] = []
    wildcard_indices: list[int] = []
    remaining = 1.0
    for index, component in enumerate(parts):
        spec = RatioSpec()
        if "#" in component:
            before, _, after = component.partition("#")
            after = after.strip()
            try:
                spec.area_id = int(after)
            except ValueError:
                return []
            spec.has_explicit_id = True
            component = before.strip()
        if component == "*":
            if spec.has_explicit_id:
                return []
            specs.append(spec)
            wildcard_indices.append(index)
            continue
        try:
            value = float(component)
        except ValueError:
            return []
        spec.ratio = value / 100.0
        remaining -= spec.ratio
        specs.append(spec)
    if remaining < 0:
        remaining = 0.0
    if wildcard_indices:
        per = remaining / len(wildcard_indices) if wildcard_indices else 0.0
        for idx in wildcard_indices:
            specs[idx].ratio = per
    total = sum(spec.ratio for spec in specs)
    if total <= 0:
        return []
    for spec in specs:
        spec.ratio /= total
    return specs


def parse_layout_description(layout_description: str) -> list[LayoutCell]:
    layout_description = layout_description.strip()
    if not layout_description:
        return [LayoutCell(0.0, 0.0, 1.0, 1.0, 1)]

    segments = [segment.strip() for segment in layout_description.split("/") if segment.strip()]
    if not segments:
        return []

    header_parts = [part.strip() for part in segments[0].split("|")]
    if len(header_parts) < 2:
        return []

    columns_token = header_parts[0]
    if not columns_token.endswith("S"):
        return []
    try:
        column_count = int(columns_token[:-1])
    except ValueError:
        return []
    if column_count <= 0:
        return []

    column_ratios = _parse_ratios(header_parts[1])
    if len(column_ratios) != column_count:
        return []

    columns: list[dict[str, list]] = [
        {"ratios": [], "specs": []} for _ in range(column_count)
    ]

    column_index = 0
    for segment in segments[1:]:
        if column_index >= column_count:
            break
        parts = [part.strip() for part in segment.split("|")]
        if len(parts) == 2:
            rows_token, ratios_token = parts
        else:
            sep_index = segment.find(":")
            if sep_index <= 0:
                return []
            rows_token = segment[:sep_index].strip()
            ratios_token = segment[sep_index + 1 :].strip()
        if not rows_token.endswith("R"):
            return []
        try:
            row_count = int(rows_token[:-1])
        except ValueError:
            return []
        if row_count <= 0:
            return []
        row_specs = _parse_ratio_specs(ratios_token)
        if len(row_specs) != row_count:
            return []
        columns[column_index]["ratios"] = [spec.ratio for spec in row_specs]
        columns[column_index]["specs"] = row_specs
        column_index += 1

    cells: list[LayoutCell] = []
    x = 0.0
    for col in range(column_count):
        column_width = column_ratios[col]
        if column_width <= 0:
            continue
        row_ratios: list[float] = columns[col]["ratios"] or [1.0]
        row_specs: list[RatioSpec] = columns[col]["specs"] or [RatioSpec(ratio=ratio) for ratio in row_ratios]
        y = 0.0
        for row, ratio in enumerate(row_ratios):
            if ratio <= 0:
                continue
            area_id = row_specs[row].area_id if row < len(row_specs) and row_specs[row].has_explicit_id else 0
            cells.append(LayoutCell(x, y, column_width, ratio, area_id))
            y += ratio
        x += column_width

    if not cells:
        return [LayoutCell(0.0, 0.0, 1.0, 1.0, 1)]

    used_ids = {cell.area_id for cell in cells if cell.area_id > 0}
    auto_indices = [index for index, cell in enumerate(cells) if cell.area_id <= 0]
    auto_indices.sort(key=lambda idx: cells[idx].width * cells[idx].height, reverse=True)
    candidate = 1
    for idx in auto_indices:
        while candidate in used_ids:
            candidate += 1
        cells[idx].area_id = candidate
        used_ids.add(candidate)
        candidate += 1
    return cells
