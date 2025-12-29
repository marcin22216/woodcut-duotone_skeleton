"""Pipeline and step abstractions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import numpy as np


class Step(ABC):
    def __init__(self, name: str, enabled: bool = True) -> None:
        self.name = name
        self.enabled = enabled

    @abstractmethod
    def apply(self, image: Any, params: dict) -> Any:
        return image


class Pipeline:
    def __init__(self, steps: list[Step]) -> None:
        self._steps = list(steps)

    def run(self, image: Any) -> Any:
        source_luma = _extract_source_luma(image)
        for step in self._steps:
            if not step.enabled:
                continue
            params = dict(getattr(step, "params", {}))
            if source_luma is not None and getattr(step, "name", "") == "Edges":
                params["source_luma"] = source_luma
            image = step.apply(image, params)
        return image

    def get_steps(self) -> list[Step]:
        return list(self._steps)


def _extract_source_luma(image: Any) -> np.ndarray | None:
    if not isinstance(image, np.ndarray):
        return None
    if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
        return None
    image_float = image.astype(np.float32)
    gray = (
        image_float[..., 0] * 0.299
        + image_float[..., 1] * 0.587
        + image_float[..., 2] * 0.114
    )
    return np.rint(gray).clip(0, 255).astype(np.uint8)
