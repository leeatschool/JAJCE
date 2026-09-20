import os
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QRadioButton,
    QButtonGroup, QSlider, QLabel, QSpinBox, QDoubleSpinBox,
    QCheckBox, QPushButton, QFileDialog, QLineEdit, QFrame
)
from PySide6.QtCore import Qt, Signal

from jajce.engine.converter import ConversionOptions

class SettingsWidget(QWidget):
    """
    Control panel for conversion parameters, lossy/lossless modes,
    SmolVLM tagging options, and output destination.
    """
    settings_changed = Signal()
    request_test_tagging = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(14)

        # 1. Mode Selection Group
        mode_group = QGroupBox("Conversion Mode")
        mode_layout = QVBoxLayout(mode_group)
        mode_layout.setSpacing(8)

        self.radio_lossless = QRadioButton("Losslessly Transcode (Reversible)")
        self.radio_lossless.setChecked(True)
        self.radio_lossless.setToolTip(
            "Losslessly transcodes JPEG bitstream coefficients with zero generational loss\n"
            "and bit-exact reversibility back to JPEG. For PNG/WebP/other formats, uses\n"
            "mathematically lossless JPEG XL modular encoding."
        )

        lossless_desc = QLabel(
            "Bit-exact reversible JPEG transcoding + lossless compression for PNG/TIFF/WebP."
        )
        lossless_desc.setStyleSheet("color: #64748B; font-size: 11px; margin-left: 24px;")

        self.radio_lossy = QRadioButton("Lossy Re-encoding (Fresh Compression)")
        self.radio_lossy.setToolTip(
            "Decompresses image to raw pixels and applies fresh JPEG XL VarDCT lossy compression\n"
            "at the chosen visual distance and effort."
        )

        lossy_desc = QLabel(
            "Fresh JPEG XL lossy re-encoding for dramatically smaller file sizes."
        )
        lossy_desc.setStyleSheet("color: #64748B; font-size: 11px; margin-left: 24px;")

        self.mode_btn_group = QButtonGroup(self)
        self.mode_btn_group.addButton(self.radio_lossless)
        self.mode_btn_group.addButton(self.radio_lossy)

        mode_layout.addWidget(self.radio_lossless)
        mode_layout.addWidget(lossless_desc)
        mode_layout.addWidget(self.radio_lossy)
        mode_layout.addWidget(lossy_desc)
        layout.addWidget(mode_group)

        # 2. Lossy Parameters Group
        self.lossy_group = QGroupBox("Lossy Compression Settings")
        lossy_param_layout = QVBoxLayout(self.lossy_group)
        lossy_param_layout.setSpacing(10)

        # Target Visual Distance
        dist_header = QHBoxLayout()
        dist_label = QLabel("Visual Distance (JND):")
        dist_label.setToolTip(
            "Target visual distance in Butteraugli JND units.\n"
            "0.5 - 0.9: Ultra High Quality\n"
            "1.0: Visually Lossless (Recommended)\n"
            "1.5 - 2.5: High Quality Web / Sharing\n"
            "3.0+: High Compression"
        )
        self.dist_spin = QDoubleSpinBox()
        self.dist_spin.setRange(0.1, 15.0)
        self.dist_spin.setSingleStep(0.1)
        self.dist_spin.setValue(1.0)
        dist_header.addWidget(dist_label)
        dist_header.addStretch()
        dist_header.addWidget(self.dist_spin)
        lossy_param_layout.addLayout(dist_header)

        self.dist_slider = QSlider(Qt.Horizontal)
        self.dist_slider.setRange(1, 150)  # 0.1 to 15.0
        self.dist_slider.setValue(10)
        lossy_param_layout.addWidget(self.dist_slider)

        # Effort
        effort_header = QHBoxLayout()
        effort_label = QLabel("Encoding Effort:")
        effort_label.setToolTip("Higher effort uses more CPU compute to find smaller file sizes.")
        self.effort_spin = QSpinBox()
        self.effort_spin.setRange(1, 9)
        self.effort_spin.setValue(7)
        effort_header.addWidget(effort_label)
        effort_header.addStretch()
        effort_header.addWidget(self.effort_spin)
        lossy_param_layout.addLayout(effort_header)

        self.effort_slider = QSlider(Qt.Horizontal)
        self.effort_slider.setRange(1, 9)
        self.effort_slider.setValue(7)
        lossy_param_layout.addWidget(self.effort_slider)

        # Progressive
        self.check_progressive = QCheckBox("Enable Progressive Decoding (-p)")
        self.check_progressive.setChecked(False)
        self.check_progressive.setToolTip("Enables responsive multi-resolution progressive rendering.")
        lossy_param_layout.addWidget(self.check_progressive)

        layout.addWidget(self.lossy_group)

        # 3. SmolVLM AI Auto-Tagging Group
        self.tagging_group = QGroupBox("AI Auto-Tagging (SmolVLM-256M-Instruct)")
        tagging_layout = QVBoxLayout(self.tagging_group)
        tagging_layout.setSpacing(10)

        tag_top_row = QHBoxLayout()
        self.check_enable_tagging = QCheckBox("Auto-Identify Items & Write Tags to .jxl")
        self.check_enable_tagging.setChecked(False)
        self.check_enable_tagging.setStyleSheet("font-weight: 600; color: #38BDF8;")
        tag_top_row.addWidget(self.check_enable_tagging)
        tag_top_row.addStretch()
        tagging_layout.addLayout(tag_top_row)

        self.vlm_status_badge = QLabel("Model: Local / Ready")
        self.vlm_status_badge.setStyleSheet("color: #10B981; font-size: 11px;")
        tagging_layout.addWidget(self.vlm_status_badge)

        prompt_label = QLabel("Tagging Prompt / Instruction:")
        self.edit_tag_prompt = QLineEdit("List the main items, objects, and subjects in this photo as a comma-separated list of short tags:")
        tagging_layout.addWidget(prompt_label)
        tagging_layout.addWidget(self.edit_tag_prompt)

        tag_options_row = QHBoxLayout()
        tag_options_row.addWidget(QLabel("Max Tags per Image:"))
        self.spin_max_tags = QSpinBox()
        self.spin_max_tags.setRange(1, 20)
        self.spin_max_tags.setValue(8)
        tag_options_row.addWidget(self.spin_max_tags)
        tag_options_row.addStretch()

        self.btn_test_tag = QPushButton("Test Tagging Selected Image")
        self.btn_test_tag.setToolTip("Run SmolVLM inference on the selected item in the queue.")
        tag_options_row.addWidget(self.btn_test_tag)
        tagging_layout.addLayout(tag_options_row)

        layout.addWidget(self.tagging_group)

        # 4. Output Destination Group
        output_group = QGroupBox("Output Destination")
        output_layout = QVBoxLayout(output_group)
        output_layout.setSpacing(8)

        self.radio_out_source = QRadioButton("Save in same directory as source image")
        self.radio_out_source.setChecked(True)
        self.radio_out_custom = QRadioButton("Save in custom directory:")
        self.out_btn_group = QButtonGroup(self)
        self.out_btn_group.addButton(self.radio_out_source)
        self.out_btn_group.addButton(self.radio_out_custom)

        output_layout.addWidget(self.radio_out_source)
        output_layout.addWidget(self.radio_out_custom)

        custom_dir_row = QHBoxLayout()
        self.edit_custom_dir = QLineEdit()
        self.edit_custom_dir.setPlaceholderText("Select destination folder...")
        self.edit_custom_dir.setEnabled(False)
        self.btn_browse_dir = QPushButton("Browse...")
        self.btn_browse_dir.setEnabled(False)
        custom_dir_row.addWidget(self.edit_custom_dir)
        custom_dir_row.addWidget(self.btn_browse_dir)
        output_layout.addLayout(custom_dir_row)

        self.check_overwrite = QCheckBox("Overwrite existing .jxl files")
        self.check_overwrite.setChecked(True)
        output_layout.addWidget(self.check_overwrite)

        layout.addWidget(output_group)

        # Connect signals
        self.radio_lossless.toggled.connect(self._on_mode_toggled)
        self.radio_lossy.toggled.connect(self._on_mode_toggled)

        self.dist_slider.valueChanged.connect(lambda v: self.dist_spin.setValue(v / 10.0))
        self.dist_spin.valueChanged.connect(lambda v: self.dist_slider.setValue(int(v * 10)))

        self.effort_slider.valueChanged.connect(self.effort_spin.setValue)
        self.effort_spin.valueChanged.connect(self.effort_slider.setValue)

        self.radio_out_custom.toggled.connect(self._on_out_dir_toggled)
        self.btn_browse_dir.clicked.connect(self._browse_custom_dir)
        self.btn_test_tag.clicked.connect(self.request_test_tagging.emit)

        self._on_mode_toggled()

    def _on_mode_toggled(self):
        is_lossy = self.radio_lossy.isChecked()
        self.lossy_group.setEnabled(is_lossy)
        self.settings_changed.emit()

    def _on_out_dir_toggled(self, checked):
        self.edit_custom_dir.setEnabled(checked)
        self.btn_browse_dir.setEnabled(checked)
        self.settings_changed.emit()

    def _browse_custom_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if folder:
            self.edit_custom_dir.setText(folder)
            self.settings_changed.emit()

    def get_options(self) -> ConversionOptions:
        out_dir = self.edit_custom_dir.text().strip() if self.radio_out_custom.isChecked() else None
        return ConversionOptions(
            mode="lossy" if self.radio_lossy.isChecked() else "lossless",
            distance=self.dist_spin.value(),
            use_distance=True,
            effort=self.effort_spin.value(),
            progressive=self.check_progressive.isChecked(),
            enable_ai_tagging=self.check_enable_tagging.isChecked(),
            ai_prompt=self.edit_tag_prompt.text().strip(),
            max_tags=self.spin_max_tags.value(),
            overwrite_existing=self.check_overwrite.isChecked(),
            output_dir=out_dir if out_dir else None
        )
