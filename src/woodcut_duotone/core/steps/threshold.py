"""Binary threshold step for duotone output."""

from __future__ import annotations

import cv2
import numpy as np

from woodcut_duotone.core.steps.base import BaseStep


MODE_OTSU = "otsu"
MODE_ADAPTIVE = "adaptive"

BIAS_MIN = -50
BIAS_MAX = 50
BLOCK_SIZE_MIN = 7
BLOCK_SIZE_MAX = 71


def _validate_rgb_image(image: np.ndarray) -> None:
    if not isinstance(image, np.ndarray):
        raise ValueError("image_rgb must be a numpy.ndarray")
    if image.dtype != np.uint8:
        raise ValueError("image_rgb must have dtype uint8")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("image_rgb must have shape (H, W, 3)")


def _rgb_to_gray(image_rgb: np.ndarray) -> np.ndarray:
    image_float = image_rgb.astype(np.float32)
    gray = (
        image_float[..., 0] * 0.299
        + image_float[..., 1] * 0.587
        + image_float[..., 2] * 0.114
    )
    return np.rint(gray).clip(0, 255).astype(np.uint8)


def _validate_params(mode: str, invert: bool, bias: int, block_size: int) -> None:
    if mode not in {MODE_OTSU, MODE_ADAPTIVE}:
        raise ValueError(f"mode must be one of: {MODE_OTSU}, {MODE_ADAPTIVE}")
    if not isinstance(invert, bool):
        raise ValueError("invert must be a boolean")
    if not (BIAS_MIN <= bias <= BIAS_MAX):
        raise ValueError(f"bias must be between {BIAS_MIN} and {BIAS_MAX}")
    if not (BLOCK_SIZE_MIN <= block_size <= BLOCK_SIZE_MAX):
        raise ValueError(
            f"block_size must be between {BLOCK_SIZE_MIN} and {BLOCK_SIZE_MAX}"
        )
    if block_size % 2 == 0:
        raise ValueError("block_size must be odd")


class ThresholdStep(BaseStep):
    def __init__(
        self,
        enabled: bool = True,
        mode: str = MODE_OTSU,
        invert: bool = False,
        bias: int = 0,
        block_size: int = 31,
    ) -> None:
        super().__init__(
            name="Threshold",
            enabled=enabled,
            params={
                "mode": mode,
                "invert": invert,
                "bias": bias,
                "block_size": block_size,
            },
        )

    def apply(self, image_rgb: np.ndarray, params: dict | None = None) -> np.ndarray:
        _validate_rgb_image(image_rgb)

        merged_params = dict(self.params)
        if params:
            merged_params.update(params)

        try:
            mode = str(merged_params["mode"]).lower()
        except KeyError as exc:
            raise ValueError("mode is required") from exc

        invert_raw = merged_params.get("invert", False)
        if isinstance(invert_raw, bool):
            invert = invert_raw
        elif isinstance(invert_raw, int) and invert_raw in (0, 1):
            invert = bool(invert_raw)
        else:
            raise ValueError("invert must be a boolean")

        try:
            bias = int(merged_params.get("bias", 0))
            block_size = int(merged_params.get("block_size", 31))
        except (TypeError, ValueError) as exc:
            raise ValueError("Invalid threshold parameters") from exc

        _validate_params(mode, invert, bias, block_size)

        gray = _rgb_to_gray(image_rgb)

        if mode == MODE_OTSU:
            threshold_value, _ = cv2.threshold(
                gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )
            threshold_value = int(round(threshold_value)) + bias
            threshold_value = int(np.clip(threshold_value, 0, 255))
            _, binary = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY)
        else:
            c_value = -bias
            binary = cv2.adaptiveThreshold(
                gray,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                block_size,
                c_value,
            )

        if invert:
            binary = 255 - binary

        binary = binary.astype(np.uint8, copy=False)
        return np.stack((binary, binary, binary), axis=-1)
