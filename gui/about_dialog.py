"""About dialog."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from utils.version import (
    APP_NAME,
    APP_VERSION,
    AUTHOR,
    DESCRIPTION,
    WEBSITE,
)


class AboutDialog(QDialog):
    def __init__(
        self,
        icon: QIcon | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        self.setWindowIcon(icon or QIcon())
        self.setFixedWidth(500)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 22)
        layout.setSpacing(14)

        header = QHBoxLayout()
        header.setSpacing(16)

        if icon is not None and not icon.isNull():
            icon_label = QLabel()
            icon_label.setPixmap(icon.pixmap(72, 72))
            icon_label.setFixedSize(76, 76)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            header.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignTop)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        title = QLabel(APP_NAME)
        title.setStyleSheet("font-size: 22px; font-weight: 600; color: #1B5E20;")
        version = QLabel(f"Version: v{APP_VERSION}")
        version.setStyleSheet("color: #6B7280; font-size: 10pt;")
        title_layout.addWidget(title)
        title_layout.addWidget(version)
        title_layout.addStretch(1)
        header.addLayout(title_layout, 1)
        layout.addLayout(header)

        description = QLabel(DESCRIPTION)
        description.setWordWrap(True)
        description.setStyleSheet("color: #374151; font-size: 10pt;")
        layout.addWidget(description)

        divider = QLabel()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background: #E5E7EB;")
        layout.addWidget(divider)

        details = QVBoxLayout()
        details.setSpacing(7)
        details.addLayout(self._row("Developed by:", AUTHOR))
        website = QLabel(
            f'<a href="{WEBSITE}" style="color:#2E7D32; '
            f'text-decoration:none;">{WEBSITE}</a>'
        )
        website.setOpenExternalLinks(True)
        website.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        details.addLayout(self._row("Website:", website))
        layout.addLayout(details)

        layout.addSpacing(8)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    @staticmethod
    def _row(label_text: str, value: str | QLabel) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)
        label = QLabel(label_text)
        label.setStyleSheet("color: #6B7280; font-size: 9pt;")
        label.setFixedWidth(96)
        row.addWidget(label)
        if isinstance(value, QLabel):
            row.addWidget(value, 1)
        else:
            text = QLabel(value)
            text.setStyleSheet("color: #1F2937; font-size: 9pt;")
            row.addWidget(text, 1)
        return row
