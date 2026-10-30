"""Generate professionally formatted Word questionnaire documentation."""

from __future__ import annotations

import logging
import re
import zipfile
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from xml.sax.saxutils import escape as xml_escape

from docx import Document
from docx.document import Document as DocumentObject
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Mm, Pt, RGBColor
from docx.table import _Cell
from docx.text.run import Run

from core.choices_builder import ChoicesBuilder
from core.errors import DocumentGenerationError, XLSFormError
from core.language_detector import (
    LanguageDetector,
    resolve_column,
    translated_column,
)
from core.models import Choice, Platform, QuestionRow, XLSForm
from core.question_types import QuestionType, parse_type
from utils.config import COLUMN_NAMES
from utils.version import APP_NAME, APP_VERSION, AUTHOR, WEBSITE

logger = logging.getLogger(__name__)

GREEN = RGBColor(0x2E, 0x7D, 0x32)
GREY = RGBColor(0x7F, 0x7F, 0x7F)
HEADER_FILL = "E8F5E9"
DEFAULT_FONT = "Calibri Light"
DEFAULT_FONT_SIZE = 9.0

COLUMN_WIDTHS_INCHES: dict[str, float] = {
    "Variable": 0.95,
    "Question": 1.55,
    "Choices": 1.75,
    "Constraint": 1.00,
    "Relevance": 1.00,
    "Calculation": 0.95,
}
INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1F]')
RTL_TEXT = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]")
RTL_LANGUAGES = {
    "arabic",
    "ar",
    "farsi",
    "fa",
    "hebrew",
    "he",
    "pashto",
    "ps",
    "persian",
    "sindhi",
    "sd",
    "urdu",
    "ur",
    "uyghur",
    "ug",
}


