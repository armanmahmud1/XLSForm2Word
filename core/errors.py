"""User-facing exception types that never expose Python tracebacks."""

from __future__ import annotations


class XLSForm2WordError(Exception):
    """Base class for expected, friendly application errors."""


class XLSFormError(XLSForm2WordError):
    """The selected file is not a usable XLSForm."""


class ValidationError(XLSForm2WordError):
    """One or more pre-generation checks failed."""

    def __init__(self, errors: list[str] | str) -> None:
        if isinstance(errors, str):
            errors = [errors]
        self.errors = errors
        super().__init__("\n".join(errors))

    @property
    def message(self) -> str:
        if len(self.errors) == 1:
            return self.errors[0]
        return "\n".join(f"• {error}" for error in self.errors)


class DocumentGenerationError(XLSForm2WordError):
    """A Word document could not be written."""
