"""Detect translation columns such as ``label::English`` and ``label:English``."""

from __future__ import annotations

import logging
from collections.abc import Iterable

import pandas as pd

from core.models import LabelColumn

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
        return None


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
