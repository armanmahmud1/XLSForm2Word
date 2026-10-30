from __future__ import annotations

from PySide6.QtWidgets import QApplication, QSizePolicy

from gui.widgets import FileDropZone
from utils.version import APP_VERSION


def test_application_version_is_patch_release() -> None:
    assert APP_VERSION == "1.0.2"


def test_file_drop_zone_path_label_can_shrink_horizontally() -> None:
    QApplication.instance() or QApplication([])
    drop_zone = FileDropZone()

    assert drop_zone._path.wordWrap()
    assert (
        drop_zone._path.sizePolicy().horizontalPolicy()
        == QSizePolicy.Policy.Ignored
    )
