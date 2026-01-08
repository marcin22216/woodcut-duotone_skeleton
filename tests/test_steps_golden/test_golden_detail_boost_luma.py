import numpy as np

from woodcut_duotone.core.steps.detail_boost import DetailBoostStep
from woodcut_duotone.io.load_save import load_image


def _fixture_path() -> str:
    return "tests/fixtures/images/test_8x8.png"


def _golden_path() -> str:
    return "tests/fixtures/golden/test_8x8_detail_boost_luma.png"


def test_detail_boost_luma_matches_golden() -> None:
    image = load_image(_fixture_path())
    expected = load_image(_golden_path())

    step = DetailBoostStep(amount=20, radius=3, apply_on="luma")
    result = step.apply(image, params=None)

    assert np.array_equal(result, expected)
