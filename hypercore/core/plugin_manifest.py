"""Plugin metadata definitions for HyperCore."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class PluginManifest:
    name: str
    version: str
    description: str
    commands: tuple[str, ...] = ()
    platforms: tuple[str, ...] = ()

    def supports_platform(self, platform: str) -> bool:
        return not self.platforms or platform in self.platforms


__all__ = ["PluginManifest"]
