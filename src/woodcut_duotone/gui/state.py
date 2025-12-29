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


class AppState:
    def __init__(self) -> None:
        self.original_image_rgb: np.ndarray | None = None
        self.enabled = _default_enabled()
        self.params = _default_params()
        self.undo_stack: list[dict[str, dict[str, Any]]] = []
        self.redo_stack: list[dict[str, dict[str, Any]]] = []
        self.render_revision = 0
        self.last_applied_revision = 0

    def snapshot(self) -> dict[str, dict[str, Any]]:
        return {
            "enabled": deepcopy(self.enabled),
            "params": deepcopy(self.params),
        }

    def restore(self, snapshot: dict[str, dict[str, Any]]) -> None:
        self.enabled = deepcopy(snapshot["enabled"])
        self.params = deepcopy(snapshot["params"])

    def push_undo(self) -> None:
        self.undo_stack.append(self.snapshot())
        self.redo_stack.clear()

    def reset_defaults(self) -> None:
        self.enabled = _default_enabled()
        self.params = _default_params()
        self.undo_stack.clear()
        self.redo_stack.clear()

    def next_render_revision(self) -> int:
        self.render_revision += 1
        return self.render_revision

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
