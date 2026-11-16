from __future__ import annotations

import zipfile
from pathlib import Path

import pandas as pd
import pytest
from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from openpyxl import Workbook

from core.choices_builder import ChoicesBuilder
from core.errors import ValidationError, XLSFormError
from core.generation_service import GenerationService
from core.language_detector import LanguageDetector, detect_platform, resolve_column, translated_column
from core.models import GenerationRequest, Platform
from core.question_types import parse_type
from core.validator import GenerationValidator
from core.word_generator import WordGenerator
from core.xlsform_loader import XLSFormLoader
from utils.version import APP_NAME, APP_VERSION, AUTHOR, WEBSITE

ROOT = Path(__file__).resolve().parents[1]
ODK_SAMPLE = ROOT / "sample" / "HouseholdSurvey_ODK.xlsx"
CTO_SAMPLE = ROOT / "sample" / "HouseholdSurvey_SurveyCTO.xlsx"
KOBO_SAMPLE = ROOT / "sample" / "HouseholdSurvey_KoboToolbox.xlsx"


def _make_form(
    survey_cols: list[str],
    choices_cols: list[str],
) -> XLSForm:
    """Create a minimal XLSForm with the given column names."""
    from core.models import XLSForm

    survey = pd.DataFrame(columns=survey_cols)
    choices = pd.DataFrame(columns=choices_cols)
    return XLSForm(
        source_path=Path("test.xlsx"),
        survey=survey,
        choices=choices,
        questionnaire_name="Test",
    )


def test_detect_platform_name_only_returns_odk() -> None:
    form = _make_form(["type", "name", "label"], ["list_name", "name", "label"])
    assert detect_platform(form) == Platform.ODK


def test_detect_platform_value_only_returns_surveycto() -> None:
    form = _make_form(["type", "name", "label"], ["list_name", "value", "label"])
    assert detect_platform(form) == Platform.SURVEYCTO


def test_detect_platform_both_columns_with_relevant_returns_odk() -> None:
    form = _make_form(
        ["type", "name", "label", "relevant"],
        ["list_name", "name", "value", "label"],
    )
    assert detect_platform(form) == Platform.ODK


def test_detect_platform_both_columns_with_relevance_returns_surveycto() -> None:
    form = _make_form(
        ["type", "name", "label", "relevance"],
        ["list_name", "name", "value", "label"],
    )
    assert detect_platform(form) == Platform.SURVEYCTO


def test_language_detection_preserves_order_and_deduplicates() -> None:
    columns = ["type", "label::English", "name", "label::Bangla", "label::english"]
    detected = LanguageDetector().detect_from_columns(columns)
    assert [item.language for item in detected] == ["English", "Bangla"]
    assert detected[0].column == "label::English"


