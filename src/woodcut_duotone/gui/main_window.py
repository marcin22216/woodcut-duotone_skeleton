"""Main application window for GUI v0."""

from __future__ import annotations

import logging
import math
from pathlib import Path

import numpy as np

from PySide6.QtCore import QPointF, QRectF, QSizeF, Qt, Signal
from PySide6.QtGui import QAction, QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from woodcut_duotone.core.pipeline import Pipeline
from woodcut_duotone.core.steps import (
    CLAHEContrastStep,
    EdgesStep,
    GaussianBlurStep,
    GrayscaleStep,
    MorphologyStep,
    ThresholdStep,
)
from woodcut_duotone.gui.state import (
    AppState,
    KNOWN_STEPS,
    RenderScheduler,
    build_step_names,
    should_apply_revision,
)
from woodcut_duotone.gui.worker import DebouncedPipelineRunner
from woodcut_duotone.io import load_image, rgb_to_qimage, save_image
from woodcut_duotone.io.preset_io import (
    apply_preset_dict,
    load_preset_file,
    save_preset_file,
    state_to_preset_dict,
)


class StepListWidget(QListWidget):
    orderChanged = Signal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)

    def dropEvent(self, event) -> None:  # type: ignore[override]
        super().dropEvent(event)
        self.orderChanged.emit(self.current_order())

    def current_order(self) -> list[str]:
        order: list[str] = []
        for index in range(self.count()):
            item = self.item(index)
            step_name = item.data(Qt.ItemDataRole.UserRole)
            if step_name:
                order.append(step_name)
        return order


