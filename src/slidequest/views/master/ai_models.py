from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(slots=True)
class SeedreamRequestMeta:
    prompt: str = "Seedream"
    style_prompt: str = ""
    aspect_ratio: str = "match_input_image"
    size: str = "2K"
    width: int = 2048
    height: int = 2048
    enhance_prompt: bool = True
    max_images: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt": self.prompt,
            "style_prompt": self.style_prompt,
            "aspect_ratio": self.aspect_ratio,
            "size": self.size,
            "width": self.width,
            "height": self.height,
            "enhance_prompt": self.enhance_prompt,
            "max_images": self.max_images,
        }

    def to_generation_kwargs(self, *, image_inputs: list[str]) -> dict[str, Any]:
        return {
            "prompt": self.prompt,
            "aspect_ratio": self.aspect_ratio,
            "size": self.size,
            "width": self.width,
            "height": self.height,
            "enhance_prompt": self.enhance_prompt,
            "max_images": self.max_images,
            "image_inputs": image_inputs,
        }


class ProjectServiceProtocol(Protocol):
    def import_file(self, bucket: str, file_path: str) -> str: ...

    def resolve_asset_path(self, asset_id: str) -> Any: ...
