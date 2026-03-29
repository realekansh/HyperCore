"""Lifecycle hook management for HyperCore."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum

LifecycleHook = Callable[[], Awaitable[None] | None]
LifecycleErrorHandler = Callable[[str, Exception], None]


class LifecycleStage(str, Enum):
    AFTER_START = "after_start"
    BEFORE_SHUTDOWN = "before_shutdown"
    BEFORE_RESTART = "before_restart"


@dataclass(slots=True, frozen=True)
class _LifecycleHookRegistration:
    name: str
    callback: LifecycleHook


class LifecycleManager:
    def __init__(self) -> None:
        self._hooks: dict[LifecycleStage, list[_LifecycleHookRegistration]] = {
            stage: [] for stage in LifecycleStage
        }

    def register(
        self,
        stage: LifecycleStage,
        callback: LifecycleHook,
        *,
        name: str | None = None,
    ) -> None:
        hook_name = name or _hook_name(callback)
        self._hooks[stage].append(
            _LifecycleHookRegistration(name=hook_name, callback=callback)
        )

    def register_after_start(
        self,
        callback: LifecycleHook,
        *,
        name: str | None = None,
    ) -> None:
        self.register(LifecycleStage.AFTER_START, callback, name=name)

    def register_before_shutdown(
        self,
        callback: LifecycleHook,
        *,
        name: str | None = None,
    ) -> None:
        self.register(LifecycleStage.BEFORE_SHUTDOWN, callback, name=name)

    def register_before_restart(
        self,
        callback: LifecycleHook,
        *,
        name: str | None = None,
    ) -> None:
        self.register(LifecycleStage.BEFORE_RESTART, callback, name=name)

    async def run(
        self,
        stage: LifecycleStage,
        *,
        on_error: LifecycleErrorHandler,
        raise_on_error: bool = False,
    ) -> None:
        for registration in tuple(self._hooks[stage]):
            try:
                result = registration.callback()
                if inspect.isawaitable(result):
                    await result
            except Exception as exc:
                on_error(
                    f"Lifecycle hook '{registration.name}' failed during {stage.value}",
                    exc,
                )
                if raise_on_error:
                    raise

    def names(self, stage: LifecycleStage) -> tuple[str, ...]:
        return tuple(hook.name for hook in self._hooks[stage])


def _hook_name(callback: LifecycleHook) -> str:
    return getattr(callback, "__name__", callback.__class__.__name__)


__all__ = [
    "LifecycleHook",
    "LifecycleManager",
    "LifecycleStage",
]
