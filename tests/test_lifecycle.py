import unittest

from hypercore.core.lifecycle import LifecycleManager, LifecycleStage


class LifecycleManagerTests(unittest.IsolatedAsyncioTestCase):
    async def test_runs_sync_and_async_hooks_in_order(self) -> None:
        manager = LifecycleManager()
        events: list[str] = []
        errors: list[tuple[str, Exception]] = []

        def sync_hook() -> None:
            events.append("sync")

        async def async_hook() -> None:
            events.append("async")

        manager.register_after_start(sync_hook, name="sync_hook")
        manager.register_after_start(async_hook, name="async_hook")

        await manager.run(
            LifecycleStage.AFTER_START,
            on_error=lambda message, exc: errors.append((message, exc)),
        )

        self.assertEqual(events, ["sync", "async"])
        self.assertEqual(errors, [])
        self.assertEqual(manager.names(LifecycleStage.AFTER_START), ("sync_hook", "async_hook"))

    async def test_reports_errors_and_continues_by_default(self) -> None:
        manager = LifecycleManager()
        events: list[str] = []
        errors: list[tuple[str, Exception]] = []

        def broken_hook() -> None:
            raise RuntimeError("boom")

        def trailing_hook() -> None:
            events.append("trailing")

        manager.register_before_shutdown(broken_hook, name="broken_hook")
        manager.register_before_shutdown(trailing_hook, name="trailing_hook")

        await manager.run(
            LifecycleStage.BEFORE_SHUTDOWN,
            on_error=lambda message, exc: errors.append((message, exc)),
        )

        self.assertEqual(events, ["trailing"])
        self.assertEqual(len(errors), 1)
        self.assertIn("broken_hook", errors[0][0])
        self.assertIn("before_shutdown", errors[0][0])
        self.assertIsInstance(errors[0][1], RuntimeError)

    async def test_raise_on_error_re_raises_exception(self) -> None:
        manager = LifecycleManager()
        errors: list[tuple[str, Exception]] = []

        def broken_hook() -> None:
            raise RuntimeError("boom")

        manager.register_before_restart(broken_hook, name="broken_hook")

        with self.assertRaises(RuntimeError):
            await manager.run(
                LifecycleStage.BEFORE_RESTART,
                on_error=lambda message, exc: errors.append((message, exc)),
                raise_on_error=True,
            )

        self.assertEqual(len(errors), 1)
        self.assertIn("before_restart", errors[0][0])
