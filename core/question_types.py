"""Parsing and display rules for XLSForm question types."""

from __future__ import annotations

from dataclasses import dataclass

TYPE_PLACEHOLDERS: dict[str, str] = {
    "note": "[Enumerator Note]",
    "text": "[Text]",
    "date": "[Date]",
    "datetime": "[Date and Time]",
    "time": "[Time]",
    "integer": "[Number]",
    "decimal": "[Decimal]",
    "geopoint": "[Lat, Long, Alt]",
    "geoshape": "[Shape]",
    "geotrace": "[Trace]",
    "gps": "[Lat, Long, Alt]",
    "calculate": "[Calculated field]",
    "calculate_here": "[Calculated field]",
    "image": "[Image]",
    "audio": "[Audio]",
    "video": "[Video]",
    "file": "[File]",
    "barcode": "[Barcode]",
    "acknowledge": "[Acknowledge]",
    "rank": "[Ranking]",
    "hidden": "[Hidden field]",
    "select_one": "[Select One]",
    "select_multiple": "[Select Multiple]",
    "select_one_from_file": "[Select One]",
    "select_multiple_from_file": "[Select Multiple]",
}

STRUCTURAL_TYPES = {
    "begin_group",
    "end_group",
    "begin_repeat",
    "end_repeat",
    "begin_group_",
    "end_group_",
    "begin_repeat_",
    "end_repeat_",
}

GENERATED_TYPES = {
    "start",
    "end",
    "today",
    "deviceid",
    "phonenumber",
    "username",
    "audit",
    "simserial",
    "subscriberid",
    "imei",
    "osversion",
    "launchtime",
    "email",
    "caseid",
    "comments",
    "start-geopoint",
    "background-audio",
    "text_audit",
    "audio_audit",
    "speed_violations_count",
    "speed_violations_list",
    "speed_violations_audit",
    "sensor_statistic",
    "sensor_stream",
}

# Types that XLSForm spells with spaces; they are normalised to underscores.
MULTI_WORD_TYPES: tuple[tuple[str, ...], ...] = tuple(
    tuple(name.split())
    for name in (
        "begin group",
        "end group",
        "begin repeat",
        "end repeat",
        "text audit",
        "audio audit",
        "speed violations count",
        "speed violations list",
        "speed violations audit",
    )
)

CHOICE_LIST_TYPES = {"select_one", "select_multiple", "rank"}


@dataclass(frozen=True)
class QuestionType:
    raw: str
    base: str
    list_name: str

    @property
    def is_select(self) -> bool:
        return self.base in {"select_one", "select_multiple"}

    @property
    def uses_choice_list(self) -> bool:
        """True for types whose answers come from the choices sheet."""
        return self.base in CHOICE_LIST_TYPES

    @property
    def is_structural(self) -> bool:
        return (
            self.base in STRUCTURAL_TYPES
            or self.base.startswith("begin_group")
            or self.base.startswith("end_group")
            or self.base.startswith("begin_repeat")
            or self.base.startswith("end_repeat")
        )

    @property
    def is_generated(self) -> bool:
        return self.base in GENERATED_TYPES

    @property
    def placeholder(self) -> str:
        if self.base in TYPE_PLACEHOLDERS:
            return TYPE_PLACEHOLDERS[self.base]
        if not self.base:
            return ""
        readable = self.base.replace("_", " ").replace("-", " ").strip().title()
        return f"[{readable}]"


def parse_type(raw_type: object) -> QuestionType:
    """Split an XLSForm ``type`` value into its base type and choice list."""
    text = "" if raw_type is None else str(raw_type).strip()
    parts = text.split()
    lowered = [part.lower() for part in parts]
    for words in MULTI_WORD_TYPES:
        if tuple(lowered[: len(words)]) == words:
            base = "_".join(words)
            rest = parts[len(words) :]
            break
    else:
        base = lowered[0] if lowered else ""
        rest = parts[1:]
    list_name = rest[0] if rest else ""
    return QuestionType(raw=text, base=base, list_name=list_name)
