"""Background pipeline execution with debounce."""

from __future__ import annotations

from typing import Optional

import logging

import numpy as np

from PySide6.QtCore import QObject, QThread, QTimer, Signal

from woodcut_duotone.core.pipeline import Pipeline


class PipelineWorker(QObject):
    completed = Signal(int, object, object)

    def __init__(self, image, pipeline: Pipeline, revision: int) -> None:
        super().__init__()
        self._image = image
        self._pipeline = pipeline
        self._revision = revision

    def run(self) -> None:
        logging.getLogger(__name__).debug(
            "WORKER start: rev=%s shape=%s dtype=%s",
            self._revision,
            getattr(self._image, "shape", None),
            getattr(self._image, "dtype", None),
        )
        try:
            result = self._pipeline.run(self._image)
        except Exception as exc:  # pragma: no cover - GUI error handling
            logging.getLogger(__name__).debug(
                "WORKER finish: rev=%s out_shape=%s out_dtype=%s out_min=%s out_max=%s err=%s",
                self._revision,
                None,
                None,
                None,
                None,
                exc,
            )
            self.completed.emit(self._revision, None, str(exc))
        else:
            out_min = int(np.min(result)) if isinstance(result, np.ndarray) else None
            out_max = int(np.max(result)) if isinstance(result, np.ndarray) else None
            logging.getLogger(__name__).debug(
                "WORKER finish: rev=%s out_shape=%s out_dtype=%s out_min=%s out_max=%s err=%s",
                self._revision,
                getattr(result, "shape", None),
                getattr(result, "dtype", None),
                out_min,
                out_max,
                None,
            )
            self.completed.emit(self._revision, result, None)


class DebouncedPipelineRunner(QObject):
    completed = Signal(int, object, object)

    def __init__(self, delay_ms: int = 200, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._start)
        self._pending: Optional[tuple] = None
        self._running = False
        self._queued = False
        self._thread: Optional[QThread] = None
        self._worker: Optional[PipelineWorker] = None

    def schedule(self, image, pipeline: Pipeline, revision: int) -> None:
        self._pending = (image.copy(), pipeline, revision)
        self._timer.start()

    def _start(self) -> None:
        if self._running:
            self._queued = True
            return
        if self._pending is None:
            return
        image, pipeline, revision = self._pending
        self._pending = None
        self._running = True

        thread = QThread()
        worker = PipelineWorker(image, pipeline, revision)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.completed.connect(self._on_completed)
        worker.completed.connect(thread.quit)
        worker.completed.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        self._thread = thread
        self._worker = worker
        thread.start()

    def _on_completed(self, revision: int, result, error: str | None) -> None:
        self._running = False
        self.completed.emit(revision, result, error)
        if self._queued:
            self._queued = False
            self._timer.start()
