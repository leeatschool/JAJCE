import os
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional, Set
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QLabel, QMenu, QFileDialog, QMessageBox,
    QInputDialog, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QColor, QFont, QAction

from jajce.engine.converter import SUPPORTED_EXTENSIONS

@dataclass
class QueueItem:
    input_path: str
    original_size: int
    dimensions: str
    status: str = "Pending"
    output_path: str = ""
    converted_size: int = 0
    saved_percent: float = 0.0
    tags: List[str] = None
    error_message: str = ""

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

def format_size(bytes_val: int) -> str:
    if bytes_val <= 0:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} TB"

class QueueWidget(QWidget):
    """
    Queue table for batch image conversion and tagging.
    Supports drag-and-drop, folder recursion, and status updates.
    """
    queue_changed = Signal(int)  # Emits current count
    selection_changed = Signal(str)  # Emits selected input path
    request_tag_item = Signal(str)   # Emits input path to trigger AI tagging

    def __init__(self, parent=None):
        super().__init__(parent)
        self.items: Dict[str, QueueItem] = {}  # input_path -> QueueItem
        self.setAcceptDrops(True)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Top Button Bar
        btn_bar = QHBoxLayout()
        self.btn_add_files = QPushButton("+ Add Images")
        self.btn_add_folder = QPushButton("+ Add Folder")
        self.btn_remove_selected = QPushButton("Remove Selected")
        self.btn_clear_all = QPushButton("Clear All")
        self.btn_clear_all.setObjectName("DangerButton")

        btn_bar.addWidget(self.btn_add_files)
        btn_bar.addWidget(self.btn_add_folder)
        btn_bar.addStretch()
        btn_bar.addWidget(self.btn_remove_selected)
        btn_bar.addWidget(self.btn_clear_all)
        layout.addLayout(btn_bar)

        # Queue Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "File Name", "Format", "Original Size", "Status",
            "JXL Size", "Saved %", "Tags / Items Identified", "Full Path"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Interactive)

        self.table.setColumnWidth(0, 190)
        self.table.setColumnWidth(7, 240)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)

        layout.addWidget(self.table)

        # Summary Bar
        self.summary_label = QLabel("0 items in queue")
        self.summary_label.setStyleSheet("color: #94A3B8; font-size: 12px;")
        layout.addWidget(self.summary_label)

        # Connect signals
        self.btn_add_files.clicked.connect(self._browse_files)
        self.btn_add_folder.clicked.connect(self._browse_folder)
        self.btn_remove_selected.clicked.connect(self._remove_selected)
        self.btn_clear_all.clicked.connect(self.clear_all)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        paths = []
        for url in event.mimeData().urls():
            local_path = url.toLocalFile()
            if local_path:
                paths.append(local_path)
        self.add_paths(paths)
        event.acceptProposedAction()

    def _browse_files(self):
        extensions_filter = "All Supported Images (*.jpg *.jpeg *.png *.webp *.gif *.bmp *.tiff *.tif *.avif *.tga *.ico *.ppm *.qoi);;JPEG (*.jpg *.jpeg *.jfif);;PNG (*.png *.apng);;WebP (*.webp);;All Files (*.*)"
        files, _ = QFileDialog.getOpenFileNames(self, "Select Images to Convert", "", extensions_filter)
        if files:
            self.add_paths(files)

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder Containing Images")
        if folder:
            self.add_paths([folder], recursive=True)

    def add_paths(self, paths: List[str], recursive: bool = True):
        to_add: Set[str] = set()
        for p_str in paths:
            p = Path(p_str)
            if p.is_dir():
                pattern = "**/*" if recursive else "*"
                for child in p.glob(pattern):
                    if child.is_file() and child.suffix.lower() in SUPPORTED_EXTENSIONS:
                        to_add.add(str(child.resolve()))
            elif p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
                to_add.add(str(p.resolve()))

        for file_path in sorted(list(to_add)):
            if file_path not in self.items:
                size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                ext = Path(file_path).suffix.lower()
                self.items[file_path] = QueueItem(
                    input_path=file_path,
                    original_size=size,
                    dimensions="",
                    status="Pending"
                )

        self._refresh_table()
        self.queue_changed.emit(len(self.items))

    def _refresh_table(self):
        self.table.setRowCount(len(self.items))
        total_size = 0

        for row, (path_str, item) in enumerate(self.items.items()):
            p = Path(path_str)
            total_size += item.original_size

            # Col 0: File Name
            name_item = QTableWidgetItem(p.name)
            name_item.setData(Qt.UserRole, path_str)

            # Col 1: Format
            fmt_item = QTableWidgetItem(p.suffix.upper().lstrip("."))
            fmt_item.setTextAlignment(Qt.AlignCenter)

            # Col 2: Original Size
            orig_size_item = QTableWidgetItem(format_size(item.original_size))
            orig_size_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            # Col 3: Status
            status_item = QTableWidgetItem(item.status)
            status_item.setTextAlignment(Qt.AlignCenter)
            if item.status == "Finished":
                status_item.setForeground(QColor("#10B981"))
            elif item.status == "Error":
                status_item.setForeground(QColor("#EF4444"))
            elif "Encoding" in item.status or "Tagging" in item.status:
                status_item.setForeground(QColor("#38BDF8"))
            else:
                status_item.setForeground(QColor("#94A3B8"))

            # Col 4: JXL Size
            jxl_size_str = format_size(item.converted_size) if item.converted_size > 0 else "-"
            jxl_size_item = QTableWidgetItem(jxl_size_str)
            jxl_size_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            # Col 5: Saved %
            if item.converted_size > 0:
                saved_str = f"{item.saved_percent:+.1f}%"
                saved_item = QTableWidgetItem(saved_str)
                saved_item.setTextAlignment(Qt.AlignCenter)
                if item.saved_percent > 0:
                    saved_item.setForeground(QColor("#10B981"))
                else:
                    saved_item.setForeground(QColor("#F59E0B"))
            else:
                saved_item = QTableWidgetItem("-")
                saved_item.setTextAlignment(Qt.AlignCenter)

            # Col 6: Tags
            tags_str = ", ".join(item.tags) if item.tags else "-"
            tags_item = QTableWidgetItem(tags_str)

            # Col 7: Full Path
            path_item = QTableWidgetItem(path_str)
            path_item.setForeground(QColor("#64748B"))

            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, fmt_item)
            self.table.setItem(row, 2, orig_size_item)
            self.table.setItem(row, 3, status_item)
            self.table.setItem(row, 4, jxl_size_item)
            self.table.setItem(row, 5, saved_item)
            self.table.setItem(row, 6, tags_item)
            self.table.setItem(row, 7, path_item)

        self.summary_label.setText(
            f"{len(self.items)} items in queue | Total input size: {format_size(total_size)}"
        )

    def update_item_status(
        self,
        input_path: str,
        status: str,
        converted_size: int = 0,
        saved_percent: float = 0.0,
        tags: Optional[List[str]] = None,
        error_message: str = ""
    ):
        if input_path in self.items:
            item = self.items[input_path]
            item.status = status
            if converted_size > 0:
                item.converted_size = converted_size
                item.saved_percent = saved_percent
            if tags is not None:
                item.tags = tags
            if error_message:
                item.error_message = error_message
            self._refresh_table()

    def get_selected_path(self) -> Optional[str]:
        selected_rows = self.table.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            item = self.table.item(row, 0)
            if item:
                return item.data(Qt.UserRole)
        return None

    def _on_table_selection_changed(self):
        selected_path = self.get_selected_path()
        if selected_path:
            self.selection_changed.emit(selected_path)

    def _remove_selected(self):
        selected_rows = self.table.selectionModel().selectedRows()
        paths_to_remove = []
        for index in selected_rows:
            item = self.table.item(index.row(), 0)
            if item:
                paths_to_remove.append(item.data(Qt.UserRole))

        for p in paths_to_remove:
            self.items.pop(p, None)

        self._refresh_table()
        self.queue_changed.emit(len(self.items))

    def clear_all(self):
        self.items.clear()
        self._refresh_table()
        self.queue_changed.emit(0)

    def _show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return
        row = item.row()
        path_item = self.table.item(row, 0)
        if not path_item:
            return
        input_path = path_item.data(Qt.UserRole)
        q_item = self.items.get(input_path)
        if not q_item:
            return

        menu = QMenu(self)
        action_open_img = menu.addAction("Open Original Image")
        action_open_folder = menu.addAction("Show in File Explorer")
        menu.addSeparator()
        action_ai_tag = menu.addAction("🔍 Identify Tags with AI (SmolVLM)")
        action_edit_tags = menu.addAction("Edit / Add Tags Manually...")
        menu.addSeparator()
        action_remove = menu.addAction("Remove from Queue")

        chosen = menu.exec(self.table.mapToGlobal(pos))
        if chosen == action_open_img:
            os.startfile(input_path)
        elif chosen == action_open_folder:
            os.system(f'explorer /select,"{input_path}"')
        elif chosen == action_ai_tag:
            self.request_tag_item.emit(input_path)
        elif chosen == action_edit_tags:
            current = ", ".join(q_item.tags)
            text, ok = QInputDialog.getText(
                self, "Edit Tags", f"Comma-separated tags for {Path(input_path).name}:",
                text=current
            )
            if ok:
                new_tags = [t.strip() for t in text.split(",") if t.strip()]
                q_item.tags = new_tags
                self._refresh_table()
        elif chosen == action_remove:
            self.items.pop(input_path, None)
            self._refresh_table()
            self.queue_changed.emit(len(self.items))