def test_loader_rejects_missing_choices_sheet(tmp_path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "survey"
    sheet.append(["type", "name", "label::English"])
    sheet.append(["text", "q1", "Question"])
    path = tmp_path / "missing_choices.xlsx"
    workbook.save(path)

    with pytest.raises(XLSFormError, match="choices"):
        XLSFormLoader().load(path)


def test_loader_reads_questionnaire_title_from_settings() -> None:
    form = XLSFormLoader().load(ODK_SAMPLE)
    assert form.questionnaire_name == "Household Survey"
    assert not form.survey.empty
    assert not form.choices.empty


def test_loader_rejects_unsupported_extension(tmp_path: Path) -> None:
    path = tmp_path / "form.csv"
    path.write_text("type,name", encoding="utf-8")
    with pytest.raises(XLSFormError, match="Unsupported file type"):
        XLSFormLoader().load(path)


def test_choices_builder_odk_uses_name_and_labels() -> None:
    form = XLSFormLoader().load(ODK_SAMPLE)
    choices = ChoicesBuilder().build(form, Platform.ODK, "English")
    sex = choices["sex"]
    assert [choice.value for choice in sex] == ["1", "2", "3"]
    assert ChoicesBuilder.display_lines(sex) == "[1] Male\n[2] Female\n[3] Other"


def test_choices_builder_surveycto_uses_value_column() -> None:
    form = XLSFormLoader().load(CTO_SAMPLE)
    choices = ChoicesBuilder().build(form, Platform.SURVEYCTO, "English")
    assert [choice.value for choice in choices["sex"]] == ["1", "2", "3"]
    assert choices["sex"][0].label == "Male"


def test_question_type_markers_appear_in_choices_column() -> None:
    form = XLSFormLoader().load(ODK_SAMPLE)
    generator = WordGenerator()
    choices = ChoicesBuilder().build(form, Platform.ODK, "English")
    rows = generator.build_question_rows(
        form,
        "label::English",
        "English",
        Platform.ODK,
        choices,
    )
    by_variable = {row.variable: row for row in rows}
    assert by_variable["respondent_name"].choices == "[Text]"
    assert by_variable["household_size"].choices == "[Number]"
    assert by_variable["interview_date"].choices == "[Date]"
    assert by_variable["household_location"].choices == "[Lat, Long, Alt]"
    assert by_variable["interviewer_note"].choices == "[Enumerator Note]"
    assert by_variable["adult_household"].choices == "[Calculated field]"
    assert "[1] Male" in by_variable["respondent_sex"].choices


def test_odk_relevance_column_is_used() -> None:
    form = XLSFormLoader().load(ODK_SAMPLE)
    generator = WordGenerator()
    choices = ChoicesBuilder().build(form, Platform.ODK, "English")
    rows = generator.build_question_rows(
        form,
        "label::English",
        "English",
        Platform.ODK,
        choices,
    )
    phone = next(row for row in rows if row.variable == "phone_number")
    assert phone.relevance == "${consent} = 'yes'"
    assert phone.constraint == "regex(., '^[0-9]{11}$')"


def test_surveycto_relevance_column_is_used() -> None:
    form = XLSFormLoader().load(CTO_SAMPLE)
    generator = WordGenerator()
    choices = ChoicesBuilder().build(form, Platform.SURVEYCTO, "English")
    rows = generator.build_question_rows(
        form,
        "label::English",
        "English",
        Platform.SURVEYCTO,
        choices,
    )
    phone = next(row for row in rows if row.variable == "phone_number")
    assert phone.relevance == "${consent} = 'yes'"


def test_question_type_placeholders() -> None:
    assert parse_type("note").placeholder == "[Enumerator Note]"
    assert parse_type("text").placeholder == "[Text]"
    assert parse_type("integer").placeholder == "[Number]"
    assert parse_type("geopoint").placeholder == "[Lat, Long, Alt]"
    assert parse_type("calculate_here").placeholder == "[Calculated field]"
    assert parse_type("select_one sex").is_select
    assert parse_type("begin_group").is_structural


def test_column_resolution_is_case_insensitive() -> None:
    assert resolve_column(["Name", "Relevant"], "name") == "Name"
    assert resolve_column(["Relevant"], "relevant") == "Relevant"
    assert resolve_column(["other"], "name") is None


def test_single_colon_language_detection() -> None:
    columns = ["type", "label:English", "name", "label:Bangla"]
    detected = LanguageDetector().detect_from_columns(columns)
    assert [item.language for item in detected] == ["English", "Bangla"]
    assert detected[0].column == "label:English"


def test_double_colon_takes_precedence_over_single_colon() -> None:
    columns = ["label::English", "label:English", "label:Bangla"]
    detected = LanguageDetector().detect_from_columns(columns)
    languages = [item.language for item in detected]
    assert "English" in languages
    assert "Bangla" in languages
    english = next(item for item in detected if item.language == "English")
    assert english.column == "label::English"


def test_bare_label_detected_as_default_language() -> None:
    columns = ["type", "label", "name"]
    detected = LanguageDetector().detect_from_columns(columns)
    assert len(detected) == 1
    assert detected[0].language == "Default"
    assert detected[0].column == "label"


def test_prefixed_columns_take_priority_over_bare_label() -> None:
    columns = ["type", "label::English", "label", "name"]
    detected = LanguageDetector().detect_from_columns(columns)
    assert [item.language for item in detected] == ["English"]


def test_resolve_finds_bare_label_for_default_language() -> None:
    columns = ["type", "label", "name"]
    result = LanguageDetector.resolve(columns, "Default")
    assert result is not None
    assert result.column == "label"
    assert result.language == "Default"


def test_translated_column_resolves_single_colon() -> None:
    columns = ["constraint:English", "name"]
    assert translated_column(columns, "constraint", "English") == "constraint:English"
    # Double-colon is preferred when both exist
    columns_both = ["constraint::English", "constraint:English"]
    assert translated_column(columns_both, "constraint", "English") == "constraint::English"


def test_validator_reports_multiple_friendly_errors(tmp_path: Path) -> None:
    request = GenerationRequest(
        form_path=tmp_path / "missing.xlsx",
        output_folder=tmp_path / "missing_folder",
        platform=Platform.ODK,
        languages=(),
        columns=(),
    )
    with pytest.raises(ValidationError) as error:
        GenerationValidator().validate_request(request)
    assert len(error.value.errors) >= 4
    assert "Select at least one language." in error.value.errors
    assert "Select at least one column." in error.value.errors


def test_word_document_formatting_and_metadata(tmp_path: Path) -> None:
    form = XLSFormLoader().load(ODK_SAMPLE)
    output = WordGenerator().generate(
        form,
        "English",
        Platform.ODK,
        ["Variable", "Question"],
        tmp_path,
    )

    assert output.name == "Household Survey_English_word.docx"
    document = Document(output)
    properties = document.core_properties
    assert properties.author == AUTHOR
    assert properties.last_modified_by == AUTHOR
    assert properties.title == "Household Survey"
    assert properties.comments == f"Generated using {APP_NAME} v{APP_VERSION}"

    section = document.sections[0]
    assert round(section.top_margin.inches, 2) == 0.75
    assert round(section.bottom_margin.inches, 2) == 0.50
    assert round(section.left_margin.inches, 2) == 0.50
    assert round(section.right_margin.inches, 2) == 0.50
    assert round(section.page_width.inches, 2) == 8.27

    title = document.paragraphs[0]
    assert title.text == "Household Survey (English)"
    assert title.alignment is not None
    assert title.runs[0].bold is True
    assert title.runs[0].font.size.pt == 18
    assert str(title.runs[0].font.color.rgb) == "2E7D32"
    assert title.runs[0].font.name == "Calibri Light"

    generated = document.paragraphs[1]
    assert generated.text.startswith("Generated on:")
    assert generated.runs[0].font.size.pt == 14
    assert str(generated.runs[0].font.color.rgb) == "7F7F7F"

    table = document.tables[0]
    assert len(table.columns) == 2
    assert [cell.text for cell in table.rows[0].cells] == ["Variable", "Question"]
    assert table.rows[0].cells[0].paragraphs[0].runs[0].bold is True
    assert "tblHeader" in table.rows[0]._tr.xml

    first_variable = table.rows[1].cells[0].paragraphs[0].runs[0]
    assert first_variable.italic is True
    assert str(first_variable.font.color.rgb) == "2E7D32"
    assert first_variable.font.size.pt == 9
    assert table.rows[1].cells[0].text == "respondent_name"

    footer_text = section.footer.paragraphs[0].text
    assert footer_text == (
        f"{APP_NAME} v{APP_VERSION} | Developed by {AUTHOR} | www.arman-mahmud.com"
    )
    footer_run = section.footer.paragraphs[0].runs[0]
    assert footer_run.font.size.pt == 8
    assert str(footer_run.font.color.rgb) == "7F7F7F"
    assert "<w:hyperlink" in section.footer._element.xml
    hyperlink_targets = [
        relationship.target_ref
        for relationship in section.footer.part.rels.values()
        if relationship.reltype == RT.HYPERLINK
    ]
    assert WEBSITE in hyperlink_targets

    with zipfile.ZipFile(output) as archive:
        app_xml = archive.read("docProps/app.xml").decode("utf-8")
    assert f"<Company>{AUTHOR}</Company>" in app_xml


def test_generation_service_creates_one_document_per_language(
    tmp_path: Path,
) -> None:
    request = GenerationRequest(
        form_path=ODK_SAMPLE,
        output_folder=tmp_path,
        platform=Platform.ODK,
        languages=("English", "Bangla", "Arabic"),
        columns=("Variable", "Question", "Choices"),
    )
    progress: list[int] = []
    result = GenerationService().generate(
        request, lambda value, _: progress.append(value)
    )
    names = sorted(path.name for path in result.outputs)
    assert names == [
        "Household Survey_Arabic_word.docx",
        "Household Survey_Bangla_word.docx",
        "Household Survey_English_word.docx",
    ]
    assert all(path.exists() for path in result.outputs)
    assert progress[-1] == 100


def test_filename_sanitization() -> None:
    assert (
        WordGenerator.build_filename("A/B: C?", "English")
        == "A_B_ C__English_word.docx"
    )


def test_empty_choices_sheet_is_allowed() -> None:
    builder = ChoicesBuilder()
    frame = pd.DataFrame(columns=["list_name", "name", "label::English"])
    assert builder.build_from_frame(frame, Platform.ODK, "English") == {}


def test_kobotoolbox_platform_properties_match_odk() -> None:
    assert Platform.KOBOTOOLBOX.choice_value_column == "name"
    assert Platform.KOBOTOOLBOX.choice_value_fallback == "value"
    assert Platform.KOBOTOOLBOX.relevance_column == "relevant"
    assert Platform.KOBOTOOLBOX.relevance_fallback == "relevance"


def test_choices_builder_kobotoolbox_uses_name_column() -> None:
    form = XLSFormLoader().load(KOBO_SAMPLE)
    choices = ChoicesBuilder().build(form, Platform.KOBOTOOLBOX, "English")
    assert [choice.value for choice in choices["sex"]] == ["1", "2", "3"]
    assert choices["sex"][0].label == "Male"


def test_kobotoolbox_relevance_column_is_used() -> None:
    form = XLSFormLoader().load(KOBO_SAMPLE)
    generator = WordGenerator()
    choices = ChoicesBuilder().build(form, Platform.KOBOTOOLBOX, "English")
    rows = generator.build_question_rows(
        form,
        "label::English",
        "English",
        Platform.KOBOTOOLBOX,
        choices,
    )
    phone = next(row for row in rows if row.variable == "phone_number")
    assert phone.relevance == "${consent} = 'yes'"


def _write_workbook(
    path: Path,
    survey: list[list[object]],
    choices: list[list[object]],
) -> Path:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "survey"
    for row in survey:
        sheet.append(row)
    choices_sheet = workbook.create_sheet("choices")
    for row in choices:
        choices_sheet.append(row)
    workbook.save(path)
    return path


def _question_rows(path: Path, language: str = "English"):
    form = XLSFormLoader().load(path)
    platform = detect_platform(form)
    choices = ChoicesBuilder().build(form, platform, language)
    label = LanguageDetector.resolve(form.survey.columns, language)
    assert label is not None
    return WordGenerator().build_question_rows(
        form, label.column, language, platform, choices
    )


def test_space_separated_structural_types_are_skipped(tmp_path: Path) -> None:
    path = _write_workbook(
        tmp_path / "groups.xlsx",
        [
            ["type", "name", "label::English"],
            ["begin group", "g1", "Section A"],
            ["begin repeat", "members", "Members"],
            ["integer", "age", "Age"],
            ["end repeat", "members", ""],
            ["End Group", "g1", ""],
        ],
        [["list_name", "name", "label::English"]],
    )
    assert [row.variable for row in _question_rows(path)] == ["age"]
    assert parse_type("begin group").is_structural
    assert parse_type("end repeat").is_structural


def test_multi_word_and_metadata_types_are_skipped(tmp_path: Path) -> None:
    path = _write_workbook(
        tmp_path / "meta.xlsx",
        [
            ["type", "name", "label::English"],
            ["text audit", "ta", ""],
            ["speed violations count", "svc", ""],
            ["start-geopoint", "sg", ""],
            ["background-audio", "ba", ""],
            ["caseid", "cid", ""],
            ["text", "q1", "Name"],
        ],
        [["list_name", "name", "label::English"]],
    )
    assert [row.variable for row in _question_rows(path)] == ["q1"]


def test_rank_and_missing_choice_lists(tmp_path: Path) -> None:
    path = _write_workbook(
        tmp_path / "choices.xlsx",
        [
            ["type", "name", "label::English"],
            ["rank fruits", "r1", "Rank"],
            ["select_one fruits or_other", "s1", "Pick"],
            ["select_one typo_list", "s2", "Missing"],
            ["select_one ${members}", "s3", "Dynamic"],
        ],
        [
            ["list_name", "name", "label::English"],
            ["fruits", "a", "Apple"],
            ["fruits", "b", "Banana"],
        ],
    )
    rows = {row.variable: row.choices for row in _question_rows(path)}
    assert rows["r1"] == "[a] Apple\n[b] Banana"
    assert rows["s1"] == "[a] Apple\n[b] Banana"
    assert rows["s2"] == "[Select One]\n[Choice list 'typo_list' not found]"
    assert rows["s3"] == "[Select One]"


def test_rtl_is_detected_for_language_codes_and_hebrew(tmp_path: Path) -> None:
    assert WordGenerator._is_rtl_language("Arabic (ar)")
    assert WordGenerator._is_rtl_language("Urdu - Pakistan")
    assert WordGenerator._is_rtl_language("arabic")
    assert not WordGenerator._is_rtl_language("English (en)")
    assert not WordGenerator._is_rtl_language("Bangla")

    path = _write_workbook(
        tmp_path / "rtl.xlsx",
        [
            ["type", "name", "label::Arabic (ar)", "label::Hebrew"],
            ["text", "q1", "ما اسمك؟", "מה שמך?"],
        ],
        [["list_name", "name", "label"]],
    )
    form = XLSFormLoader().load(path)
    for language in ("Arabic (ar)", "Hebrew"):
        output = WordGenerator().generate(
            form, language, Platform.ODK, ["Variable", "Question"], tmp_path
        )
        with zipfile.ZipFile(output) as archive:
            document_xml = archive.read("word/document.xml").decode("utf-8")
        # Title paragraph and the question cell.
        assert document_xml.count("<w:bidi") == 2, language


def test_control_characters_are_removed_on_load(tmp_path: Path) -> None:
    from core.xlsform_loader import clean_text

    assert clean_text("  a\x0bb\x01c\x00 ") == "a\nbc"
    assert clean_text("line_x000D_\nnext_x0041_") == "line\r\nnext_x0041_"
    assert clean_text(None) == ""
    assert clean_text(float("nan")) == ""

    path = _write_workbook(
        tmp_path / "control.xlsx",
        [
            ["type", "name", "label::English"],
            ["text", "q1", "First_x000B_Second_x0001_"],
        ],
        [["list_name", "name", "label"]],
    )
    form = XLSFormLoader().load(path)
    output = WordGenerator().generate(
        form, "English", Platform.ODK, ["Variable", "Question"], tmp_path
    )
    assert output.exists()
    assert form.survey["label::English"][0] == "First\nSecond"


def test_duplicate_columns_do_not_create_phantom_languages(tmp_path: Path) -> None:
    path = _write_workbook(
        tmp_path / "duplicate.xlsx",
        [
            ["type", "name", "label::English", "label::English", "label::Bangla"],
            ["text", "q1", "First", "Second", "Bangla"],
        ],
        [["list_name", "name", "label"]],
    )
    form = XLSFormLoader().load(path)
    assert list(form.survey.columns) == [
        "type",
        "name",
        "label::English",
        "label::Bangla",
    ]
    assert form.survey["label::English"][0] == "First"
    languages = [item.language for item in LanguageDetector().detect(form.survey)]
    assert languages == ["English", "Bangla"]


def test_colliding_language_filenames_get_distinct_outputs(tmp_path: Path) -> None:
    path = _write_workbook(
        tmp_path / "collision.xlsx",
        [
            ["type", "name", "label::A:B", "label::A?B"],
            ["text", "q1", "One", "Two"],
        ],
        [["list_name", "name", "label"]],
    )
    result = GenerationService().generate(
        GenerationRequest(
            form_path=path,
            output_folder=tmp_path,
            platform=Platform.ODK,
            languages=("A:B", "A?B"),
            columns=("Variable", "Question"),
        )
    )
    names = [output.name for output in result.outputs]
    assert names == ["collision_A_B_word.docx", "collision_A_B_word_2.docx"]
    assert all(output.exists() for output in result.outputs)


def test_failed_save_leaves_no_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    form = XLSFormLoader().load(ODK_SAMPLE)

    def explode(*_: object, **__: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(WordGenerator, "_set_company_property", explode)
    with pytest.raises(RuntimeError):
        WordGenerator().generate(
            form, "English", Platform.ODK, ["Variable"], tmp_path
        )
    assert list(tmp_path.iterdir()) == []


def test_generation_service_kobotoolbox(tmp_path: Path) -> None:
    request = GenerationRequest(
        form_path=KOBO_SAMPLE,
        output_folder=tmp_path,
        platform=Platform.KOBOTOOLBOX,
        languages=("English",),
        columns=("Variable", "Question", "Choices"),
    )
    result = GenerationService().generate(request)
    assert len(result.outputs) == 1
    assert result.outputs[0].exists()
    assert result.outputs[0].name == "Household Survey_English_word.docx"
