import numpy as np

from woodcut_duotone.core.steps.grayscale import GrayscaleStep
from woodcut_duotone.io import load_image


def _fixture_path() -> str:
    return "tests/fixtures/images/test_8x8.png"


def _golden_path() -> str:
    return "tests/fixtures/golden/test_8x8_grayscale.png"


def test_grayscale_matches_golden() -> None:
    image = load_image(_fixture_path())
    expected = load_image(_golden_path())

    step = GrayscaleStep()
    result = step.apply(image, params=None)

    assert np.array_equal(result, expected)
