import numpy as np

from woodcut_duotone.core.steps.contrast_clahe import CLAHEContrastStep
from woodcut_duotone.io.load_save import load_image


def _fixture_path() -> str:
    return "tests/fixtures/images/test_8x8.png"


def _golden_path() -> str:
    return "tests/fixtures/golden/test_8x8_clahe.png"


def test_clahe_matches_golden() -> None:
    image = load_image(_fixture_path())
    expected = load_image(_golden_path())

    step = CLAHEContrastStep()
    result = step.apply(image, params=None)

    assert np.array_equal(result, expected)
