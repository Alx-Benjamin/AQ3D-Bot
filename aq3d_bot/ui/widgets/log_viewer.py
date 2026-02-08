from __future__ import annotations

import time

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QColor, QTextCharFormat
from PySide6.QtWidgets import (
    QTextEdit, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QCheckBox,
)


LOG_COLORS = {
    "DEBUG": QColor("#9399b2"),
    "INFO": QColor("#cdd6f4"),
    "SUCCESS": QColor("#a6e3a1"),
    "WARNING": QColor("#fab387"),
    "ERROR": QColor("#f38ba8"),
}

MAX_LOG_LINES = 500


class LogViewer(QWidget):
    """Colored, auto-scrolling log viewer widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._line_count = 0
        self._show_debug = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        header_row = QHBoxLayout()
        header = QLabel("Logs")
        header.setObjectName("heading")
        header_row.addWidget(header)
        header_row.addStretch()
        self._debug_check = QCheckBox("Show DEBUG")
        self._debug_check.setChecked(False)
        self._debug_check.stateChanged.connect(self._on_debug_toggled)
        header_row.addWidget(self._debug_check)
        layout.addLayout(header_row)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setObjectName("log_text")
        layout.addWidget(self._text)

        # Store raw entries for re-rendering when debug toggle changes
        self._entries: list[tuple[str, str, str]] = []  # (timestamp, level, message)

    @Slot(str, str)
    def append_log(self, message: str, level: str = "INFO") -> None:
        """Append a log entry with colored formatting."""
        timestamp = time.strftime("%H:%M:%S")

        # Store raw entry
        self._entries.append((timestamp, level, message))
        if len(self._entries) > MAX_LOG_LINES:
            self._entries = self._entries[-MAX_LOG_LINES:]

        # Skip rendering if DEBUG and toggle is off
        if level == "DEBUG" and not self._show_debug:
            return

        self._render_entry(timestamp, level, message)

    def _render_entry(self, timestamp: str, level: str, message: str) -> None:
        """Render a single log entry into the text widget."""
        color = LOG_COLORS.get(level, LOG_COLORS["INFO"])
        fmt = QTextCharFormat()

        fmt.setForeground(QColor("#9399b2"))
        cursor = self._text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(f"[{timestamp}] ", fmt)

        fmt.setForeground(color)
        cursor.insertText(f"[{level}] {message}\n", fmt)

        self._line_count += 1

        # Trim old lines
        if self._line_count > MAX_LOG_LINES:
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.movePosition(
                cursor.MoveOperation.Down,
                cursor.MoveMode.KeepAnchor,
                self._line_count - MAX_LOG_LINES,
            )
            cursor.removeSelectedText()
            self._line_count = MAX_LOG_LINES

        # Auto-scroll
        scrollbar = self._text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _on_debug_toggled(self, state: int) -> None:
        self._show_debug = bool(state)
        self._rerender()

    def _rerender(self) -> None:
        """Re-render all stored entries respecting current filter."""
        self._text.clear()
        self._line_count = 0
        for timestamp, level, message in self._entries:
            if level == "DEBUG" and not self._show_debug:
                continue
            self._render_entry(timestamp, level, message)

    def clear_logs(self) -> None:
        self._text.clear()
        self._line_count = 0
        self._entries.clear()
