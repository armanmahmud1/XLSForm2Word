"""Pre-generation validation with clear, user-friendly messages."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from core.errors import ValidationError
from core.language_detector import LanguageDetector
from core.models import GenerationRequest, XLSForm
from utils.config import COLUMN_NAMES

logger = logging.getLogger(__name__)


class GenerationValidator:
    """Validate every requirement before a document is generated."""

    def validate_request(self, request: GenerationRequest) -> GenerationRequest:
        errors: list[str] = []
        form_path = Path(request.form_path).expanduser()
        output_folder = Path(request.output_folder).expanduser()

        if not str(request.form_path).strip():
            errors.append("Select an XLSForm file.")
        elif not form_path.exists() or not form_path.is_file():
            errors.append("The selected XLSForm file does not exist.")
        elif form_path.suffix.casefold() not in {".xlsx", ".xls"}:
            errors.append("Select a valid XLSForm (.xlsx or .xls).")

        if not str(request.output_folder).strip():
            errors.append("Select an output folder.")
        elif not output_folder.exists() or not output_folder.is_dir():
            errors.append("The selected output folder does not exist.")
        elif not self._is_writable(output_folder):
            errors.append(
                "The selected output folder is not writable. Choose another folder."
            )

        languages = [item for item in request.languages if str(item).strip()]
        if not languages:
            errors.append("Select at least one language.")
        if len({item.casefold() for item in languages}) != len(languages):
            errors.append("Each selected language must be unique.")

        columns = [item for item in request.columns if item in COLUMN_NAMES]
        if not columns:
            errors.append("Select at least one column.")
        elif len(columns) != len(request.columns):
            errors.append("One or more selected columns are not valid.")

        if errors:
            logger.warning("Validation failed: %s", "; ".join(errors))
            raise ValidationError(errors)

        resolved = GenerationRequest(
            form_path=form_path.resolve(),
            output_folder=output_folder.resolve(),
            platform=request.platform,
            languages=tuple(languages),
            columns=tuple(columns),
        )
        logger.info(
            "Validation passed for %s (%s language(s), %s column(s))",
            resolved.form_path,
            len(resolved.languages),
            len(resolved.columns),
        )
        return resolved

    def validate_against_form(
        self,
        request: GenerationRequest,
        form: XLSForm,
    ) -> None:
        available = {
            item.language.casefold(): item.language
            for item in LanguageDetector().detect(form.survey)
        }
        missing = [
            language
            for language in request.languages
            if language.casefold() not in available
        ]
        if missing:
            raise ValidationError(
                "The selected workbook no longer contains the language column(s): "
                + ", ".join(missing)
                + ". Select the file again and choose an available language."
            )

    @staticmethod
    def _is_writable(folder: Path) -> bool:
        try:
            with tempfile.NamedTemporaryFile(
                dir=folder,
                prefix=".xlsform2word-write-",
                suffix=".tmp",
                delete=True,
            ):
                return True
        except OSError:
            return False
