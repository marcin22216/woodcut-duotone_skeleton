"""Local contrast enhancement using CLAHE."""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from woodcut_duotone.core.steps.base import BaseStep


CLIP_LIMIT_MIN = 0.5
CLIP_LIMIT_MAX = 10.0
TILE_GRID_MIN = 2
TILE_GRID_MAX = 32


def _validate_rgb_image(image: np.ndarray) -> None:
    if not isinstance(image, np.ndarray):
        raise ValueError("image_rgb must be a numpy.ndarray")
    if image.dtype != np.uint8:
        raise ValueError("image_rgb must have dtype uint8")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("image_rgb must have shape (H, W, 3)")


def _validate_params(clip_limit: float, tile_grid_size: int) -> None:
    if not (CLIP_LIMIT_MIN <= clip_limit <= CLIP_LIMIT_MAX):
        raise ValueError(
            f"clip_limit must be between {CLIP_LIMIT_MIN} and {CLIP_LIMIT_MAX}"
        )
    if not (TILE_GRID_MIN <= tile_grid_size <= TILE_GRID_MAX):
        raise ValueError(
            f"tile_grid_size must be between {TILE_GRID_MIN} and {TILE_GRID_MAX}"
        )


class CLAHEContrastStep(BaseStep):
    def __init__(
        self, enabled: bool = True, clip_limit: float = 2.0, tile_grid_size: int = 8
    ) -> None:
        super().__init__(
            name="CLAHE Contrast",
            enabled=enabled,
            params={
                "clip_limit": clip_limit,
                "tile_grid_size": tile_grid_size,
            },
        )

    def apply(self, image_rgb: np.ndarray, params: dict | None = None) -> np.ndarray:
        _validate_rgb_image(image_rgb)

        merged_params = dict(self.params)
        if params:
            merged_params.update(params)

        try:
            clip_limit = float(merged_params["clip_limit"])
            tile_grid_size = int(merged_params["tile_grid_size"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Invalid CLAHE parameters") from exc

        _validate_params(clip_limit, tile_grid_size)

        image_bgr = np.ascontiguousarray(image_rgb[..., ::-1])
        lab = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)

        clahe = cv2.createCLAHE(
            clipLimit=clip_limit, tileGridSize=(tile_grid_size, tile_grid_size)
        )
        l_channel = clahe.apply(l_channel)

        merged = cv2.merge((l_channel, a_channel, b_channel))
        bgr_out = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
        rgb_out = np.ascontiguousarray(bgr_out[..., ::-1])
        return rgb_out
