# Development Log (CHANGELOG_DEV)

This is a running engineering diary. It must be updated after every task.

## 2025-12-29 — Project bootstrap
### Done
- Created repository skeleton (folders only) plus README and development rules.
- Captured GUI requirements: two previews, reorderable steps, standard Undo/Redo, single-file workflow.

### Issues / risks
- Golden image tests can become flaky if tolerances/metrics are poorly chosen.
- GUI responsiveness requires debouncing + background processing.

### Decisions
- Target GUI: PySide6 (Qt).
- Output style: duotone / woodcut-like pipeline with step-based processing.

### Next
- Stage 1: create `pyproject.toml`, package skeleton, and a first passing test suite (imports + pipeline placeholder).

## 2025-12-29 — Stage 1 bootstrap (package + tests)
### Done
- Added `pyproject.toml` with src-layout packaging, runtime deps, and dev deps.
- Created minimal package with `main()` entry point printing a bootstrap message.
- Added a basic pytest to cover imports and a no-error `main()` run.

### Issues / risks
- None encountered.

### Decisions
- Used `setuptools` with `src`-layout package discovery for editable installs.

### Next
- Stage 2: define initial pipeline scaffolding (no GUI yet) with tests.

## 2025-12-29 — Stage 2 core pipeline + step abstraction
### Done
- Added core pipeline and step abstractions with a minimal, pass-through `apply()`.
- Introduced `BaseStep` with parameter storage helpers.
- Added tests covering ordering, skipping disabled steps, pass-through behavior, and param handling.

### Issues / risks
- None encountered.

### Decisions
- Pipeline passes `step.params` when available to keep steps lightweight and future-GUI friendly.
- `BaseStep` implements a no-op `apply()` so it is instantiable in tests and can serve as a simple base.

### Next
- Stage 3: add first concrete processing step modules and fixtures (still no GUI).

## 2025-12-29 — Stage 3 IO + image conversions
### Done
- Added IO helpers for loading/saving RGB uint8 images via PIL with validation.
- Added explicit RGB/BGR conversions and RGB-to-QImage conversion for Qt previews.
- Added IO tests with a small fixture image and roundtrip coverage.

### Issues / risks
- QImage wraps raw buffers; `rgb_to_qimage` copies the data to avoid lifetime issues.

### Decisions
- Internal image format is RGB uint8 ndarray `(H, W, 3)` with explicit color conversions.
- PIL is the only load/save path to keep format support consistent.

### Next
- Stage 4: first real processing step (e.g., GrayscaleStep) with a golden test.

## 2025-12-29 — Stage 4 GrayscaleStep + golden test
### Done
- Added `GrayscaleStep` with explicit RGB grayscale conversion and input validation.
- Added unit tests, a pipeline smoke test, and a golden test backed by a small PNG fixture.
- Committed golden output in `tests/fixtures/golden/test_8x8_grayscale.png`.

### Issues / risks
- Grayscale uses explicit RGB weights; swapping to OpenCV later should regenerate the golden fixture.

### Decisions
- Used numpy-based RGB weights to avoid BGR ambiguity and keep output deterministic.
- Golden fixtures live under `tests/fixtures/golden/`; update by rerunning the grayscale conversion on the source fixture and overwriting the PNG.

### Next
- Stage 5: add a contrast/threshold step (e.g., CLAHE or basic threshold) with a golden test.

## 2025-12-29 — Stage 5 CLAHE contrast step + golden test
### Done
- Added `CLAHEContrastStep` with `clip_limit` and `tile_grid_size` params and validation.
- Implemented LAB L-channel CLAHE via OpenCV with RGB-in/RGB-out handling.
- Added unit tests, a pipeline smoke test, and a golden fixture `tests/fixtures/golden/test_8x8_clahe.png`.

### Issues / risks
- CLAHE output can vary across OpenCV versions; if golden mismatches, regenerate from fixture with the same parameters and OpenCV version.

### Decisions
- CLAHE runs on the L channel in LAB to preserve color while improving local contrast.
- Golden fixtures live under `tests/fixtures/golden/`; update by rerunning the step on `tests/fixtures/images/test_8x8.png`.

### Next
- Stage 6: add a blur or threshold step (Gaussian/threshold) with golden tests.

