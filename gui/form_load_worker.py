"""Background worker that keeps the UI responsive while reading XLSForms."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from core.errors import XLSForm2WordError
from core.language_detector import LanguageDetector
from core.xlsform_loader import XLSFormLoader

logger = logging.getLogger(__name__)


class FormLoadWorker(QObject):
    """Load and inspect an XLSForm on a dedicated QThread."""

    loaded = Signal(object, object)
    failed = Signal(str)

    def __init__(
        self,
        path: Path,
        loader: XLSFormLoader | None = None,
        language_detector: LanguageDetector | None = None,
    ) -> None:
        super().__init__()
        self.path = path
        self.loader = loader or XLSFormLoader()
        self.language_detector = language_detector or LanguageDetector()

    @Slot()
    def run(self) -> None:
        try:
            form = self.loader.load(self.path)
            languages = self.language_detector.detect(form.survey)
            if not languages:
                raise XLSForm2WordError(
                    "No language columns were found in the survey sheet. "
                    "Add at least one column such as 'label::English' and try again."
                )
        except XLSForm2WordError as exc:
            message = getattr(exc, "message", str(exc))
            logger.warning("Could not load XLSForm: %s", message)
            self.failed.emit(message)
        except Exception:
            logger.exception("Unexpected error while loading form")
            self.failed.emit(
                "An unexpected error occurred while reading the workbook. "
                "Please check that the file is a valid XLSForm."
            )
        else:
            self.loaded.emit(form, languages)
