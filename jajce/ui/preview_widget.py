import os
from pathlib import Path
from typing import List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame, QHBoxLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage
from PIL import Image

class PreviewWidget(QWidget):
    """
    Side panel displaying image preview, resolution, color mode, and tag chips.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        title = QLabel("Image Details & Tags")
        title.setStyleSheet("font-weight: 700; color: #60A5FA; font-size: 14px;")
        layout.addWidget(title)

        # Thumbnail display container
        self.thumb_container = QFrame()
        self.thumb_container.setStyleSheet(
            "background-color: #101216; border: 1px solid #232832; border-radius: 8px;"
        )
        self.thumb_container.setMinimumHeight(240)
        self.thumb_container.setMaximumHeight(320)
        thumb_layout = QVBoxLayout(self.thumb_container)
        thumb_layout.setAlignment(Qt.AlignCenter)

        self.lbl_image = QLabel("No image selected")
        self.lbl_image.setAlignment(Qt.AlignCenter)
        self.lbl_image.setStyleSheet("color: #64748B;")
        thumb_layout.addWidget(self.lbl_image)

        layout.addWidget(self.thumb_container)

        # Metadata labels
        self.lbl_filename = QLabel("Name: -")
        self.lbl_filename.setStyleSheet("font-weight: 600; color: #F1F5F9;")
        self.lbl_filename.setWordWrap(True)

        self.lbl_dimensions = QLabel("Dimensions: -")
        self.lbl_dimensions.setStyleSheet("color: #94A3B8;")

        self.lbl_filesize = QLabel("Size: -")
        self.lbl_filesize.setStyleSheet("color: #94A3B8;")

        layout.addWidget(self.lbl_filename)
        layout.addWidget(self.lbl_dimensions)
        layout.addWidget(self.lbl_filesize)

        # Tags Section
        tags_header = QLabel("Identified Tags / Items:")
        tags_header.setStyleSheet("font-weight: 600; color: #38BDF8; margin-top: 8px;")
        layout.addWidget(tags_header)

        # Tags container
        self.tags_scroll = QScrollArea()
        self.tags_scroll.setWidgetResizable(True)
        self.tags_scroll.setStyleSheet("background: transparent; border: none;")
        self.tags_widget = QWidget()
        self.tags_widget.setStyleSheet("background: transparent;")
        self.tags_layout = QVBoxLayout(self.tags_widget)
        self.tags_layout.setContentsMargins(0, 0, 0, 0)
        self.tags_layout.setSpacing(4)
        self.tags_layout.setAlignment(Qt.AlignTop)

        self.lbl_no_tags = QLabel("No tags identified yet")
        self.lbl_no_tags.setStyleSheet("color: #64748B; font-style: italic;")
        self.tags_layout.addWidget(self.lbl_no_tags)

        self.tags_scroll.setWidget(self.tags_widget)
        layout.addWidget(self.tags_scroll)

        layout.addStretch()

    def set_image(self, file_path: str, tags: Optional[List[str]] = None):
        p = Path(file_path)
        if not p.exists():
            return

        self.lbl_filename.setText(f"Name: {p.name}")
        size_bytes = os.path.getsize(file_path)
        self.lbl_filesize.setText(f"Size: {size_bytes / 1024:.1f} KB")

        try:
            with Image.open(file_path) as pil_img:
                w, h = pil_img.size
                mode = pil_img.mode
                self.lbl_dimensions.setText(f"Dimensions: {w} × {h} ({mode})")

                # Generate thumbnail
                thumb = pil_img.copy()
                thumb.thumbnail((260, 240))
                thumb = thumb.convert("RGBA")
                data = thumb.tobytes("raw", "RGBA")
                qimg = QImage(data, thumb.width, thumb.height, QImage.Format_RGBA8888)
                pix = QPixmap.fromImage(qimg)
                self.lbl_image.setPixmap(pix)
        except Exception:
            self.lbl_image.setText("Unable to load preview")
            self.lbl_dimensions.setText("Dimensions: Unknown")

        self.update_tags(tags or [])

    def update_tags(self, tags: List[str]):
        # Clear existing tags
        while self.tags_layout.count():
            child = self.tags_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not tags:
            lbl = QLabel("No tags identified yet")
            lbl.setStyleSheet("color: #64748B; font-style: italic;")
            self.tags_layout.addWidget(lbl)
            return

        # Display tags as chips
        for tag in tags:
            chip = QLabel(f"  🏷️  {tag}  ")
            chip.setStyleSheet(
                "background-color: #1E293B; color: #38BDF8; "
                "border: 1px solid #334155; border-radius: 10px; "
                "padding: 4px 8px; font-weight: 500; font-size: 11px;"
            )
            self.tags_layout.addWidget(chip)
