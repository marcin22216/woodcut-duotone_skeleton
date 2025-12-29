"""Image loading and saving utilities."""

from __future__ import annotations

from pathlib import Path
import numpy as np
from PIL import Image


def _validate_rgb_image(image_rgb: np.ndarray, *, name: str = "image_rgb") -> None:
    if not isinstance(image_rgb, np.ndarray):
        raise ValueError(f"{name} must be a numpy.ndarray")
    if image_rgb.dtype != np.uint8:
        raise ValueError(f"{name} must have dtype uint8")
    if image_rgb.ndim != 3 or image_rgb.shape[2] != 3:
        raise ValueError(f"{name} must have shape (H, W, 3)")


def load_image(path: str) -> np.ndarray:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")

    try:
        with Image.open(file_path) as img:
            rgb_img = img.convert("RGB")
            array = np.array(rgb_img, dtype=np.uint8)
    except Exception as exc:
        raise ValueError(f"Failed to load image: {path}") from exc

    _validate_rgb_image(array, name="loaded image")
    return array


def save_image(path: str, image_rgb: np.ndarray) -> None:
    _validate_rgb_image(image_rgb)

    image = Image.fromarray(image_rgb)
    image.save(path)
