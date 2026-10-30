"""Build the portable Windows distribution of XLSForm2Word."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.config import AppSettings
from utils.version import APP_NAME, APP_VERSION, AUTHOR, WEBSITE

DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
TARGET_DIR = DIST_DIR / APP_NAME
VERSION_FILE = BUILD_DIR / "version_info.txt"


def _version_tuple(version: str) -> tuple[int, int, int, int]:
    parts: list[int] = []
    for part in version.split("."):
        try:
            parts.append(max(0, min(65535, int(part))))
        except ValueError:
            parts.append(0)
    return tuple((parts + [0, 0, 0, 0])[:4])  # type: ignore[return-value]


def _write_version_info() -> Path:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    number = _version_tuple(APP_VERSION)
    year = datetime.now().year
    content = f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={number},
    prodvers={number},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', {AUTHOR!r}),
          StringStruct('FileDescription', 'XLSForm to Word questionnaire converter'),
          StringStruct('FileVersion', {APP_VERSION!r}),
          StringStruct('InternalName', {APP_NAME!r}),
          StringStruct('LegalCopyright', f'Copyright (c) {year} {AUTHOR}'),
          StringStruct('OriginalFilename', {f"{APP_NAME}.exe"!r}),
          StringStruct('ProductName', {APP_NAME!r}),
          StringStruct('ProductVersion', {APP_VERSION!r}),
          StringStruct('Comments', f'Generated using {APP_NAME} v{APP_VERSION}'),
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
    VERSION_FILE.write_text(content, encoding="utf-8")
    return VERSION_FILE


def _write_default_settings(target: Path) -> None:
    settings = AppSettings().normalized()
    payload = json.dumps(asdict(settings), indent=2, ensure_ascii=False) + "\n"
    (target / "settings.json").write_text(payload, encoding="utf-8")


def _ensure_assets() -> None:
    if not (ROOT / "assets" / "icon.ico").exists():
        from tools.make_icon import main as make_icon

        make_icon()
    from tools.build_user_guide_pdf import main as make_readme

    make_readme()


def _run_tests() -> None:
    if importlib.util.find_spec("pytest") is None:
        print("pytest is not installed; skipping tests.")
        return
    print("Running test suite...")
    subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=ROOT,
        check=True,
    )


def _run_pyinstaller() -> None:
    if importlib.util.find_spec("PyInstaller") is None:
        raise SystemExit(
            "PyInstaller is not installed. Run:\n  pip install -r requirements-dev.txt"
        )
    print("Building executable with PyInstaller...")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--clean",
            "--noconfirm",
            str(ROOT / f"{APP_NAME}.spec"),
        ],
        cwd=ROOT,
        check=True,
    )


def _require_python_version() -> None:
    if sys.version_info < (3, 12):
        raise SystemExit(
            f"{APP_NAME} builds require Python 3.12 or newer; detected "
            f"{sys.version.split()[0]}.\n"
            "Install Python 3.12 and run build.py with that interpreter."
        )


def _remove_tree_with_retries(path: Path, attempts: int = 4) -> bool:
    for attempt in range(attempts):
        try:
            shutil.rmtree(path)
            return True
        except FileNotFoundError:
            return True
        except OSError:
            if attempt == attempts - 1:
                return False
            time.sleep(0.5)
    return False


def _backup_path() -> Path:
    return DIST_DIR / f".{APP_NAME}.old-{uuid.uuid4().hex[:8]}"


def _replace_build_directory(staging: Path, target: Path) -> None:
    backup: Path | None = None
    if target.exists():
        backup = _backup_path()
        try:
            target.rename(backup)
        except OSError as exc:
            raise SystemExit(
                f"Could not replace {target}.\n"
                "Close any running XLSForm2Word window and try again."
            ) from exc

    try:
        staging.rename(target)
    except OSError as exc:
        if backup is not None and not target.exists():
            try:
                backup.rename(target)
            except OSError:
                print(f"Warning: previous build remains at {backup}")
        raise SystemExit(
            f"Could not finalize the portable build at {target}.\n"
            "Close any running XLSForm2Word window and try again."
        ) from exc

    if backup is not None and not _remove_tree_with_retries(backup):
        print(f"Warning: the previous build could not be removed: {backup}")


def _run_frozen_smoke_test(executable: Path) -> None:
    sample = ROOT / "sample" / "HouseholdSurvey_ODK.xlsx"
    if not sample.exists():
        raise SystemExit(f"Smoke-test sample is missing: {sample}")

    smoke_dir = Path(tempfile.mkdtemp(prefix="xlsform2word-smoke-"))
    log_file = executable.parent / "logs" / "xlsform2word.log"
    try:
        print("Running frozen EXE smoke test...")
        try:
            completed = subprocess.run(
                [str(executable), "--smoke-test", str(sample), str(smoke_dir)],
                cwd=executable.parent,
                timeout=180,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise SystemExit(
                "Frozen EXE smoke test timed out after 180 seconds."
            ) from exc

        result_file = smoke_dir / "smoke_test_result.txt"
        result_text = (
            result_file.read_text(encoding="utf-8")
            if result_file.exists()
            else "The frozen EXE did not write a smoke-test result file."
        )
        if completed.returncode != 0 or not result_text.startswith("OK"):
            raise SystemExit(
                "Frozen EXE smoke test failed.\n"
                f"Exit code: {completed.returncode}\n{result_text}"
            )

        expected = {
            "Household Survey_English_word.docx",
            "Household Survey_Bangla_word.docx",
            "Household Survey_Arabic_word.docx",
        }
        outputs = {path.name: path for path in smoke_dir.glob("*_word.docx")}
        if set(outputs) != expected:
            raise SystemExit(
                "Frozen EXE smoke test generated unexpected documents: "
                f"{sorted(outputs)}"
            )

        for path in outputs.values():
            with zipfile.ZipFile(path) as archive:
                app_xml = archive.read("docProps/app.xml").decode("utf-8")
                document_xml = archive.read("word/document.xml").decode("utf-8")
            if f"<Company>{xml_escape(AUTHOR)}</Company>" not in app_xml:
                raise SystemExit(f"Company metadata missing from {path.name}")
            if WEBSITE not in document_xml:
                raise SystemExit(f"Footer hyperlink missing from {path.name}")

        with zipfile.ZipFile(outputs["Household Survey_Arabic_word.docx"]) as archive:
            arabic_document = archive.read("word/document.xml").decode("utf-8")
        if "<w:bidi" not in arabic_document:
            raise SystemExit("Arabic smoke-test document does not contain RTL text.")
        print("Frozen EXE smoke test passed: 3 documents generated and verified.")
    finally:
        try:
            log_file.unlink(missing_ok=True)
        except OSError:
            pass
        shutil.rmtree(smoke_dir, ignore_errors=True)


def _create_archive(archive_stem: str) -> Path:
    archive_path = DIST_DIR / f"{archive_stem}.zip"
    temp_base = DIST_DIR / f".{archive_stem}-{uuid.uuid4().hex[:8]}"
    temp_zip = Path(f"{temp_base}.zip")
    try:
        shutil.make_archive(
            str(temp_base),
            "zip",
            root_dir=DIST_DIR,
            base_dir=TARGET_DIR.name,
        )
        try:
            temp_zip.replace(archive_path)
        except OSError as exc:
            raise SystemExit(
                f"Could not replace {archive_path}.\n"
                "Close any program using the previous ZIP and try again."
            ) from exc
    finally:
        temp_zip.unlink(missing_ok=True)
    return archive_path


def _assemble_portable_build() -> Path:
    source_exe = DIST_DIR / f"{APP_NAME}.exe"
    if not source_exe.exists():
        raise SystemExit(
            f"PyInstaller did not create {source_exe}.\n"
            "Review the build output above for details."
        )

    staging_root = Path(
        tempfile.mkdtemp(prefix=f".{APP_NAME}-stage-", dir=DIST_DIR)
    )
    staging_dir = staging_root / APP_NAME
    try:
        staging_dir.mkdir()
        shutil.copy2(source_exe, staging_dir / f"{APP_NAME}.exe")
        shutil.copytree(ROOT / "assets", staging_dir / "assets", dirs_exist_ok=True)
        (staging_dir / "logs").mkdir(exist_ok=True)
        (staging_dir / "logs" / "README.txt").write_text(
            "XLSForm2Word writes xlsform2word.log in this folder.\n",
            encoding="utf-8",
        )

        readme_pdf = ROOT / "README.pdf"
        if readme_pdf.exists():
            shutil.copy2(readme_pdf, staging_dir / "README.pdf")

        license_file = ROOT / "LICENSE"
        if license_file.exists():
            shutil.copy2(license_file, staging_dir / "LICENSE")

        _write_default_settings(staging_dir)
        _run_frozen_smoke_test(staging_dir / f"{APP_NAME}.exe")
        _replace_build_directory(staging_dir, TARGET_DIR)
        source_exe.unlink(missing_ok=True)
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)

    return _create_archive(f"{APP_NAME}_v{APP_VERSION}_Windows")


def _print_summary(archive: Path) -> None:
    print()
    print(f"{APP_NAME} v{APP_VERSION} portable build created")
    print(f"  Folder : {TARGET_DIR}")
    print(f"  ZIP    : {archive}")
    print(f"  Author : {AUTHOR}")
    print(f"  Web    : {WEBSITE}")
    print()
    print("Distribute the ZIP. Users extract it and double-click the EXE.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Build without running the test suite first.",
    )
    args = parser.parse_args()

    _require_python_version()
    _ensure_assets()
    if not args.skip_tests:
        _run_tests()
    _write_version_info()
    _run_pyinstaller()
    archive = _assemble_portable_build()
    _print_summary(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
