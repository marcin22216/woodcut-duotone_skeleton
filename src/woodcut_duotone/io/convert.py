"""Color space and Qt conversion helpers."""

from __future__ import annotations

import numpy as np
from PySide6.QtGui import QImage


def _validate_rgb_image(image: np.ndarray, *, name: str = "image") -> None:
    if not isinstance(image, np.ndarray):
        raise ValueError(f"{name} must be a numpy.ndarray")
    if image.dtype != np.uint8:
        raise ValueError(f"{name} must have dtype uint8")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"{name} must have shape (H, W, 3)")


def _swap_channels(image: np.ndarray) -> np.ndarray:
    return np.ascontiguousarray(image[..., ::-1])


def rgb_to_bgr(image_rgb: np.ndarray) -> np.ndarray:
    _validate_rgb_image(image_rgb, name="image_rgb")
    return _swap_channels(image_rgb)


def bgr_to_rgb(image_bgr: np.ndarray) -> np.ndarray:
    _validate_rgb_image(image_bgr, name="image_bgr")
    return _swap_channels(image_bgr)


def rgb_to_qimage(image_rgb: np.ndarray) -> QImage:
    _validate_rgb_image(image_rgb, name="image_rgb")

    rgb = np.ascontiguousarray(image_rgb)
    height, width, _ = rgb.shape
    bytes_per_line = int(rgb.strides[0])

    qimage = QImage(rgb.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
    if qimage.isNull():
        raise ValueError("Failed to create QImage from RGB data")
    return qimage.copy()
