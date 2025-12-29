"""Base step with parameter storage."""

from __future__ import annotations

from typing import Any

from woodcut_duotone.core.pipeline import Step


class BaseStep(Step):
    def __init__(self, name: str, enabled: bool = True, params: dict | None = None) -> None:
        super().__init__(name=name, enabled=enabled)
        self.params: dict = params or {}

    def apply(self, image: Any, params: dict) -> Any:
        return image

    def set_param(self, name: str, value: Any) -> None:
        self.params[name] = value

    def get_param(self, name: str) -> Any:
        return self.params.get(name)
