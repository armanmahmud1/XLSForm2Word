"""Read ODK, SurveyCTO, and KoboToolbox XLSForm workbooks."""

from __future__ import annotations

import logging
import re
from pathlib import Path

import pandas as pd

from core.errors import XLSFormError
from core.models import XLSForm

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".xlsx", ".xls"}
SURVEY_SHEET = "survey"
CHOICES_SHEET = "choices"
SETTINGS_SHEET = "settings"

# Excel stores control characters as "_x000B_"-style escapes, which the Excel
# readers pass through as literal text.
_EXCEL_CONTROL_ESCAPE = re.compile(r"_x(00[01][0-9A-Fa-f])_")
# Characters that cannot be stored in a Word (XML) document.
_LINE_BREAK_CONTROLS = re.compile(r"[\x0b\x0c]")
_ILLEGAL_XML_CHARS = re.compile(r"[\x00-\x08\x0e-\x1f\ud800-\udfff￾￿]")


def clean_text(value: object) -> str:
    """Return a stripped string that is safe to write into a Word document."""
    if value is None or (isinstance(value, float) and value != value):
        return ""
    text = _EXCEL_CONTROL_ESCAPE.sub(lambda m: chr(int(m.group(1), 16)), str(value))
    text = _LINE_BREAK_CONTROLS.sub("\n", text)
    return _ILLEGAL_XML_CHARS.sub("", text).strip()


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
        # The header row is read as data so that duplicate column names can be
        # detected; pandas would otherwise silently rename them to "name.1".
        raw = pd.read_excel(
            workbook,
            sheet_name=sheet_name,
            header=None,
            dtype=str,
            keep_default_na=False,
        )
        if raw.empty:
            return pd.DataFrame()

        names: list[str] = []
        positions: list[int] = []
        seen: set[str] = set()
        for position, header in enumerate(raw.iloc[0]):
            name = clean_text(header) or f"Unnamed: {position}"
            key = name.casefold()
            if key in seen:
                logger.warning(
                    "Duplicate column %r in sheet %r ignored; the first one is used",
                    name,
                    sheet_name,
                )
                continue
            seen.add(key)
            names.append(name)
            positions.append(position)

        frame = raw.iloc[1:, positions].reset_index(drop=True)
        frame.columns = names
        for column in frame.columns:
            frame[column] = frame[column].map(clean_text)
        return frame

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
