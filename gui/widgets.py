"""Reusable PySide6 widgets."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class FileDropZone(QFrame):
    """A file selector that also accepts drag-and-drop from Explorer."""

    fileDropped = Signal(str)
    browseRequested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("DropZone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(78)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        badge = QLabel("XLS")
        badge.setObjectName("FileBadge")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(badge)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        self._title = QLabel("XLSForm file")
        self._title.setStyleSheet("font-weight: 600; color: #1F2937;")
        self._path = QLabel("Drag and drop an .xlsx or .xls file here, or browse.")
        self._path.setObjectName("PathLabel")
        self._path.setWordWrap(True)
        self._path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        text_layout.addWidget(self._title)
        text_layout.addWidget(self._path)
        layout.addLayout(text_layout, 1)

        self.browse_button = QPushButton("Browse XLSForm")
        self.browse_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_button.clicked.connect(self.browseRequested.emit)
        layout.addWidget(self.browse_button)

    def set_path(self, path: str | Path | None) -> None:
        if path:
            text = str(path)
            self._path.setText(text)
            self._path.setToolTip(text)
            self._title.setText("Selected XLSForm")
        else:
            self._path.setText("Drag and drop an .xlsx or .xls file here, or browse.")
            self._path.setToolTip("")
            self._title.setText("XLSForm file")

    def _set_dragging(self, active: bool) -> None:
        self.setProperty("dragging", active)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if self._first_local_file(event) is not None:
            event.acceptProposedAction()
            self._set_dragging(True)
        else:
            event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        self._set_dragging(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        self._set_dragging(False)
        path = self._first_local_file(event)
        if path is None:
            event.ignore()
            return
        event.acceptProposedAction()
        self.fileDropped.emit(str(path))

    @staticmethod
    def _first_local_file(event: QDragEnterEvent | QDropEvent) -> Path | None:
        mime = event.mimeData()
        if mime is None or not mime.hasUrls():
            return None
        for url in mime.urls():
            if url.isLocalFile():
                path = Path(url.toLocalFile())
                if path.is_file():
                    return path
        return None
