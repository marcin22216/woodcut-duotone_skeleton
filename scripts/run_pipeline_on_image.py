"""Run the current pipeline on a single image for manual testing."""

from __future__ import annotations

import argparse
import sys

from woodcut_duotone.core.pipeline import Pipeline
from woodcut_duotone.core.steps import (
    CLAHEContrastStep,
    EdgesStep,
    GaussianBlurStep,
    GrayscaleStep,
    MorphologyStep,
    ThresholdStep,
)
from woodcut_duotone.io.load_save import load_image, save_image


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the woodcut pipeline (pre-GUI) on a single image."
    )
    parser.add_argument("--in", dest="input_path", required=True, help="Input image path")
    parser.add_argument("--out", dest="output_path", required=True, help="Output image path")
    parser.add_argument(
        "--mode",
        choices=["otsu", "adaptive"],
        default="otsu",
        help="Threshold mode",
    )
    parser.add_argument(
        "--invert",
        type=int,
        choices=[0, 1],
        default=0,
        help="Invert threshold output (0 or 1)",
    )
    parser.add_argument("--bias", type=int, default=0, help="Threshold bias")
    parser.add_argument(
        "--block-size",
        dest="block_size",
        type=int,
        default=31,
        help="Adaptive threshold block size (odd)",
    )
    parser.add_argument(
        "--morph-op",
        dest="morph_op",
        choices=["close", "open", "close_then_open"],
        default=None,
        help="Morphology operation (optional)",
    )
    parser.add_argument(
        "--morph-kernel",
        dest="morph_kernel",
        type=int,
        default=None,
        help="Morphology kernel size (odd, optional)",
    )
    parser.add_argument(
        "--morph-iters",
        dest="morph_iters",
        type=int,
        default=None,
        help="Morphology iterations (optional)",
    )
    parser.add_argument(
        "--edges",
        dest="edges",
        type=int,
        choices=[0, 1],
        default=0,
        help="Enable edge overlay (0 or 1)",
    )
    parser.add_argument(
        "--edge-low",
        dest="edge_low",
        type=int,
        default=60,
        help="Canny low threshold",
    )
    parser.add_argument(
        "--edge-high",
        dest="edge_high",
        type=int,
        default=140,
        help="Canny high threshold",
    )
    parser.add_argument(
        "--edge-thickness",
        dest="edge_thickness",
        type=int,
        default=1,
        help="Edge thickness (dilation radius)",
    )
    parser.add_argument(
        "--edge-apply-on",
        dest="edge_apply_on",
        choices=["luma", "binary"],
        default="luma",
        help="Edge detection input (luma or binary)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = sys.argv[1:] if argv is None else argv
    if not args:
        parser.print_help()
        return 0

    parsed = parser.parse_args(args)

    threshold_step = ThresholdStep(
        mode=parsed.mode,
        invert=bool(parsed.invert),
        bias=parsed.bias,
        block_size=parsed.block_size,
    )
    pipeline_steps = [
        GrayscaleStep(),
        CLAHEContrastStep(),
        GaussianBlurStep(),
        threshold_step,
    ]

    use_morphology = any(
        value is not None
        for value in (parsed.morph_op, parsed.morph_kernel, parsed.morph_iters)
    )
    if use_morphology:
        morph_op = parsed.morph_op or "close"
        morph_kernel = parsed.morph_kernel if parsed.morph_kernel is not None else 3
        morph_iters = parsed.morph_iters if parsed.morph_iters is not None else 1
        pipeline_steps.append(
            MorphologyStep(
                operation=morph_op,
                kernel_size=morph_kernel,
                iterations=morph_iters,
            )
        )

    if parsed.edges == 1:
        pipeline_steps.append(
            EdgesStep(
                low=parsed.edge_low,
                high=parsed.edge_high,
                thickness=parsed.edge_thickness,
                apply_on=parsed.edge_apply_on,
            )
        )

    pipeline = Pipeline(pipeline_steps)

    image = load_image(parsed.input_path)
    result = pipeline.run(image)
    save_image(parsed.output_path, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
