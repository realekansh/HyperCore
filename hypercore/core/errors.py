"""Structured command errors for HyperCore."""

from __future__ import annotations


class CommandError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_label: str = "Error",
        edit: bool = True,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_label = status_label
        self.edit = edit


class UsageError(CommandError):
    def __init__(self, message: str, *, edit: bool = True) -> None:
        super().__init__(message, status_label="Usage", edit=edit)


class PermissionDeniedError(CommandError):
    def __init__(self, message: str = "Permission denied.", *, edit: bool = True) -> None:
        super().__init__(message, status_label="Permission", edit=edit)


class PlatformError(CommandError):
    def __init__(self, message: str, *, edit: bool = True) -> None:
        super().__init__(message, status_label="Platform", edit=edit)


__all__ = [
    "CommandError",
    "PermissionDeniedError",
    "PlatformError",
    "UsageError",
]
