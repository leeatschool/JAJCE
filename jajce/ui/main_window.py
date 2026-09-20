import os
import sys
from pathlib import Path
from typing import Optional, List
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QSplitter, QTabWidget,
    QPlainTextEdit, QMessageBox, QFrame, QApplication
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIcon, QPixmap

from jajce.engine.jxl_bin import JXLBinaries
from jajce.engine.worker import BatchWorker
from jajce.engine.converter import ConversionResult
from jajce.vlm.tagger import SmolVLMTagger
from jajce.ui.queue_widget import QueueWidget
from jajce.ui.settings_widget import SettingsWidget
from jajce.ui.preview_widget import PreviewWidget

class SingleTagWorker(QThread):
    progress = Signal(str)
    finished = Signal(str, list)
    error = Signal(str, str)

    def __init__(self, file_path: str, prompt: Optional[str], max_tags: int):
        super().__init__()
        self.file_path = file_path
        self.prompt = prompt
        self.max_tags = max_tags

    def run(self):
        try:
            tagger = SmolVLMTagger.get_instance()
            self.progress.emit(f"Loading SmolVLM & analyzing {Path(self.file_path).name}...")
            tags = tagger.tag_image(
                self.file_path,
                custom_prompt=self.prompt,
                max_tags=self.max_tags,
                status_callback=self.progress.emit
            )
            self.finished.emit(self.file_path, tags)
        except Exception as e:
            self.error.emit(self.file_path, str(e))

