"""Read ODK, SurveyCTO, and KoboToolbox XLSForm workbooks."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from core.errors import XLSFormError
from core.models import XLSForm

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".xlsx", ".xls"}
SURVEY_SHEET = "survey"
CHOICES_SHEET = "choices"
SETTINGS_SHEET = "settings"


class XLSFormLoader:
    """Load the required survey and choices sheets from an XLSForm."""

    def load(self, file_path: str | Path) -> XLSForm:
        path = Path(file_path).expanduser().resolve()
        self._validate_path(path)
        logger.info("Selected file: %s", path)

        try:
            with pd.ExcelFile(path) as workbook:
                sheet_names = list(workbook.sheet_names)
                resolved = {name.casefold(): name for name in sheet_names}

                missing = [
                    name
                    for name in (SURVEY_SHEET, CHOICES_SHEET)
                    if name.casefold() not in resolved
                ]
                if missing:
                    raise XLSFormError(
                        "The selected workbook is missing the required "
                        f"{' and '.join(repr(name) for name in missing)} sheet(s). "
                        "An XLSForm must contain both 'survey' and 'choices' sheets."
                    )

                survey = self._read_sheet(workbook, resolved[SURVEY_SHEET])
                choices = self._read_sheet(workbook, resolved[CHOICES_SHEET])
                settings = None
                if SETTINGS_SHEET in resolved:
                    settings = self._read_sheet(workbook, resolved[SETTINGS_SHEET])

                questionnaire_name = self._questionnaire_name(settings, path)
                logger.info(
                    "Workbook loaded: %s survey row(s), %s choice row(s); "
                    "questionnaire name: %s",
                    len(survey),
                    len(choices),
                    questionnaire_name,
                )
                return XLSForm(
                    source_path=path,
                    survey=survey,
                    choices=choices,
                    questionnaire_name=questionnaire_name,
                    sheet_names=tuple(sheet_names),
                )
        except XLSFormError:
            raise
        except ImportError as exc:
            raise XLSFormError(
                "Support for this Excel format is not available. "
                "Please install the required Excel reader or re-save the form "
                "as an .xlsx file."
            ) from exc
        except PermissionError as exc:
            raise XLSFormError(
                "The workbook is open or cannot be read. Close it in Excel and "
                "try again, or move it to a folder you can access."
            ) from exc
        except Exception as exc:  # pandas/openpyxl raise many format-specific errors
            logger.exception("Failed to read workbook %s", path)
            raise XLSFormError(
                f"The workbook could not be read: {exc}. "
                "Make sure it is a valid, uncorrupted XLSForm."
            ) from exc

    @staticmethod
    def _validate_path(path: Path) -> None:
        if not path.exists() or not path.is_file():
            raise XLSFormError("The selected XLSForm file does not exist.")
        if path.suffix.casefold() not in SUPPORTED_EXTENSIONS:
            raise XLSFormError(
                "Unsupported file type. Please select an Excel XLSForm (.xlsx or .xls)."
            )

    @staticmethod
    def _read_sheet(workbook: pd.ExcelFile, sheet_name: str) -> pd.DataFrame:
        frame = pd.read_excel(
            workbook,
            sheet_name=sheet_name,
            dtype=str,
            keep_default_na=False,
        )
        frame = frame.copy()
        frame.columns = XLSFormLoader._unique_columns(
            [str(column).strip() for column in frame.columns]
        )
        for column in frame.columns:
            frame[column] = frame[column].map(
                lambda value: "" if value is None else str(value).strip()
            )
        return frame

    @staticmethod
    def _unique_columns(columns: list[str]) -> list[str]:
        seen: dict[str, int] = {}
        result: list[str] = []
        for column in columns:
            key = column.casefold()
            if key in seen:
                seen[key] += 1
                result.append(f"{column}.{seen[key]}")
            else:
                seen[key] = 0
                result.append(column)
        return result

    @staticmethod
    def _questionnaire_name(settings: pd.DataFrame | None, path: Path) -> str:
        if settings is not None and not settings.empty:
            normalized = {column.casefold(): column for column in settings.columns}
            for candidate in ("form_title", "form_name", "title", "name"):
                column = normalized.get(candidate)
                if column is None:
                    continue
                for value in settings[column]:
                    text = str(value).strip()
                    if text and text.casefold() != "nan":
                        return text
        return path.stem


def load_xlsform(file_path: str | Path) -> XLSForm:
    """Convenience wrapper for callers that do not need a loader instance."""
    return XLSFormLoader().load(file_path)