## 2025-12-29 — Stage 6 Gaussian blur step + tests
### Done
- Added `GaussianBlurStep` with a `strength` parameter mapped to odd kernel sizes.
- Added unit tests, a pipeline smoke test, and a golden fixture `tests/fixtures/golden/test_8x8_blur.png`.
- Pinned numpy to `>=1.26,<3` to reduce version conflicts with OpenCV.

### Issues / risks
- OpenCV versions may produce slight numeric differences in blur; if golden mismatches, regenerate using the same parameters and OpenCV build.

### Decisions
- Blur runs directly on RGB arrays since Gaussian blur is color-space neutral.
- `strength=0` returns a copy of the input to guarantee a no-op without in-place mutation.

### Next
- Stage 7: Threshold step (Otsu + optional adaptive) with golden tests.

## 2025-12-29 — Stage 7 Threshold step + runner
### Done
- Added `ThresholdStep` with Otsu and adaptive modes, `invert`, `bias`, and `block_size` parameters.
- Added unit tests, golden tests for Otsu + adaptive, and pipeline smoke coverage.
- Added `scripts/run_pipeline_on_image.py` for manual pipeline testing and documented it in `README.md`.
- Added golden fixtures: `tests/fixtures/golden/test_8x8_threshold_otsu.png` and `tests/fixtures/golden/test_8x8_threshold_adaptive.png`.

### Issues / risks
- Threshold output may vary slightly across OpenCV builds; if a golden mismatch occurs, regenerate from the fixture with the same parameters and OpenCV version.

### Decisions
- Grayscale conversion uses explicit RGB weights before thresholding to avoid RGB/BGR ambiguity.
- Otsu bias shifts the computed threshold after Otsu (clamped 0..255); adaptive bias maps to `C = -bias` so positive bias raises the effective threshold.
- Manual runner applies the default pipeline (grayscale -> CLAHE -> blur -> threshold) with CLI overrides for threshold parameters.

### Next
- Stage 8: Morphology step (open/close) and edge enhancement steps with golden tests.

## 2025-12-29 — Stage 8 Morphology step + runner updates
### Done
- Added `MorphologyStep` with `operation`, `kernel_size`, and `iterations` params and binary cleanup logic.
- Added unit tests, pipeline smoke coverage, and a golden fixture `tests/fixtures/golden/test_8x8_morphology.png`.
- Extended the manual runner to support optional morphology arguments and documented usage in `README.md`.

### Issues / risks
- Morphology output may vary across OpenCV builds; regenerate the golden fixture if a mismatch occurs.

### Decisions
- Morphology operates on the inferred ink mask (black pixels) by inverting to a foreground mask, then inverting back to binary RGB.
- `kernel_size` must be odd and within 1..31; `iterations` within 1..5 for GUI-friendly sliders.
- Golden fixture is produced from the pipeline: grayscale -> CLAHE -> blur -> threshold -> morphology.

### Next
- Stage 9: Edge enhancement step (EdgesStep) with unit and golden tests.

## 2025-12-29 — Stage 9 Edges step + runner updates
### Done
- Added `EdgesStep` (Canny) with `low`, `high`, `thickness`, and `apply_on` parameters.
- Added unit tests, pipeline smoke coverage, and a golden fixture `tests/fixtures/golden/test_8x8_edges.png`.
- Extended the manual runner with optional edge overlays and documented usage in `README.md`.

### Issues / risks
- Edge output may vary with OpenCV version; regenerate the golden fixture if a mismatch occurs.

### Decisions
- Edges are computed on either luma or binary input, then overlaid as black ink on the original RGB.
- `thickness` uses dilation with an elliptical kernel sized by `2*thickness+1`.
- Golden fixture is produced from the pipeline: grayscale -> CLAHE -> blur -> threshold -> morphology -> edges.

### Next
- Stage 10: GUI v0 (two previews, open/save, and step controls).

## 2025-12-29 — Stage 10 GUI v0
### Done
- Added GUI v0 with two live previews, open/save actions, step toggles, and parameter controls.
- Implemented debounced background processing worker for responsive preview updates.
- Added `AppState` with undo/redo snapshots and unit tests for state logic.
- Updated app entrypoint to launch GUI via `--gui` and documented GUI usage in `README.md`.

### Issues / risks
- GUI controls are minimal and do not yet support step reordering or preset management.
- Undo/redo tracks parameter/enabled changes but not image history.

### Decisions
- Debounce uses a short timer and background thread per run to keep the UI responsive.
- State snapshots only include step params/enabled flags for now.

### Next
- Stage 11: step reordering, richer Undo/Redo semantics, and presets.
