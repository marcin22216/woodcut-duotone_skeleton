"""Grayscale processing step."""

from __future__ import annotations

import numpy as np

from woodcut_duotone.core.steps.base import BaseStep


def _validate_rgb_image(image: np.ndarray) -> None:
    if not isinstance(image, np.ndarray):
        raise ValueError("image_rgb must be a numpy.ndarray")
    if image.dtype != np.uint8:
        raise ValueError("image_rgb must have dtype uint8")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("image_rgb must have shape (H, W, 3)")


class GrayscaleStep(BaseStep):
    def __init__(self, enabled: bool = True) -> None:
        super().__init__(name="Grayscale", enabled=enabled)

    def apply(self, image_rgb: np.ndarray, params: dict | None = None) -> np.ndarray:
        _validate_rgb_image(image_rgb)

        image_float = image_rgb.astype(np.float32)
        gray = (
            image_float[..., 0] * 0.299
            + image_float[..., 1] * 0.587
            + image_float[..., 2] * 0.114
        )
        gray = np.rint(gray).clip(0, 255).astype(np.uint8)
        return np.stack((gray, gray, gray), axis=-1)
