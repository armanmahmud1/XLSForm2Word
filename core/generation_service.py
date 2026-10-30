"""Application service that orchestrates validation, parsing and generation."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from core.errors import DocumentGenerationError, XLSForm2WordError
from core.language_detector import LanguageDetector
from core.models import GenerationRequest
from core.validator import GenerationValidator
from core.word_generator import WordGenerator
from core.xlsform_loader import XLSFormLoader
from utils.version import APP_NAME, APP_VERSION

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, str], None]


@dataclass(frozen=True)
class GenerationResult:
    request: GenerationRequest
    outputs: tuple[Path, ...]


class GenerationService:
    """Run the complete conversion pipeline independently of the GUI."""

    def __init__(
        self,
        validator: GenerationValidator | None = None,
        loader: XLSFormLoader | None = None,
        generator: WordGenerator | None = None,
    ) -> None:
        self.validator = validator or GenerationValidator()
        self.loader = loader or XLSFormLoader()
        self.generator = generator or WordGenerator()
        self.language_detector = LanguageDetector()

    def generate(
        self,
        request: GenerationRequest,
        progress: ProgressCallback | None = None,
    ) -> GenerationResult:
        def report(percent: int, message: str) -> None:
            if progress is not None:
                progress(max(0, min(100, percent)), message)

        logger.info(
            "%s v%s generation started | platform=%s | languages=%s | columns=%s",
            APP_NAME,
            APP_VERSION,
            request.platform.value,
            ", ".join(request.languages),
            ", ".join(request.columns),
        )
        report(2, "Loading form...")
        resolved = self.validator.validate_request(request)

        report(8, "Reading workbook...")
        form = self.loader.load(resolved.form_path)
        self.validator.validate_against_form(resolved, form)

        self.language_detector.detect(form.survey)
        logger.info(
            "Generating %s document(s) for questionnaire: %s",
            len(resolved.languages),
            form.questionnaire_name,
        )

        outputs: list[Path] = []
        language_count = len(resolved.languages)
        for index, language in enumerate(resolved.languages, start=1):
            base_percent = 12 + int(((index - 1) / language_count) * 80)
            report(
                base_percent,
                f"Generating documents... ({index} of {language_count}: {language})",
            )
            try:
                output = self.generator.generate(
                    form=form,
                    language=language,
                    platform=resolved.platform,
                    columns=resolved.columns,
                    output_folder=resolved.output_folder,
                )
            except XLSForm2WordError:
                raise
            except Exception as exc:
                logger.exception("Unexpected failure generating %s", language)
                raise DocumentGenerationError(
                    f"An unexpected error occurred while generating the "
                    f"{language} document: {exc}"
                ) from exc
            outputs.append(output)

        report(100, "Completed")
        logger.info(
            "Generation completed successfully: %s document(s) in %s",
            len(outputs),
            resolved.output_folder,
        )
        return GenerationResult(
            request=resolved,
            outputs=tuple(outputs),
        )
