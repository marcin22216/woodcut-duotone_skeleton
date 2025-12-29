# CODEx_RULES — Non-negotiable development rules

This document MUST be read before starting any new development stage or task.

## 1. Scope and goals
We are building a desktop app that converts images into a two-color (duotone) woodcut/linocut-like style through a step-based pipeline.

The application MUST provide:
- GUI with two live previews (original + processed)
- per-step controls (buttons + sliders)
- suggested pipeline order, but user-reorderable
- Undo/Redo behaving like in common creative apps (revert the most recent user action)
- previous/next step navigation
- open from disk + save anywhere with any filename

## 2. Repository discipline
- Do not place application code outside `src/woodcut_duotone/`.
- Each processing step is a separate module in `src/woodcut_duotone/core/steps/`.
- IO conversion utilities live in `src/woodcut_duotone/io/`.
- GUI code lives in `src/woodcut_duotone/gui/`.
- Tests live in `tests/` and must be runnable with `pytest`.

## 3. Tests-first requirement (mandatory)
For EVERY stage:
1) Write tests FIRST (or in the same PR) for the new functionality.
2) Implement the feature.
3) Ensure ALL tests pass.
4) Only then proceed to the next stage.

No stage is considered “done” until:
- unit tests pass (`pytest`)
- minimal coverage exists for new logic
- relevant golden tests are added/updated when output is image-based

## 4. Golden tests policy
If a processing step affects image output, add at least one golden test:
- input image in `tests/fixtures/images/`
- expected output in `tests/fixtures/golden/`
- comparison uses a robust metric (e.g., pixel diff with tolerance or SSIM) to avoid flakiness

Golden outputs MUST be small and stable (resize fixtures if needed).

## 5. GUI performance and correctness
- Any slider change must update preview with debounce/throttle.
- GUI must not freeze during processing (use a worker/threading strategy).
- Always handle color space correctly (OpenCV BGR vs RGB).

## 6. Logging and errors
- Any user-facing error (load/save/processing) must be caught and presented in GUI.
- Use structured logging in code paths where failures are likely (I/O, conversions).

## 7. Documentation and changelog (mandatory)
A development log MUST be updated for EVERY assigned task:
- Update `CHANGELOG_DEV.md` at the end of each task with:
  - what was done
  - what failed / what was tricky
  - how it was resolved
  - what remains

No task is complete if `CHANGELOG_DEV.md` is not updated.

## 8. Incremental stages
Work must be delivered in small, verifiable increments:
- one step at a time (e.g., threshold step)
- one GUI feature at a time (e.g., Undo/Redo)
Each increment must be test-backed.

## 9. Definition of Done
A stage is DONE only if:
- tests pass
- GUI runs (if applicable for that stage)
- changelog is updated
- code is formatted and linted (if tooling present)

End of rules.
