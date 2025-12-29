import numpy as np

from woodcut_duotone.core.pipeline import Pipeline
from woodcut_duotone.core.steps import (
    CLAHEContrastStep,
    GaussianBlurStep,
    GrayscaleStep,
    MorphologyStep,
    ThresholdStep,
)
from woodcut_duotone.io.load_save import load_image


def _fixture_path() -> str:
    return "tests/fixtures/images/test_8x8.png"


def _golden_path() -> str:
    return "tests/fixtures/golden/test_8x8_morphology.png"


def test_morphology_pipeline_matches_golden() -> None:
    image = load_image(_fixture_path())
    expected = load_image(_golden_path())

    pipeline = Pipeline(
        [
            GrayscaleStep(),
            CLAHEContrastStep(),
            GaussianBlurStep(),
            ThresholdStep(),
            MorphologyStep(),
        ]
    )
    result = pipeline.run(image)

    assert np.array_equal(result, expected)
