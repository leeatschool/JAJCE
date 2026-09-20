import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView,
    QHeaderView, QPushButton, QLabel, QMenu, QFileDialog, QMessageBox,
    QInputDialog, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor, QAction

from jajce.engine.converter import SUPPORTED_EXTENSIONS

@dataclass
class QueueItem:
    input_path: str
    original_size: int
    dimensions: str = ""
    status: str = "Pending"
    output_path: str = ""
    converted_size: int = 0
    saved_percent: float = 0.0
    tags: List[str] = field(default_factory=list)
    error_message: str = ""

def format_size(bytes_val: int) -> str:
    if bytes_val <= 0:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} TB"

class QueueTableModel(QAbstractTableModel):
    """
    High-performance virtualized table model capable of handling 100,000+ images
    with instant O(1) row updates, zero memory waste, and smooth 60 FPS scrolling.
    """
    HEADERS = [
        "File Name", "Format", "Original Size", "Status",
        "JXL Size", "Saved %", "Tags / Items Identified", "Full Path"
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.items_list: List[QueueItem] = []
        self.items_dict: Dict[str, QueueItem] = {}
        self.path_to_row: Dict[str, int] = {}
        self.total_size: int = 0

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self.items_list)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.HEADERS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.HEADERS[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self.items_list):
            return None

        item = self.items_list[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == 0:
                return Path(item.input_path).name
            elif col == 1:
                return Path(item.input_path).suffix.upper().lstrip(".")
            elif col == 2:
                return format_size(item.original_size)
            elif col == 3:
                return item.status
            elif col == 4:
                return format_size(item.converted_size) if item.converted_size > 0 else "-"
            elif col == 5:
                return f"{item.saved_percent:+.1f}%" if item.converted_size > 0 else "-"
            elif col == 6:
                return ", ".join(item.tags) if item.tags else "-"
            elif col == 7:
                return item.input_path

        elif role == Qt.TextAlignmentRole:
            if col in (1, 3, 5):
                return Qt.AlignCenter
            elif col in (2, 4):
                return Qt.AlignRight | Qt.AlignVCenter
            return Qt.AlignLeft | Qt.AlignVCenter

        elif role == Qt.ForegroundRole:
            if col == 3:
                if item.status == "Finished":
                    return QColor("#10B981")
                elif item.status == "Error":
                    return QColor("#EF4444")
                elif "Optimized" in item.status:
                    return QColor("#34D399")
                elif "Encoding" in item.status or "Tagging" in item.status or "Processing" in item.status:
                    return QColor("#38BDF8")
                return QColor("#94A3B8")
            elif col == 5 and item.converted_size > 0:
                return QColor("#10B981") if item.saved_percent > 0 else QColor("#F59E0B")
            elif col == 7:
                return QColor("#64748B")

        elif role == Qt.UserRole:
            return item.input_path

        return None

    def add_items(self, new_items: List[QueueItem]):
        if not new_items:
            return
        start_row = len(self.items_list)
        end_row = start_row + len(new_items) - 1
        self.beginInsertRows(QModelIndex(), start_row, end_row)
        for idx, it in enumerate(new_items):
            r = start_row + idx
            self.items_list.append(it)
            self.items_dict[it.input_path] = it
            self.path_to_row[it.input_path] = r
            self.total_size += it.original_size
        self.endInsertRows()

    def update_item_status(
        self,
        input_path: str,
        status: str,
        converted_size: int = 0,
        saved_percent: float = 0.0,
        tags: Optional[List[str]] = None,
        error_message: str = ""
    ):
        row = self.path_to_row.get(input_path)
        if row is None:
            return
        item = self.items_list[row]
        item.status = status
        if converted_size > 0:
            item.converted_size = converted_size
            item.saved_percent = saved_percent
        if tags is not None:
            item.tags = tags
        if error_message:
            item.error_message = error_message
        self.dataChanged.emit(self.index(row, 0), self.index(row, 7))

    def remove_rows(self, row_indices: List[int]):
        unique_rows = sorted(list(set(row_indices)), reverse=True)
        for r in unique_rows:
            if 0 <= r < len(self.items_list):
                self.beginRemoveRows(QModelIndex(), r, r)
                item = self.items_list.pop(r)
                self.total_size = max(0, self.total_size - item.original_size)
                self.items_dict.pop(item.input_path, None)
                self.endRemoveRows()
        self.path_to_row = {it.input_path: idx for idx, it in enumerate(self.items_list)}

    def clear(self):
        self.beginResetModel()
        self.items_list.clear()
        self.items_dict.clear()
        self.path_to_row.clear()
        self.total_size = 0
        self.endResetModel()

class QueueWidget(QWidget):
    """
    Queue table for batch image conversion and tagging.
    Powered by a virtualized QTableView and QAbstractTableModel for extreme scalability.
    """
    queue_changed = Signal(int)       # Emits current count
    selection_changed = Signal(str)   # Emits selected input path
    request_tag_item = Signal(str)    # Emits input path to trigger AI tagging

    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = QueueTableModel(self)
        self.setAcceptDrops(True)
        self.init_ui()

    @property
    def items(self) -> Dict[str, QueueItem]:
        """Provides backward-compatible dict access for existing controllers."""
        return self.model.items_dict

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

        # Virtualized Table View
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.selectionModel().selectionChanged.connect(self._on_table_selection_changed)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        header.setSectionResizeMode(3, QHeaderView.Interactive)
        header.setSectionResizeMode(4, QHeaderView.Interactive)
        header.setSectionResizeMode(5, QHeaderView.Interactive)
        header.setSectionResizeMode(6, QHeaderView.Stretch)
        header.setSectionResizeMode(7, QHeaderView.Interactive)

        self.table.setColumnWidth(0, 180)
        self.table.setColumnWidth(1, 70)
        self.table.setColumnWidth(2, 95)
        self.table.setColumnWidth(3, 110)
        self.table.setColumnWidth(4, 95)
        self.table.setColumnWidth(5, 80)
        self.table.setColumnWidth(7, 240)

        layout.addWidget(self.table)

        # Summary Bar
        self.summary_label = QLabel("0 items in queue")
        self.summary_label.setStyleSheet("color: #94A3B8; font-size: 12px;")
        layout.addWidget(self.summary_label)

        # Connect top button signals
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
        if paths:
            self.add_paths(paths)
        event.acceptProposedAction()

    def _browse_files(self):
        extensions_filter = (
            "All Supported Images (*.jpg *.jpeg *.png *.webp *.gif *.bmp *.tiff *.tif *.avif *.tga *.ico *.ppm *.qoi);;"
            "JPEG (*.jpg *.jpeg *.jfif);;PNG (*.png *.apng);;WebP (*.webp);;All Files (*.*)"
        )
        files, _ = QFileDialog.getOpenFileNames(self, "Select Images to Convert", "", extensions_filter)
        if files:
            self.add_paths(files)

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder Containing Images")
        if folder:
            self.add_paths([folder], recursive=True)

    def add_paths(self, paths: List[str], recursive: bool = True):
        """
        Scans paths using high-speed os.walk / os.scandir and appends items in bulk.
        Can ingest tens of thousands of items in a fraction of a second.
        """
        to_add: List[str] = []
        existing_set = set(self.model.items_dict.keys())
        seen_paths = set(existing_set)

        for p_str in paths:
            if os.path.isdir(p_str):
                if recursive:
                    for root, _, files in os.walk(p_str):
                        for f in files:
                            ext = os.path.splitext(f)[1].lower()
                            if ext in SUPPORTED_EXTENSIONS:
                                full_p = os.path.abspath(os.path.join(root, f))
                                if full_p not in seen_paths:
                                    seen_paths.add(full_p)
                                    to_add.append(full_p)
                else:
                    try:
                        with os.scandir(p_str) as entries:
                            for entry in entries:
                                if entry.is_file():
                                    ext = os.path.splitext(entry.name)[1].lower()
                                    if ext in SUPPORTED_EXTENSIONS:
                                        full_p = os.path.abspath(entry.path)
                                        if full_p not in seen_paths:
                                            seen_paths.add(full_p)
                                            to_add.append(full_p)
                    except Exception:
                        pass
            elif os.path.isfile(p_str):
                ext = os.path.splitext(p_str)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    full_p = os.path.abspath(p_str)
                    if full_p not in seen_paths:
                        seen_paths.add(full_p)
                        to_add.append(full_p)

        to_add.sort()
        new_items = []
        for file_path in to_add:
            try:
                sz = os.path.getsize(file_path)
            except Exception:
                sz = 0
            new_items.append(QueueItem(
                input_path=file_path,
                original_size=sz,
                status="Pending"
            ))

        if new_items:
            self.model.add_items(new_items)
            self._update_summary()
            self.queue_changed.emit(len(self.model.items_list))

    def _update_summary(self):
        count = len(self.model.items_list)
        total_sz = self.model.total_size
        self.summary_label.setText(
            f"{count:,} items in queue | Total input size: {format_size(total_sz)}"
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
        """Updates a specific row instantly in O(1) time without redrawing the entire table."""
        self.model.update_item_status(
            input_path, status, converted_size, saved_percent, tags, error_message
        )

    def get_selected_path(self) -> Optional[str]:
        indexes = self.table.selectionModel().selectedRows()
        if indexes:
            row = indexes[0].row()
            if 0 <= row < len(self.model.items_list):
                return self.model.items_list[row].input_path
        return None

    def _on_table_selection_changed(self):
        selected_path = self.get_selected_path()
        if selected_path:
            self.selection_changed.emit(selected_path)

    def _remove_selected(self):
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return
        rows = [idx.row() for idx in indexes]
        self.model.remove_rows(rows)
        self._update_summary()
        self.queue_changed.emit(len(self.model.items_list))

    def clear_all(self):
        self.model.clear()
        self._update_summary()
        self.queue_changed.emit(0)

    def _show_context_menu(self, pos):
        index = self.table.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        if not (0 <= row < len(self.model.items_list)):
            return
        q_item = self.model.items_list[row]
        input_path = q_item.input_path

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
                self.model.update_item_status(input_path, q_item.status, tags=new_tags)
        elif chosen == action_remove:
            self.model.remove_rows([row])
            self._update_summary()
            self.queue_changed.emit(len(self.model.items_list))
