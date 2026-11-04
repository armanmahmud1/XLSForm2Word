"""Detect translation columns such as ``label::English`` and ``label:English``."""

from __future__ import annotations

import logging
from collections.abc import Iterable

import pandas as pd

from core.models import LabelColumn, Platform, XLSForm

logger = logging.getLogger(__name__)

LABEL_PREFIXES = ("label::", "label:")


class LanguageDetector:
    """Find every language declared by a ``label::<language>`` column."""

    def detect(self, frame: pd.DataFrame) -> list[LabelColumn]:
        return self.detect_from_columns(frame.columns)

    def detect_from_columns(self, columns: Iterable[object]) -> list[LabelColumn]:
        detected: list[LabelColumn] = []
        seen: set[str] = set()

        for raw_column in columns:
            column = str(raw_column).strip()
            language: str | None = None
            for prefix in LABEL_PREFIXES:
                if column.casefold().startswith(prefix):
                    language = column[len(prefix) :].strip()
                    break
            if not language:
                continue
            key = language.casefold()
            if key in seen:
                logger.warning(
                    "Duplicate language column for %r found; using %r",
                    language,
                    column,
                )
                continue
            seen.add(key)
            detected.append(LabelColumn(column=column, language=language))

        # Fallback: bare "label" column → language "Default"
        if not detected:
            for raw_column in columns:
                column = str(raw_column).strip()
                if column.casefold() == "label":
                    detected.append(LabelColumn(column=column, language="Default"))
                    break

        logger.info(
            "Detected language(s): %s",
            ", ".join(item.language for item in detected) or "none",
        )
        return detected

    @staticmethod
    def resolve(
        columns: Iterable[object],
        language: str,
    ) -> LabelColumn | None:
        for raw_column in columns:
            column = str(raw_column).strip()
            for prefix in LABEL_PREFIXES:
                if column.casefold().startswith(prefix):
                    candidate = column[len(prefix) :].strip()
                    if candidate.casefold() == language.casefold():
                        return LabelColumn(column=column, language=candidate)
                    break

        # Fallback: bare "label" column for language "Default"
        if language.casefold() == "default":
            for raw_column in columns:
                column = str(raw_column).strip()
                if column.casefold() == "label":
                    return LabelColumn(column=column, language="Default")

        return None


def detect_platform(form: XLSForm) -> Platform:
    """Auto-detect the XLSForm platform from column names.

    - Choices sheet has ``value`` but not ``name`` → SurveyCTO
    - Choices sheet has ``name`` but not ``value`` → ODK
    - Both exist → check survey for ``relevance`` vs ``relevant``
    - Default fallback → ODK
    """
    choices_cols = {str(c).strip().casefold() for c in form.choices.columns}
    has_value = "value" in choices_cols
    has_name = "name" in choices_cols

    if has_value and not has_name:
        return Platform.SURVEYCTO
    if has_name and not has_value:
        return Platform.ODK

    # Tiebreaker: inspect survey columns
    survey_cols = {str(c).strip().casefold() for c in form.survey.columns}
    if "relevance" in survey_cols and "relevant" not in survey_cols:
        return Platform.SURVEYCTO

    return Platform.ODK


def resolve_column(
    columns: Iterable[object],
    *candidates: str,
) -> str | None:
    """Return the first case-insensitive column match, or ``None``."""
    lookup = {str(column).strip().casefold(): str(column).strip() for column in columns}
    for candidate in candidates:
        match = lookup.get(candidate.casefold())
        if match is not None:
            return match
    return None


def translated_column(
    columns: Iterable[object],
    base_name: str,
    language: str,
) -> str | None:
    """Resolve a language-specific column, falling back to the base column."""
    return resolve_column(
        columns,
        f"{base_name}::{language}",
        f"{base_name}:{language}",
        base_name,
    )
