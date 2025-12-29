import numpy as np

from woodcut_duotone.core.pipeline import Pipeline
from woodcut_duotone.core.steps import (
    CLAHEContrastStep,
    EdgesStep,
    GaussianBlurStep,
    GrayscaleStep,
    MorphologyStep,
    ThresholdStep,
)
from woodcut_duotone.io.load_save import load_image


def _fixture_path() -> str:
    return "tests/fixtures/images/test_8x8.png"


def _golden_path() -> str:
    return "tests/fixtures/golden/test_8x8_edges.png"


def test_edges_pipeline_matches_golden() -> None:
    image = load_image(_fixture_path())
    expected = load_image(_golden_path())

    pipeline = Pipeline(
        [
            GrayscaleStep(),
            CLAHEContrastStep(),
            GaussianBlurStep(),
            ThresholdStep(),
            MorphologyStep(),
            EdgesStep(),
        ]
    )
    result = pipeline.run(image)

    assert np.array_equal(result, expected)
