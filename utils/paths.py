"""Filesystem locations that work both in development and in a frozen build."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

APP_DIR_NAME = "XLSForm2Word"


def is_frozen() -> bool:
    """Return ``True`` when running from a PyInstaller executable."""
    return bool(getattr(sys, "frozen", False))


def application_dir() -> Path:
    """Return the portable application directory.

    In a frozen build this is the folder containing ``XLSForm2Word.exe`` so
    that ``settings.json`` and ``logs`` stay next to the executable.
    """
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def resource_path(relative: str | Path) -> Path:
    """Resolve a bundled read-only asset (for example the application icon)."""
    relative_path = Path(relative)
    if is_frozen():
        bundle_dir = Path(getattr(sys, "_MEIPASS", application_dir()))
        candidate = bundle_dir / relative_path
        if candidate.exists():
            return candidate
    return application_dir() / relative_path


def settings_path() -> Path:
    return application_dir() / "settings.json"


def logs_dir() -> Path:
    """Return a writable log directory, falling back to the temp folder."""
    preferred = application_dir() / "logs"
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        probe = preferred / ".write-test"
        probe.write_text("", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return preferred
    except OSError:
        fallback = Path(tempfile.gettempdir()) / APP_DIR_NAME / "logs"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def log_file_path() -> Path:
    return logs_dir() / "xlsform2word.log"


def default_output_dir() -> Path:
    documents = Path.home() / "Documents"
    return documents if documents.is_dir() else Path.home()


def open_in_explorer(path: Path) -> None:
    """Open a file or folder using the operating system's default handler."""
    if sys.platform == "win32":
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        import subprocess

        subprocess.Popen(["open", str(path)])
    else:
        import subprocess

        subprocess.Popen(["xdg-open", str(path)])
