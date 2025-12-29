"""Morphology step for binary cleanup."""

from __future__ import annotations

import cv2
import numpy as np

from woodcut_duotone.core.steps.base import BaseStep


OP_CLOSE = "close"
OP_OPEN = "open"
OP_CLOSE_THEN_OPEN = "close_then_open"

KERNEL_MIN = 1
KERNEL_MAX = 31
ITERATIONS_MIN = 1
ITERATIONS_MAX = 5


def _validate_rgb_image(image: np.ndarray) -> None:
    if not isinstance(image, np.ndarray):
        raise ValueError("image_rgb must be a numpy.ndarray")
    if image.dtype != np.uint8:
        raise ValueError("image_rgb must have dtype uint8")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("image_rgb must have shape (H, W, 3)")


def _validate_params(operation: str, kernel_size: int, iterations: int) -> None:
    if operation not in {OP_CLOSE, OP_OPEN, OP_CLOSE_THEN_OPEN}:
        raise ValueError(
            f"operation must be one of: {OP_CLOSE}, {OP_OPEN}, {OP_CLOSE_THEN_OPEN}"
        )
    if not (KERNEL_MIN <= kernel_size <= KERNEL_MAX):
        raise ValueError(
            f"kernel_size must be between {KERNEL_MIN} and {KERNEL_MAX}"
        )
    if kernel_size % 2 == 0:
        raise ValueError("kernel_size must be odd")
    if not (ITERATIONS_MIN <= iterations <= ITERATIONS_MAX):
        raise ValueError(
            f"iterations must be between {ITERATIONS_MIN} and {ITERATIONS_MAX}"
        )


def _binarize(channel: np.ndarray) -> np.ndarray:
    if np.all((channel == 0) | (channel == 255)):
        return channel.astype(np.uint8, copy=False)
    return np.where(channel > 127, 255, 0).astype(np.uint8)


def _ink_mask_from_binary(binary: np.ndarray) -> np.ndarray:
    return np.where(binary == 0, 255, 0).astype(np.uint8)


def _binary_from_ink_mask(ink_mask: np.ndarray) -> np.ndarray:
    return np.where(ink_mask > 127, 0, 255).astype(np.uint8)


class MorphologyStep(BaseStep):
    def __init__(
        self,
        enabled: bool = True,
        operation: str = OP_CLOSE,
        kernel_size: int = 3,
        iterations: int = 1,
    ) -> None:
        super().__init__(
            name="Morphology",
            enabled=enabled,
            params={
                "operation": operation,
                "kernel_size": kernel_size,
                "iterations": iterations,
            },
        )

    def apply(self, image_rgb: np.ndarray, params: dict | None = None) -> np.ndarray:
        _validate_rgb_image(image_rgb)

        merged_params = dict(self.params)
        if params:
            merged_params.update(params)

        try:
            operation = str(merged_params["operation"]).lower()
            kernel_size = int(merged_params["kernel_size"])
            iterations = int(merged_params["iterations"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Invalid morphology parameters") from exc

        _validate_params(operation, kernel_size, iterations)

        channel = image_rgb[..., 0]
        binary = _binarize(channel)
        ink_mask = _ink_mask_from_binary(binary)

        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (kernel_size, kernel_size)
        )

        if operation == OP_CLOSE:
            processed = cv2.morphologyEx(
                ink_mask, cv2.MORPH_CLOSE, kernel, iterations=iterations
            )
        elif operation == OP_OPEN:
            processed = cv2.morphologyEx(
                ink_mask, cv2.MORPH_OPEN, kernel, iterations=iterations
            )
        else:
            closed = cv2.morphologyEx(
                ink_mask, cv2.MORPH_CLOSE, kernel, iterations=iterations
            )
            processed = cv2.morphologyEx(
                closed, cv2.MORPH_OPEN, kernel, iterations=iterations
            )

        output = _binary_from_ink_mask(processed)
        return np.stack((output, output, output), axis=-1)
