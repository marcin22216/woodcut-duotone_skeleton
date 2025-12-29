"""Edge detection step using Canny."""

from __future__ import annotations

import logging

import cv2
import numpy as np

from woodcut_duotone.core.steps.base import BaseStep


APPLY_LUMA = "luma"
APPLY_BINARY = "binary"

LOW_MIN = 0
LOW_MAX = 255
HIGH_MIN = 0
HIGH_MAX = 255
THICKNESS_MIN = 1
THICKNESS_MAX = 5


def _validate_rgb_image(image: np.ndarray) -> None:
    if not isinstance(image, np.ndarray):
        raise ValueError("image_rgb must be a numpy.ndarray")
    if image.dtype != np.uint8:
        raise ValueError("image_rgb must have dtype uint8")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("image_rgb must have shape (H, W, 3)")


def _validate_params(low: int, high: int, thickness: int, apply_on: str) -> None:
    if not (LOW_MIN <= low <= LOW_MAX):
        raise ValueError(f"low must be between {LOW_MIN} and {LOW_MAX}")
    if not (HIGH_MIN <= high <= HIGH_MAX):
        raise ValueError(f"high must be between {HIGH_MIN} and {HIGH_MAX}")
    if high < low:
        raise ValueError("high must be >= low")
    if not (THICKNESS_MIN <= thickness <= THICKNESS_MAX):
        raise ValueError(
            f"thickness must be between {THICKNESS_MIN} and {THICKNESS_MAX}"
        )
    if apply_on not in {APPLY_LUMA, APPLY_BINARY}:
        raise ValueError("apply_on must be 'luma' or 'binary'")


def _rgb_to_gray(image_rgb: np.ndarray) -> np.ndarray:
    image_float = image_rgb.astype(np.float32)
    gray = (
        image_float[..., 0] * 0.299
        + image_float[..., 1] * 0.587
        + image_float[..., 2] * 0.114
    )
    return np.rint(gray).clip(0, 255).astype(np.uint8)


def _prepare_binary(channel: np.ndarray) -> np.ndarray:
    if np.all((channel == 0) | (channel == 255)):
        return channel.astype(np.uint8, copy=False)
    return np.where(channel > 127, 255, 0).astype(np.uint8)


class EdgesStep(BaseStep):
    def __init__(
        self,
        enabled: bool = True,
        low: int = 60,
        high: int = 140,
        thickness: int = 1,
        apply_on: str = APPLY_LUMA,
    ) -> None:
        super().__init__(
            name="Edges",
            enabled=enabled,
            params={
                "low": low,
                "high": high,
                "thickness": thickness,
                "apply_on": apply_on,
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
            thickness = int(merged_params["thickness"])
            apply_on = str(merged_params["apply_on"]).lower()
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Invalid edges parameters") from exc

        _validate_params(low, high, thickness, apply_on)
        logging.getLogger(__name__).debug(
            "Edges params: low=%s high=%s thickness=%s apply_on=%s",
            low,
            high,
            thickness,
            apply_on,
        )

        if apply_on == APPLY_LUMA:
            gray = _rgb_to_gray(image_rgb)
        else:
            channel = image_rgb[..., 0]
            gray = _prepare_binary(channel)

        edges = cv2.Canny(gray, low, high)

        if thickness > 1:
            kernel_size = 2 * thickness + 1
            kernel = cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE, (kernel_size, kernel_size)
            )
            edges = cv2.dilate(edges, kernel, iterations=1)

        output = image_rgb.copy()
        output[edges > 0] = 0
        return output
