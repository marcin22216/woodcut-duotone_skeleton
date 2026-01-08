import numpy as np

from woodcut_duotone.core.steps.denoise import DenoiseStep
from woodcut_duotone.io.load_save import load_image


def _fixture_path() -> str:
    return "tests/fixtures/images/test_8x8.png"


def _golden_path() -> str:
    return "tests/fixtures/golden/test_8x8_denoise.png"


def test_denoise_matches_golden() -> None:
    image = load_image(_fixture_path())
    expected = load_image(_golden_path())

    step = DenoiseStep(kernel_size=3)
    result = step.apply(image, params=None)

    assert np.array_equal(result, expected)
