import numpy as np

from woodcut_duotone.core.pipeline import Pipeline, Step
from woodcut_duotone.core.steps.base import BaseStep
from woodcut_duotone.core.steps.blur import GaussianBlurStep
from woodcut_duotone.core.steps.contrast_clahe import CLAHEContrastStep
from woodcut_duotone.core.steps.grayscale import GrayscaleStep
from woodcut_duotone.core.steps.morphology import MorphologyStep
from woodcut_duotone.core.steps.threshold import ThresholdStep


class AppendStep(Step):
    def __init__(self, name: str, suffix: str, enabled: bool = True, calls=None) -> None:
        super().__init__(name=name, enabled=enabled)
        self.suffix = suffix
        self.calls = calls

    def apply(self, image, params):
        if self.calls is not None:
            self.calls.append(self.name)
        return f"{image}{self.suffix}"


class PassStep(Step):
    def apply(self, image, params):
        return image


def test_pipeline_order() -> None:
    calls = []
    steps = [
        AppendStep(name="one", suffix="A", calls=calls),
        AppendStep(name="two", suffix="B", calls=calls),
    ]
    pipeline = Pipeline(steps)

    result = pipeline.run("X")

    assert result == "XAB"
    assert calls == ["one", "two"]


def test_pipeline_skips_disabled_steps() -> None:
    calls = []
    steps = [
        AppendStep(name="one", suffix="A", calls=calls),
        AppendStep(name="two", suffix="B", enabled=False, calls=calls),
        AppendStep(name="three", suffix="C", calls=calls),
    ]
    pipeline = Pipeline(steps)

    result = pipeline.run("X")

    assert result == "XAC"
    assert calls == ["one", "three"]


def test_pipeline_passes_image_through_when_no_op() -> None:
    image = {"value": 1}
    pipeline = Pipeline([PassStep(name="pass")])

    result = pipeline.run(image)

    assert result is image


def test_base_step_params() -> None:
    step = BaseStep(name="base")

    assert step.get_param("missing") is None

    step.set_param("threshold", 123)

    assert step.get_param("threshold") == 123
    assert step.params["threshold"] == 123


def test_pipeline_with_grayscale_step_smoke() -> None:
    image = np.zeros((3, 3, 3), dtype=np.uint8)
    pipeline = Pipeline([GrayscaleStep()])

    result = pipeline.run(image)

    assert result.shape == image.shape
    assert result.dtype == np.uint8


def test_pipeline_with_grayscale_and_clahe_smoke() -> None:
    image = np.zeros((4, 4, 3), dtype=np.uint8)
    pipeline = Pipeline([GrayscaleStep(), CLAHEContrastStep()])

    result = pipeline.run(image)

    assert result.shape == image.shape
    assert result.dtype == np.uint8


def test_pipeline_with_grayscale_clahe_blur_smoke() -> None:
    image = np.zeros((5, 5, 3), dtype=np.uint8)
    pipeline = Pipeline([GrayscaleStep(), CLAHEContrastStep(), GaussianBlurStep()])

    result = pipeline.run(image)

    assert result.shape == image.shape
    assert result.dtype == np.uint8


def test_pipeline_with_threshold_smoke() -> None:
    image = np.zeros((6, 6, 3), dtype=np.uint8)
    pipeline = Pipeline(
        [GrayscaleStep(), CLAHEContrastStep(), GaussianBlurStep(), ThresholdStep()]
    )

    result = pipeline.run(image)

    assert result.shape == image.shape
    assert result.dtype == np.uint8
    values = np.unique(result)
    assert set(values.tolist()).issubset({0, 255})


def test_pipeline_with_morphology_smoke() -> None:
    image = np.zeros((6, 6, 3), dtype=np.uint8)
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

    assert result.shape == image.shape
    assert result.dtype == np.uint8
    values = np.unique(result)
    assert set(values.tolist()).issubset({0, 255})
