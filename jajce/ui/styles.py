DARK_THEME_QSS = """
/* JAJCE Modern Dark Theme */
QWidget {
    background-color: #121418;
    color: #E2E8F0;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
}

QMainWindow, QDialog {
    background-color: #0E1013;
}

QGroupBox {
    background-color: #181B21;
    border: 1px solid #282E39;
    border-radius: 8px;
    margin-top: 18px;
    padding-top: 16px;
    padding-bottom: 12px;
    padding-left: 12px;
    padding-right: 12px;
    font-weight: 600;
    color: #60A5FA;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 6px;
    background-color: #181B21;
}

QLabel {
    color: #CBD5E1;
}

QLabel#HeaderTitle {
    font-size: 22px;
    font-weight: 700;
    color: #F8FAFC;
}

QLabel#HeaderSubtitle {
    font-size: 12px;
    color: #94A3B8;
}

QPushButton {
    background-color: #1E232B;
    border: 1px solid #333C4D;
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 500;
    color: #F1F5F9;
}

QPushButton:hover {
    background-color: #28303C;
    border-color: #3B82F6;
}

QPushButton:pressed {
    background-color: #1B2129;
}

QPushButton:disabled {
    background-color: #15181E;
    border-color: #222731;
    color: #64748B;
}

QPushButton#PrimaryButton {
    background-color: #2563EB;
    border: 1px solid #3B82F6;
    color: #FFFFFF;
    font-weight: 600;
    font-size: 14px;
    padding: 9px 24px;
}

QPushButton#PrimaryButton:hover {
    background-color: #1D4ED8;
    border-color: #60A5FA;
}

QPushButton#PrimaryButton:pressed {
    background-color: #1E40AF;
}

QPushButton#DangerButton {
    background-color: #7F1D1D;
    border: 1px solid #991B1B;
    color: #FCA5A5;
}

QPushButton#DangerButton:hover {
    background-color: #991B1B;
}

QTableWidget {
    background-color: #15181E;
    alternate-background-color: #181B21;
    border: 1px solid #252A34;
    border-radius: 8px;
    gridline-color: #1E222A;
    selection-background-color: #2563EB;
    selection-color: #FFFFFF;
}

QHeaderView::section {
    background-color: #1A1E26;
    color: #94A3B8;
    padding: 8px;
    border: none;
    border-bottom: 2px solid #282E39;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
}

QScrollBar:vertical {
    border: none;
    background: #121418;
    width: 10px;
    margin: 0px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background: #2D3442;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #3B82F6;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background: #121418;
    height: 10px;
    margin: 0px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background: #2D3442;
    min-width: 20px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal:hover {
    background: #3B82F6;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

QSlider::groove:horizontal {
    border: 1px solid #2A303C;
    height: 6px;
    background: #181B21;
    margin: 2px 0;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #3B82F6;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #60A5FA;
    border: 1px solid #93C5FD;
    width: 16px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}

QSlider::handle:horizontal:hover {
    background: #93C5FD;
}

QRadioButton {
    spacing: 8px;
    color: #E2E8F0;
    font-weight: 500;
}

QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border-radius: 8px;
    border: 2px solid #475569;
    background-color: #181B21;
}

QRadioButton::indicator:checked {
    border-color: #3B82F6;
    background-color: #2563EB;
}

QCheckBox {
    spacing: 8px;
    color: #E2E8F0;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #475569;
    background-color: #181B21;
}

QCheckBox::indicator:checked {
    border-color: #3B82F6;
    background-color: #2563EB;
}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #1A1E26;
    border: 1px solid #2D3442;
    border-radius: 6px;
    padding: 6px 10px;
    color: #F1F5F9;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border-color: #3B82F6;
}

QProgressBar {
    border: 1px solid #282E39;
    border-radius: 6px;
    background-color: #15181E;
    text-align: center;
    color: #F8FAFC;
    font-weight: 600;
    height: 20px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563EB, stop:1 #06B6D4);
    border-radius: 5px;
}

QTextEdit, QPlainTextEdit {
    background-color: #101317;
    border: 1px solid #232832;
    border-radius: 6px;
    color: #94A3B8;
    font-family: "Cascadia Code", "Consolas", monospace;
    font-size: 11px;
}

QToolTip {
    background-color: #1E232B;
    border: 1px solid #3B82F6;
    color: #F8FAFC;
    padding: 6px 10px;
    border-radius: 4px;
}
"""