class ImageView(QWidget):
    roiChanged = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pixmap: QPixmap | None = None
        self._zoom = 1.0
        self._pan = QPointF(0.0, 0.0)
        self._panning = False
        self._last_pos = QPointF(0.0, 0.0)
        self._roi_enabled = False
        self._roi_selectable = False
        self._roi_dragging = False
        self._roi_drag_start = QPointF(0.0, 0.0)
        self._roi_drag_rect: QRectF | None = None
        self._roi_image_rect: QRectF | None = None
        self._min_zoom = 0.25
        self._max_zoom = 8.0
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

    def set_image(self, image, reset_view: bool = False) -> None:
        self._pixmap = QPixmap.fromImage(image) if image is not None else None
        if reset_view:
            self.reset_view()
        self.update()

    def reset_view(self) -> None:
        self._zoom = 1.0
        self._pan = QPointF(0.0, 0.0)
        self.update()

    def set_roi_selectable(self, selectable: bool) -> None:
        self._roi_selectable = selectable

    def set_roi_enabled(self, enabled: bool) -> None:
        self._roi_enabled = enabled
        self._roi_dragging = False
        self._roi_drag_rect = None
        self.update()
        self.roiChanged.emit()

    def clear_roi(self) -> None:
        self._roi_image_rect = None
        self._roi_dragging = False
        self._roi_drag_rect = None
        self.update()
        self.roiChanged.emit()

    def get_roi_rect(self) -> QRectF | None:
        if not self._roi_enabled or self._roi_image_rect is None:
            return None
        return QRectF(self._roi_image_rect)

    def _fit_scale(self) -> float:
        if self._pixmap is None:
            return 1.0
        width = self._pixmap.width()
        height = self._pixmap.height()
        if width <= 0 or height <= 0:
            return 1.0
        return min(self.width() / width, self.height() / height)

    def _target_rect(self) -> tuple[QRectF, float] | None:
        if self._pixmap is None:
            return None
        scale = self._fit_scale() * self._zoom
        if scale <= 0:
            return None
        center = QPointF(self.rect().center())
        size = QSizeF(
            self._pixmap.width() * scale,
            self._pixmap.height() * scale,
        )
        top_left = QPointF(
            center.x() - size.width() / 2,
            center.y() - size.height() / 2,
        )
        target = QRectF(top_left + self._pan, size)
        return target, scale

    def _view_to_image(self, point: QPointF) -> QPointF | None:
        target_data = self._target_rect()
        if target_data is None or self._pixmap is None:
            return None
        target, scale = target_data
        if scale <= 0:
            return None
        x = (point.x() - target.left()) / scale
        y = (point.y() - target.top()) / scale
        x = max(0.0, min(x, float(self._pixmap.width())))
        y = max(0.0, min(y, float(self._pixmap.height())))
        return QPointF(x, y)

    def _image_to_view(self, rect: QRectF) -> QRectF | None:
        target_data = self._target_rect()
        if target_data is None:
            return None
        target, scale = target_data
        top_left = QPointF(
            target.left() + rect.left() * scale,
            target.top() + rect.top() * scale,
        )
        size = QSizeF(rect.width() * scale, rect.height() * scale)
        return QRectF(top_left, size)

    def _commit_roi_from_view(self, rect: QRectF) -> None:
        if self._pixmap is None:
            return
        start = self._view_to_image(rect.topLeft())
        end = self._view_to_image(rect.bottomRight())
        if start is None or end is None:
            return
        x0 = min(start.x(), end.x())
        x1 = max(start.x(), end.x())
        y0 = min(start.y(), end.y())
        y1 = max(start.y(), end.y())
        if x1 - x0 < 1.0 or y1 - y0 < 1.0:
            self._roi_image_rect = None
        else:
            self._roi_image_rect = QRectF(x0, y0, x1 - x0, y1 - y0)
        self.roiChanged.emit()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#222"))
        if self._pixmap is None:
            return
        target_data = self._target_rect()
        if target_data is None:
            return
        target, _scale = target_data
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.drawPixmap(target, self._pixmap)
        if self._roi_selectable and self._roi_enabled:
            rect = self._roi_drag_rect
            if rect is None and self._roi_image_rect is not None:
                rect = self._image_to_view(self._roi_image_rect)
            if rect is not None:
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                pen = QPen(QColor(255, 200, 0, 220))
                pen.setWidth(2)
                painter.setPen(pen)
                painter.setBrush(QColor(255, 200, 0, 40))
                painter.drawRect(rect.normalized())

    def wheelEvent(self, event) -> None:  # type: ignore[override]
        if self._pixmap is None:
            return
        delta = event.angleDelta().y()
        if delta == 0:
            return
        steps = delta / 120.0
        factor = 1.1**steps
        new_zoom = max(self._min_zoom, min(self._max_zoom, self._zoom * factor))
        if new_zoom == self._zoom:
            return
        center = QPointF(self.rect().center())
        scale = self._fit_scale() * self._zoom
        new_scale = self._fit_scale() * new_zoom
        cursor = event.position()
        if scale > 0:
            image_pos = (cursor - center - self._pan) / scale
            self._pan = cursor - center - image_pos * new_scale
        self._zoom = new_zoom
        self.update()

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if self._pixmap is None:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            if self._roi_selectable and self._roi_enabled:
                self._roi_dragging = True
                self._roi_drag_start = event.position()
                self._roi_drag_rect = QRectF(self._roi_drag_start, self._roi_drag_start)
                self.update()
                return
            self._panning = True
            self._last_pos = event.position()
            return
        if event.button() == Qt.MouseButton.RightButton and self._roi_selectable:
            self._panning = True
            self._last_pos = event.position()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if self._roi_dragging:
            self._roi_drag_rect = QRectF(self._roi_drag_start, event.position())
            self.update()
            return
        if not self._panning or self._zoom <= 1.0:
            return
        current = event.position()
        delta = current - self._last_pos
        self._pan += delta
        self._last_pos = current
        self.update()

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton and self._roi_dragging:
            self._roi_dragging = False
            if self._roi_drag_rect is not None:
                self._commit_roi_from_view(self._roi_drag_rect.normalized())
            self._roi_drag_rect = None
            self.update()
            return
        if event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            self._panning = False

    def mouseDoubleClickEvent(self, event) -> None:  # type: ignore[override]
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self.reset_view()

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        if (
            event.key() == Qt.Key.Key_Escape
            and self._roi_selectable
            and self._roi_enabled
        ):
            self.clear_roi()
            return
        super().keyPressEvent(event)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Woodcut Duotone")

        self.state = AppState()
        self._runner = DebouncedPipelineRunner()
        self._runner.completed.connect(self._on_worker_done)

        self._original_qimage = None
        self._preview_qimage = None
        self._preview_image_rgb = None
        self._preview_snapshot_qimage = None
        self._compare_snapshot = False
        self._expected_revision = 0
        self._last_ignored_revision: int | None = None
        self._suppress_updates = False
        self._render_scheduler = RenderScheduler()
        self._render_in_flight = False
        self._pending_render = False

        self._step_items: dict[str, QListWidgetItem] = {}
        self._roi_by_revision: dict[int, tuple[int, int, int, int] | None] = {}

        self._build_ui()
        self._apply_state_to_controls()
        self._update_action_states()

    def _build_ui(self) -> None:
        self._toolbar = QToolBar("Main")
        self.addToolBar(self._toolbar)

        self._open_action = QAction("Open", self)
        self._open_action.triggered.connect(self._open_image)
        self._toolbar.addAction(self._open_action)

        self._save_action = QAction("Save As", self)
        self._save_action.triggered.connect(self._save_image)
        self._toolbar.addAction(self._save_action)

        self._save_preset_action = QAction("Save Preset...", self)
        self._save_preset_action.triggered.connect(self._save_preset)
        self._toolbar.addAction(self._save_preset_action)

        self._load_preset_action = QAction("Load Preset...", self)
        self._load_preset_action.triggered.connect(self._load_preset)
        self._toolbar.addAction(self._load_preset_action)

        self._toolbar.addSeparator()

        self._undo_action = QAction("Undo", self)
        self._undo_action.triggered.connect(self._undo)
        self._toolbar.addAction(self._undo_action)

        self._redo_action = QAction("Redo", self)
        self._redo_action.triggered.connect(self._redo)
        self._toolbar.addAction(self._redo_action)

        self._reset_action = QAction("Reset", self)
        self._reset_action.triggered.connect(self._reset_state)
        self._toolbar.addAction(self._reset_action)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)

        left_panel = self._build_left_panel()
        layout.addWidget(left_panel, 1)

        right_panel = self._build_preview_panel()
        layout.addWidget(right_panel, 2)

        self.setCentralWidget(central)

    def _build_left_panel(self) -> QWidget:
        container = QWidget()
        left_layout = QVBoxLayout(container)
        left_layout.setContentsMargins(0, 0, 0, 0)

        steps_group = QGroupBox("Steps")
        steps_layout = QVBoxLayout(steps_group)
        self._step_list = StepListWidget()
        self._step_list.orderChanged.connect(self._on_steps_reordered)
        self._step_list.itemChanged.connect(self._on_step_checkbox_changed)
        steps_layout.addWidget(self._step_list)
        steps_hint = QLabel("Drag steps to reorder the pipeline.")
        steps_hint.setWordWrap(True)
        steps_layout.addWidget(steps_hint)
        left_layout.addWidget(steps_group)

        left_layout.addWidget(self._build_threshold_group())
        left_layout.addWidget(self._build_morphology_group())
        left_layout.addWidget(self._build_edges_group())

        left_layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(container)
        scroll.setMinimumWidth(280)
        return scroll

    def _build_threshold_group(self) -> QGroupBox:
        group = QGroupBox("Threshold")
        layout = QFormLayout(group)

        self._threshold_mode = QComboBox()
        self._threshold_mode.addItems(["otsu", "adaptive"])
        self._threshold_mode.currentIndexChanged.connect(self._on_controls_changed)
        layout.addRow("Mode", self._threshold_mode)

        self._threshold_bias_slider, self._threshold_bias_label = self._make_slider(
            -50, 50, 0
        )
        self._threshold_bias_slider.valueChanged.connect(
            lambda value: self._on_slider_changed(value, self._threshold_bias_label)
        )
        layout.addRow("Bias", self._wrap_slider(self._threshold_bias_slider))
        layout.addRow("", self._threshold_bias_label)

        self._threshold_invert = QCheckBox("Invert")
        self._threshold_invert.stateChanged.connect(self._on_controls_changed)
        layout.addRow(self._threshold_invert)

        self._threshold_block_slider, self._threshold_block_label = self._make_slider(
            7, 71, 31, step=2
        )
        self._threshold_block_slider.valueChanged.connect(
            lambda value: self._on_odd_slider_changed(
                value, self._threshold_block_slider, self._threshold_block_label
            )
        )
        layout.addRow("Block size", self._wrap_slider(self._threshold_block_slider))
        layout.addRow("", self._threshold_block_label)

        return group

    def _build_morphology_group(self) -> QGroupBox:
        group = QGroupBox("Morphology")
        layout = QFormLayout(group)

        self._morph_op = QComboBox()
        self._morph_op.addItems(["close", "open", "close_then_open"])
        self._morph_op.currentIndexChanged.connect(self._on_controls_changed)
        layout.addRow("Operation", self._morph_op)

        self._morph_kernel_slider, self._morph_kernel_label = self._make_slider(
            1, 31, 3, step=2
        )
        self._morph_kernel_slider.valueChanged.connect(
            lambda value: self._on_odd_slider_changed(
                value, self._morph_kernel_slider, self._morph_kernel_label
            )
        )
        layout.addRow("Kernel", self._wrap_slider(self._morph_kernel_slider))
        layout.addRow("", self._morph_kernel_label)

        self._morph_iters_slider, self._morph_iters_label = self._make_slider(1, 5, 1)
        self._morph_iters_slider.valueChanged.connect(
            lambda value: self._on_slider_changed(value, self._morph_iters_label)
        )
        layout.addRow("Iterations", self._wrap_slider(self._morph_iters_slider))
        layout.addRow("", self._morph_iters_label)

        return group

    def _build_edges_group(self) -> QGroupBox:
        group = QGroupBox("Edges")
        layout = QFormLayout(group)

        self._edges_apply_on = QComboBox()
        self._edges_apply_on.addItems(["luma", "binary"])
        self._edges_apply_on.currentIndexChanged.connect(self._on_controls_changed)
        layout.addRow("Apply on", self._edges_apply_on)

        self._edges_low_slider, self._edges_low_label = self._make_slider(0, 255, 60)
        self._edges_low_slider.valueChanged.connect(
            lambda value: self._on_slider_changed(value, self._edges_low_label)
        )
        layout.addRow("Low", self._wrap_slider(self._edges_low_slider))
        layout.addRow("", self._edges_low_label)

        self._edges_high_slider, self._edges_high_label = self._make_slider(0, 255, 140)
        self._edges_high_slider.valueChanged.connect(
            lambda value: self._on_slider_changed(value, self._edges_high_label)
        )
        layout.addRow("High", self._wrap_slider(self._edges_high_slider))
        layout.addRow("", self._edges_high_label)

        self._edges_thickness_slider, self._edges_thickness_label = self._make_slider(
            1, 5, 1
        )
        self._edges_thickness_slider.valueChanged.connect(
            lambda value: self._on_slider_changed(value, self._edges_thickness_label)
        )
        layout.addRow("Thickness", self._wrap_slider(self._edges_thickness_slider))
        layout.addRow("", self._edges_thickness_label)

        return group

    def _build_preview_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        self._original_label = QLabel("Original")
        self._original_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._original_image_label = ImageView()
        self._original_image_label.setMinimumSize(480, 360)

        original_box = QVBoxLayout()
        original_box.setAlignment(Qt.AlignmentFlag.AlignTop)
        original_box.addWidget(self._original_label)
        original_box.addWidget(self._original_image_label)

        self._preview_label = QLabel("Preview")
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_image_label = ImageView()
        self._preview_image_label.setMinimumSize(480, 360)
        self._preview_image_label.set_roi_selectable(True)
        self._preview_image_label.roiChanged.connect(self._on_preview_roi_changed)

        preview_box = QVBoxLayout()
        preview_box.setAlignment(Qt.AlignmentFlag.AlignTop)
        snapshot_controls = QHBoxLayout()
        self._snapshot_button = QPushButton("Snapshot")
        self._snapshot_button.clicked.connect(self._take_snapshot)
        self._compare_toggle = QCheckBox("Compare")
        self._compare_toggle.toggled.connect(self._toggle_compare)
        self._clear_snapshot_button = QPushButton("Clear snapshot")
        self._clear_snapshot_button.clicked.connect(self._clear_snapshot)
        snapshot_controls.addWidget(self._snapshot_button)
        snapshot_controls.addWidget(self._compare_toggle)
        snapshot_controls.addWidget(self._clear_snapshot_button)
        snapshot_controls.addStretch(1)
        preview_box.addLayout(snapshot_controls)
        roi_controls = QHBoxLayout()
        self._roi_preview_toggle = QCheckBox("ROI preview")
        self._roi_preview_toggle.toggled.connect(self._on_roi_toggled)
        self._roi_clear_button = QPushButton("Clear ROI")
        self._roi_clear_button.clicked.connect(self._clear_roi)
        roi_controls.addWidget(self._roi_preview_toggle)
        roi_controls.addWidget(self._roi_clear_button)
        roi_controls.addStretch(1)
        preview_box.addLayout(roi_controls)
        preview_box.addWidget(self._preview_label)
        preview_box.addWidget(self._preview_image_label)

        row = QHBoxLayout()
        row.setAlignment(Qt.AlignmentFlag.AlignTop)
        row.addLayout(original_box, 1)
        row.addLayout(preview_box, 1)

        layout.addLayout(row)
        layout.addStretch(1)

        return panel

    def _make_slider(self, minimum: int, maximum: int, value: int, step: int = 1):
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(minimum)
        slider.setMaximum(maximum)
        slider.setValue(value)
        slider.setSingleStep(step)
        slider.setPageStep(step)
        label = QLabel(str(value))
        return slider, label

    def _wrap_slider(self, slider: QSlider) -> QWidget:
        wrapper = QWidget()
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(slider)
        return wrapper

    def _apply_state_to_controls(self) -> None:
        self._suppress_updates = True

        self._populate_step_list()

        threshold_params = self.state.params["Threshold"]
        self._threshold_mode.setCurrentText(threshold_params["mode"])
        self._threshold_bias_slider.setValue(threshold_params["bias"])
        self._threshold_bias_label.setText(str(threshold_params["bias"]))
        self._threshold_invert.setChecked(threshold_params["invert"])
        self._threshold_block_slider.setValue(threshold_params["block_size"])
        self._threshold_block_label.setText(str(threshold_params["block_size"]))
        self._update_threshold_controls()

        morph_params = self.state.params["Morphology"]
        self._morph_op.setCurrentText(morph_params["operation"])
        self._morph_kernel_slider.setValue(morph_params["kernel_size"])
        self._morph_kernel_label.setText(str(morph_params["kernel_size"]))
        self._morph_iters_slider.setValue(morph_params["iterations"])
        self._morph_iters_label.setText(str(morph_params["iterations"]))

        edges_params = self.state.params["Edges"]
        self._edges_apply_on.setCurrentText(edges_params["apply_on"])
        self._edges_low_slider.setValue(edges_params["low"])
        self._edges_low_label.setText(str(edges_params["low"]))
        self._edges_high_slider.setValue(edges_params["high"])
        self._edges_high_label.setText(str(edges_params["high"]))
        self._edges_thickness_slider.setValue(edges_params["thickness"])
        self._edges_thickness_label.setText(str(edges_params["thickness"]))

        self._suppress_updates = False

    def _sync_state_from_controls(self) -> None:
        self.state.enabled = {}
        for index in range(self._step_list.count()):
            item = self._step_list.item(index)
            step_name = item.data(Qt.ItemDataRole.UserRole)
            if not step_name:
                continue
            self.state.enabled[step_name] = (
                item.checkState() == Qt.CheckState.Checked
            )

        self.state.params["Threshold"] = {
            "mode": self._threshold_mode.currentText(),
            "invert": self._threshold_invert.isChecked(),
            "bias": int(self._threshold_bias_slider.value()),
            "block_size": int(self._threshold_block_slider.value()),
        }
        self.state.params["Morphology"] = {
            "operation": self._morph_op.currentText(),
            "kernel_size": int(self._morph_kernel_slider.value()),
            "iterations": int(self._morph_iters_slider.value()),
        }
        self.state.params["Edges"] = {
            "low": int(self._edges_low_slider.value()),
            "high": int(self._edges_high_slider.value()),
            "thickness": int(self._edges_thickness_slider.value()),
            "apply_on": self._edges_apply_on.currentText(),
        }

    def _on_controls_changed(self) -> None:
        if self._suppress_updates:
            return
        logger = logging.getLogger(__name__)
        logger.info(
            "CONTROLS changed: edges low=%s high=%s thickness=%s apply_on=%s thr_mode=%s block_size=%s",
            self._edges_low_slider.value(),
            self._edges_high_slider.value(),
            self._edges_thickness_slider.value(),
            self._edges_apply_on.currentText(),
            self._threshold_mode.currentText(),
            self._threshold_block_slider.value(),
        )
        self.state.push_undo()
        self._sync_state_from_controls()
        logger.info(
            "EDGES UI->STATE low=%s high=%s thickness=%s apply_on=%s",
            self.state.params["Edges"]["low"],
            self.state.params["Edges"]["high"],
            self.state.params["Edges"]["thickness"],
            self.state.params["Edges"]["apply_on"],
        )
        self._update_threshold_controls()
        self._update_action_states()
        self._schedule_preview()

    def _on_slider_changed(self, value: int, label: QLabel) -> None:
        if self._suppress_updates:
            return
        label.setText(str(value))
        self._on_controls_changed()

    def _on_odd_slider_changed(
        self, value: int, slider: QSlider, label: QLabel
    ) -> None:
        if self._suppress_updates:
            return
        if value % 2 == 0:
            adjusted = value - 1 if value > slider.minimum() else value + 1
            self._suppress_updates = True
            slider.setValue(adjusted)
            self._suppress_updates = False
            value = adjusted
        label.setText(str(value))
        self._on_controls_changed()

    def _build_pipeline(self) -> Pipeline:
        params = self.state.params
        enabled = self.state.enabled
        step_names = build_step_names(self.state.step_order, enabled)
        logging.getLogger(__name__).debug("PIPELINE steps=%s", step_names)
        logging.getLogger(__name__).debug(
            "Edges enabled=%s params=%s",
            enabled.get("Edges", False),
            params["Edges"],
        )
        if enabled.get("Edges", False):
            assert "low" in params["Edges"] and "high" in params["Edges"]
        steps_by_name = {
            "Grayscale": GrayscaleStep(enabled=enabled["Grayscale"]),
            "CLAHE Contrast": CLAHEContrastStep(
                enabled=enabled["CLAHE Contrast"],
                clip_limit=params["CLAHE Contrast"]["clip_limit"],
                tile_grid_size=params["CLAHE Contrast"]["tile_grid_size"],
            ),
            "Gaussian Blur": GaussianBlurStep(
                enabled=enabled["Gaussian Blur"],
                strength=params["Gaussian Blur"]["strength"],
            ),
            "Threshold": ThresholdStep(
                enabled=enabled["Threshold"],
                mode=params["Threshold"]["mode"],
                invert=params["Threshold"]["invert"],
                bias=params["Threshold"]["bias"],
                block_size=params["Threshold"]["block_size"],
            ),
            "Morphology": MorphologyStep(
                enabled=enabled["Morphology"],
                operation=params["Morphology"]["operation"],
                kernel_size=params["Morphology"]["kernel_size"],
                iterations=params["Morphology"]["iterations"],
            ),
            "Edges": EdgesStep(
                enabled=enabled["Edges"],
                low=params["Edges"]["low"],
                high=params["Edges"]["high"],
                thickness=params["Edges"]["thickness"],
                apply_on=params["Edges"]["apply_on"],
            ),
        }
        ordered_steps = []
        for name in self.state.step_order:
            if name not in steps_by_name:
                raise ValueError(f"Unknown step in pipeline: {name}")
            if enabled.get(name, False):
                ordered_steps.append(steps_by_name[name])
        return Pipeline(ordered_steps)

    def _schedule_preview(self) -> None:
        if self.state.original_image_rgb is None:
            return
        if not self._render_scheduler.request_render():
            self._sync_render_flags()
            return
        self._sync_render_flags()
        pipeline = self._build_pipeline()
        self._expected_revision = self.state.next_render_revision()
        image = self.state.original_image_rgb
        roi = self._get_active_roi()
        roi_slice = None
        if roi is not None:
            image, roi_slice = self._crop_for_roi(image, roi)
        self._roi_by_revision[self._expected_revision] = roi_slice
        logging.getLogger(__name__).info(
            "SCHEDULE render expected_rev=%s in_flight=%s pending=%s",
            self._expected_revision,
            self._render_scheduler.in_flight,
            self._render_scheduler.pending,
        )
        self._runner.schedule(image, pipeline, self._expected_revision)

    def _open_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open image", "", "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)"
        )
        if not path:
            return
        try:
            image = load_image(path)
        except Exception as exc:  # pragma: no cover - GUI error handling
            QMessageBox.critical(self, "Open failed", str(exc))
            return
        self.state.original_image_rgb = image
        self.state.preview_image_rgb = None
        self._set_original_image(image)
        self._preview_image_rgb = None
        self._preview_qimage = None
        self._preview_image_label.clear_roi()
        self._update_label_pixmap(self._preview_image_label, None, reset_view=True)
        self._clear_snapshot()
        self._update_action_states()
        logging.getLogger(__name__).debug(
            "OPEN loaded: shape=%s dtype=%s",
            image.shape,
            image.dtype,
        )
        self._render_sync_preview()
        self._schedule_preview()

    def _save_image(self) -> None:
        if self.state.original_image_rgb is None:
            QMessageBox.information(self, "Save", "No image loaded to save.")
            return
        roi_active = self._roi_preview_toggle.isChecked() and (
            self._preview_image_label.get_roi_rect() is not None
        )
        if self.state.preview_image_rgb is None and not roi_active:
            QMessageBox.information(self, "Save", "No preview available to save.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save As", "", "PNG (*.png);;JPEG (*.jpg *.jpeg);;BMP (*.bmp)"
        )
        if not path:
            return
        try:
            if roi_active:
                pipeline = self._build_pipeline()
                result = pipeline.run(self.state.original_image_rgb.copy())
                save_image(path, result)
            else:
                save_image(path, self.state.preview_image_rgb)
        except Exception as exc:  # pragma: no cover - GUI error handling
            QMessageBox.critical(self, "Save failed", str(exc))

    def _save_preset(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Preset", "", "Preset (*.json)"
        )
        if not path:
            return
        preset = state_to_preset_dict(self.state)
        try:
            save_preset_file(path, preset)
        except Exception as exc:  # pragma: no cover - GUI error handling
            QMessageBox.critical(self, "Save preset failed", str(exc))

    def _load_preset(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Preset", "", "Preset (*.json)"
        )
        if not path:
            return
        try:
            preset = load_preset_file(path)
            snapshot = self.state.snapshot()
            apply_preset_dict(self.state, preset)
        except Exception as exc:  # pragma: no cover - GUI error handling
            QMessageBox.critical(self, "Load preset failed", str(exc))
            return
        self.state.undo_stack.append(snapshot)
        self.state.redo_stack.clear()
        self._apply_state_to_controls()
        self._update_action_states()
        self._schedule_preview()

    def _undo(self) -> None:
        if self.state.undo():
            self._apply_state_to_controls()
            self._update_action_states()
            self._schedule_preview()

    def _redo(self) -> None:
        if self.state.redo():
            self._apply_state_to_controls()
            self._update_action_states()
            self._schedule_preview()

    def _reset_state(self) -> None:
        self.state.reset_defaults()
        self._apply_state_to_controls()
        self._update_action_states()
        self._schedule_preview()

    def _update_action_states(self) -> None:
        self._undo_action.setEnabled(self.state.can_undo)
        self._redo_action.setEnabled(self.state.can_redo)
        self._save_action.setEnabled(self.state.preview_image_rgb is not None)
        if hasattr(self, "_snapshot_button"):
            self._snapshot_button.setEnabled(self._preview_qimage is not None)
        if hasattr(self, "_compare_toggle"):
            self._compare_toggle.setEnabled(self._preview_snapshot_qimage is not None)
        if hasattr(self, "_clear_snapshot_button"):
            self._clear_snapshot_button.setEnabled(
                self._preview_snapshot_qimage is not None
            )
        if hasattr(self, "_roi_clear_button"):
            self._roi_clear_button.setEnabled(
                self._roi_preview_toggle.isChecked()
                and self._preview_image_label.get_roi_rect() is not None
            )

    def _on_roi_toggled(self, checked: bool) -> None:
        if self._suppress_updates:
            return
        self._preview_image_label.set_roi_enabled(checked)
        self._update_action_states()
        self._schedule_preview()

    def _clear_roi(self) -> None:
        self._preview_image_label.clear_roi()
        self._update_action_states()
        self._schedule_preview()

    def _on_preview_roi_changed(self) -> None:
        if self._suppress_updates:
            return
        self._update_action_states()
        self._schedule_preview()

    def _get_active_roi(self) -> QRectF | None:
        if not self._roi_preview_toggle.isChecked():
            return None
        return self._preview_image_label.get_roi_rect()

    def _crop_for_roi(
        self, image: np.ndarray, roi: QRectF
    ) -> tuple[np.ndarray, tuple[int, int, int, int] | None]:
        height, width = image.shape[:2]
        x0 = max(0, min(int(math.floor(roi.left())), width))
        y0 = max(0, min(int(math.floor(roi.top())), height))
        x1 = max(0, min(int(math.ceil(roi.right())), width))
        y1 = max(0, min(int(math.ceil(roi.bottom())), height))
        if x1 <= x0 or y1 <= y0:
            return image, None
        return image[y0:y1, x0:x1], (x0, y0, x1, y1)

    def _on_worker_done(self, revision: int, image, error: str | None) -> None:
        self._sync_render_flags()
        accepted = should_apply_revision(self._expected_revision, revision)
        logging.getLogger(__name__).info(
            "APPLY preview rev=%s accepted=%s",
            revision,
            accepted,
        )
        if not accepted:
            self._log_ignored_revision(revision)
            self._roi_by_revision.pop(revision, None)
            self._finalize_render_cycle()
            return
        if error:
            QMessageBox.critical(self, "Processing failed", error)
            self._roi_by_revision.pop(revision, None)
            self._finalize_render_cycle()
            return
        if not isinstance(image, np.ndarray):
            logging.getLogger(__name__).debug(
                "APPLY preview: rev=%s invalid image type=%s",
                revision,
                type(image),
            )
            self._roi_by_revision.pop(revision, None)
            self._finalize_render_cycle()
            return
        self._apply_preview(image, revision)
        self._finalize_render_cycle()

    def _set_original_image(self, image) -> None:
        self._original_qimage = rgb_to_qimage(image)
        self._update_label_pixmap(
            self._original_image_label,
            self._original_qimage,
            reset_view=True,
        )

    def _update_label_pixmap(
        self, label: ImageView, qimage, reset_view: bool = False
    ) -> None:
        if qimage is None:
            label.set_image(None, reset_view=reset_view)
            return
        label.set_image(qimage, reset_view=reset_view)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._original_image_label.update()
        self._preview_image_label.update()

    def _log_ignored_revision(self, revision: int) -> None:
        if revision == self._last_ignored_revision:
            return
        self._last_ignored_revision = revision
        logging.getLogger(__name__).debug(
            "IGNORE preview: incoming_rev=%s expected_rev=%s",
            revision,
            self._expected_revision,
        )

    def _write_debug_preview(self, image: np.ndarray) -> None:
        primary_path = Path(__file__).resolve().parents[3] / "_debug_preview.png"
        fallback_path = Path("/tmp/_debug_preview.png")
        try:
            save_image(str(primary_path), image)
        except Exception as exc:  # pragma: no cover - diagnostic fallback
            logging.getLogger(__name__).debug(
                "debug preview save failed path=%s err=%s",
                primary_path,
                exc,
            )
            try:
                save_image(str(fallback_path), image)
            except Exception as fallback_exc:  # pragma: no cover - best effort
                logging.getLogger(__name__).debug(
                    "debug preview fallback save failed path=%s err=%s",
                    fallback_path,
                    fallback_exc,
                )

    def _populate_step_list(self) -> None:
        self._step_list.blockSignals(True)
        self._step_list.clear()
        self._step_items.clear()
        for step_name in self.state.step_order:
            if step_name not in KNOWN_STEPS:
                continue
            item = QListWidgetItem(step_name)
            item.setData(Qt.ItemDataRole.UserRole, step_name)
            item.setFlags(
                item.flags()
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsDragEnabled
            )
            item.setCheckState(
                Qt.CheckState.Checked
                if self.state.enabled.get(step_name, False)
                else Qt.CheckState.Unchecked
            )
            self._step_list.addItem(item)
            self._step_items[step_name] = item
        self._step_list.blockSignals(False)

    def _on_step_checkbox_changed(self, item: QListWidgetItem) -> None:
        if self._suppress_updates:
            return
        self._on_controls_changed()

    def _on_steps_reordered(self, new_order: list[str]) -> None:
        if self._suppress_updates:
            return
        if new_order == self.state.step_order:
            return
        old_order = self.state.step_order
        moved_step = None
        moved_index = None
        for index, (old, new) in enumerate(zip(old_order, new_order)):
            if old != new:
                moved_step = new
                moved_index = index
                break
        if moved_step is None or moved_index is None:
            return
        self.state.move_step(moved_step, moved_index)
        self._update_action_states()
        self._schedule_preview()

    def _update_threshold_controls(self) -> None:
        is_adaptive = self._threshold_mode.currentText() == "adaptive"
        self._threshold_block_slider.setEnabled(is_adaptive)
        self._threshold_block_label.setEnabled(is_adaptive)

    def _apply_preview(self, image: np.ndarray, revision: int) -> None:
        roi_slice = self._roi_by_revision.pop(revision, None)
        if roi_slice is not None and self.state.original_image_rgb is not None:
            x0, y0, x1, y1 = roi_slice
            composite = self.state.original_image_rgb.copy()
            if (
                image.shape[0] == y1 - y0
                and image.shape[1] == x1 - x0
                and image.shape[2] == composite.shape[2]
            ):
                composite[y0:y1, x0:x1] = image
                image = composite
        self._preview_image_rgb = image
        self.state.preview_image_rgb = image
        self._preview_qimage = rgb_to_qimage(image)
        self._update_preview_view()
        self._update_action_states()
        self.state.last_applied_revision = revision
        logging.getLogger(__name__).debug(
            "APPLY preview: rev=%s shape=%s dtype=%s min=%s max=%s",
            revision,
            image.shape,
            image.dtype,
            int(np.min(image)),
            int(np.max(image)),
        )
        self._write_debug_preview(image)

    def _render_sync_preview(self) -> None:
        try:
            pipeline = self._build_pipeline()
            image = self.state.original_image_rgb.copy()
            roi = self._get_active_roi()
            roi_slice = None
            if roi is not None:
                image, roi_slice = self._crop_for_roi(image, roi)
            result = pipeline.run(image)
        except Exception as exc:  # pragma: no cover - GUI error handling
            QMessageBox.critical(self, "Processing failed", str(exc))
            return
        revision = self.state.next_render_revision()
        self._expected_revision = revision
        if isinstance(result, np.ndarray):
            if roi_slice is not None:
                self._roi_by_revision[revision] = roi_slice
            self._apply_preview(result, revision)
        else:
            logging.getLogger(__name__).debug(
                "APPLY preview: rev=%s invalid image type=%s",
                revision,
                type(result),
            )

    def _finalize_render_cycle(self) -> None:
        if self._render_scheduler.on_render_finished():
            self._sync_render_flags()
            self._schedule_preview()
        else:
            self._sync_render_flags()

    def _sync_render_flags(self) -> None:
        self._render_in_flight = self._render_scheduler.in_flight
        self._pending_render = self._render_scheduler.pending

    def _update_preview_view(self) -> None:
        if self._compare_snapshot and self._preview_snapshot_qimage is not None:
            self._update_label_pixmap(
                self._preview_image_label, self._preview_snapshot_qimage
            )
            return
        self._update_label_pixmap(self._preview_image_label, self._preview_qimage)

    def _take_snapshot(self) -> None:
        if self._preview_qimage is None:
            return
        self._preview_snapshot_qimage = self._preview_qimage.copy()
        self._update_action_states()
        if self._compare_toggle.isChecked():
            self._update_preview_view()

    def _clear_snapshot(self) -> None:
        self._preview_snapshot_qimage = None
        if hasattr(self, "_compare_toggle"):
            self._compare_toggle.blockSignals(True)
            self._compare_toggle.setChecked(False)
            self._compare_toggle.blockSignals(False)
        self._compare_snapshot = False
        if hasattr(self, "_clear_snapshot_button"):
            self._clear_snapshot_button.setEnabled(False)
        self._update_preview_view()
        self._update_action_states()

    def _toggle_compare(self, checked: bool) -> None:
        if checked and self._preview_snapshot_qimage is None:
            self._compare_toggle.blockSignals(True)
            self._compare_toggle.setChecked(False)
            self._compare_toggle.blockSignals(False)
            return
        self._compare_snapshot = checked
        self._update_preview_view()


def run_gui() -> int:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    return app.exec()
