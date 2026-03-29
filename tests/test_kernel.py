from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from hypercore.core.commands import CommandResponse
from hypercore.core.env_loader import PlatformEnv
from hypercore.core.kernel import HyperCoreKernel
from hypercore.core.platforms import PlatformCapabilities, PlatformInfo
from hypercore.core.storage import MemoryStateStore
from hypercore.core.updater import UpdateResult


HTML_PLATFORM = PlatformInfo(
    key="userbot",
    display_name="Telethon",
    version="1.40.0",
    capabilities=PlatformCapabilities(
        can_edit_source_message=True,
        can_edit_response_message=True,
        preferred_parse_mode="HTML",
    ),
)


class _DummyStore(MemoryStateStore):
    def __init__(self) -> None:
        super().__init__()
        self.initialized = False
        self.closed = False

    async def initialize(self) -> None:
        self.initialized = True

    async def close(self) -> None:
        self.closed = True
        await super().close()


class _DummyLoader:
    def __init__(self, core) -> None:
        self.core = core
        self.loaded_plugins = ["system", "sudo"]
        self.loaded_manifests = []

    async def load_all(self) -> None:
        return None


class _DummyUserbot:
    def __init__(self, core, env) -> None:
        del env
        self.core = core
        self.owner_id = 777
        self.is_running = False

    async def start(self) -> None:
        self.is_running = True

    async def stop(self) -> None:
        self.is_running = False


class _DummyBot:
    def __init__(self, core, token) -> None:
        del token
        self.core = core
        self.is_running = False

    async def start(self) -> None:
        self.is_running = True

    async def stop(self) -> None:
        self.is_running = False


class _FailingGuard:
    def __init__(self) -> None:
        self.released = False

    def acquire(self, runtime_mode: str) -> None:
        del runtime_mode
        raise RuntimeError("Another HyperCore instance is already running.")

    def release(self) -> None:
        self.released = True


class KernelIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_bootstrap_emits_startup_event(self) -> None:
        env = PlatformEnv(
            api_id=1,
            api_hash="hash",
            bot_token="token",
            database_url=None,
            log_channel=None,
            env_path=Path("C:/HyperCore/.env"),
        )
        store = _DummyStore()

        with patch("hypercore.core.kernel.load_platform_env", return_value=env), patch(
            "hypercore.core.kernel.create_state_store",
            return_value=store,
        ), patch("hypercore.core.kernel.PluginLoader", _DummyLoader), patch(
            "hypercore.core.kernel.TelegramUserbot",
            _DummyUserbot,
        ), patch("hypercore.core.kernel.TelegramBot", _DummyBot):
            kernel = HyperCoreKernel(runtime_mode="both")
            await kernel._bootstrap()

        startup_events = [
            event
            for event in kernel.events.recent()
            if event.event_type.value == "startup_complete"
        ]
        self.assertTrue(store.initialized)
        self.assertEqual(kernel.owner_id, 777)
        self.assertEqual(len(startup_events), 1)
        self.assertEqual(startup_events[0].payload["plugin_count"], 2)

    async def test_handle_incoming_message_dispatches_through_core(self) -> None:
        kernel = HyperCoreKernel(runtime_mode="userbot")
        kernel.owner_id = 1
        kernel.store = MemoryStateStore()
        await kernel.store.initialize()

        async def demo(ctx):
            del ctx
            return CommandResponse(text="ok", parse_mode="HTML")

        kernel.registry.register("demo", demo)
        responses: list[CommandResponse] = []

        async def send_reply(response: CommandResponse) -> None:
            responses.append(response)

        await kernel.handle_incoming_message(
            platform=HTML_PLATFORM.key,
            platform_info=HTML_PLATFORM,
            sender_id=1,
            chat_id=100,
            text=".demo",
            received_at=0.0,
            reply_to_user_id=None,
            send_reply=send_reply,
        )

        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0].text, "ok")
        self.assertEqual(
            kernel.events.recent()[-1].event_type.value,
            "command_executed",
        )

    async def test_perform_core_update_emits_result_event(self) -> None:
        kernel = HyperCoreKernel()
        kernel.updater = SimpleNamespace(
            update_core=lambda: UpdateResult(True, False, "Core is already up to date.")
        )

        result = await kernel.perform_core_update()

        self.assertTrue(result.success)
        self.assertEqual(kernel.events.recent()[-1].event_type.value, "update_finished")
        self.assertFalse(kernel.events.recent()[-1].payload["changed"])

    async def test_run_releases_guard_when_instance_is_already_active(self) -> None:
        with TemporaryDirectory() as temp_dir:
            with patch("hypercore.core.kernel.project_root", return_value=Path(temp_dir)):
                kernel = HyperCoreKernel()

            kernel.instance_guard = _FailingGuard()
            kernel.store = _DummyStore()

            with self.assertRaisesRegex(
                RuntimeError,
                "Another HyperCore instance is already running.",
            ):
                await kernel.run()

            self.assertTrue(kernel.instance_guard.released)
            self.assertTrue(kernel.store.closed)
