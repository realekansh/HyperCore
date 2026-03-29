import logging
import unittest

from hypercore.core.events import CoreEventBus, CoreEventType


class CoreEventBusTests(unittest.TestCase):
    def test_emit_records_recent_events(self) -> None:
        bus = CoreEventBus(logging.getLogger("hypercore.test"), max_events=2)

        bus.emit(CoreEventType.STARTUP_COMPLETE, runtime_mode="bot")
        bus.emit(CoreEventType.RESTART_REQUESTED, runtime_mode="bot")
        bus.emit(CoreEventType.SHUTDOWN_REQUESTED, runtime_mode="bot")

        recent = bus.recent()

        self.assertEqual(len(recent), 2)
        self.assertEqual(recent[0].event_type, CoreEventType.RESTART_REQUESTED)
        self.assertEqual(recent[1].payload["runtime_mode"], "bot")
