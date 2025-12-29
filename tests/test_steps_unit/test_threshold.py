import numpy as np
import pytest

from woodcut_duotone.core.steps.threshold import ThresholdStep
from woodcut_duotone.io.load_save import load_image


def _fixture_path() -> str:
    return "tests/fixtures/images/test_8x8.png"


def test_threshold_output_binary_rgb() -> None:
    image = load_image(_fixture_path())
    step = ThresholdStep()

    output = step.apply(image, params=None)

    assert output.shape == image.shape
    assert output.dtype == np.uint8
    assert np.all(output[..., 0] == output[..., 1])
    assert np.all(output[..., 1] == output[..., 2])
    values = np.unique(output)
    assert set(values.tolist()).issubset({0, 255})


def test_threshold_invert_changes_output() -> None:
    image = load_image(_fixture_path())

    normal = ThresholdStep().apply(image, params=None)
    inverted = ThresholdStep(invert=True).apply(image, params=None)

    assert not np.array_equal(normal, inverted)


def test_threshold_block_size_even_raises() -> None:
    image = load_image(_fixture_path())
    step = ThresholdStep(mode="adaptive", block_size=30)

    with pytest.raises(ValueError):
        step.apply(image, params=None)
