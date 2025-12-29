"""Gaussian blur step for noise reduction."""

from __future__ import annotations

import cv2
import numpy as np

from woodcut_duotone.core.steps.base import BaseStep


STRENGTH_MIN = 0
STRENGTH_MAX = 10


def _validate_rgb_image(image: np.ndarray) -> None:
    if not isinstance(image, np.ndarray):
        raise ValueError("image_rgb must be a numpy.ndarray")
    if image.dtype != np.uint8:
        raise ValueError("image_rgb must have dtype uint8")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("image_rgb must have shape (H, W, 3)")


def _validate_strength(strength: int) -> None:
    if not (STRENGTH_MIN <= strength <= STRENGTH_MAX):
        raise ValueError(
            f"strength must be between {STRENGTH_MIN} and {STRENGTH_MAX}"
        )


class GaussianBlurStep(BaseStep):
    def __init__(self, enabled: bool = True, strength: int = 1) -> None:
        super().__init__(
            name="Gaussian Blur",
            enabled=enabled,
            params={
                "strength": strength,
            },
        )

    def apply(self, image_rgb: np.ndarray, params: dict | None = None) -> np.ndarray:
        _validate_rgb_image(image_rgb)

        merged_params = dict(self.params)
        if params:
            merged_params.update(params)

        try:
            strength = int(merged_params["strength"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Invalid blur parameters") from exc

        _validate_strength(strength)

        if strength == 0:
            return image_rgb.copy()

        kernel_size = 2 * strength + 1
        blurred = cv2.GaussianBlur(
            np.ascontiguousarray(image_rgb), (kernel_size, kernel_size), 0
        )
        return blurred
