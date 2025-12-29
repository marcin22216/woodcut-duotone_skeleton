import numpy as np
import pytest

from woodcut_duotone.core.steps.edges import EdgesStep


def _make_test_image() -> np.ndarray:
    image = np.full((32, 32, 3), 200, dtype=np.uint8)
    image[8:24, 8:24] = 100
    return image


def test_edges_output_shape_dtype() -> None:
    image = _make_test_image()
    step = EdgesStep()

    output = step.apply(image, params=None)

    assert output.shape == image.shape
    assert output.dtype == np.uint8


def test_edges_high_lower_than_low_raises() -> None:
    image = _make_test_image()
    step = EdgesStep(low=120, high=100)

    with pytest.raises(ValueError):
        step.apply(image, params=None)


def test_edges_adds_black_pixels() -> None:
    image = _make_test_image()
    step = EdgesStep(low=30, high=90)

    output = step.apply(image, params=None)

    original_black = np.sum(np.all(image == 0, axis=-1))
    output_black = np.sum(np.all(output == 0, axis=-1))
    assert output_black > original_black


def test_edges_thickness_increases_ink() -> None:
    image = _make_test_image()

    thin = EdgesStep(low=30, high=90, thickness=1)
    thick = EdgesStep(low=30, high=90, thickness=2)

    thin_out = thin.apply(image, params=None)
    thick_out = thick.apply(image, params=None)

    thin_black = np.sum(np.all(thin_out == 0, axis=-1))
    thick_black = np.sum(np.all(thick_out == 0, axis=-1))

    assert thick_black > thin_black
