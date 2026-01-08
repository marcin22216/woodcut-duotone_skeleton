import numpy as np
import pytest

from woodcut_duotone.core.steps.detail_boost import DetailBoostStep


def test_detail_boost_radius_must_be_odd() -> None:
    image = np.zeros((3, 3, 3), dtype=np.uint8)
    with pytest.raises(ValueError):
        DetailBoostStep(radius=2).apply(image)


def test_detail_boost_zero_amount_is_noop_copy() -> None:
    image = np.zeros((4, 4, 3), dtype=np.uint8)
    image[0, 0] = 120

    result = DetailBoostStep(amount=0, radius=3).apply(image)

    assert np.array_equal(result, image)
    assert result is not image


def test_detail_boost_changes_gradient() -> None:
    gradient = np.linspace(20, 220, 25, dtype=np.uint8).reshape(5, 5)
    image = np.stack([gradient, gradient, gradient], axis=-1)

    result = DetailBoostStep(amount=80, radius=3).apply(image)

    assert np.any(result != image)


def test_detail_boost_invalid_apply_on() -> None:
    image = np.zeros((3, 3, 3), dtype=np.uint8)
    with pytest.raises(ValueError):
        DetailBoostStep(apply_on="nope").apply(image)
