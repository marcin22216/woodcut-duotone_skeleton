"""Main application window for GUI v0."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
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
from woodcut_duotone.gui.state import AppState
from woodcut_duotone.gui.worker import DebouncedPipelineRunner
from woodcut_duotone.io import load_image, rgb_to_qimage, save_image


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Woodcut Duotone")

        self.state = AppState()
        self._runner = DebouncedPipelineRunner()
        self._runner.result_ready.connect(self._on_preview_ready)
        self._runner.error.connect(self._on_worker_error)

        self._original_qimage = None
        self._preview_qimage = None
        self._preview_image_rgb = None
        self._suppress_updates = False

        self._enabled_checkboxes: dict[str, QCheckBox] = {}

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
        layout.addWidget(left_panel, 0)

        right_panel = self._build_preview_panel()
        layout.addWidget(right_panel, 1)

        self.setCentralWidget(central)

    def _build_left_panel(self) -> QWidget:
        container = QWidget()
        left_layout = QVBoxLayout(container)
        left_layout.setContentsMargins(0, 0, 0, 0)

        steps_group = QGroupBox("Steps")
        steps_layout = QVBoxLayout(steps_group)
        for key, label in [
            ("grayscale", "Grayscale"),
            ("clahe", "CLAHE Contrast"),
            ("blur", "Gaussian Blur"),
            ("threshold", "Threshold"),
            ("morphology", "Morphology"),
            ("edges", "Edges"),
        ]:
            checkbox = QCheckBox(label)
            checkbox.stateChanged.connect(self._on_setting_changed)
            steps_layout.addWidget(checkbox)
            self._enabled_checkboxes[key] = checkbox
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
        self._threshold_mode.currentIndexChanged.connect(self._on_setting_changed)
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
        self._threshold_invert.stateChanged.connect(self._on_setting_changed)
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
        self._morph_op.currentIndexChanged.connect(self._on_setting_changed)
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
        self._edges_apply_on.currentIndexChanged.connect(self._on_setting_changed)
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
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        self._original_label = QLabel("Original")
        self._original_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._original_image_label = QLabel()
        self._original_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._original_image_label.setMinimumSize(320, 240)
        self._original_image_label.setStyleSheet("QLabel { background: #222; }")

        original_box = QVBoxLayout()
        original_box.addWidget(self._original_label)
        original_box.addWidget(self._original_image_label)

        self._preview_label = QLabel("Preview")
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_image_label = QLabel()
        self._preview_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_image_label.setMinimumSize(320, 240)
        self._preview_image_label.setStyleSheet("QLabel { background: #222; }")

        preview_box = QVBoxLayout()
        preview_box.addWidget(self._preview_label)
        preview_box.addWidget(self._preview_image_label)

        layout.addLayout(original_box)
        layout.addLayout(preview_box)

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

        for key, checkbox in self._enabled_checkboxes.items():
            checkbox.setChecked(self.state.enabled.get(key, False))

        threshold_params = self.state.params["threshold"]
        self._threshold_mode.setCurrentText(threshold_params["mode"])
        self._threshold_bias_slider.setValue(threshold_params["bias"])
        self._threshold_bias_label.setText(str(threshold_params["bias"]))
        self._threshold_invert.setChecked(threshold_params["invert"])
        self._threshold_block_slider.setValue(threshold_params["block_size"])
        self._threshold_block_label.setText(str(threshold_params["block_size"]))

        morph_params = self.state.params["morphology"]
        self._morph_op.setCurrentText(morph_params["operation"])
        self._morph_kernel_slider.setValue(morph_params["kernel_size"])
        self._morph_kernel_label.setText(str(morph_params["kernel_size"]))
        self._morph_iters_slider.setValue(morph_params["iterations"])
        self._morph_iters_label.setText(str(morph_params["iterations"]))

        edges_params = self.state.params["edges"]
        self._edges_apply_on.setCurrentText(edges_params["apply_on"])
        self._edges_low_slider.setValue(edges_params["low"])
        self._edges_low_label.setText(str(edges_params["low"]))
        self._edges_high_slider.setValue(edges_params["high"])
        self._edges_high_label.setText(str(edges_params["high"]))
        self._edges_thickness_slider.setValue(edges_params["thickness"])
        self._edges_thickness_label.setText(str(edges_params["thickness"]))

        self._suppress_updates = False

    def _sync_state_from_controls(self) -> None:
        for key, checkbox in self._enabled_checkboxes.items():
            self.state.enabled[key] = checkbox.isChecked()

        self.state.params["threshold"] = {
            "mode": self._threshold_mode.currentText(),
            "invert": self._threshold_invert.isChecked(),
            "bias": int(self._threshold_bias_slider.value()),
            "block_size": int(self._threshold_block_slider.value()),
        }
        self.state.params["morphology"] = {
            "operation": self._morph_op.currentText(),
            "kernel_size": int(self._morph_kernel_slider.value()),
            "iterations": int(self._morph_iters_slider.value()),
        }
        self.state.params["edges"] = {
            "low": int(self._edges_low_slider.value()),
            "high": int(self._edges_high_slider.value()),
            "thickness": int(self._edges_thickness_slider.value()),
            "apply_on": self._edges_apply_on.currentText(),
        }

    def _on_setting_changed(self) -> None:
        if self._suppress_updates:
            return
        self.state.push_undo()
        self._sync_state_from_controls()
        self._update_action_states()
        self._schedule_preview()

    def _on_slider_changed(self, value: int, label: QLabel) -> None:
        if self._suppress_updates:
            return
        label.setText(str(value))
        self._on_setting_changed()

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
        self._on_setting_changed()

    def _build_pipeline(self) -> Pipeline:
        params = self.state.params
        enabled = self.state.enabled
        steps = [
            GrayscaleStep(enabled=enabled["grayscale"]),
            CLAHEContrastStep(
                enabled=enabled["clahe"],
                clip_limit=params["clahe"]["clip_limit"],
                tile_grid_size=params["clahe"]["tile_grid_size"],
            ),
            GaussianBlurStep(
                enabled=enabled["blur"],
                strength=params["blur"]["strength"],
            ),
            ThresholdStep(
                enabled=enabled["threshold"],
                mode=params["threshold"]["mode"],
                invert=params["threshold"]["invert"],
                bias=params["threshold"]["bias"],
                block_size=params["threshold"]["block_size"],
            ),
            MorphologyStep(
                enabled=enabled["morphology"],
                operation=params["morphology"]["operation"],
                kernel_size=params["morphology"]["kernel_size"],
                iterations=params["morphology"]["iterations"],
            ),
            EdgesStep(
                enabled=enabled["edges"],
                low=params["edges"]["low"],
                high=params["edges"]["high"],
                thickness=params["edges"]["thickness"],
                apply_on=params["edges"]["apply_on"],
            ),
        ]
        return Pipeline(steps)

    def _schedule_preview(self) -> None:
        if self.state.original_image_rgb is None:
            return
        pipeline = self._build_pipeline()
        self._runner.schedule(self.state.original_image_rgb, pipeline)

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
        self._set_original_image(image)
        self._schedule_preview()

    def _save_image(self) -> None:
        if self._preview_image_rgb is None:
            QMessageBox.information(self, "Save", "No preview available to save.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save As", "", "PNG (*.png);;JPEG (*.jpg *.jpeg);;BMP (*.bmp)"
        )
        if not path:
            return
        try:
            save_image(path, self._preview_image_rgb)
        except Exception as exc:  # pragma: no cover - GUI error handling
            QMessageBox.critical(self, "Save failed", str(exc))

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
        self.state.push_undo()
        self.state.reset_defaults()
        self._apply_state_to_controls()
        self._update_action_states()
        self._schedule_preview()

    def _update_action_states(self) -> None:
        self._undo_action.setEnabled(self.state.can_undo)
        self._redo_action.setEnabled(self.state.can_redo)

    def _on_preview_ready(self, image) -> None:
        self._preview_image_rgb = image
        self._preview_qimage = rgb_to_qimage(image)
        self._update_label_pixmap(self._preview_image_label, self._preview_qimage)

    def _on_worker_error(self, message: str) -> None:
        QMessageBox.critical(self, "Processing failed", message)

    def _set_original_image(self, image) -> None:
        self._original_qimage = rgb_to_qimage(image)
        self._update_label_pixmap(self._original_image_label, self._original_qimage)

    def _update_label_pixmap(self, label: QLabel, qimage) -> None:
        if qimage is None:
            label.clear()
            return
        pixmap = QPixmap.fromImage(qimage)
        scaled = pixmap.scaled(
            label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        label.setPixmap(scaled)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        if self._original_qimage is not None:
            self._update_label_pixmap(self._original_image_label, self._original_qimage)
        if self._preview_qimage is not None:
            self._update_label_pixmap(self._preview_image_label, self._preview_qimage)


def run_gui() -> int:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    return app.exec()
