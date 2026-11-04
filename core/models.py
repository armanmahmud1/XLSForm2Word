"""Shared domain models for XLSForm processing."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import pandas as pd


class Platform(str, Enum):
    ODK = "ODK"
    SURVEYCTO = "SurveyCTO"
    KOBOTOOLBOX = "KoboToolbox"

    @property
    def choice_value_column(self) -> str:
        return "value" if self is Platform.SURVEYCTO else "name"

    @property
    def choice_value_fallback(self) -> str:
        return "name" if self is Platform.SURVEYCTO else "value"

    @property
    def relevance_column(self) -> str:
        return "relevance" if self is Platform.SURVEYCTO else "relevant"

    @property
    def relevance_fallback(self) -> str:
        return "relevant" if self is Platform.SURVEYCTO else "relevance"


@dataclass(frozen=True)
class LabelColumn:
    column: str
    language: str


@dataclass(frozen=True)
class Choice:
    value: str
    label: str


@dataclass(frozen=True)
class XLSForm:
    source_path: Path
    survey: pd.DataFrame
    choices: pd.DataFrame
    questionnaire_name: str
    sheet_names: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.questionnaire_name.strip():
            object.__setattr__(self, "questionnaire_name", self.source_path.stem)


@dataclass(frozen=True)
class GenerationRequest:
    form_path: Path
    output_folder: Path
    platform: Platform
    languages: tuple[str, ...]
    columns: tuple[str, ...]


@dataclass(frozen=True)
class QuestionRow:
    variable: str
    question: str
    choices: str
    constraint: str
    relevance: str
    calculation: str

    def value_for(self, column: str) -> str:
        return {
            "Variable": self.variable,
            "Question": self.question,
            "Choices": self.choices,
            "Constraint": self.constraint,
            "Relevance": self.relevance,
            "Calculation": self.calculation,
        }.get(column, "")
