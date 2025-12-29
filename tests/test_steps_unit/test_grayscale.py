import numpy as np

from woodcut_duotone.core.steps.grayscale import GrayscaleStep


def test_grayscale_output_shape_dtype_and_channels() -> None:
    image = np.array(
        [
            [[10, 20, 30], [40, 50, 60]],
            [[70, 80, 90], [100, 110, 120]],
        ],
        dtype=np.uint8,
    )
    original = image.copy()
    step = GrayscaleStep()

    output = step.apply(image, params=None)

    assert output.shape == image.shape
    assert output.dtype == np.uint8
    assert np.all(output[..., 0] == output[..., 1])
    assert np.all(output[..., 1] == output[..., 2])
    assert np.array_equal(image, original)
    assert output is not image
