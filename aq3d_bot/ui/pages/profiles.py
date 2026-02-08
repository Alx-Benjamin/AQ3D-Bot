from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QListWidget,
    QListWidgetItem, QLineEdit, QMessageBox, QInputDialog, QFileDialog,
)

from ...models.profile import Profile


class ProfilesPage(QWidget):
    """Profile management page — create, rename, duplicate, delete, export, import profiles."""

    profile_switched = Signal(str)       # emits profile name
    profiles_list_changed = Signal()  # emits when list of profiles changes

    def __init__(self, profiles_dir: str = "profiles", parent=None):
        super().__init__(parent)
        self._profiles_dir = profiles_dir

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        header = QLabel("Profiles")
        header.setObjectName("heading")
        layout.addWidget(header)

        desc = QLabel("Each profile stores skills, rotation, cooldowns, potions, and combat settings for a class.")
        desc.setWordWrap(True)
        desc.setObjectName("subheading")
        layout.addWidget(desc)

        # Profile list
        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._on_selection_changed)
        layout.addWidget(self._list, stretch=1)

        # Action buttons row 1
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self._new_btn = QPushButton("New Profile")
        self._new_btn.clicked.connect(self._create_profile)
        btn_layout.addWidget(self._new_btn)

        self._duplicate_btn = QPushButton("Duplicate")
        self._duplicate_btn.clicked.connect(self._duplicate_profile)
        btn_layout.addWidget(self._duplicate_btn)

        self._rename_btn = QPushButton("Rename")
        self._rename_btn.clicked.connect(self._rename_profile)
        btn_layout.addWidget(self._rename_btn)

        self._delete_btn = QPushButton("Delete")
        self._delete_btn.setStyleSheet("background-color: #f38ba8; color: #1e1e2e;")
        self._delete_btn.clicked.connect(self._delete_profile)
        btn_layout.addWidget(self._delete_btn)

        self._switch_btn = QPushButton("Switch to Selected")
        self._switch_btn.setStyleSheet("background-color: #a6e3a1; color: #1e1e2e;")
        self._switch_btn.clicked.connect(self._switch_profile)
        btn_layout.addWidget(self._switch_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Action buttons row 2 — Export / Import
        io_layout = QHBoxLayout()
        io_layout.setSpacing(8)

        self._export_btn = QPushButton("Export Profile")
        self._export_btn.clicked.connect(self._export_profile)
        io_layout.addWidget(self._export_btn)

        self._import_btn = QPushButton("Import Profile")
        self._import_btn.clicked.connect(self._import_profile)
        io_layout.addWidget(self._import_btn)

        io_layout.addStretch()
        layout.addLayout(io_layout)

        self._update_buttons()

    def refresh_list(self, current_name: str = "") -> None:
        """Reload the profile list from disk."""
        self._list.clear()
        names = Profile.list_profiles(self._profiles_dir)

        if not names:
            # Create default profile
            Profile(name="Default").save(self._profiles_dir)
            names = ["Default"]

        for name in names:
            item = QListWidgetItem(name)
            self._list.addItem(item)
            if name == current_name:
                self._list.setCurrentItem(item)

        self._update_buttons()
        self.profiles_list_changed.emit()

    def _get_selected_name(self) -> str | None:
        item = self._list.currentItem()
        return item.text() if item else None

    def _update_buttons(self) -> None:
        has_selection = self._list.currentItem() is not None
        self._duplicate_btn.setEnabled(has_selection)
        self._rename_btn.setEnabled(has_selection)
        self._delete_btn.setEnabled(has_selection and self._list.count() > 1)
        self._switch_btn.setEnabled(has_selection)
        self._export_btn.setEnabled(has_selection)

    def _on_selection_changed(self) -> None:
        self._update_buttons()

    def _create_profile(self) -> None:
        name, ok = QInputDialog.getText(self, "New Profile", "Profile name:")
        if ok and name.strip():
            name = name.strip()
            existing = Profile.list_profiles(self._profiles_dir)
            if name in existing:
                QMessageBox.warning(self, "Duplicate", f"Profile '{name}' already exists.")
                return
            Profile(name=name).save(self._profiles_dir)
            self.refresh_list(name)

    def _duplicate_profile(self) -> None:
        source_name = self._get_selected_name()
        if not source_name:
            return
        name, ok = QInputDialog.getText(
            self, "Duplicate Profile", "New profile name:", text=f"{source_name} Copy"
        )
        if ok and name.strip():
            name = name.strip()
            existing = Profile.list_profiles(self._profiles_dir)
            if name in existing:
                QMessageBox.warning(self, "Duplicate", f"Profile '{name}' already exists.")
                return
            source = Profile.load(source_name, self._profiles_dir)
            dup = source.duplicate(name)
            dup.save(self._profiles_dir)
            self.refresh_list(name)

    def _rename_profile(self) -> None:
        old_name = self._get_selected_name()
        if not old_name:
            return
        new_name, ok = QInputDialog.getText(
            self, "Rename Profile", "New name:", text=old_name
        )
        if ok and new_name.strip() and new_name.strip() != old_name:
            new_name = new_name.strip()
            existing = Profile.list_profiles(self._profiles_dir)
            if new_name in existing:
                QMessageBox.warning(self, "Duplicate", f"Profile '{new_name}' already exists.")
                return
            profile = Profile.load(old_name, self._profiles_dir)
            profile.rename(new_name, self._profiles_dir)
            self.refresh_list(new_name)

    def _delete_profile(self) -> None:
        name = self._get_selected_name()
        if not name:
            return
        if self._list.count() <= 1:
            QMessageBox.warning(self, "Cannot Delete", "You must have at least one profile.")
            return
        reply = QMessageBox.question(
            self, "Delete Profile", f"Delete profile '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            Profile(name=name).delete(self._profiles_dir)
            self.refresh_list()

    def _switch_profile(self) -> None:
        name = self._get_selected_name()
        if name:
            self.profile_switched.emit(name)

    def _export_profile(self) -> None:
        """Export the selected profile to a JSON file."""
        name = self._get_selected_name()
        if not name:
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Profile", f"{name}.json",
            "JSON Files (*.json);;All Files (*)",
        )
        if not path:
            return

        try:
            profile = Profile.load(name, self._profiles_dir)
            profile.export_to_file(path)
            QMessageBox.information(self, "Export Successful", f"Profile '{name}' exported to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Failed to export profile:\n{e}")

    def _import_profile(self) -> None:
        """Import a profile from a JSON file."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Profile", "",
            "JSON Files (*.json);;All Files (*)",
        )
        if not path:
            return

        try:
            profile = Profile.import_from_file(path)
        except Exception as e:
            QMessageBox.critical(self, "Import Failed", f"Failed to read profile file:\n{e}")
            return

        # Check for name collision
        existing = Profile.list_profiles(self._profiles_dir)
        if profile.name in existing:
            name, ok = QInputDialog.getText(
                self, "Name Conflict",
                f"Profile '{profile.name}' already exists. Enter a new name:",
                text=f"{profile.name} (Imported)",
            )
            if not ok or not name.strip():
                return
            profile.name = name.strip()

        profile.save(self._profiles_dir)
        self.refresh_list(profile.name)
        QMessageBox.information(self, "Import Successful", f"Profile '{profile.name}' imported.")
