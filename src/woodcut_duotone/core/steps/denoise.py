"""Denoise step with selectable methods."""

from __future__ import annotations

import cv2
import numpy as np

from woodcut_duotone.core.steps.base import BaseStep


METHOD_MEDIAN = "median"
METHOD_BILATERAL = "bilateral"
METHOD_NLMEANS = "nlmeans"

KERNEL_MIN = 1
KERNEL_MAX = 15
DIAMETER_MIN = 1
DIAMETER_MAX = 25
SIGMA_MIN = 0
SIGMA_MAX = 200
H_MIN = 0
H_MAX = 50
TEMPLATE_MIN = 1
TEMPLATE_MAX = 21
SEARCH_MIN = 1
SEARCH_MAX = 31


def _validate_rgb_image(image: np.ndarray) -> None:
    if not isinstance(image, np.ndarray):
        raise ValueError("image_rgb must be a numpy.ndarray")
    if image.dtype != np.uint8:
        raise ValueError("image_rgb must have dtype uint8")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("image_rgb must have shape (H, W, 3)")


def _validate_range(value: int, min_val: int, max_val: int, name: str) -> None:
    if not (min_val <= value <= max_val):
        raise ValueError(f"{name} must be between {min_val} and {max_val}")


def _coerce_odd(value: int, min_val: int, max_val: int) -> int:
    value = max(min_val, min(max_val, value))
    if value % 2 == 0:
        value = value - 1 if value > min_val else value + 1
    return max(min_val, min(max_val, value))


class DenoiseStep(BaseStep):
    def __init__(
        self,
        enabled: bool = True,
        method: str = METHOD_MEDIAN,
        kernel_size: int = 3,
        diameter: int = 5,
        sigma_color: int = 50,
        sigma_space: int = 50,
        h: int = 10,
        template_window: int = 7,
        search_window: int = 21,
    ) -> None:
        super().__init__(
            name="Denoise",
            enabled=enabled,
            params={
                "method": method,
                "kernel_size": kernel_size,
                "diameter": diameter,
                "sigma_color": sigma_color,
                "sigma_space": sigma_space,
                "h": h,
                "template_window": template_window,
                "search_window": search_window,
            },
        )

    def apply(self, image_rgb: np.ndarray, params: dict | None = None) -> np.ndarray:
        _validate_rgb_image(image_rgb)

        merged_params = dict(self.params)
        if params:
            merged_params.update(params)

        try:
            method = str(merged_params["method"]).lower()
            kernel_size = int(merged_params["kernel_size"])
            diameter = int(merged_params["diameter"])
            sigma_color = int(merged_params["sigma_color"])
            sigma_space = int(merged_params["sigma_space"])
            h = int(merged_params["h"])
            template_window = int(merged_params["template_window"])
            search_window = int(merged_params["search_window"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Invalid denoise parameters") from exc

        if method not in {METHOD_MEDIAN, METHOD_BILATERAL, METHOD_NLMEANS}:
            raise ValueError("method must be 'median', 'bilateral', or 'nlmeans'")

        if method == METHOD_MEDIAN:
            _validate_range(kernel_size, KERNEL_MIN, KERNEL_MAX, "kernel_size")
            kernel_size = _coerce_odd(kernel_size, KERNEL_MIN, KERNEL_MAX)
            if kernel_size == 1:
                return image_rgb.copy()
            return cv2.medianBlur(np.ascontiguousarray(image_rgb), kernel_size)

        if method == METHOD_BILATERAL:
            _validate_range(diameter, DIAMETER_MIN, DIAMETER_MAX, "diameter")
            _validate_range(sigma_color, SIGMA_MIN, SIGMA_MAX, "sigma_color")
            _validate_range(sigma_space, SIGMA_MIN, SIGMA_MAX, "sigma_space")
            return cv2.bilateralFilter(
                np.ascontiguousarray(image_rgb),
                diameter,
                sigma_color,
                sigma_space,
            )

        _validate_range(h, H_MIN, H_MAX, "h")
        _validate_range(template_window, TEMPLATE_MIN, TEMPLATE_MAX, "template_window")
        _validate_range(search_window, SEARCH_MIN, SEARCH_MAX, "search_window")
        if h == 0:
            return image_rgb.copy()
        search_window = _coerce_odd(search_window, SEARCH_MIN, SEARCH_MAX)
        template_window = _coerce_odd(template_window, TEMPLATE_MIN, search_window)
        return cv2.fastNlMeansDenoisingColored(
            np.ascontiguousarray(image_rgb),
            None,
            h,
            h,
            template_window,
            search_window,
        )