class MainWindow(QMainWindow):
    """
    Main application window for JAJCE (Just Another JPEG Conversion Engine).
    """
    def __init__(self):
        super().__init__()
        self.worker: Optional[BatchWorker] = None
        self.tag_worker: Optional[SingleTagWorker] = None
        self.init_window()
        self.init_ui()
        self.check_system_binaries()

    def init_window(self):
        self.setWindowTitle("JAJCE — Just Another JPEG Conversion Engine")
        self.resize(1280, 840)
        self.setMinimumSize(960, 640)

        # Set Window and Application Icon
        icon_path = self._find_icon()
        if icon_path:
            app_icon = QIcon(icon_path)
            self.setWindowIcon(app_icon)
            QApplication.setWindowIcon(app_icon)

    def _find_icon(self) -> Optional[str]:
        base_dir = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent.parent
        candidates = [
            base_dir / "assets" / "icon.ico",
            base_dir / "assets" / "icon.png",
            Path(getattr(sys, "_MEIPASS", base_dir)) / "assets" / "icon.ico",
            Path(getattr(sys, "_MEIPASS", base_dir)) / "assets" / "icon.png",
            Path(r"C:\Users\Aaron\Downloads\writref\10.png"),
            Path(r"C:\Users\Aaron\Downloads\writref.png"),
        ]
        for c in candidates:
            if c.exists():
                return str(c)
        return None

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)

        # Header Bar
        header = QFrame()
        header.setStyleSheet("background-color: #161A22; border: 1px solid #282E39; border-radius: 8px; padding: 6px 12px;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 6, 8, 6)

        # Icon thumbnail in header
        icon_path = self._find_icon()
        if icon_path:
            icon_lbl = QLabel()
            pix = QPixmap(icon_path).scaled(42, 42, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon_lbl.setPixmap(pix)
            header_layout.addWidget(icon_lbl)

        # Title labels
        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        lbl_title = QLabel("JAJCE")
        lbl_title.setObjectName("HeaderTitle")
        lbl_sub = QLabel("Just Another JPEG Conversion Engine — JPEG XL Transcoder & AI Auto-Tagger")
        lbl_sub.setObjectName("HeaderSubtitle")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        # Engine badges
        badges_layout = QVBoxLayout()
        badges_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_jxl_badge = QLabel("libjxl: Detecting...")
        self.lbl_jxl_badge.setStyleSheet("color: #38BDF8; font-size: 11px; font-weight: 600;")
        self.lbl_vlm_badge = QLabel("SmolVLM-256M-Instruct: Ready (Local)")
        self.lbl_vlm_badge.setStyleSheet("color: #10B981; font-size: 11px; font-weight: 600;")
        badges_layout.addWidget(self.lbl_jxl_badge)
        badges_layout.addWidget(self.lbl_vlm_badge)
        header_layout.addLayout(badges_layout)

        main_layout.addWidget(header)

        # Central Splitter (Left: Queue, Right: Settings & Preview)
        splitter = QSplitter(Qt.Horizontal)

        # Left: Queue Widget
        self.queue_widget = QueueWidget()
        splitter.addWidget(self.queue_widget)

        # Right: Tabs (Settings & Preview)
        self.right_container = QTabWidget()
        self.right_container.setMinimumWidth(400)

        self.settings_widget = SettingsWidget()
        self.preview_widget = PreviewWidget()

        # Note: Escaped ampersand && ensures literal '&' is rendered
        self.right_container.addTab(self.settings_widget, "Conversion && AI Settings")
        self.right_container.addTab(self.preview_widget, "Image && Tags Preview")

        splitter.addWidget(self.right_container)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        main_layout.addWidget(splitter)

        # Bottom Action and Progress Bar
        bottom_panel = QFrame()
        bottom_panel.setStyleSheet("background-color: #161A22; border: 1px solid #282E39; border-radius: 8px; padding: 10px;")
        bottom_layout = QVBoxLayout(bottom_panel)
        bottom_layout.setContentsMargins(8, 8, 8, 8)
        bottom_layout.setSpacing(8)

        # Controls row
        ctrl_row = QHBoxLayout()

        self.lbl_status = QLabel("Ready")
        self.lbl_status.setStyleSheet("font-weight: 600; color: #94A3B8;")

        self.btn_toggle_log = QPushButton("Show Logs ▲")
        self.btn_toggle_log.setFixedWidth(110)

        self.btn_pause = QPushButton("Pause")
        self.btn_pause.setEnabled(False)
        self.btn_pause.setFixedWidth(90)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.setFixedWidth(90)
        self.btn_cancel.setObjectName("DangerButton")

        self.btn_start = QPushButton("Start Batch Conversion")
        self.btn_start.setObjectName("PrimaryButton")

        ctrl_row.addWidget(self.lbl_status)
        ctrl_row.addStretch()
        ctrl_row.addWidget(self.btn_toggle_log)
        ctrl_row.addWidget(self.btn_pause)
        ctrl_row.addWidget(self.btn_cancel)
        ctrl_row.addWidget(self.btn_start)
        bottom_layout.addLayout(ctrl_row)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        bottom_layout.addWidget(self.progress_bar)

        # Log Drawer (Collapsible)
        self.log_drawer = QPlainTextEdit()
        self.log_drawer.setReadOnly(True)
        self.log_drawer.setMaximumBlockCount(1000)
        self.log_drawer.setMaximumHeight(140)
        self.log_drawer.setVisible(False)
        bottom_layout.addWidget(self.log_drawer)

        main_layout.addWidget(bottom_panel)

        # Connect signals
        self.btn_start.clicked.connect(self.start_conversion)
        self.btn_pause.clicked.connect(self.toggle_pause)
        self.btn_cancel.clicked.connect(self.cancel_conversion)
        self.btn_toggle_log.clicked.connect(self.toggle_log_drawer)

        self.queue_widget.selection_changed.connect(self._on_queue_selection_changed)
        self.queue_widget.request_tag_item.connect(self._tag_specific_item)
        self.settings_widget.request_test_tagging.connect(self.test_tag_selected)

    def check_system_binaries(self):
        binaries = JXLBinaries.verify()
        if binaries.get("cjxl", False):
            self.lbl_jxl_badge.setText("libjxl 0.12.0: Connected (AVX2)")
            self.lbl_jxl_badge.setStyleSheet("color: #10B981; font-size: 11px; font-weight: 600;")
        else:
            self.lbl_jxl_badge.setText("libjxl: Not Detected (Warning)")
            self.lbl_jxl_badge.setStyleSheet("color: #EF4444; font-size: 11px; font-weight: 600;")
            self.log("Warning: cjxl.exe was not detected in bin or PATH. JXL conversion may fail.")

    def log(self, text: str):
        self.log_drawer.appendPlainText(text)
        sb = self.log_drawer.verticalScrollBar()
        sb.setValue(sb.maximum())

    def toggle_log_drawer(self):
        is_visible = self.log_drawer.isVisible()
        self.log_drawer.setVisible(not is_visible)
        self.btn_toggle_log.setText("Hide Logs ▼" if not is_visible else "Show Logs ▲")

    def _on_queue_selection_changed(self, file_path: str):
        item = self.queue_widget.items.get(file_path)
        tags = item.tags if item else []
        self.preview_widget.set_image(file_path, tags)

    def _tag_specific_item(self, file_path: str):
        options = self.settings_widget.get_options()
        self.lbl_status.setText(f"AI Tagging: {Path(file_path).name}...")
        self.log(f"Running SmolVLM-256M-Instruct on: {file_path}")
        self.settings_widget.btn_test_tag.setEnabled(False)
        self.settings_widget.btn_test_tag.setText("Analyzing Image...")

        self.tag_worker = SingleTagWorker(file_path, options.ai_prompt, options.max_tags)
        self.tag_worker.progress.connect(self._on_single_tag_progress)
        self.tag_worker.finished.connect(self._on_single_tag_finished)
        self.tag_worker.error.connect(self._on_single_tag_error)
        self.tag_worker.start()

    def test_tag_selected(self):
        selected_path = self.queue_widget.get_selected_path()
        if not selected_path:
            QMessageBox.information(
                self,
                "No Image Selected",
                "Please add and select an image in the queue table first to test tagging."
            )
            return
        self._tag_specific_item(selected_path)

    def _on_single_tag_progress(self, msg: str):
        self.lbl_status.setText(msg)
        self.log(f"[SmolVLM] {msg}")

    def _on_single_tag_finished(self, file_path: str, tags: list):
        self.settings_widget.btn_test_tag.setEnabled(True)
        self.settings_widget.btn_test_tag.setText("🔍 Test Tagging Selected Image")
        self.queue_widget.update_item_status(file_path, "Tags Ready", tags=tags)
        self.preview_widget.update_tags(tags)
        self.lbl_status.setText(f"Identified {len(tags)} tags for {Path(file_path).name}.")
        self.log(f"SmolVLM tags for {Path(file_path).name}: {tags}")
        # Switch to Preview Tab to immediately view tags
        self.right_container.setCurrentIndex(1)

    def _on_single_tag_error(self, file_path: str, err: str):
        self.settings_widget.btn_test_tag.setEnabled(True)
        self.settings_widget.btn_test_tag.setText("🔍 Test Tagging Selected Image")
        self.lbl_status.setText("Tagging error.")
        self.log(f"Error during tagging {file_path}: {err}")
        QMessageBox.warning(self, "Tagging Error", f"Failed to tag {Path(file_path).name}:\n{err}")

    def start_conversion(self):
        if not self.queue_widget.items:
            QMessageBox.information(self, "Queue Empty", "Please add images or a folder to the queue first.")
            return

        options = self.settings_widget.get_options()
        paths = list(self.queue_widget.items.keys())
        item_tags = {p: item.tags for p, item in self.queue_widget.items.items()}

        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_pause.setText("Pause")
        self.btn_cancel.setEnabled(True)
        self.progress_bar.setValue(0)

        mode_str = "Lossless Reversible" if options.mode == "lossless" else "Lossy Fresh"
        tagging_status = "with AI Auto-Tagging" if options.enable_ai_tagging else "without AI Tagging"
        self.lbl_status.setText(f"Converting {len(paths)} files ({mode_str} | {tagging_status})...")

        self.worker = BatchWorker(paths, options, item_tags)
        self.worker.item_started.connect(self._on_item_started)
        self.worker.item_progress.connect(self._on_item_progress)
        self.worker.item_tagged.connect(self._on_item_tagged)
        self.worker.item_finished.connect(self._on_item_finished)
        self.worker.batch_progress.connect(self._on_batch_progress)
        self.worker.batch_finished.connect(self._on_batch_finished)
        self.worker.log_message.connect(self.log)
        self.worker.start()

    def toggle_pause(self):
        if not self.worker:
            return
        if self.worker._is_paused:
            self.worker.resume()
            self.btn_pause.setText("Pause")
            self.lbl_status.setText("Resumed...")
            self.log("Batch conversion resumed.")
        else:
            self.worker.pause()
            self.btn_pause.setText("Resume")
            self.lbl_status.setText("Paused")
            self.log("Batch conversion paused.")

    def cancel_conversion(self):
        if self.worker:
            self.worker.cancel()
            self.lbl_status.setText("Cancelling...")
            self.log("Cancelling batch conversion...")

    def _on_item_started(self, path_str: str, status_text: str):
        self.queue_widget.update_item_status(path_str, status_text)

    def _on_item_progress(self, path_str: str, detail_text: str):
        self.queue_widget.update_item_status(path_str, detail_text)
        self.lbl_status.setText(f"{Path(path_str).name}: {detail_text}")

    def _on_item_tagged(self, path_str: str, tags: list):
        self.queue_widget.update_item_status(path_str, "Tagging Done", tags=tags)
        if self.queue_widget.get_selected_path() == path_str:
            self.preview_widget.update_tags(tags)

    def _on_item_finished(self, path_str: str, result: ConversionResult):
        if not result.success:
            status = "Error"
        elif result.fallback_applied:
            status = "Optimized (Lossless)"
        else:
            status = "Finished"

        self.queue_widget.update_item_status(
            path_str,
            status=status,
            converted_size=result.converted_size,
            saved_percent=result.compression_ratio,
            tags=result.tags,
            error_message=result.error_message or ""
        )

    def _on_batch_progress(self, current: int, total: int, percent: float):
        self.progress_bar.setValue(int(percent))
        self.lbl_status.setText(f"Processed {current} of {total} images ({percent:.0f}%)")

    def _on_batch_finished(self, success_count: int, error_count: int):
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.progress_bar.setValue(100)
        self.lbl_status.setText(f"Completed: {success_count} succeeded, {error_count} errors.")
        QMessageBox.information(
            self,
            "Batch Conversion Complete",
            f"Conversion finished!\n\n"
            f"Successfully converted: {success_count}\n"
            f"Errors / Skipped: {error_count}"
        )
