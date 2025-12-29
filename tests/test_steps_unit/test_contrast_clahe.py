import numpy as np

from woodcut_duotone.core.steps.contrast_clahe import CLAHEContrastStep
from woodcut_duotone.io.load_save import load_image


def _fixture_path() -> str:
    return "tests/fixtures/images/test_8x8.png"


def test_clahe_output_shape_dtype_and_changes() -> None:
    image = load_image(_fixture_path())
    step = CLAHEContrastStep()

    output = step.apply(image, params=None)

    assert output.shape == image.shape
    assert output.dtype == np.uint8
    assert np.any(output != image)


def test_clahe_params_affect_output() -> None:
    image = load_image(_fixture_path())

    small_tiles = CLAHEContrastStep(tile_grid_size=2)
    large_tiles = CLAHEContrastStep(tile_grid_size=8)

    small_out = small_tiles.apply(image, params=None)
    large_out = large_tiles.apply(image, params=None)

    assert np.any(small_out != large_out)
