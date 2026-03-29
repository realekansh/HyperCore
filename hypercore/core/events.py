"""Core runtime event recording for HyperCore."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
from typing import Any


class CoreEventType(str, Enum):
    STARTUP_COMPLETE = "startup_complete"
    COMMAND_EXECUTED = "command_executed"
    RESTART_REQUESTED = "restart_requested"
    SHUTDOWN_REQUESTED = "shutdown_requested"
    UPDATE_FINISHED = "update_finished"


@dataclass(slots=True, frozen=True)
class CoreEvent:
    event_type: CoreEventType
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class CoreEventBus:
    def __init__(
        self,
        logger: logging.Logger,
        *,
        max_events: int = 100,
    ) -> None:
        self._logger = logger
        self._events: deque[CoreEvent] = deque(maxlen=max_events)

    def emit(self, event_type: CoreEventType, **payload: Any) -> CoreEvent:
        event = CoreEvent(event_type=event_type, payload=dict(payload))
        self._events.append(event)
        details = " ".join(
            f"{key}={value}"
            for key, value in sorted(payload.items())
            if value is not None
        )
        if details:
            self._logger.debug("Core event: %s %s", event_type.value, details)
        else:
            self._logger.debug("Core event: %s", event_type.value)
        return event

    def recent(self) -> tuple[CoreEvent, ...]:
        return tuple(self._events)


__all__ = ["CoreEvent", "CoreEventBus", "CoreEventType"]
