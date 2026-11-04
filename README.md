<p align="center">
  <img src="assets/icon.png" alt="XLSForm2Word" width="128" />
</p>

<h1 align="center">XLSForm2Word</h1>

<p align="center">
  Convert ODK, SurveyCTO, and KoboToolbox XLSForms into clean, print-ready Word documents — no Python, no internet, no installation.
</p>

<p align="center">
  <a href="https://github.com/armanmahmud1/XLSForm2Word/releases/latest"><strong>Download v1.2.1</strong></a>
</p>

---

## What It Does

XLSForm2Word reads an `.xlsx` or `.xls` XLSForm and produces a professionally formatted `.docx` questionnaire for each selected language. It is built for research assistants, survey programmers, M&E specialists, and data analysts who need reliable paper questionnaires.

**Input:** an XLSForm workbook &rarr; **Output:** one Word document per language

```
Household Survey_English_word.docx
Household Survey_Bangla_word.docx
Household Survey_Arabic_word.docx
```

---

## Quick Start

1. Download [`XLSForm2Word_v1.2.1_Windows.zip`](https://github.com/armanmahmud1/XLSForm2Word/releases/latest) and extract it.
2. Double-click **`XLSForm2Word.exe`** (no install needed).
3. Drag and drop your XLSForm (or click Browse).
4. Select languages and output columns.
5. Click **Generate Word Documents**.

> **Note:** Windows Defender may show a SmartScreen warning. Click **More info** then **Run anyway**.

---

## Features

| Category | Details |
|---|---|
| **Platforms** | ODK, SurveyCTO, KoboToolbox |
| **Language detection** | `label::English`, `label:English`, and bare `label` columns |
| **Multi-language** | One Word document per selected language |
| **Output columns** | Variable, Question, Choices, Constraint, Relevance, Calculation |
| **Choice lists** | Rendered as `[value] label` from the choices sheet |
| **Document format** | A4 portrait, Calibri Light, repeat-on-every-page headers, branded footer |
| **File input** | Drag-and-drop or file browser, `.xlsx` and `.xls` |
| **Auto-detection** | Platform (SurveyCTO vs ODK) is detected automatically from form columns |
| **Portable settings** | `settings.json` remembers output folder, columns, and window size |
| **Logging** | Rotating log file with startup, generation, and error records |
| **Privacy** | Fully offline — nothing is uploaded, ever |

---

## Portable Folder Layout

Keep all files beside the executable:

```
XLSForm2Word/
  XLSForm2Word.exe
  settings.json
  LICENSE
  README.pdf
  assets/
  logs/
```

---

## Development

**Requirements:** Windows 10/11, Python 3.12+

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python app/main.py
```

### Testing

```powershell
python -m pytest -q
```

Three sample workbooks are included in `sample/` (ODK, SurveyCTO, KoboToolbox) with English, Bangla, and Arabic labels.

### Building the Portable EXE

```powershell
python build.py              # full build with tests
python build.py --skip-tests # skip test suite
```

The build script generates the icon, rebuilds `README.pdf`, runs tests, creates Windows version metadata, packages with PyInstaller, and writes the final ZIP to `dist/`.

---

## Project Structure

```
app/main.py                  Entry point
gui/
  main_window.py             Main window and worker orchestration
  about_dialog.py            About dialog
  settings_dialog.py         Settings and support paths
  generation_worker.py       Background generation thread
  widgets.py                 Drag-and-drop file selector
  theme.py                   Stylesheet
core/
  xlsform_loader.py          Excel loading and sheet validation
  language_detector.py       Language detection and column resolution
  choices_builder.py         Choice dictionary and formatting
  question_types.py          Type parsing and placeholders
  validator.py               Pre-generation checks
  generation_service.py      Conversion pipeline
  word_generator.py          Word document generation
  models.py                  Domain models
  errors.py                  Exception types
utils/
  version.py                 Version and branding (single source of truth)
  config.py                  settings.json persistence
  logger.py                  Rotating file logger
  paths.py                   Portable and bundled resource paths
sample/                      Sample XLSForms
tests/                       Pytest suite
tools/                       Icon, sample form, and PDF builders
docs/                        User guide source
```

---

## License

MIT License. See [`LICENSE`](LICENSE).

Developed by [Arman Mahmud](https://www.arman-mahmud.com)
