import sys
import os
import ctypes
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from jajce.ui.main_window import MainWindow
from jajce.ui.styles import DARK_THEME_QSS

def create_application() -> QApplication:
    # Set Windows App User Model ID so the taskbar displays the custom icon
    if sys.platform == "win32":
        try:
            myappid = "LeeAtSchool.JAJCE.JPEGXLConverter.1.0"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    app.setApplicationName("JAJCE")
    app.setApplicationDisplayName("JAJCE — Just Another JPEG Conversion Engine")
    app.setStyleSheet(DARK_THEME_QSS)

    # Set icon with 10.png as top priority
    icon_candidates = [
        Path(r"C:\Users\Aaron\Downloads\writref\10.png"),
        Path(__file__).resolve().parent.parent / "assets" / "icon.ico",
        Path(__file__).resolve().parent.parent / "assets" / "icon.png",
        Path(r"C:\Users\Aaron\Downloads\writref.png"),
    ]
    for c in icon_candidates:
        if c.exists():
            app.setWindowIcon(QIcon(str(c)))
            break

    return app

def run_app():
    app = create_application()
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
