"""Build choice lists from the XLSForm ``choices`` sheet."""

from __future__ import annotations

import logging
from collections import OrderedDict

import pandas as pd

from core.errors import XLSFormError
from core.language_detector import resolve_column
from core.models import Choice, Platform, XLSForm

logger = logging.getLogger(__name__)


class ChoicesBuilder:
    """Create a ``list_name -> choices`` dictionary for one language."""

    def build(
        self,
        form: XLSForm,
        platform: Platform | str,
        language: str,
    ) -> dict[str, list[Choice]]:
        platform_enum = (
            platform if isinstance(platform, Platform) else Platform(platform)
        )
        return self.build_from_frame(form.choices, platform_enum, language)

    def build_from_frame(
        self,
        choices_frame: pd.DataFrame,
        platform: Platform,
        language: str,
    ) -> dict[str, list[Choice]]:
        if choices_frame.empty:
            logger.info("Choices sheet is empty; no choice lists available")
            return {}

        list_column = resolve_column(choices_frame.columns, "list_name")
        if list_column is None:
            raise XLSFormError(
                "The choices sheet is missing the required 'list_name' column."
            )

        value_column = resolve_column(
            choices_frame.columns,
            platform.choice_value_column,
            platform.choice_value_fallback,
        )
        if value_column is None:
            expected = platform.choice_value_column
            raise XLSFormError(
                f"The choices sheet is missing the required '{expected}' column "
                f"for {platform.value} forms."
            )
        if value_column.casefold() != platform.choice_value_column.casefold():
            logger.info(
                "Choice value column '%s' not found; using '%s' instead",
                platform.choice_value_column,
                value_column,
            )

        label_column = resolve_column(
            choices_frame.columns,
            f"label::{language}",
            f"label:{language}",
            "label",
        )
        if label_column is None:
            logger.warning(
                "No label column found for language %r; choice values will be used",
                language,
            )

        lookup: dict[str, list[Choice]] = OrderedDict()
        for _, row in choices_frame.iterrows():
            list_name = str(row.get(list_column, "")).strip()
            value = str(row.get(value_column, "")).strip()
            if not list_name or not value:
                continue
            label = (
                str(row.get(label_column, "")).strip() if label_column else ""
            ) or value
            lookup.setdefault(list_name, []).append(Choice(value=value, label=label))

        logger.info(
            "Built %s choice list(s) with %s choice(s) for language %s",
            len(lookup),
            sum(len(items) for items in lookup.values()),
            language,
        )
        return lookup

    @staticmethod
    def display_lines(choices: list[Choice]) -> str:
        """Format choices as ``[value] label`` with one choice per line."""
        return "\n".join(f"[{choice.value}] {choice.label}" for choice in choices)
