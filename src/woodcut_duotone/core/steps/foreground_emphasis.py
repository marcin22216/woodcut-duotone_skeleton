"""Foreground emphasis step based on edge density."""

from __future__ import annotations

import cv2
import numpy as np

from woodcut_duotone.core.steps.base import BaseStep


LOW_MIN = 0
LOW_MAX = 255
HIGH_MIN = 0
HIGH_MAX = 255
SPREAD_MIN = 0
SPREAD_MAX = 100
THRESHOLD_MIN = 0
THRESHOLD_MAX = 100
STRENGTH_MIN = 0
STRENGTH_MAX = 100
BACKGROUND_MIN = 0
BACKGROUND_MAX = 255


def _validate_rgb_image(image: np.ndarray) -> None:
    if not isinstance(image, np.ndarray):
        raise ValueError("image_rgb must be a numpy.ndarray")
    if image.dtype != np.uint8:
        raise ValueError("image_rgb must have dtype uint8")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("image_rgb must have shape (H, W, 3)")


def _validate_params(
    low: int,
    high: int,
    spread: int,
    threshold: int,
    strength: int,
    background: int,
) -> None:
    if not (LOW_MIN <= low <= LOW_MAX):
        raise ValueError(f"low must be between {LOW_MIN} and {LOW_MAX}")
    if not (HIGH_MIN <= high <= HIGH_MAX):
        raise ValueError(f"high must be between {HIGH_MIN} and {HIGH_MAX}")
    if high < low:
        raise ValueError("high must be >= low")
    if not (SPREAD_MIN <= spread <= SPREAD_MAX):
        raise ValueError(f"spread must be between {SPREAD_MIN} and {SPREAD_MAX}")
    if not (THRESHOLD_MIN <= threshold <= THRESHOLD_MAX):
        raise ValueError(
            f"threshold must be between {THRESHOLD_MIN} and {THRESHOLD_MAX}"
        )
    if not (STRENGTH_MIN <= strength <= STRENGTH_MAX):
        raise ValueError(
            f"strength must be between {STRENGTH_MIN} and {STRENGTH_MAX}"
        )
    if not (BACKGROUND_MIN <= background <= BACKGROUND_MAX):
        raise ValueError(
            f"background must be between {BACKGROUND_MIN} and {BACKGROUND_MAX}"
        )


def _rgb_to_gray(image_rgb: np.ndarray) -> np.ndarray:
    image_float = image_rgb.astype(np.float32)
    gray = (
        image_float[..., 0] * 0.299
        + image_float[..., 1] * 0.587
        + image_float[..., 2] * 0.114
    )
    return np.rint(gray).clip(0, 255).astype(np.uint8)


class ForegroundEmphasisStep(BaseStep):
    def __init__(
        self,
        enabled: bool = True,
        low: int = 40,
        high: int = 120,
        spread: int = 30,
        threshold: int = 10,
        strength: int = 70,
        background: int = 255,
    ) -> None:
        super().__init__(
            name="Foreground Emphasis",
            enabled=enabled,
            params={
                "low": low,
                "high": high,
                "spread": spread,
                "threshold": threshold,
                "strength": strength,
                "background": background,
            },
        )

    def apply(self, image_rgb: np.ndarray, params: dict | None = None) -> np.ndarray:
        _validate_rgb_image(image_rgb)

        merged_params = dict(self.params)
        if params:
            merged_params.update(params)

        try:
            low = int(merged_params["low"])
            high = int(merged_params["high"])
            spread = int(merged_params["spread"])
            threshold = int(merged_params["threshold"])
            strength = int(merged_params["strength"])
            background = int(merged_params["background"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Invalid foreground emphasis parameters") from exc

        _validate_params(low, high, spread, threshold, strength, background)

        if strength == 0:
            return image_rgb.copy()

        gray = _rgb_to_gray(image_rgb)
        edges = cv2.Canny(gray, low, high)
        mask = edges.astype(np.float32) / 255.0

        if spread > 0:
            sigma = spread / 5.0
            if sigma > 0:
                mask = cv2.GaussianBlur(mask, (0, 0), sigmaX=sigma, sigmaY=sigma)

        max_val = float(mask.max()) if mask.size else 0.0
        if max_val > 0:
            mask = mask / max_val

        threshold_f = threshold / 100.0
        if threshold_f >= 1.0:
            mask = np.zeros_like(mask)
        elif threshold_f > 0:
            denom = 1.0 - threshold_f
            mask = np.clip((mask - threshold_f) / denom, 0.0, 1.0)

        strength_f = strength / 100.0
        background_mask = 1.0 - mask
        blend = strength_f * background_mask

        output = image_rgb.astype(np.float32)
        output = output * (1.0 - blend[..., None]) + background * blend[..., None]
        return np.rint(output).clip(0, 255).astype(np.uint8)
