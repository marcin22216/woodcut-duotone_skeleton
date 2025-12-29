"""Background pipeline execution with debounce."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, QThread, QTimer, Signal

from woodcut_duotone.core.pipeline import Pipeline


class PipelineWorker(QObject):
    finished = Signal(int, object)
    failed = Signal(int, str)

    def __init__(self, image, pipeline: Pipeline, revision: int) -> None:
        super().__init__()
        self._image = image
        self._pipeline = pipeline
        self._revision = revision

    def run(self) -> None:
        try:
            result = self._pipeline.run(self._image)
        except Exception as exc:  # pragma: no cover - GUI error handling
            self.failed.emit(self._revision, str(exc))
        else:
            self.finished.emit(self._revision, result)


class DebouncedPipelineRunner(QObject):
    result_ready = Signal(int, object)
    error = Signal(int, str)

    def __init__(self, delay_ms: int = 200, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._start)
        self._pending: Optional[tuple] = None
        self._running = False
        self._queued = False
        self._thread: Optional[QThread] = None

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
        worker.finished.connect(self._on_finished)
        worker.failed.connect(self._on_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        self._thread = thread
        thread.start()

    def _on_finished(self, result) -> None:
        self._running = False
        self.result_ready.emit(result)
        if self._queued:
            self._queued = False
            self._timer.start()

    def _on_failed(self, message: str) -> None:
        self._running = False
        self.error.emit(message)
        if self._queued:
            self._queued = False
            self._timer.start()
