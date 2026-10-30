"""Background worker that keeps the UI responsive during generation."""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal, Slot

from core.errors import XLSForm2WordError
from core.generation_service import GenerationResult, GenerationService
from core.models import GenerationRequest

logger = logging.getLogger(__name__)


class GenerationWorker(QObject):
    """Run the conversion pipeline on a dedicated QThread."""

    progress = Signal(int, str)
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        request: GenerationRequest,
        service: GenerationService | None = None,
    ) -> None:
        super().__init__()
        self.request = request
        self.service = service or GenerationService()

    @Slot()
    def run(self) -> None:
        try:
            result: GenerationResult = self.service.generate(
                self.request,
                progress=lambda value, message: self.progress.emit(value, message),
            )
        except XLSForm2WordError as exc:
            message = getattr(exc, "message", str(exc))
            logger.warning("Generation stopped: %s", message)
            self.failed.emit(message)
        except Exception:
            logger.exception("Unexpected generation failure")
            self.failed.emit(
                "An unexpected error occurred while generating the documents. "
                "No traceback was shown. Please check the log file for details."
            )
        else:
            self.succeeded.emit(result)
