import numpy as np
import pytest

from woodcut_duotone.core.steps.morphology import MorphologyStep


def _to_rgb(binary: np.ndarray) -> np.ndarray:
    return np.stack((binary, binary, binary), axis=-1)


def test_morphology_output_shape_dtype_and_binary() -> None:
    image = np.array(
        [
            [[10, 20, 30], [200, 210, 220], [10, 20, 30]],
            [[200, 210, 220], [10, 20, 30], [200, 210, 220]],
            [[10, 20, 30], [200, 210, 220], [10, 20, 30]],
        ],
        dtype=np.uint8,
    )
    step = MorphologyStep()

    output = step.apply(image, params=None)

    assert output.shape == image.shape
    assert output.dtype == np.uint8
    values = np.unique(output)
    assert set(values.tolist()).issubset({0, 255})


def test_morphology_kernel_size_even_raises() -> None:
    image = _to_rgb(np.full((5, 5), 255, dtype=np.uint8))
    step = MorphologyStep(kernel_size=4)

    with pytest.raises(ValueError):
        step.apply(image, params=None)


def test_morphology_close_fills_hole() -> None:
    binary = np.full((5, 5), 255, dtype=np.uint8)
    binary[1:4, 1:4] = 0
    binary[2, 2] = 255
    image = _to_rgb(binary)

    step = MorphologyStep(operation="close", kernel_size=3)
    output = step.apply(image, params=None)

    assert output[2, 2, 0] == 0


def test_morphology_open_removes_island() -> None:
    binary = np.full((5, 5), 255, dtype=np.uint8)
    binary[2, 2] = 0
    image = _to_rgb(binary)

    step = MorphologyStep(operation="open", kernel_size=3)
    output = step.apply(image, params=None)

    assert output[2, 2, 0] == 255
