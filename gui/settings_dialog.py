"""Application settings and support-path dialog."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from utils.config import SettingsManager
from utils.paths import log_file_path, open_in_explorer, settings_path
from utils.version import APP_NAME, APP_VERSION

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """Show portable storage locations and allow a safe preferences reset."""

    def __init__(
        self,
        manager: SettingsManager,
        icon: QIcon | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.manager = manager
        self.reset_requested = False
        self.setWindowTitle(f"{APP_NAME} Settings")
        self.setWindowIcon(icon or QIcon())
        self.setMinimumWidth(590)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 20)
        layout.setSpacing(14)

        title = QLabel("Settings & Support")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        subtitle = QLabel(
            f"{APP_NAME} v{APP_VERSION} stores preferences next to the "
            "application so it remains portable."
        )
        subtitle.setWordWrap(True)
        subtitle.setObjectName("MutedLabel")
        layout.addWidget(subtitle)

        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(10)

        card_layout.addWidget(self._path_row("Settings file", settings_path()))
        card_layout.addWidget(self._path_row("Log file", log_file_path()))
        layout.addWidget(card)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        open_settings = QPushButton("Open Settings Folder")
        open_settings.clicked.connect(lambda: self._open(settings_path().parent))
        open_logs = QPushButton("Open Logs")
        open_logs.clicked.connect(lambda: self._open(log_file_path().parent))
        reset = QPushButton("Reset Preferences")
        reset.setObjectName("DangerButton")
        reset.clicked.connect(self._reset)
        actions.addWidget(open_settings)
        actions.addWidget(open_logs)
        actions.addStretch(1)
        actions.addWidget(reset)
        layout.addLayout(actions)

        layout.addSpacing(4)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    @staticmethod
    def _path_row(label_text: str, path: Path) -> QWidget:
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        label = QLabel(label_text)
        label.setFixedWidth(84)
        label.setStyleSheet("color: #6B7280; font-size: 9pt;")
        field = QLineEdit(str(path))
        field.setReadOnly(True)
        field.setToolTip(str(path))
        field.setCursorPosition(0)
        row.addWidget(label)
        row.addWidget(field, 1)
        return container

    def _open(self, path: Path) -> None:
        try:
            open_in_explorer(path)
        except OSError as exc:
            logger.warning("Could not open %s: %s", path, exc)
            QMessageBox.warning(
                self,
                "Cannot Open Folder",
                f"The folder could not be opened:\n{path}",
            )

    def _reset(self) -> None:
        answer = QMessageBox.question(
            self,
            "Reset Preferences",
            "Reset the platform, output folder, and selected columns to their "
            "defaults?\n\nThis does not delete any generated documents.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.manager.reset()
        self.reset_requested = True
        self.accept()
