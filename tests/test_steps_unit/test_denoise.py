import numpy as np
import pytest

from woodcut_duotone.core.steps.denoise import DenoiseStep


def test_denoise_kernel_out_of_range() -> None:
    with pytest.raises(ValueError):
        DenoiseStep(kernel_size=0).apply(np.zeros((3, 3, 3), dtype=np.uint8))


def test_denoise_invalid_method() -> None:
    with pytest.raises(ValueError):
        DenoiseStep(method="nope").apply(np.zeros((3, 3, 3), dtype=np.uint8))


def test_denoise_kernel_one_is_noop_copy() -> None:
    image = np.zeros((4, 4, 3), dtype=np.uint8)
    image[1, 1] = 200

    result = DenoiseStep(kernel_size=1).apply(image)

    assert np.array_equal(result, image)
    assert result is not image


def test_denoise_removes_impulse_noise() -> None:
    image = np.zeros((5, 5, 3), dtype=np.uint8)
    image[2, 2] = 255

    result = DenoiseStep(kernel_size=3).apply(image)

    assert int(result[2, 2, 0]) == 0
    assert int(result[2, 2, 1]) == 0
    assert int(result[2, 2, 2]) == 0


def test_denoise_bilateral_changes_noisy_image() -> None:
    rng = np.random.default_rng(0)
    image = rng.integers(0, 256, size=(10, 10, 3), dtype=np.uint8)

    result = DenoiseStep(
        method="bilateral",
        diameter=9,
        sigma_color=80,
        sigma_space=80,
    ).apply(image)

    assert result.shape == image.shape
    assert result.dtype == np.uint8
    assert np.any(result != image)


def test_denoise_nlmeans_changes_noisy_image() -> None:
    rng = np.random.default_rng(1)
    image = rng.integers(0, 256, size=(10, 10, 3), dtype=np.uint8)

    result = DenoiseStep(
        method="nlmeans",
        h=15,
        template_window=7,
        search_window=21,
    ).apply(image)

    assert result.shape == image.shape
    assert result.dtype == np.uint8
    assert np.any(result != image)