class WordGenerator:
    """Create one Word document per language from an XLSForm."""

    def __init__(self) -> None:
        self.choices_builder = ChoicesBuilder()
        self.language_detector = LanguageDetector()

    def generate(
        self,
        form: XLSForm,
        language: str,
        platform: Platform | str,
        columns: list[str] | tuple[str, ...],
        output_folder: str | Path,
    ) -> Path:
        platform_enum = (
            platform if isinstance(platform, Platform) else Platform(platform)
        )
        selected_columns = [name for name in COLUMN_NAMES if name in set(columns)]
        if not selected_columns:
            raise XLSFormError("Select at least one column before generating.")

        label_column = self.language_detector.resolve(form.survey.columns, language)
        if label_column is None:
            raise XLSFormError(
                f"The label column for '{language}' could not be found in the "
                "survey sheet. Select the file again and choose an available language."
            )

        choice_lists = self.choices_builder.build(form, platform_enum, language)
        rows = self.build_question_rows(
            form=form,
            label_column=label_column.column,
            language=language,
            platform=platform_enum,
            choice_lists=choice_lists,
        )

        output_dir = Path(output_folder).expanduser()
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise DocumentGenerationError(
                f"The output folder could not be created: {exc}"
            ) from exc

        output_path = output_dir / self.build_filename(
            form.questionnaire_name, language
        )

        document = self._create_document(
            questionnaire_name=form.questionnaire_name,
            language=language,
            rows=rows,
            columns=selected_columns,
        )

        temp_output = output_dir / f".{output_path.stem}.{uuid4().hex}.tmp.docx"
        try:
            document.save(temp_output)
            self._set_company_property(temp_output, AUTHOR)
            try:
                temp_output.replace(output_path)
            except PermissionError as exc:
                raise DocumentGenerationError(
                    f"Could not write '{output_path.name}'. If the file is open "
                    "in Word, close it and try again."
                ) from exc
            except OSError as exc:
                raise DocumentGenerationError(
                    f"Could not write '{output_path.name}': {exc}"
                ) from exc
            logger.info("Generated document: %s", output_path)
        except DocumentGenerationError:
            self._remove_partial(temp_output)
            raise
        except OSError as exc:
            self._remove_partial(temp_output)
            raise DocumentGenerationError(
                f"Could not write '{output_path.name}': {exc}"
            ) from exc

        return output_path

    def build_question_rows(
        self,
        form: XLSForm,
        label_column: str,
        language: str,
        platform: Platform,
        choice_lists: dict[str, list[Choice]],
    ) -> list[QuestionRow]:
        survey = form.survey
        if survey.empty:
            return []

        name_column = resolve_column(survey.columns, "name")
        type_column = resolve_column(survey.columns, "type")
        constraint_column = translated_column(survey.columns, "constraint", language)
        relevance_column = resolve_column(
            survey.columns,
            f"{platform.relevance_column}::{language}",
            f"{platform.relevance_fallback}::{language}",
            platform.relevance_column,
            platform.relevance_fallback,
        )
        calculation_column = translated_column(survey.columns, "calculation", language)

        rows: list[QuestionRow] = []
        for _, row in survey.iterrows():
            question_type = parse_type(row.get(type_column, "") if type_column else "")
            if question_type.is_structural or question_type.is_generated:
                continue

            variable = str(row.get(name_column, "")).strip() if name_column else ""
            question = str(row.get(label_column, "")).strip()

            if not variable and not question:
                continue

            if question_type.is_select:
                choices_text = self._choices_for(question_type, choice_lists)
            else:
                choices_text = question_type.placeholder

            rows.append(
                QuestionRow(
                    variable=variable,
                    question=question,
                    choices=choices_text,
                    constraint=self._cell(row, constraint_column),
                    relevance=self._cell(row, relevance_column),
                    calculation=self._cell(row, calculation_column),
                )
            )

        return rows

    def _choices_for(
        self,
        question_type: QuestionType,
        choice_lists: dict[str, list[Choice]],
    ) -> str:
        if not question_type.list_name:
            return ""
        choices = choice_lists.get(question_type.list_name)
        if not choices:
            return ""
        return self.choices_builder.display_lines(choices)

    @staticmethod
    def _cell(row: object, column: str | None) -> str:
        if not column:
            return ""
        try:
            value = row.get(column, "")  # type: ignore[attr-defined]
        except AttributeError:
            return ""
        return "" if value is None else str(value).strip()

    @staticmethod
    def build_filename(questionnaire_name: str, language: str) -> str:
        name = WordGenerator._sanitize_filename(questionnaire_name) or "Questionnaire"
        safe_language = WordGenerator._sanitize_filename(language) or "Language"
        if len(name) > 120:
            name = name[:120].rstrip(" .")
        if len(safe_language) > 60:
            safe_language = safe_language[:60].rstrip(" .")
        return f"{name}_{safe_language}_word.docx"

    @staticmethod
    def _sanitize_filename(value: str) -> str:
        cleaned = INVALID_FILENAME_CHARS.sub("_", str(value))
        cleaned = re.sub(r"\s+", " ", cleaned).strip().strip(".")
        return cleaned

    def _create_document(
        self,
        questionnaire_name: str,
        language: str,
        rows: list[QuestionRow],
        columns: list[str],
    ) -> DocumentObject:
        document = Document()
        is_rtl = self._is_rtl_language(language)
        self._configure_page(document)
        self._configure_default_font(document)
        self._configure_properties(document, questionnaire_name, language)
        self._add_title(document, questionnaire_name, language, is_rtl=is_rtl)
        self._add_generated_date(document)
        self._add_table(document, rows, columns, is_rtl=is_rtl)
        self._add_footer(document)
        return document

    @staticmethod
    def _configure_page(document: DocumentObject) -> None:
        section = document.sections[0]
        section.orientation = WD_ORIENT.PORTRAIT
        section.page_width = Mm(210)
        section.page_height = Mm(297)
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.50)
        section.left_margin = Inches(0.50)
        section.right_margin = Inches(0.50)
        section.footer_distance = Inches(0.28)

    @staticmethod
    def _configure_default_font(document: DocumentObject) -> None:
        style = document.styles["Normal"]
        style.font.name = DEFAULT_FONT
        style.font.size = Pt(DEFAULT_FONT_SIZE)
        style.paragraph_format.space_before = Pt(0)
        style.paragraph_format.space_after = Pt(0)
        rpr = style.element.get_or_add_rPr()
        fonts = rpr.get_or_add_rFonts()
        for attribute in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
            fonts.set(qn(attribute), DEFAULT_FONT)

    @staticmethod
    def _configure_properties(
        document: DocumentObject,
        questionnaire_name: str,
        language: str,
    ) -> None:
        properties = document.core_properties
        properties.author = AUTHOR
        properties.last_modified_by = AUTHOR
        properties.title = questionnaire_name
        properties.subject = f"{questionnaire_name} - {language} questionnaire"
        properties.category = "Questionnaire"
        properties.keywords = "XLSForm, ODK, SurveyCTO, questionnaire"
        properties.comments = f"Generated using {APP_NAME} v{APP_VERSION}"
        properties.language = language
        now = datetime.now()
        properties.created = now
        properties.modified = now

    def _add_title(
        self,
        document: DocumentObject,
        questionnaire_name: str,
        language: str,
        *,
        is_rtl: bool = False,
    ) -> None:
        paragraph = document.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.space_after = Pt(4)
        run = paragraph.add_run(f"{questionnaire_name} ({language})")
        self._format_run(run, size=18, color=GREEN, bold=True)
        if is_rtl:
            self._set_paragraph_rtl(paragraph)
            run.font.rtl = True

    def _add_generated_date(self, document: DocumentObject) -> None:
        paragraph = document.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.space_after = Pt(10)
        text = datetime.now().strftime("Generated on: %d %B %Y")
        run = paragraph.add_run(text)
        self._format_run(run, size=14, color=GREY)

    def _add_table(
        self,
        document: DocumentObject,
        rows: list[QuestionRow],
        columns: list[str],
        *,
        is_rtl: bool = False,
    ) -> None:
        table = document.add_table(rows=1, cols=len(columns))
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False

        widths = self._column_widths(columns)
        for index, column_name in enumerate(columns):
            table.columns[index].width = Inches(widths[index])

        header_row = table.rows[0]
        self._repeat_header_row(header_row)
        for index, column_name in enumerate(columns):
            cell = header_row.cells[index]
            cell.width = Inches(widths[index])
            self._set_cell_shading(cell, HEADER_FILL)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_before = Pt(1)
            paragraph.paragraph_format.space_after = Pt(1)
            run = paragraph.add_run(column_name)
            self._format_run(run, size=DEFAULT_FONT_SIZE, bold=True)

        for row_data in rows:
            row = table.add_row()
            for index, column_name in enumerate(columns):
                cell = row.cells[index]
                cell.width = Inches(widths[index])
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
                paragraph = cell.paragraphs[0]
                paragraph.paragraph_format.space_before = Pt(1)
                paragraph.paragraph_format.space_after = Pt(1)
                value = row_data.value_for(column_name)
                run = paragraph.add_run(value)
                self._format_run(
                    run,
                    size=DEFAULT_FONT_SIZE,
                    color=GREEN if column_name == "Variable" else None,
                    italic=column_name == "Variable",
                )
                if (
                    is_rtl
                    and column_name in {"Question", "Choices"}
                    and RTL_TEXT.search(value)
                ):
                    self._set_paragraph_rtl(paragraph)
                    run.font.rtl = True

    @staticmethod
    def _column_widths(columns: list[str]) -> list[float]:
        content_width = 8.27 - 0.50 - 0.50
        raw = [COLUMN_WIDTHS_INCHES.get(name, 1.0) for name in columns]
        total = sum(raw)
        if total <= 0:
            return [content_width / len(columns)] * len(columns)
        scale = content_width / total
        return [width * scale for width in raw]

    @staticmethod
    def _repeat_header_row(row: object) -> None:
        tr_pr = row._tr.get_or_add_trPr()  # type: ignore[attr-defined]
        header = OxmlElement("w:tblHeader")
        header.set(qn("w:val"), "true")
        tr_pr.append(header)

    @staticmethod
    def _set_cell_shading(cell: _Cell, fill: str) -> None:
        tc_pr = cell._tc.get_or_add_tcPr()
        shading = OxmlElement("w:shd")
        shading.set(qn("w:val"), "clear")
        shading.set(qn("w:color"), "auto")
        shading.set(qn("w:fill"), fill)
        tc_pr.append(shading)

    def _add_footer(self, document: DocumentObject) -> None:
        section = document.sections[0]
        footer = section.footer
        footer.is_linked_to_previous = False
        paragraph = footer.paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT

        prefix = paragraph.add_run(
            f"{APP_NAME} v{APP_VERSION} | Developed by {AUTHOR} | "
        )
        self._format_run(prefix, size=8, color=GREY)

        website_text = re.sub(r"^https?://", "", WEBSITE).rstrip("/")
        link_run = paragraph.add_run(website_text)
        self._format_run(link_run, size=8, color=GREY)
        relationship_id = paragraph.part.relate_to(
            WEBSITE, RT.HYPERLINK, is_external=True
        )
        hyperlink = OxmlElement("w:hyperlink")
        hyperlink.set(qn("r:id"), relationship_id)
        link_run._r.addprevious(hyperlink)
        hyperlink.append(link_run._r)

    @staticmethod
    def _format_run(
        run: Run,
        *,
        size: float = DEFAULT_FONT_SIZE,
        color: RGBColor | None = None,
        bold: bool | None = None,
        italic: bool | None = None,
    ) -> None:
        run.font.name = DEFAULT_FONT
        run.font.size = Pt(size)
        if bold is not None:
            run.bold = bold
        if italic is not None:
            run.italic = italic
        if color is not None:
            run.font.color.rgb = color
        rpr = run._element.get_or_add_rPr()
        fonts = rpr.get_or_add_rFonts()
        for attribute in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
            fonts.set(qn(attribute), DEFAULT_FONT)

    @staticmethod
    def _remove_partial(path: Path) -> None:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass

    @staticmethod
    def _is_rtl_language(language: str) -> bool:
        return language.strip().casefold() in RTL_LANGUAGES

    @staticmethod
    def _set_paragraph_rtl(paragraph: object) -> None:
        p_pr = paragraph._p.get_or_add_pPr()  # type: ignore[attr-defined]
        if p_pr.find(qn("w:bidi")) is not None:
            return
        bidi = OxmlElement("w:bidi")
        successors = (
            "w:adjustRightInd",
            "w:snapToGrid",
            "w:spacing",
            "w:ind",
            "w:contextualSpacing",
            "w:mirrorIndents",
            "w:suppressOverlap",
            "w:jc",
            "w:textDirection",
            "w:textAlignment",
            "w:textboxTightWrap",
            "w:outlineLvl",
            "w:divId",
            "w:cnfStyle",
            "w:rPr",
            "w:sectPr",
            "w:pPrChange",
        )
        p_pr.insert_element_before(bidi, *successors)

    @staticmethod
    def _set_company_property(document_path: Path, company: str) -> None:
        """Set the Word "Company" extended property, which python-docx omits."""
        try:
            with zipfile.ZipFile(document_path, "r") as archive:
                entries = [
                    (info, archive.read(info.filename)) for info in archive.infolist()
                ]
        except (OSError, zipfile.BadZipFile) as exc:
            raise DocumentGenerationError(
                "The generated document could not be opened to set its "
                "Company metadata."
            ) from exc

        app_entry = b""
        for _, data in entries:
            if b"<Properties" in data and b"extended-properties" in data:
                app_entry = data
                break

        if not app_entry:
            raise DocumentGenerationError(
                "The generated document is missing its extended properties part; "
                "Company metadata could not be set."
            )

        app_xml = app_entry.decode("utf-8", errors="replace")
        company_element = f"<Company>{xml_escape(company)}</Company>"
        if re.search(r"<Company\s*/>", app_xml):
            app_xml = re.sub(r"<Company\s*/>", company_element, app_xml, count=1)
        elif re.search(r"<Company>.*?</Company>", app_xml, flags=re.DOTALL):
            app_xml = re.sub(
                r"<Company>.*?</Company>",
                company_element,
                app_xml,
                count=1,
                flags=re.DOTALL,
            )
        else:
            app_xml = app_xml.replace(
                "</Properties>", f"{company_element}</Properties>"
            )

        updated = app_xml.encode("utf-8")
        temp_path = document_path.with_name(f"{document_path.name}.meta.tmp")
        try:
            with zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as archive:
                for info, data in entries:
                    payload = updated if data == app_entry else data
                    archive.writestr(info, payload)
            temp_path.replace(document_path)
        except (OSError, zipfile.BadZipFile) as exc:
            temp_path.unlink(missing_ok=True)
            raise DocumentGenerationError(
                "The generated document could not be updated with the required "
                "Company metadata."
            ) from exc
