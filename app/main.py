"""XLSForm2Word application entry point."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from gui.main_window import MainWindow
from gui.theme import APP_STYLESHEET
from utils.logger import setup_logging
from utils.paths import resource_path
from utils.version import APP_NAME, APP_VERSION, AUTHOR, WEBSITE


def _set_windows_app_id() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            f"ArmanMahmud.{APP_NAME}"
        )
    except (AttributeError, OSError):
        pass


def _install_exception_hook(logger: logging.Logger) -> None:
    def handle_exception(exc_type, exc_value, exc_traceback) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.critical(
            "Unhandled exception",
            exc_info=(exc_type, exc_value, exc_traceback),
        )
        try:
            QMessageBox.critical(
                None,
                "Unexpected Error",
                "An unexpected error occurred.\n\n"
                f"{exc_value}\n\n"
                "Technical details were written to the log file so the "
                "application can be diagnosed without showing a code traceback.",
            )
        except Exception as dialog_error:
            logger.debug(
                "Could not show the unexpected-error dialog",
                exc_info=dialog_error,
            )

    sys.excepthook = handle_exception


def _application_icon() -> QIcon:
    icon_path = resource_path("assets/icon.ico")
    if icon_path.exists():
        return QIcon(str(icon_path))
    return QIcon()


def _run_smoke_test(arguments: list[str], logger: logging.Logger) -> int:
    """Generate all sample languages without opening the GUI."""
    output_dir = Path(arguments[1]).expanduser() if len(arguments) >= 2 else None
    result_path = output_dir / "smoke_test_result.txt" if output_dir else None

    def write_result(text: str) -> None:
        if result_path is None:
            return
        try:
            result_path.parent.mkdir(parents=True, exist_ok=True)
            result_path.write_text(text, encoding="utf-8")
        except OSError:
            logger.exception("Could not write the smoke-test result file")

    if len(arguments) != 2:
        message = "Usage: XLSForm2Word.exe --smoke-test <form> <output-folder>"
        logger.error(message)
        write_result(f"FAILED\n{message}\n")
        return 2

    form_path = Path(arguments[0]).expanduser()
    try:
        from core.generation_service import GenerationService
        from core.language_detector import LanguageDetector
        from core.models import GenerationRequest, Platform
        from utils.config import COLUMN_NAMES

        service = GenerationService()
        form = service.loader.load(form_path)
        languages = [
            item.language
            for item in LanguageDetector().detect(form.survey)
        ]
        if not languages:
            raise ValueError("The smoke-test form contains no languages.")
        result = service.generate(
            GenerationRequest(
                form_path=form_path,
                output_folder=output_dir,
                platform=Platform.ODK,
                languages=tuple(languages),
                columns=COLUMN_NAMES,
            )
        )
    except Exception as exc:
        message = getattr(exc, "message", str(exc))
        logger.exception("Frozen smoke test failed")
        write_result(f"FAILED\n{message}\n")
        return 1

    lines = "\n".join(f"- {path.name}" for path in result.outputs)
    write_result(f"OK\n{len(result.outputs)} documents generated\n{lines}\n")
    logger.info("Frozen smoke test completed: %s document(s)", len(result.outputs))
    return 0


def main() -> int:
    _set_windows_app_id()
    logger = setup_logging()
    logger.info("%s v%s started", APP_NAME, APP_VERSION)

    if len(sys.argv) > 1 and sys.argv[1] == "--smoke-test":
        return _run_smoke_test(sys.argv[2:], logger)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(AUTHOR)
    app.setOrganizationDomain(
        WEBSITE.replace("https://", "").replace("http://", "").strip("/")
    )
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(APP_STYLESHEET)

    icon = _application_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)
    _install_exception_hook(logger)

    window = MainWindow()
    window.show()

    if len(sys.argv) > 1:
        candidate = Path(sys.argv[1])
        if candidate.exists():
            QTimer.singleShot(0, lambda: window.load_form(candidate))

    logger.info(
        "%s is ready | developer: %s | website: %s",
        APP_NAME,
        AUTHOR,
        WEBSITE,
    )
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
