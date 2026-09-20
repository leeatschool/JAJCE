import os
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QRadioButton,
    QButtonGroup, QSlider, QLabel, QSpinBox, QDoubleSpinBox,
    QCheckBox, QPushButton, QFileDialog, QLineEdit, QScrollArea,
    QFrame
)
from PySide6.QtCore import Qt, Signal

from jajce.engine.converter import ConversionOptions

class SettingsWidget(QWidget):
    """
    Control panel for conversion parameters, lossy/lossless modes,
    SmolVLM tagging options, and output destination.
    Encapsulated inside a QScrollArea for responsiveness across all screen sizes.
    """
    settings_changed = Signal()
    request_test_tagging = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        # Outer layout containing the scroll area
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Content widget inside scroll area
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(12, 12, 12, 12)
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
        lossless_desc.setWordWrap(True)
        lossless_desc.setStyleSheet("color: #64748B; font-size: 11px; margin-left: 24px;")

        self.radio_lossy = QRadioButton("Lossy Re-encoding (Fresh Compression)")
        self.radio_lossy.setToolTip(
            "Decompresses image to raw pixels and applies fresh JPEG XL VarDCT lossy compression\n"
            "at the chosen visual distance and effort."
        )

        lossy_desc = QLabel(
            "Fresh JPEG XL lossy re-encoding for dramatically smaller file sizes."
        )
        lossy_desc.setWordWrap(True)
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

        # Quick Presets Bar
        preset_header = QLabel("Quick Compression Presets:")
        preset_header.setStyleSheet("font-weight: 600; color: #CBD5E1; font-size: 12px;")
        lossy_param_layout.addWidget(preset_header)

        preset_row = QHBoxLayout()
        preset_row.setSpacing(6)

        self.btn_preset_web = QPushButton("⚡ Web (d=2.0 / ~80%)")
        self.btn_preset_web.setToolTip("Recommended for dramatic 40%–70% file size reductions while staying visually pristine.")
        self.btn_preset_balanced = QPushButton("⚖️ Balanced (d=1.5 / ~85%)")
        self.btn_preset_balanced.setToolTip("Sweet spot between high visual fidelity and solid file savings (25%–50%).")
        self.btn_preset_lossless = QPushButton("💎 Lossless Look (d=1.0 / ~90%)")
        self.btn_preset_lossless.setToolTip("Visually lossless archival quality. Minimal compression difference on already-compressed JPEGs.")
        self.btn_preset_max = QPushButton("📦 Max Comp (d=3.0 / ~70%)")
        self.btn_preset_max.setToolTip("Aggressive compression for maximum space savings (60%–80%).")

        for btn in [self.btn_preset_web, self.btn_preset_balanced, self.btn_preset_lossless, self.btn_preset_max]:
            btn.setStyleSheet("font-size: 11px; padding: 4px 8px;")
            preset_row.addWidget(btn)

        lossy_param_layout.addLayout(preset_row)

        # Target Visual Distance
        dist_header = QHBoxLayout()
        dist_label = QLabel("Visual Distance (JND):")
        dist_label.setToolTip(
            "Target visual distance in Butteraugli JND units.\n"
            "0.5 - 0.9: Ultra High Quality / Archival\n"
            "1.0: Visually Lossless\n"
            "1.5 - 2.5: High Quality Web & Sharing (Dramatically Smaller)\n"
            "3.0+: High Compression"
        )
        self.dist_spin = QDoubleSpinBox()
        self.dist_spin.setRange(0.1, 15.0)
        self.dist_spin.setSingleStep(0.1)
        self.dist_spin.setValue(1.5)
        dist_header.addWidget(dist_label)
        dist_header.addStretch()
        dist_header.addWidget(self.dist_spin)
        lossy_param_layout.addLayout(dist_header)

        self.dist_slider = QSlider(Qt.Horizontal)
        self.dist_slider.setRange(1, 150)  # 0.1 to 15.0
        self.dist_slider.setValue(15)
        lossy_param_layout.addWidget(self.dist_slider)

        # Target Quality %
        quality_header = QHBoxLayout()
        quality_label = QLabel("Equivalent Quality (%):")
        quality_label.setToolTip("Estimated JPEG-equivalent quality corresponding to the chosen visual distance.")
        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(10, 100)
        self.quality_spin.setValue(85)
        quality_header.addWidget(quality_label)
        quality_header.addStretch()
        quality_header.addWidget(self.quality_spin)
        lossy_param_layout.addLayout(quality_header)

        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setRange(10, 100)
        self.quality_slider.setValue(85)
        lossy_param_layout.addWidget(self.quality_slider)

        # Effort
        effort_header = QHBoxLayout()
        effort_label = QLabel("Encoding Effort (1-9):")
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

        # Smart Safeguard & Progressive
        self.check_auto_fallback = QCheckBox("Auto-optimize if lossy output exceeds source file size")
        self.check_auto_fallback.setChecked(True)
        self.check_auto_fallback.setToolTip(
            "If an already-compressed JPEG expands due to compression noise at the chosen quality,\n"
            "automatically falls back to lossless JPEG transcoding so the output is never larger than the source."
        )
        lossy_param_layout.addWidget(self.check_auto_fallback)

        self.check_progressive = QCheckBox("Enable Progressive Decoding (-p)")
        self.check_progressive.setChecked(False)
        self.check_progressive.setToolTip("Enables responsive multi-resolution progressive rendering.")
        lossy_param_layout.addWidget(self.check_progressive)

        # Tip Callout Frame
        tip_frame = QFrame()
        tip_frame.setStyleSheet(
            "background-color: #1A212D; border-left: 3px solid #38BDF8; "
            "border-radius: 4px; padding: 6px 10px; margin-top: 4px;"
        )
        tip_layout = QVBoxLayout(tip_frame)
        tip_layout.setContentsMargins(4, 4, 4, 4)
        lbl_tip = QLabel(
            "💡 <b>Compression Tip:</b> Distance 1.0 (Q=90) is visually lossless and preserves the exact noise of input pixels. "
            "On pre-compressed JPEGs, this spends bits encoding existing block/ringing artifacts, giving little savings or slight enlargement.<br>"
            "For <b>dramatic 40–70% reductions</b>, use <b>⚡ Web (d=2.0 / ~80%)</b>."
        )
        lbl_tip.setWordWrap(True)
        lbl_tip.setStyleSheet("color: #94A3B8; font-size: 11px;")
        tip_layout.addWidget(lbl_tip)
        lossy_param_layout.addWidget(tip_frame)

        layout.addWidget(self.lossy_group)

        # 3. SmolVLM AI Auto-Tagging Group
        self.tagging_group = QGroupBox("AI Auto-Tagging (SmolVLM-256M-Instruct)")
        tagging_layout = QVBoxLayout(self.tagging_group)
        tagging_layout.setSpacing(10)

        self.check_enable_tagging = QCheckBox("Auto-Identify Items & Write Tags to .jxl")
        self.check_enable_tagging.setChecked(False)
        self.check_enable_tagging.setStyleSheet("font-weight: 600; color: #38BDF8; font-size: 13px;")
        tagging_layout.addWidget(self.check_enable_tagging)

        self.vlm_status_badge = QLabel("Model: Local weights ready (CPU)")
        self.vlm_status_badge.setStyleSheet("color: #10B981; font-size: 11px;")
        tagging_layout.addWidget(self.vlm_status_badge)

        prompt_label = QLabel("Instruction Prompt for SmolVLM:")
        self.edit_tag_prompt = QLineEdit("Describe the main objects, subjects, text, and visual elements in this image:")
        tagging_layout.addWidget(prompt_label)
        tagging_layout.addWidget(self.edit_tag_prompt)

        tag_options_row = QHBoxLayout()
        tag_options_row.addWidget(QLabel("Max Tags per Image:"))
        self.spin_max_tags = QSpinBox()
        self.spin_max_tags.setRange(1, 20)
        self.spin_max_tags.setValue(8)
        tag_options_row.addWidget(self.spin_max_tags)
        tag_options_row.addStretch()
        tagging_layout.addLayout(tag_options_row)

        self.btn_test_tag = QPushButton("🔍 Test Tagging Selected Image")
        self.btn_test_tag.setStyleSheet("font-weight: 600; padding: 8px 16px;")
        self.btn_test_tag.setToolTip("Run SmolVLM inference immediately on the selected item in the queue.")
        tagging_layout.addWidget(self.btn_test_tag)

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

        # Bottom stretch so items stay comfortably aligned
        layout.addStretch()

        self.scroll_area.setWidget(content_widget)
        outer_layout.addWidget(self.scroll_area)

        # Connect signals
        self.radio_lossless.toggled.connect(self._on_mode_toggled)
        self.radio_lossy.toggled.connect(self._on_mode_toggled)

        self._syncing = False

        self.btn_preset_web.clicked.connect(lambda: self._apply_preset(2.0, 80))
        self.btn_preset_balanced.clicked.connect(lambda: self._apply_preset(1.5, 85))
        self.btn_preset_lossless.clicked.connect(lambda: self._apply_preset(1.0, 90))
        self.btn_preset_max.clicked.connect(lambda: self._apply_preset(3.0, 70))

        self.dist_slider.valueChanged.connect(self._on_dist_slider_changed)
        self.dist_spin.valueChanged.connect(self._on_dist_spin_changed)
        self.quality_slider.valueChanged.connect(self._on_quality_slider_changed)
        self.quality_spin.valueChanged.connect(self._on_quality_spin_changed)

        self.effort_slider.valueChanged.connect(self.effort_spin.setValue)
        self.effort_spin.valueChanged.connect(self.effort_slider.setValue)

        self.radio_out_custom.toggled.connect(self._on_out_dir_toggled)
        self.btn_browse_dir.clicked.connect(self._browse_custom_dir)
        self.btn_test_tag.clicked.connect(self.request_test_tagging.emit)

        self._on_mode_toggled()

    def _apply_preset(self, distance: float, quality: int):
        self._syncing = True
        self.dist_spin.setValue(distance)
        self.dist_slider.setValue(int(distance * 10))
        self.quality_spin.setValue(quality)
        self.quality_slider.setValue(quality)
        self._syncing = False
        self.settings_changed.emit()

    def _on_dist_slider_changed(self, v: int):
        if self._syncing:
            return
        self._syncing = True
        d = v / 10.0
        self.dist_spin.setValue(d)
        q = max(10, min(100, int(round(100 - (d - 0.1) / 0.09))))
        self.quality_spin.setValue(q)
        self.quality_slider.setValue(q)
        self._syncing = False
        self.settings_changed.emit()

    def _on_dist_spin_changed(self, d: float):
        if self._syncing:
            return
        self._syncing = True
        self.dist_slider.setValue(int(d * 10))
        q = max(10, min(100, int(round(100 - (d - 0.1) / 0.09))))
        self.quality_spin.setValue(q)
        self.quality_slider.setValue(q)
        self._syncing = False
        self.settings_changed.emit()

    def _on_quality_slider_changed(self, q: int):
        if self._syncing:
            return
        self._syncing = True
        self.quality_spin.setValue(q)
        d = max(0.1, min(15.0, round(0.1 + (100 - q) * 0.09, 2)))
        self.dist_spin.setValue(d)
        self.dist_slider.setValue(int(d * 10))
        self._syncing = False
        self.settings_changed.emit()

    def _on_quality_spin_changed(self, q: int):
        if self._syncing:
            return
        self._syncing = True
        self.quality_slider.setValue(q)
        d = max(0.1, min(15.0, round(0.1 + (100 - q) * 0.09, 2)))
        self.dist_spin.setValue(d)
        self.dist_slider.setValue(int(d * 10))
        self._syncing = False
        self.settings_changed.emit()

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
            quality=self.quality_spin.value(),
            use_distance=True,
            effort=self.effort_spin.value(),
            progressive=self.check_progressive.isChecked(),
            enable_ai_tagging=self.check_enable_tagging.isChecked(),
            ai_prompt=self.edit_tag_prompt.text().strip(),
            max_tags=self.spin_max_tags.value(),
            overwrite_existing=self.check_overwrite.isChecked(),
            output_dir=out_dir if out_dir else None,
            auto_fallback_if_larger=self.check_auto_fallback.isChecked()
        )
