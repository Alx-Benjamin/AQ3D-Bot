"""AQ3D Bot — Entry point."""

import subprocess
import sys
import os

# Prevent Tesseract from spawning console windows || Thanks @tycreager on Discord for adding this contribution.
if sys.platform.startswith("win"):
    _original_popen = subprocess.Popen

    def _silent_popen(args, **kwargs):
        kwargs.setdefault("creationflags", subprocess.CREATE_NO_WINDOW)
        return _original_popen(args, **kwargs)

    subprocess.Popen = _silent_popen


def main():
    # DPI awareness on Windows
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    # Resolve application directory for settings.json, profiles/, resources/
    if getattr(sys, "frozen", False):
        app_dir = os.path.dirname(sys.executable)
    else:
        project_dir = os.path.dirname(os.path.abspath(__file__))
        app_dir = os.path.dirname(project_dir)
        if app_dir not in sys.path:
            sys.path.insert(0, app_dir)

    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt

    app = QApplication(sys.argv)
    app.setApplicationName("AQ3D Bot")
    app.setApplicationVersion("4.0.0")

    # Set working directory so settings.json and profiles/ resolve correctly
    os.chdir(app_dir)

    from aq3d_bot.ui.app import MainWindow

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
