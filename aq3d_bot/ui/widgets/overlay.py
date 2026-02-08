from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QPoint, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QCursor
from PySide6.QtWidgets import QWidget, QApplication


class OverlayWindow(QWidget):
    """Fullscreen transparent overlay for selecting screen regions or points.

    Usage:
        overlay = OverlayWindow()
        result = overlay.get_area()   # Returns (x1, y1, x2, y2) or None
        result = overlay.get_point()  # Returns (x, y) or None
    """

    area_selected = Signal(tuple)
    point_selected = Signal(tuple)
    selection_cancelled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self._mode: str = "area"  # "area" or "point"
        self._start_pos: QPoint | None = None
        self._current_pos: QPoint | None = None
        self._result: tuple | None = None

    def get_area(self) -> tuple[int, int, int, int] | None:
        """Show overlay and let user drag to select a rectangular area."""
        self._mode = "area"
        self._result = None
        self._show_fullscreen()
        return self._result

    def get_point(self) -> tuple[int, int] | None:
        """Show overlay and let user click to select a point."""
        self._mode = "point"
        self._result = None
        self._show_fullscreen()
        return self._result

    def _show_fullscreen(self) -> None:
        """Show the overlay covering all screens."""
        # Get the combined geometry of all screens
        screens = QApplication.screens()
        if not screens:
            return

        combined = screens[0].geometry()
        for screen in screens[1:]:
            combined = combined.united(screen.geometry())

        self.setGeometry(combined)
        self.showFullScreen()

        # Block until closed (modal behavior)
        loop = __import__("PySide6.QtCore", fromlist=["QEventLoop"]).QEventLoop()
        self.destroyed.connect(loop.quit)
        self._loop = loop
        loop.exec()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)

        # Semi-transparent dark overlay
        painter.fillRect(self.rect(), QColor(0, 0, 0, 80))

        # Draw selection rectangle
        if self._mode == "area" and self._start_pos and self._current_pos:
            pen = QPen(QColor("#f38ba8"), 2)
            painter.setPen(pen)
            rect = QRect(self._start_pos, self._current_pos).normalized()
            painter.drawRect(rect)

            # Light fill inside selection
            fill = QColor("#89b4fa")
            fill.setAlpha(30)
            painter.fillRect(rect, fill)

        painter.end()

    def _to_physical(self, pos: QPoint) -> tuple[int, int]:
        """Convert Qt logical position to physical screen pixels.

        Qt6 uses logical (device-independent) pixels internally, but
        PIL's ImageGrab.grab() needs actual physical screen pixels.
        On a 4K monitor at 150% scaling, logical coords are 1.5x too small.
        """
        screen = self.screen() or QApplication.primaryScreen()
        dpr = screen.devicePixelRatio() if screen else 1.0
        return (int(pos.x() * dpr), int(pos.y() * dpr))

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._start_pos = event.globalPosition().toPoint()
            self._current_pos = self._start_pos

    def mouseMoveEvent(self, event) -> None:
        if self._start_pos:
            self._current_pos = event.globalPosition().toPoint()
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return

        end = event.globalPosition().toPoint()

        if self._mode == "point":
            px, py = self._to_physical(end)
            self._result = (px, py)
        elif self._mode == "area" and self._start_pos:
            sx, sy = self._to_physical(self._start_pos)
            ex, ey = self._to_physical(end)
            x1 = min(sx, ex)
            y1 = min(sy, ey)
            x2 = max(sx, ex)
            y2 = max(sy, ey)
            # Ensure minimum 1px size
            if x2 - x1 < 1:
                x2 = x1 + 1
            if y2 - y1 < 1:
                y2 = y1 + 1
            self._result = (x1, y1, x2, y2)

        self._close()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self._result = None
            self._close()

    def _close(self) -> None:
        self._start_pos = None
        self._current_pos = None
        self.close()
        self.deleteLater()
        if hasattr(self, "_loop"):
            self._loop.quit()
