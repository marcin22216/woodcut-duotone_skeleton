import numpy as np

from woodcut_duotone.core.steps.blur import GaussianBlurStep
from woodcut_duotone.io.load_save import load_image


def _fixture_path() -> str:
    return "tests/fixtures/images/test_8x8.png"


def test_blur_shape_dtype_and_no_inplace() -> None:
    image = load_image(_fixture_path())
    original = image.copy()

    step = GaussianBlurStep(strength=2)
    output = step.apply(image, params=None)

    assert output.shape == image.shape
    assert output.dtype == np.uint8
    assert np.array_equal(image, original)
    assert output is not image


def test_blur_strength_zero_is_noop() -> None:
    image = load_image(_fixture_path())

    step = GaussianBlurStep(strength=0)
    output = step.apply(image, params=None)

    assert np.array_equal(output, image)


def test_blur_strength_changes_image() -> None:
    image = load_image(_fixture_path())

    step = GaussianBlurStep(strength=2)
    output = step.apply(image, params=None)

    assert np.any(output != image)
