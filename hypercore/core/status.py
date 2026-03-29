"""Status service for HyperCore runtime information."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING

from hypercore.core.config import CORE_NAME, CORE_VERSION
from hypercore.core.platforms import PlatformInfo

if TYPE_CHECKING:
    from hypercore.core.kernel import HyperCoreKernel


@dataclass(slots=True, frozen=True)
class CoreStatus:
    core_name: str
    core_version: str
    uptime: timedelta
    request_platform_name: str
    request_platform_version: str
    runtime_platform_summary: str
    python_version: str
    plugin_count: int
    plugin_names: tuple[str, ...]
    database_status: str
    storage_mode: str
    sudo_user_count: int


class CoreStatusService:
    def __init__(self, core: "HyperCoreKernel") -> None:
        self._core = core

    async def collect(self, request_platform: PlatformInfo) -> CoreStatus:
        loaded_plugins = tuple(self._core.loader.loaded_plugins)
        storage_mode = self._core.store.mode
        return CoreStatus(
            core_name=CORE_NAME,
            core_version=CORE_VERSION,
            uptime=self._core.uptime,
            request_platform_name=request_platform.display_name,
            request_platform_version=request_platform.version,
            runtime_platform_summary=self._runtime_platform_summary(),
            python_version=sys.version.split()[0],
            plugin_count=len(loaded_plugins),
            plugin_names=loaded_plugins,
            database_status=self._database_status(storage_mode),
            storage_mode=storage_mode,
            sudo_user_count=await self._core.store.count_sudos(),
        )

    def _runtime_platform_summary(self) -> str:
        if self._core.userbot and self._core.userbot.is_running:
            platforms = ["userbot=online"]
        elif self._core.runtime_mode == "bot":
            platforms = ["userbot=disabled"]
        else:
            platforms = ["userbot=offline"]

        if self._core.bot and self._core.bot.is_running:
            platforms.append("bot=online")
        elif self._core.runtime_mode == "userbot":
            platforms.append("bot=disabled")
        elif self._core.env and self._core.env.bot_token:
            platforms.append("bot=offline")
        else:
            platforms.append("bot=disabled")
        return ", ".join(platforms)

    def _database_status(self, storage_mode: str) -> str:
        if storage_mode == "sqlite":
            return "Functional (SQLite)"
        if storage_mode == "memory":
            return "Functional (Memory)"
        return "Unavailable"


__all__ = ["CoreStatus", "CoreStatusService"]
