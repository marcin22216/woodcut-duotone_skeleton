"""Pipeline and step abstractions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


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
        for step in self._steps:
            if not step.enabled:
                continue
            params = getattr(step, "params", {})
            image = step.apply(image, params)
        return image

    def get_steps(self) -> list[Step]:
        return list(self._steps)
