"""Application state and undo/redo helpers."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import numpy as np


def _default_enabled() -> dict[str, bool]:
    return {
        "grayscale": True,
        "clahe": True,
        "blur": True,
        "threshold": True,
        "morphology": True,
        "edges": False,
    }


def _default_params() -> dict[str, dict[str, Any]]:
    return {
        "grayscale": {},
        "clahe": {"clip_limit": 2.0, "tile_grid_size": 8},
        "blur": {"strength": 1},
        "threshold": {
            "mode": "otsu",
            "invert": False,
            "bias": 0,
            "block_size": 31,
        },
        "morphology": {
            "operation": "close",
            "kernel_size": 3,
            "iterations": 1,
        },
        "edges": {
            "low": 60,
            "high": 140,
            "thickness": 1,
            "apply_on": "luma",
        },
    }


def _default_step_order() -> list[str]:
    return [
        "grayscale",
        "clahe",
        "blur",
        "threshold",
        "morphology",
        "edges",
    ]


class AppState:
    def __init__(self) -> None:
        self.original_image_rgb: np.ndarray | None = None
        self.preview_image_rgb: np.ndarray | None = None
        self.enabled = _default_enabled()
        self.params = _default_params()
        self.step_order = _default_step_order()
        self.undo_stack: list[dict[str, object]] = []
        self.redo_stack: list[dict[str, object]] = []
        self.render_revision = 0
        self.last_applied_revision = 0

    def snapshot(self) -> dict[str, object]:
        return {
            "enabled": deepcopy(self.enabled),
            "params": deepcopy(self.params),
            "step_order": list(self.step_order),
        }

    def restore(self, snapshot: dict[str, object]) -> None:
        self.enabled = deepcopy(snapshot["enabled"])
        self.params = deepcopy(snapshot["params"])
        self.step_order = list(snapshot["step_order"])

    def push_undo(self) -> None:
        self.undo_stack.append(self.snapshot())
        self.redo_stack.clear()

    def reset_defaults(self) -> None:
        self.enabled = _default_enabled()
        self.params = _default_params()
        self.step_order = _default_step_order()
        self.undo_stack.clear()
        self.redo_stack.clear()

    def next_render_revision(self) -> int:
        self.render_revision += 1
        return self.render_revision

    def move_step(self, step_name: str, new_index: int) -> None:
        if step_name not in self.step_order:
            raise ValueError(f"Unknown step: {step_name}")
        if not (0 <= new_index < len(self.step_order)):
            raise ValueError("new_index out of range")
        current_index = self.step_order.index(step_name)
        if current_index == new_index:
            return
        self.push_undo()
        self.step_order.pop(current_index)
        self.step_order.insert(new_index, step_name)

    @property
    def can_undo(self) -> bool:
        return bool(self.undo_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self.redo_stack)

    def undo(self) -> bool:
        if not self.undo_stack:
            return False
        self.redo_stack.append(self.snapshot())
        snapshot = self.undo_stack.pop()
        self.restore(snapshot)
        return True

    def redo(self) -> bool:
        if not self.redo_stack:
            return False
        self.undo_stack.append(self.snapshot())
        snapshot = self.redo_stack.pop()
        self.restore(snapshot)
        return True


def should_apply_revision(expected: int, incoming: int) -> bool:
    return incoming == expected


class RenderScheduler:
    def __init__(self) -> None:
        self.in_flight = False
        self.pending = False

    def request_render(self) -> bool:
        if self.in_flight:
            self.pending = True
            return False
        self.in_flight = True
        self.pending = False
        return True

    def on_render_finished(self) -> bool:
        self.in_flight = False
        if self.pending:
            self.pending = False
            return True
        return False
