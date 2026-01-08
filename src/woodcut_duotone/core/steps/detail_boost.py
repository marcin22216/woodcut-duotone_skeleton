"""Detail boost step using a light unsharp mask."""

from __future__ import annotations

import cv2
import numpy as np

from woodcut_duotone.core.steps.base import BaseStep


APPLY_RGB = "rgb"
APPLY_LUMA = "luma"

AMOUNT_MIN = 0
AMOUNT_MAX = 200
RADIUS_MIN = 1
RADIUS_MAX = 9


def _validate_rgb_image(image: np.ndarray) -> None:
    if not isinstance(image, np.ndarray):
        raise ValueError("image_rgb must be a numpy.ndarray")
    if image.dtype != np.uint8:
        raise ValueError("image_rgb must have dtype uint8")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("image_rgb must have shape (H, W, 3)")


def _validate_params(amount: int, radius: int, apply_on: str) -> None:
    if not (AMOUNT_MIN <= amount <= AMOUNT_MAX):
        raise ValueError(f"amount must be between {AMOUNT_MIN} and {AMOUNT_MAX}")
    if not (RADIUS_MIN <= radius <= RADIUS_MAX):
        raise ValueError(f"radius must be between {RADIUS_MIN} and {RADIUS_MAX}")
    if radius % 2 == 0:
        raise ValueError("radius must be odd")
    if apply_on not in {APPLY_RGB, APPLY_LUMA}:
        raise ValueError("apply_on must be 'rgb' or 'luma'")


def _rgb_to_luma(image_rgb: np.ndarray) -> np.ndarray:
    image_float = image_rgb.astype(np.float32)
    gray = (
        image_float[..., 0] * 0.299
        + image_float[..., 1] * 0.587
        + image_float[..., 2] * 0.114
    )
    return np.rint(gray).clip(0, 255).astype(np.uint8)


class DetailBoostStep(BaseStep):
    def __init__(
        self,
        enabled: bool = True,
        amount: int = 20,
        radius: int = 3,
        apply_on: str = APPLY_RGB,
    ) -> None:
        super().__init__(
            name="Detail Boost",
            enabled=enabled,
            params={
                "amount": amount,
                "radius": radius,
                "apply_on": apply_on,
            },
        )

    def apply(self, image_rgb: np.ndarray, params: dict | None = None) -> np.ndarray:
        _validate_rgb_image(image_rgb)

        merged_params = dict(self.params)
        if params:
            merged_params.update(params)

        try:
            amount = int(merged_params["amount"])
            radius = int(merged_params["radius"])
            apply_on = str(merged_params["apply_on"]).lower()
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Invalid detail boost parameters") from exc

        _validate_params(amount, radius, apply_on)

        if amount == 0 or radius == 1:
            return image_rgb.copy()

        strength = amount / 100.0

        if apply_on == APPLY_LUMA:
            luma = _rgb_to_luma(image_rgb).astype(np.float32)
            blurred = cv2.GaussianBlur(luma, (radius, radius), 0)
            boosted = cv2.addWeighted(luma, 1.0 + strength, blurred, -strength, 0)
            delta = boosted - luma
            output = image_rgb.astype(np.float32) + delta[..., None]
            return np.rint(output).clip(0, 255).astype(np.uint8)

        blurred = cv2.GaussianBlur(
            np.ascontiguousarray(image_rgb), (radius, radius), 0
        )
        boosted = cv2.addWeighted(image_rgb, 1.0 + strength, blurred, -strength, 0)
        return boosted
