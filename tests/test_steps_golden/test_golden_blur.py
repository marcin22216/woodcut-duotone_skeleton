import numpy as np

from woodcut_duotone.core.steps.blur import GaussianBlurStep
from woodcut_duotone.io.load_save import load_image


def _fixture_path() -> str:
    return "tests/fixtures/images/test_8x8.png"


def _golden_path() -> str:
    return "tests/fixtures/golden/test_8x8_blur.png"


def test_blur_matches_golden() -> None:
    image = load_image(_fixture_path())
    expected = load_image(_golden_path())

    step = GaussianBlurStep()
    result = step.apply(image, params=None)

    assert np.array_equal(result, expected)
