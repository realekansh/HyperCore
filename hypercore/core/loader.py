"""Plugin loading for HyperCore."""

from __future__ import annotations

import importlib
import inspect
from typing import TYPE_CHECKING, Final

from hypercore.core.config import PLUGIN_FAIL_STRATEGY
from hypercore.core.plugin_manifest import PluginManifest

if TYPE_CHECKING:
    from hypercore.core.kernel import HyperCoreKernel

DEFAULT_PLUGIN_MODULES: Final[tuple[str, ...]] = (
    "hypercore.plugins.system",
    "hypercore.plugins.sudo",
)


class PluginLoader:
    def __init__(
        self,
        core: "HyperCoreKernel",
        modules: tuple[str, ...] = DEFAULT_PLUGIN_MODULES,
    ) -> None:
        self._core = core
        self._modules = modules
        self.loaded_plugins: list[str] = []
        self.loaded_manifests: list[PluginManifest] = []

    async def load_all(self) -> None:
        for module_name in self._modules:
            try:
                module = importlib.import_module(module_name)
                manifest = self._load_manifest(module_name, module)
                setup = getattr(module, "setup", None)
                if setup is None:
                    raise RuntimeError(f"Plugin has no setup() function: {module_name}")

                result = setup(self._core)
                if inspect.isawaitable(result):
                    await result

                self._validate_registered_commands(manifest)
                self.loaded_plugins.append(manifest.name)
                self.loaded_manifests.append(manifest)
                self._core.logger.info("Loaded plugin: %s", manifest.name)
            except Exception as exc:
                self._core.log_exception(f"Failed to load plugin {module_name}", exc)
                if PLUGIN_FAIL_STRATEGY == "stop":
                    raise

    def _load_manifest(self, module_name: str, module: object) -> PluginManifest:
        manifest = getattr(module, "PLUGIN_MANIFEST", None)
        if manifest is None:
            raise RuntimeError(f"Plugin has no PLUGIN_MANIFEST: {module_name}")
        if not isinstance(manifest, PluginManifest):
            raise RuntimeError(f"Invalid plugin manifest for {module_name}")
        self._validate_manifest(module_name, manifest)
        if any(existing.name == manifest.name for existing in self.loaded_manifests):
            raise RuntimeError(f"Duplicate plugin name: {manifest.name}")
        return manifest

    def _validate_manifest(self, module_name: str, manifest: PluginManifest) -> None:
        if not manifest.name.strip():
            raise RuntimeError(f"Plugin manifest has no name: {module_name}")
        if not manifest.version.strip():
            raise RuntimeError(f"Plugin manifest has no version: {module_name}")
        normalized_commands = tuple(command.strip().lower() for command in manifest.commands)
        if len(set(normalized_commands)) != len(normalized_commands):
            raise RuntimeError(f"Plugin manifest has duplicate commands: {module_name}")
        for command_name in normalized_commands:
            if not command_name:
                raise RuntimeError(f"Plugin manifest has an empty command entry: {module_name}")
        for platform in manifest.platforms:
            if platform not in {"bot", "userbot"}:
                raise RuntimeError(
                    f"Plugin manifest has an unsupported platform '{platform}': {module_name}"
                )

    def _validate_registered_commands(self, manifest: PluginManifest) -> None:
        missing_commands = [
            command_name
            for command_name in manifest.commands
            if not self._core.registry.has_command(command_name)
        ]
        if missing_commands:
            joined = ", ".join(sorted(missing_commands))
            raise RuntimeError(
                f"Plugin manifest commands were not registered: {manifest.name} ({joined})"
            )


__all__ = ["DEFAULT_PLUGIN_MODULES", "PluginLoader"]
