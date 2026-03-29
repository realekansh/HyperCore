"""Platform metadata and capability models for HyperCore."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class PlatformCapabilities:
    can_edit_source_message: bool
    can_edit_response_message: bool
    preferred_parse_mode: str | None = None

    @property
    def supports_formatting(self) -> bool:
        return self.preferred_parse_mode is not None

    @property
    def supports_html(self) -> bool:
        return (self.preferred_parse_mode or "").upper() == "HTML"


@dataclass(slots=True, frozen=True)
class PlatformInfo:
    key: str
    display_name: str
    version: str
    capabilities: PlatformCapabilities
    command_prefixes: tuple[str, ...] = (".",)

    @property
    def primary_command_prefix(self) -> str:
        if self.command_prefixes:
            return self.command_prefixes[0]
        return "."


__all__ = ["PlatformCapabilities", "PlatformInfo"]
