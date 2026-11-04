"""Main application window."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QByteArray, Qt, QThread, QTimer
from PySide6.QtGui import (
    QAction,
    QCloseEvent,
    QDragEnterEvent,
    QDropEvent,
    QIcon,
    QKeySequence,
)
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.errors import ValidationError, XLSForm2WordError
from core.generation_service import GenerationResult, GenerationService
from core.language_detector import LanguageDetector
from core.models import GenerationRequest, LabelColumn, Platform, XLSForm
from gui.about_dialog import AboutDialog
from gui.form_load_worker import FormLoadWorker
from gui.generation_worker import GenerationWorker
from gui.settings_dialog import SettingsDialog
from gui.widgets import FileDropZone
from utils.config import (
    COLUMN_NAMES,
    PLATFORMS,
    AppSettings,
    SettingsManager,
)
from utils.paths import (
    application_dir,
    default_output_dir,
    log_file_path,
    open_in_explorer,
    resource_path,
)
from utils.version import APP_NAME, APP_VERSION, AUTHOR, WEBSITE

logger = logging.getLogger(__name__)

WINDOW_TITLE = APP_NAME
SUBTITLE = "Convert ODK, SurveyCTO, and KoboToolbox XLSForms into Word documentation"
COLUMN_LAYOUT_ROWS = 3
LANGUAGE_COLUMNS = 4


class MainWindow(QMainWindow):
    def __init__(
        self,
        settings_manager: SettingsManager | None = None,
        service: GenerationService | None = None,
    ) -> None:
        super().__init__()
        self.settings_manager = settings_manager or SettingsManager()
        self.settings = self.settings_manager.load()
        self.service = service or GenerationService()
        self.validator = self.service.validator
        self.loader = self.service.loader
        self.language_detector = LanguageDetector()

        self.current_form: XLSForm | None = None
        self.detected_languages: list[LabelColumn] = []
        self.language_checkboxes: dict[str, QCheckBox] = {}
        self.column_checkboxes: dict[str, QCheckBox] = {}
        self._thread: QThread | None = None
        self._worker: GenerationWorker | None = None
        self._load_thread: QThread | None = None
        self._load_worker: FormLoadWorker | None = None
        self._busy = False
        self._loading = False
        self._suspend_column_guard = False
        self._applying_settings = False
        self._icon = self._load_icon()

        self.setWindowTitle(WINDOW_TITLE)
        self.setWindowIcon(self._icon)
        self.setMinimumSize(840, 640)
        screen = QApplication.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            self.resize(
                min(960, available.width()),
                min(830, available.height()),
            )
        else:
            self.resize(960, 830)
        self.setAcceptDrops(True)

        self._build_menu()
        self._build_ui()
        self._apply_settings(self.settings, reset_state=True)

    @property
    def _locked(self) -> bool:
        return self._busy or self._loading

    # ------------------------------------------------------------------ UI
    def _load_icon(self) -> QIcon:
        icon_path = resource_path("assets/icon.ico")
        if icon_path.exists():
            return QIcon(str(icon_path))
        return QIcon()

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")

        self.open_action = QAction("Open XLSForm...", self)
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_action.triggered.connect(self._browse_form)
        file_menu.addAction(self.open_action)

        self.output_action = QAction("Select Output Folder...", self)
        self.output_action.setShortcut("Ctrl+Shift+O")
        self.output_action.triggered.connect(self._browse_output_folder)
        file_menu.addAction(self.output_action)
        file_menu.addSeparator()

        self.settings_action = QAction("Settings...", self)
        self.settings_action.setShortcut("Ctrl+,")
        self.settings_action.triggered.connect(self._open_settings)
        file_menu.addAction(self.settings_action)
        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = self.menuBar().addMenu("&Help")

        guide_action = QAction("Open User Guide", self)
        guide_action.triggered.connect(self._open_user_guide)
        help_menu.addAction(guide_action)

        log_action = QAction("Open Log File", self)
        log_action.triggered.connect(self._open_log_file)
        help_menu.addAction(log_action)
        help_menu.addSeparator()

        about_action = QAction(f"About {APP_NAME}", self)
        about_action.setShortcut(QKeySequence.StandardKey.HelpContents)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("ContentArea")
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        central_layout.addWidget(self._build_header())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content.setObjectName("ScrollContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(28, 22, 28, 22)
        content_layout.setSpacing(16)
        content_layout.addWidget(self._build_form_card())
        content_layout.addLayout(self._build_middle_cards())
        content_layout.addWidget(self._build_action_card())
        content_layout.addStretch(1)
        scroll.setWidget(content)
        central_layout.addWidget(scroll, 1)

        central_layout.addWidget(self._build_footer())
        self.setCentralWidget(central)

    def _build_header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("Header")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(28, 18, 28, 18)
        layout.setSpacing(14)

        icon_label = QLabel()
        icon_label.setFixedSize(52, 52)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if not self._icon.isNull():
            icon_label.setPixmap(self._icon.pixmap(48, 48))
        layout.addWidget(icon_label)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)
        title = QLabel(APP_NAME)
        title.setObjectName("AppTitle")
        subtitle = QLabel(SUBTITLE)
        subtitle.setObjectName("AppSubtitle")
        text_layout.addWidget(title)
        text_layout.addWidget(subtitle)
        layout.addLayout(text_layout, 1)

        version_chip = QLabel(f"v{APP_VERSION}")
        version_chip.setObjectName("VersionChip")
        version_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_chip, 0, Qt.AlignmentFlag.AlignTop)
        return header

    def _build_form_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 18)
        layout.setSpacing(12)

        title = QLabel("1. Form")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        platform_row = QHBoxLayout()
        platform_row.setSpacing(16)
        platform_label = QLabel("Platform")
        platform_label.setStyleSheet("font-weight: 500; color: #374151;")
        platform_row.addWidget(platform_label)

        self.platform_group = QButtonGroup(self)
        for name in PLATFORMS:
            radio = QRadioButton(name)
            radio.setCursor(Qt.CursorShape.PointingHandCursor)
            tooltips = {
                "ODK": "ODK forms use 'name' values and 'relevant'.",
                "SurveyCTO": "SurveyCTO forms use 'value' values and 'relevance'.",
                "KoboToolbox": "KoboToolbox forms use 'name' values and 'relevant' (same as ODK).",
            }
            radio.setToolTip(tooltips.get(name, ""))
            radio.toggled.connect(self._on_platform_changed)
            self.platform_group.addButton(radio)
            platform_row.addWidget(radio)
        platform_row.addStretch(1)
        layout.addLayout(platform_row)

        self.file_drop = FileDropZone()
        self.file_drop.browseRequested.connect(self._browse_form)
        self.file_drop.fileDropped.connect(self.load_form)
        layout.addWidget(self.file_drop)

        language_header = QHBoxLayout()
        languages_label = QLabel("Documentation languages")
        languages_label.setStyleSheet("font-weight: 500; color: #374151;")
        language_hint = QLabel("Detected from label:: columns")
        language_hint.setObjectName("SectionHint")
        language_header.addWidget(languages_label)
        language_header.addStretch(1)
        language_header.addWidget(language_hint)
        layout.addLayout(language_header)

        self.languages_placeholder = QLabel(
            "Select an XLSForm file to detect available languages."
        )
        self.languages_placeholder.setObjectName("SectionHint")
        layout.addWidget(self.languages_placeholder)

        self.languages_container = QWidget()
        self.languages_layout = QGridLayout(self.languages_container)
        self.languages_layout.setContentsMargins(0, 0, 0, 0)
        self.languages_layout.setHorizontalSpacing(22)
        self.languages_layout.setVerticalSpacing(8)
        self.languages_container.hide()
        layout.addWidget(self.languages_container)

        self.language_note = QLabel(
            "One Word document is generated for each selected language."
        )
        self.language_note.setObjectName("SectionHint")
        layout.addWidget(self.language_note)
        return card

    def _build_middle_cards(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(16)
        row.addWidget(self._build_output_card(), 1)
        row.addWidget(self._build_columns_card(), 1)
        return row

    def _build_output_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 18)
        layout.setSpacing(10)

        title = QLabel("2. Output folder")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        hint = QLabel("Word documents are saved to this folder.")
        hint.setObjectName("SectionHint")
        layout.addWidget(hint)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.output_edit = QLineEdit()
        self.output_edit.setReadOnly(True)
        self.output_edit.setPlaceholderText("Select an output folder")
        row.addWidget(self.output_edit, 1)

        self.output_button = QPushButton("Browse")
        self.output_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.output_button.clicked.connect(self._browse_output_folder)
        row.addWidget(self.output_button)
        layout.addLayout(row)
        layout.addStretch(1)
        return card

    def _build_columns_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 18)
        layout.setSpacing(10)

        title = QLabel("3. Columns")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        hint = QLabel("Choose the columns to include in the Word table.")
        hint.setObjectName("SectionHint")
        layout.addWidget(hint)

        grid = QGridLayout()
        grid.setHorizontalSpacing(22)
        grid.setVerticalSpacing(8)
        for index, name in enumerate(COLUMN_NAMES):
            checkbox = QCheckBox(name)
            checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
            checkbox.toggled.connect(self._on_column_toggled)
            self.column_checkboxes[name] = checkbox
            grid.addWidget(
                checkbox,
                index % COLUMN_LAYOUT_ROWS,
                index // COLUMN_LAYOUT_ROWS,
            )
        layout.addLayout(grid)
        layout.addStretch(1)
        return card

    def _build_action_card(self) -> QWidget:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 18)
        layout.setSpacing(12)

        self.generate_button = QPushButton("Generate Word Documents")
        self.generate_button.setObjectName("PrimaryButton")
        self.generate_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.generate_button.setMinimumHeight(50)
        self.generate_button.clicked.connect(self._start_generation)
        layout.addWidget(self.generate_button)

        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("StatusLabel")
        self.percent_label = QLabel("")
        self.percent_label.setObjectName("SectionHint")
        status_row.addWidget(self.status_label)
        status_row.addStretch(1)
        status_row.addWidget(self.percent_label)
        layout.addLayout(status_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)
        return card

    def _build_footer(self) -> QWidget:
        footer = QFrame()
        footer.setObjectName("Footer")
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(28, 9, 28, 9)
        layout.addStretch(1)
        website_text = WEBSITE.replace("https://", "").replace("http://", "")
        label = QLabel(
            f"{APP_NAME} v{APP_VERSION} | Developed by {AUTHOR} | "
            f'<a href="{WEBSITE}" style="color:#2E7D32; '
            f'text-decoration:none;">{website_text}</a>'
        )
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setOpenExternalLinks(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        layout.addWidget(label)
        layout.addStretch(1)
        return footer

    # ------------------------------------------------------------- settings
    def _apply_settings(
        self,
        settings: AppSettings,
        *,
        reset_state: bool = False,
    ) -> None:
        self._applying_settings = True
        try:
            self._apply_settings_values(settings, reset_state=reset_state)
        finally:
            self._applying_settings = False

    def _apply_settings_values(
        self,
        settings: AppSettings,
        *,
        reset_state: bool = False,
    ) -> None:
        selected_platform = settings.platform
        for button in self.platform_group.buttons():
            if button.text() == selected_platform:
                button.setChecked(True)
                break
        else:
            self.platform_group.buttons()[0].setChecked(True)

        self._suspend_column_guard = True
        for name, checkbox in self.column_checkboxes.items():
            checkbox.setChecked(name in settings.selected_columns)
        self._suspend_column_guard = False

        if reset_state and not settings.output_folder:
            output_folder = str(default_output_dir())
        else:
            output_folder = settings.output_folder
        self.output_edit.setText(output_folder)
        self.output_edit.setToolTip(output_folder)

        if settings.window_geometry and reset_state:
            try:
                geometry = QByteArray.fromBase64(
                    settings.window_geometry.encode("ascii")
                )
                self.restoreGeometry(geometry)
            except (ValueError, UnicodeEncodeError):
                logger.warning("Stored window geometry could not be restored")

        if reset_state:
            self._set_status("Ready", "normal")
            self.progress_bar.setValue(0)
            self.percent_label.setText("")

    def _selected_platform(self) -> Platform:
        button = self.platform_group.checkedButton()
        name = button.text() if button is not None else "ODK"
        try:
            return Platform(name)
        except ValueError:
            return Platform.ODK

    def _selected_columns(self) -> list[str]:
        return [
            name for name in COLUMN_NAMES if self.column_checkboxes[name].isChecked()
        ]

    def _selected_languages(self) -> list[str]:
        return [
            language
            for language, checkbox in self.language_checkboxes.items()
            if checkbox.isChecked()
        ]

    def _save_settings(self, *, include_geometry: bool = False) -> None:
        geometry = self.settings.window_geometry
        if include_geometry:
            geometry = bytes(self.saveGeometry().toBase64()).decode("ascii")
        self.settings = AppSettings(
            platform=self._selected_platform().value,
            output_folder=self.output_edit.text().strip(),
            selected_columns=self._selected_columns(),
            window_geometry=geometry,
        ).normalized()
        if not self.settings_manager.save(self.settings):
            logger.warning("Settings could not be persisted")

    # ------------------------------------------------------------- events
    def _on_platform_changed(self, checked: bool) -> None:
        if not checked or self._applying_settings:
            return
        platform = self._selected_platform()
        logger.info("Selected platform: %s", platform.value)
        self._save_settings()

    def _on_column_toggled(self, checked: bool) -> None:
        if self._suspend_column_guard or self._applying_settings:
            return
        if not any(
            checkbox.isChecked() for checkbox in self.column_checkboxes.values()
        ):
            sender = self.sender()
            if isinstance(sender, QCheckBox):
                self._suspend_column_guard = True
                sender.setChecked(True)
                self._suspend_column_guard = False
            self._set_status("At least one column must remain selected.", "warning")
            QTimer.singleShot(2600, self._restore_ready_status)
            return
        self._save_settings()

    def _restore_ready_status(self) -> None:
        if not self._busy:
            self._set_status("Ready", "normal")

    def _set_status(self, text: str, tone: str = "normal") -> None:
        colors = {
            "normal": "#4B5563",
            "success": "#2E7D32",
            "warning": "#B45309",
            "error": "#B91C1C",
        }
        self.status_label.setText(text)
        self.status_label.setStyleSheet(
            f"color: {colors.get(tone, colors['normal'])}; font-weight: 500;"
        )

    # ------------------------------------------------------------- actions
    def _browse_form(self) -> None:
        if self._busy:
            return
        start = (
            str(self.current_form.source_path.parent)
            if self.current_form
            else str(Path.home())
        )
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select XLSForm",
            start,
            "XLSForm files (*.xlsx *.xls);;Excel workbooks (*.xlsx *.xls);;"
            "All files (*)",
        )
        if path:
            self.load_form(path)

    def load_form(self, path: str | Path) -> bool:
        if self._busy:
            return False
        form_path = Path(path)
        self._set_status("Loading form...", "normal")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        try:
            form = self.loader.load(form_path)
            languages = self.language_detector.detect(form.survey)
            if not languages:
                raise XLSForm2WordError(
                    "No language columns were found in the survey sheet. "
                    "Add at least one column such as 'label::English' and try again."
                )
            self.current_form = form
            self.detected_languages = languages
            self.file_drop.set_path(form.source_path)
            self._populate_languages(languages)
            self._set_status("Ready", "normal")
            logger.info(
                "Form loaded: %s | %s detected language(s)",
                form.source_path,
                len(languages),
            )
            return True
        except XLSForm2WordError as exc:
            message = getattr(exc, "message", str(exc))
            logger.warning("Could not load XLSForm: %s", message)
            self._set_status("Ready", "normal")
            QMessageBox.warning(self, "Cannot Load XLSForm", message)
            return False
        except Exception:
            logger.exception("Unexpected error while loading form")
            self._set_status("Ready", "normal")
            QMessageBox.critical(
                self,
                "Cannot Load XLSForm",
                "An unexpected error occurred while reading the workbook. "
                "Please check that the file is a valid XLSForm.",
            )
            return False
        finally:
            QApplication.restoreOverrideCursor()

    def _populate_languages(self, languages: list[LabelColumn]) -> None:
        self._clear_layout(self.languages_layout)
        self.language_checkboxes.clear()
        for index, item in enumerate(languages):
            checkbox = QCheckBox(item.language)
            checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
            checkbox.setChecked(True)
            checkbox.setToolTip(f"Source column: {item.column}")
            self.language_checkboxes[item.language] = checkbox
            self.languages_layout.addWidget(
                checkbox,
                index // LANGUAGE_COLUMNS,
                index % LANGUAGE_COLUMNS,
            )
        self.languages_placeholder.hide()
        self.languages_container.show()

    @staticmethod
    def _clear_layout(layout: QGridLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def _browse_output_folder(self) -> None:
        if self._busy:
            return
        start = self.output_edit.text().strip() or str(default_output_dir())
        if not Path(start).is_dir():
            start = str(default_output_dir())
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder", start)
        if folder:
            self.output_edit.setText(folder)
            self.output_edit.setToolTip(folder)
            logger.info("Selected output folder: %s", folder)
            self._save_settings()

    def _start_generation(self) -> None:
        if self._busy:
            return
        if self.current_form is None:
            QMessageBox.warning(
                self,
                "No XLSForm Selected",
                "Choose an XLSForm file before generating Word documents.",
            )
            return

        output_text = self.output_edit.text().strip()
        if not output_text:
            QMessageBox.warning(
                self,
                "Output Folder Required",
                "Select an output folder before generating Word documents.",
            )
            return

        request = GenerationRequest(
            form_path=self.current_form.source_path,
            output_folder=Path(output_text),
            platform=self._selected_platform(),
            languages=tuple(self._selected_languages()),
            columns=tuple(self._selected_columns()),
        )
        try:
            request = self.validator.validate_request(request)
        except ValidationError as exc:
            QMessageBox.warning(self, "Cannot Generate", exc.message)
            self._set_status("Ready", "normal")
            return
        except XLSForm2WordError as exc:
            QMessageBox.warning(
                self, "Cannot Generate", getattr(exc, "message", str(exc))
            )
            self._set_status("Ready", "normal")
            return

        self._save_settings()
        self.progress_bar.setValue(0)
        self.percent_label.setText("0%")
        self._set_status("Loading form...", "normal")
        self._set_busy(True)

        self._thread = QThread(self)
        self._worker = GenerationWorker(request, self.service)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.succeeded.connect(self._on_generation_succeeded)
        self._worker.failed.connect(self._on_generation_failed)
        self._worker.succeeded.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._on_thread_finished)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _on_progress(self, value: int, message: str) -> None:
        self.progress_bar.setValue(value)
        self.percent_label.setText(f"{value}%")
        self._set_status(message, "normal")

    def _on_generation_succeeded(self, result: object) -> None:
        generation_result = result if isinstance(result, GenerationResult) else None
        self._set_busy(False)
        self.progress_bar.setValue(100)
        self.percent_label.setText("100%")
        self._set_status("Completed", "success")
        if generation_result is None:
            return

        count = len(generation_result.outputs)
        lines = "\n".join(f"- {path.name}" for path in generation_result.outputs)
        box = QMessageBox(self)
        box.setWindowTitle("Generation Complete")
        box.setIcon(QMessageBox.Icon.Information)
        box.setText(
            f"Generated {count} Word document(s) in:\n"
            f"{generation_result.request.output_folder}\n\n{lines}"
        )
        open_button = box.addButton("Open Folder", QMessageBox.ButtonRole.ActionRole)
        box.addButton(QMessageBox.StandardButton.Ok)
        box.exec()
        if box.clickedButton() is open_button:
            try:
                open_in_explorer(generation_result.request.output_folder)
            except OSError as exc:
                logger.warning("Could not open output folder: %s", exc)

    def _on_generation_failed(self, message: str) -> None:
        self._set_busy(False)
        self._set_status("Failed", "error")
        QMessageBox.critical(self, "Generation Failed", message)

    def _on_thread_finished(self) -> None:
        self._worker = None
        self._thread = None

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.generate_button.setEnabled(not busy)
        self.generate_button.setText(
            "Generating..." if busy else "Generate Word Documents"
        )
        self.output_button.setEnabled(not busy)
        self.file_drop.browse_button.setEnabled(not busy)
        self.open_action.setEnabled(not busy)
        self.output_action.setEnabled(not busy)
        self.settings_action.setEnabled(not busy)
        for button in self.platform_group.buttons():
            button.setEnabled(not busy)
        for checkbox in self.column_checkboxes.values():
            checkbox.setEnabled(not busy)
        for checkbox in self.language_checkboxes.values():
            checkbox.setEnabled(not busy)

    # --------------------------------------------------------------- help
    def _show_about(self) -> None:
        dialog = AboutDialog(self._icon, self)
        dialog.exec()

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self.settings_manager, self._icon, self)
        dialog.exec()
        if dialog.reset_requested:
            self.settings = self.settings_manager.load()
            self._apply_settings(self.settings, reset_state=True)
            logger.info("User preferences were reset")

    def _open_user_guide(self) -> None:
        candidates = [
            resource_path("README.pdf"),
            application_dir() / "README.pdf",
            application_dir() / "docs" / "XLSForm2Word_UserGuide.pdf",
        ]
        for path in candidates:
            if path.exists():
                try:
                    open_in_explorer(path)
                    return
                except OSError as exc:
                    logger.warning("Could not open user guide: %s", exc)
        QMessageBox.information(
            self,
            "User Guide",
            "The README.pdf user guide was not found next to the application.",
        )

    def _open_log_file(self) -> None:
        path = log_file_path()
        if not path.exists():
            QMessageBox.information(
                self,
                "Log File",
                "The log file has not been created yet.",
            )
            return
        try:
            open_in_explorer(path)
        except OSError as exc:
            logger.warning("Could not open log file: %s", exc)
            QMessageBox.warning(
                self, "Log File", f"The log file could not be opened:\n{path}"
            )

    # ------------------------------------------------------------- drag/drop
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if not self._busy and self._drop_path(event) is not None:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        if self._busy:
            event.ignore()
            return
        path = self._drop_path(event)
        if path is None:
            event.ignore()
            return
        event.acceptProposedAction()
        self.load_form(path)

    @staticmethod
    def _drop_path(event: QDragEnterEvent | QDropEvent) -> Path | None:
        mime = event.mimeData()
        if mime is None or not mime.hasUrls():
            return None
        for url in mime.urls():
            if url.isLocalFile():
                path = Path(url.toLocalFile())
                if path.is_file():
                    return path
        return None

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._busy:
            QMessageBox.warning(
                self,
                "Generation In Progress",
                "Please wait for document generation to finish before closing.",
            )
            event.ignore()
            return
        if self._thread is not None and self._thread.isRunning():
            self._thread.quit()
            if not self._thread.wait(3000):
                QMessageBox.warning(
                    self,
                    "Please Wait",
                    "The application is still finishing a background task.",
                )
                event.ignore()
                return
        self._save_settings(include_geometry=True)
        logger.info("%s closed", APP_NAME)
        event.accept()
