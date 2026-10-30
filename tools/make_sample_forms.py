"""Create sample ODK and SurveyCTO XLSForms used for testing and demos."""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

LANGUAGES = ("English", "Bangla", "Arabic")

SURVEY_ROWS = [
    {
        "type": "begin_group",
        "name": "",
        "label::English": "Household information",
        "label::Bangla": "পরিবারের তথ্য",
        "label::Arabic": "معلومات الأسرة",
        "relevant": "",
        "relevance": "",
        "constraint": "",
        "calculation": "",
    },
    {
        "type": "text",
        "name": "respondent_name",
        "label::English": "What is the name of the respondent?",
        "label::Bangla": "উত্তরদাতার নাম কী?",
        "label::Arabic": "ما اسم المستجيب؟",
        "relevant": "",
        "relevance": "",
        "constraint": "",
        "calculation": "",
    },
    {
        "type": "integer",
        "name": "household_size",
        "label::English": "How many people live in this household?",
        "label::Bangla": "এই পরিবারে কতজন বাস করেন?",
        "label::Arabic": "كم عدد الأشخاص الذين يعيشون في هذه الأسرة؟",
        "relevant": "",
        "relevance": "",
        "constraint": ". > 0 and . <= 30",
        "calculation": "",
    },
    {
        "type": "select_one sex",
        "name": "respondent_sex",
        "label::English": "What is the respondent's sex?",
        "label::Bangla": "উত্তরদাতার লিঙ্গ কী?",
        "label::Arabic": "ما جنس المستجيب؟",
        "relevant": "",
        "relevance": "",
        "constraint": "",
        "calculation": "",
    },
    {
        "type": "select_one consent",
        "name": "consent",
        "label::English": "Does the respondent consent to the interview?",
        "label::Bangla": "উত্তরদাতা সাক্ষাৎকারে সম্মতি দিয়েছেন কি?",
        "label::Arabic": "هل يوافق المستجيب على المقابلة؟",
        "relevant": "",
        "relevance": "",
        "constraint": "",
        "calculation": "",
    },
    {
        "type": "select_multiple assets",
        "name": "household_assets",
        "label::English": "Which assets does the household own?",
        "label::Bangla": "পরিবারটি কোন কোন সম্পদ মালিকানায় রয়েছে?",
        "label::Arabic": "ما الأصول التي تمتلكها الأسرة؟",
        "relevant": "${consent} = 'yes'",
        "relevance": "${consent} = 'yes'",
        "constraint": "",
        "calculation": "",
    },
    {
        "type": "date",
        "name": "interview_date",
        "label::English": "Date of interview",
        "label::Bangla": "সাক্ষাৎকারের তারিখ",
        "label::Arabic": "تاريخ المقابلة",
        "relevant": "",
        "relevance": "",
        "constraint": "",
        "calculation": "",
    },
    {
        "type": "geopoint",
        "name": "household_location",
        "label::English": "Capture the household location",
        "label::Bangla": "পরিবারের অবস্থান রেকর্ড করুন",
        "label::Arabic": "التقط موقع الأسرة",
        "relevant": "",
        "relevance": "",
        "constraint": "",
        "calculation": "",
    },
    {
        "type": "note",
        "name": "interviewer_note",
        "label::English": "Ask questions in a private setting.",
        "label::Bangla": "একান্ত পরিবেশে প্রশ্ন করুন।",
        "label::Arabic": "اطرح الأسئلة في مكان خاص.",
        "relevant": "",
        "relevance": "",
        "constraint": "",
        "calculation": "",
    },
    {
        "type": "calculate",
        "name": "adult_household",
        "label::English": "",
        "label::Bangla": "",
        "label::Arabic": "",
        "relevant": "",
        "relevance": "",
        "constraint": "",
        "calculation": "if(${household_size} > 0, 1, 0)",
    },
    {
        "type": "text",
        "name": "phone_number",
        "label::English": "What is the household's phone number?",
        "label::Bangla": "পরিবারের ফোন নম্বর কী?",
        "label::Arabic": "ما رقم هاتف الأسرة؟",
        "relevant": "${consent} = 'yes'",
        "relevance": "${consent} = 'yes'",
        "constraint": "regex(., '^[0-9]{11}$')",
        "calculation": "",
    },
    {
        "type": "end_group",
        "name": "",
        "label::English": "",
        "label::Bangla": "",
        "label::Arabic": "",
        "relevant": "",
        "relevance": "",
        "constraint": "",
        "calculation": "",
    },
]

CHOICES = [
    ("yesno", "yes", "Yes", "হ্যাঁ", "نعم"),
    ("yesno", "no", "No", "না", "لا"),
    ("sex", "1", "Male", "পুরুষ", "ذكر"),
    ("sex", "2", "Female", "মহিলা", "أنثى"),
    ("sex", "3", "Other", "অন্য", "آخر"),
    ("consent", "yes", "Yes", "হ্যাঁ", "نعم"),
    ("consent", "no", "No", "না", "لا"),
    ("assets", "mobile", "Mobile phone", "মোবাইল ফোন", "هاتف محمول"),
    ("assets", "bicycle", "Bicycle", "সাইকেল", "دراجة"),
    ("assets", "radio", "Radio", "রেডিও", "راديو"),
    ("assets", "television", "Television", "টেলিভিশন", "تلفزيون"),
]


def build_form(path: Path, platform: str) -> None:
    workbook = Workbook()
    survey_sheet = workbook.active
    survey_sheet.title = "survey"
    value_column = "name" if platform == "ODK" else "value"
    relevance_column = "relevant" if platform == "ODK" else "relevance"

    survey_headers = [
        "type",
        "name",
        *[f"label::{language}" for language in LANGUAGES],
        "hint",
        "required",
        "constraint",
        "constraint_message",
        relevance_column,
        "calculation",
        "appearance",
    ]
    survey_sheet.append(survey_headers)
    for row in SURVEY_ROWS:
        survey_sheet.append(
            [
                row["type"],
                row["name"],
                row["label::English"],
                row["label::Bangla"],
                row["label::Arabic"],
                "",
                "yes" if row["type"] in {"text", "integer"} else "",
                row["constraint"],
                "",
                row[relevance_column],
                row["calculation"],
                "",
            ]
        )

    choices_sheet = workbook.create_sheet("choices")
    choices_sheet.append(
        [
            "list_name",
            value_column,
            *[f"label::{language}" for language in LANGUAGES],
        ]
    )
    for list_name, value, english, bangla, arabic in CHOICES:
        choices_sheet.append([list_name, value, english, bangla, arabic])

    settings_sheet = workbook.create_sheet("settings")
    settings_sheet.append(["form_title", "form_id", "version", "default_language"])
    settings_sheet.append(
        ["Household Survey", "household_survey", "2026103001", "English"]
    )

    for sheet in (survey_sheet, choices_sheet, settings_sheet):
        for column_cells in sheet.columns:
            width = max(len(str(cell.value or "")) for cell in column_cells) + 2
            sheet.column_dimensions[column_cells[0].column_letter].width = min(
                max(width, 12), 55
            )

    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)
    print(f"Created {path}")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    build_form(root / "sample" / "HouseholdSurvey_ODK.xlsx", "ODK")
    build_form(root / "sample" / "HouseholdSurvey_SurveyCTO.xlsx", "SurveyCTO")


if __name__ == "__main__":
    main()
