# XLSForm2Word

![XLSForm2Word](assets/icon.png)

XLSForm2Word is a portable Windows desktop application that converts ODK and
SurveyCTO XLSForms into professionally formatted Microsoft Word questionnaire
documentation. It is built for research assistants, survey programmers, M&E
specialists, data analysts, and researchers who need reliable questionnaire
printouts without installing Python or using an internet connection.

Current release: **v1.0.2**

The current application version, author, and website are defined in one place:
`utils/version.py`. The interface, Word metadata, footers, About dialog, logs,
user guide, and Windows executable metadata all read from that file.

## Features

- ODK and SurveyCTO support
- Automatic detection of `label::<language>` columns
- One Word document per selected language
- Drag and drop or file browsing
- Choice lists rendered as `[value] label`
- Selectable Variable, Question, Choices, Constraint, Relevance, and
  Calculation columns
- A4 portrait Word output with repeat-on-every-page table headers
- Calibri Light typography, branded title, generated date, and a clickable page footer
- Portable `settings.json` for output folder, platform, columns, and window size
- Rotating log file with startup, file, language, generation, and error records
- Friendly validation and error dialogs with no raw Python tracebacks
- Background generation so the interface stays responsive

## Portable use

1. Download and extract the portable ZIP.
2. Open the extracted `XLSForm2Word` folder.
3. Double-click `XLSForm2Word.exe`.
4. Select an XLSForm, choose languages and columns, and generate.

No installation, administrator rights, Python runtime, or internet connection is
required. Keep `settings.json`, `logs`, `assets`, and `README.pdf` beside the
executable.

The distributed folder has this layout:

```text
XLSForm2Word/
├── XLSForm2Word.exe
├── settings.json
├── logs/
├── assets/
├── README.pdf
└── LICENSE
```

## Development setup

Recommended environment: Windows 10/11 and Python 3.12 or newer.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python app/main.py
```

On systems where PowerShell activation is restricted, use:

```powershell
.\.venv\Scripts\activate.bat
```

Runtime dependencies are listed in `requirements.txt`; build and test tools are
listed in `requirements-dev.txt`.

## Usage

1. Select ODK or SurveyCTO.
2. Browse for or drag in an `.xlsx` or `.xls` XLSForm.
3. Select one or more detected languages.
4. Select the output folder.
5. Tick the table columns to include. At least one column must remain selected.
6. Click **Generate Word Documents**.

Documents are named:

```text
<QuestionnaireName>_<Language>_word.docx
```

The questionnaire name is read from `form_title` or `form_name` in the settings
sheet. If neither exists, the workbook file name is used.

## Testing

Run the automated test suite:

```powershell
python -m pytest -q
```

The tests cover language detection, required sheets, ODK and SurveyCTO column
mapping, choice formatting, validation, Word formatting and metadata, and
multi-language generation.

Two ready-to-use test workbooks are included:

- `sample/HouseholdSurvey_ODK.xlsx`
- `sample/HouseholdSurvey_SurveyCTO.xlsx`

Both contain English, Bangla, and Arabic labels.

Regenerate the sample workbooks with:

```powershell
python tools/make_sample_forms.py
```

## Building the portable EXE

Install the development requirements, then run:

```powershell
python build.py
```

`build.py` will:

1. Generate the application icon if needed.
2. Rebuild `README.pdf` from `docs/USER_GUIDE.md`.
3. Run the test suite unless `--skip-tests` is supplied.
4. Generate Windows version metadata from `utils/version.py`.
5. Run PyInstaller using `XLSForm2Word.spec`.
6. Assemble the portable folder and ZIP archive under `dist/`.

Final artifacts:

```text
dist/XLSForm2Word/XLSForm2Word.exe
dist/XLSForm2Word_v<version>_Windows.zip
```

To build without tests:

```powershell
python build.py --skip-tests
```

The executable is a single-file, windowed PyInstaller build. The ZIP includes the
portable folder with default settings and support files.

## Project structure

```text
app/
    main.py                 Application entry point
gui/
    main_window.py          Main window, drag/drop, worker orchestration
    about_dialog.py         About dialog
    settings_dialog.py      Settings and support paths
    generation_worker.py    QThread background worker
    widgets.py              Drag-and-drop file selector
    theme.py                Application stylesheet
core/
    xlsform_loader.py       Excel sheet loading and validation
    language_detector.py    label:: language detection and column resolution
    choices_builder.py      Choice dictionary and display formatting
    question_types.py       Question type parsing and placeholders
    validator.py            Pre-generation checks
    generation_service.py   Conversion pipeline
    word_generator.py       python-docx document generation
    models.py               Domain models
    errors.py               Friendly exception types
utils/
    logger.py               Rotating file logging
    config.py               settings.json persistence
    paths.py                Portable and bundled resource paths
    version.py              Single source of version and branding data
assets/
    icon.ico                Windows application icon
    icon.png                Documentation icon
app/, gui/, core/, utils/  Application source
sample/                     Sample XLSForms
tests/                      Pytest suite
tools/                      Icon, sample form, and user guide builders
docs/                       User guide source
logs/                       Runtime logs (created/managed by the app)
XLSForm2Word.spec           PyInstaller configuration
build.py                    Portable Windows build script
requirements.txt            Runtime dependencies
requirements-dev.txt        Build and test dependencies
```

## Settings and logs

`settings.json` is created beside the executable. It stores the last output
folder, platform, selected columns, and window geometry. Use **File > Settings**
to view the settings and log locations or reset preferences.

Logs are written to `logs/xlsform2word.log` with rotation. If the application
folder is read-only, logs fall back to a temporary directory; **Help > Open Log
File** opens the active file.

## Privacy

The application works fully offline. It reads the selected workbook and writes
Word documents to the chosen output folder. Nothing is uploaded.

## License

MIT License. See `LICENSE`.

Developed by Arman Mahmud — https://www.arman-mahmud.com
