import numpy as np
import pytest

from woodcut_duotone.core.steps.foreground_emphasis import ForegroundEmphasisStep


def test_foreground_emphasis_rejects_high_below_low() -> None:
    image = np.zeros((3, 3, 3), dtype=np.uint8)
    with pytest.raises(ValueError):
        ForegroundEmphasisStep(low=120, high=60).apply(image)


def test_foreground_emphasis_strength_zero_is_noop_copy() -> None:
    image = np.zeros((4, 4, 3), dtype=np.uint8)
    image[1, 1] = 200

    result = ForegroundEmphasisStep(strength=0).apply(image)

    assert np.array_equal(result, image)
    assert result is not image


def test_foreground_emphasis_whitens_background_when_no_edges() -> None:
    image = np.full((5, 5, 3), 64, dtype=np.uint8)

    step = ForegroundEmphasisStep(
        low=80,
        high=160,
        spread=0,
        threshold=0,
        strength=100,
        background=200,
    )
    result = step.apply(image)

    assert np.all(result == 200)
