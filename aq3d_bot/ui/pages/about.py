from __future__ import annotations

import webbrowser

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton


class AboutPage(QWidget):
    """About page with project info and links."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        header = QLabel("About AQ3D Bot")
        header.setObjectName("heading")
        layout.addWidget(header)

        layout.addWidget(QLabel("A customizable automation bot for AdventureQuest 3D."))
        layout.addWidget(QLabel("Built with Python + PySide6"))

        # Version
        version_label = QLabel("Version 4.0.0")
        version_label.setStyleSheet("color: #89b4fa; font-weight: bold;")
        layout.addWidget(version_label)

        # Links
        links_layout = QHBoxLayout()
        links_layout.setSpacing(8)

        source_btn = QPushButton("Source Code")
        source_btn.clicked.connect(
            lambda: webbrowser.open_new_tab("https://github.com/Alx-Benjamin/AQ3D-Bot")
        )
        links_layout.addWidget(source_btn)

        discord_btn = QPushButton("Discord")
        discord_btn.clicked.connect(
            lambda: webbrowser.open_new_tab("https://discord.gg/MfW5Mt7KUe")
        )
        links_layout.addWidget(discord_btn)

        donate_btn = QPushButton("Donate")
        donate_btn.clicked.connect(
            lambda: webbrowser.open_new_tab("https://buymeacoffee.com/deadlink")
        )
        links_layout.addWidget(donate_btn)

        links_layout.addStretch()
        layout.addLayout(links_layout)

        layout.addStretch()
