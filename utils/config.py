"""Persistent user settings backed by a portable ``settings.json`` file."""

from __future__ import annotations

import json
import logging
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from utils.paths import settings_path

logger = logging.getLogger(__name__)

PLATFORMS: tuple[str, ...] = ("ODK", "SurveyCTO")
COLUMN_NAMES: tuple[str, ...] = (
    "Variable",
    "Question",
    "Choices",
    "Constraint",
    "Relevance",
    "Calculation",
)
DEFAULT_COLUMNS: tuple[str, ...] = COLUMN_NAMES
DEFAULT_PLATFORM = "ODK"


@dataclass
class AppSettings:
    """User preferences that survive application restarts."""

    platform: str = DEFAULT_PLATFORM
    output_folder: str = ""
    selected_columns: list[str] = field(default_factory=lambda: list(DEFAULT_COLUMNS))
    window_geometry: str = ""

    def normalized(self) -> AppSettings:
        """Return a copy with only valid values."""
        platform = self.platform if self.platform in PLATFORMS else DEFAULT_PLATFORM
        columns = [name for name in self.selected_columns if name in COLUMN_NAMES]
        if not columns:
            columns = list(DEFAULT_COLUMNS)
        return AppSettings(
            platform=platform,
            output_folder=str(self.output_folder or "").strip(),
            selected_columns=columns,
            window_geometry=str(self.window_geometry or ""),
        )


class SettingsManager:
    """Load and save :class:`AppSettings` without ever crashing on bad data."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or settings_path()
        self.settings = AppSettings()

    def load(self) -> AppSettings:
        if not self.path.exists():
            self.settings = AppSettings()
            return self.settings

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise TypeError("settings.json must contain a JSON object")
            self.settings = AppSettings(
                platform=str(raw.get("platform", DEFAULT_PLATFORM)),
                output_folder=str(raw.get("output_folder", "")),
                selected_columns=self._read_columns(raw.get("selected_columns")),
                window_geometry=str(raw.get("window_geometry", "")),
            ).normalized()
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            logger.warning("Could not read settings; using defaults: %s", exc)
            self.settings = AppSettings()
        return self.settings

    @staticmethod
    def _read_columns(value: Any) -> list[str]:
        if not isinstance(value, list):
            return list(DEFAULT_COLUMNS)
        return [str(item) for item in value]

    def save(self, settings: AppSettings | None = None) -> bool:
        if settings is not None:
            self.settings = settings.normalized()

        payload = json.dumps(asdict(self.settings), indent=2, ensure_ascii=False) + "\n"
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=".settings-",
                suffix=".tmp",
                delete=False,
            ) as handle:
                handle.write(payload)
                temp_path = Path(handle.name)
            temp_path.replace(self.path)
            return True
        except OSError as exc:
            logger.error("Could not save settings to %s: %s", self.path, exc)
            return False

    def reset(self) -> AppSettings:
        self.settings = AppSettings()
        self.save()
        return self.settings
