import unittest

from hypercore.core.commands import (
    CommandAccess,
    CommandRegistry,
    CommandResponse,
    IncomingMessage,
)
from hypercore.core.errors import UsageError
from hypercore.core.platforms import PlatformCapabilities, PlatformInfo


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

PLAIN_PLATFORM = PlatformInfo(
    key="plain",
    display_name="Plain",
    version="1.0",
    capabilities=PlatformCapabilities(
        can_edit_source_message=False,
        can_edit_response_message=False,
        preferred_parse_mode=None,
    ),
)

BOT_PLATFORM = PlatformInfo(
    key="bot",
    display_name="Telegram Bot API",
    version="22.5",
    capabilities=PlatformCapabilities(
        can_edit_source_message=False,
        can_edit_response_message=True,
        preferred_parse_mode="HTML",
    ),
    command_prefixes=("/", "."),
)


class _DummyStore:
    def __init__(self, sudo_users: tuple[int, ...] = ()) -> None:
        self._sudo_users = set(sudo_users)

    async def is_sudo(self, user_id: int) -> bool:
        return user_id in self._sudo_users


class _DummyAuthorizer:
    def __init__(self, core: "_DummyCore") -> None:
        self._core = core

    async def is_authorized(self, sender_id: int, access: CommandAccess) -> bool:
        if self._core.owner_id is not None and sender_id == self._core.owner_id:
            return True
        if access is CommandAccess.OWNER:
            return False
        return await self._core.store.is_sudo(sender_id)


class _DummyEvents:
    def __init__(self) -> None:
        self.emitted: list[tuple[object, dict[str, object]]] = []

    def emit(self, event_type, **payload):
        self.emitted.append((event_type, payload))


class _DummyCore:
    def __init__(self, owner_id: int = 1, sudo_users: tuple[int, ...] = ()) -> None:
        self.owner_id = owner_id
        self.store = _DummyStore(sudo_users=sudo_users)
        self.authorizer = _DummyAuthorizer(self)
        self.events = _DummyEvents()
        self.logged_errors: list[tuple[str, Exception]] = []

    def handle_command_error(self, command_name: str, exc: Exception) -> None:
        self.logged_errors.append((command_name, exc))


class CommandRegistryTests(unittest.IsolatedAsyncioTestCase):
    async def test_dispatch_renders_permission_error(self) -> None:
        core = _DummyCore(owner_id=1)
        registry = CommandRegistry(core)

        async def owner_only(ctx):
            del ctx
            return "secret"

        registry.register("secret", owner_only, access=CommandAccess.OWNER)
        handled, responses = await self._dispatch(
            registry,
            platform_info=HTML_PLATFORM,
            sender_id=2,
            text=".secret",
        )

        self.assertTrue(handled)
        self.assertEqual(len(responses), 1)
        self.assertEqual(
            responses[0].text,
            "<b>Permission:</b> <code>Permission denied.</code>",
        )
        self.assertEqual(responses[0].parse_mode, "HTML")

    async def test_dispatch_renders_usage_error_from_handler(self) -> None:
        core = _DummyCore(owner_id=1)
        registry = CommandRegistry(core)

        async def invalid_usage(ctx):
            del ctx
            raise UsageError("Use .demo <id>")

        registry.register("demo", invalid_usage)
        handled, responses = await self._dispatch(
            registry,
            platform_info=HTML_PLATFORM,
            sender_id=1,
            text=".demo",
        )

        self.assertTrue(handled)
        self.assertEqual(
            responses[0].text,
            "<b>Usage:</b> <code>Use .demo &lt;id&gt;</code>",
        )
        self.assertEqual(responses[0].parse_mode, "HTML")

    async def test_dispatch_renders_platform_error_with_plain_fallback(self) -> None:
        core = _DummyCore(owner_id=1)
        registry = CommandRegistry(core)

        async def requires_edit(ctx):
            ctx.require_capability(
                "can_edit_source_message",
                message="Source edit not supported.",
            )
            return None

        registry.register("cap", requires_edit)
        handled, responses = await self._dispatch(
            registry,
            platform_info=PLAIN_PLATFORM,
            sender_id=1,
            text=".cap",
        )

        self.assertTrue(handled)
        self.assertEqual(responses[0].text, "Platform: Source edit not supported.")
        self.assertIsNone(responses[0].parse_mode)

    async def test_dispatch_logs_and_renders_generic_failure(self) -> None:
        core = _DummyCore(owner_id=1)
        registry = CommandRegistry(core)

        async def exploding_handler(ctx):
            del ctx
            raise RuntimeError("boom")

        registry.register("boom", exploding_handler)
        handled, responses = await self._dispatch(
            registry,
            platform_info=HTML_PLATFORM,
            sender_id=1,
            text=".boom",
        )

        self.assertTrue(handled)
        self.assertEqual(
            responses[0].text,
            "<b>Error:</b> <code>Command failed.</code>",
        )
        self.assertEqual(len(core.logged_errors), 1)
        self.assertEqual(core.logged_errors[0][0], "boom")
        self.assertIsInstance(core.logged_errors[0][1], RuntimeError)

    async def test_dispatch_passes_command_response_through(self) -> None:
        core = _DummyCore(owner_id=1)
        registry = CommandRegistry(core)
        expected = CommandResponse(text="ok", parse_mode="HTML", edit=False)

        async def custom_response(ctx):
            del ctx
            return expected

        registry.register("ok", custom_response)
        handled, responses = await self._dispatch(
            registry,
            platform_info=HTML_PLATFORM,
            sender_id=1,
            text=".ok",
        )

        self.assertTrue(handled)
        self.assertEqual(responses, [expected])

    async def test_dispatch_supports_platform_specific_command_prefixes(self) -> None:
        core = _DummyCore(owner_id=1)
        registry = CommandRegistry(core)

        async def slash_ok(ctx):
            return ctx.command_ref("ok")

        registry.register("ok", slash_ok)
        handled, responses = await self._dispatch(
            registry,
            platform_info=BOT_PLATFORM,
            sender_id=1,
            text="/ok",
        )

        self.assertTrue(handled)
        self.assertEqual(responses[0].text, "/ok")

    async def test_dispatch_strips_bot_username_from_slash_commands(self) -> None:
        core = _DummyCore(owner_id=1)
        registry = CommandRegistry(core)

        async def ping(ctx):
            del ctx
            return "pong"

        registry.register("ping", ping)
        handled, responses = await self._dispatch(
            registry,
            platform_info=BOT_PLATFORM,
            sender_id=1,
            text="/ping@HyperCoreTestingBot",
        )

        self.assertTrue(handled)
        self.assertEqual(responses[0].text, "pong")

    async def test_dispatch_skips_commands_for_unsupported_platform(self) -> None:
        core = _DummyCore(owner_id=1)
        registry = CommandRegistry(core)

        async def bot_only(ctx):
            del ctx
            return "bot"

        registry.register("botonly", bot_only, platforms=("bot",))
        handled, responses = await self._dispatch(
            registry,
            platform_info=HTML_PLATFORM,
            sender_id=1,
            text=".botonly",
        )

        self.assertFalse(handled)
        self.assertEqual(responses, [])

    async def test_command_metadata_tracks_aliases_and_usage(self) -> None:
        core = _DummyCore(owner_id=1)
        registry = CommandRegistry(core)

        async def demo(ctx):
            return ctx.spec.usage or ""

        spec = registry.register(
            "demo",
            demo,
            aliases=("sample",),
            usage="demo <id>",
            description="Demo command",
        )
        handled, responses = await self._dispatch(
            registry,
            platform_info=HTML_PLATFORM,
            sender_id=1,
            text=".sample",
        )

        self.assertEqual(spec.aliases, ("sample",))
        self.assertEqual(spec.usage, "demo <id>")
        self.assertEqual(registry.names, ("demo",))
        self.assertTrue(handled)
        self.assertEqual(responses[0].text, "demo <id>")

    async def _dispatch(
        self,
        registry: CommandRegistry,
        *,
        platform_info: PlatformInfo,
        sender_id: int,
        text: str,
    ) -> tuple[bool, list[CommandResponse]]:
        responses: list[CommandResponse] = []

        async def send_reply(response: CommandResponse) -> None:
            responses.append(response)

        handled = await registry.dispatch(
            IncomingMessage(
                platform=platform_info.key,
                platform_info=platform_info,
                sender_id=sender_id,
                chat_id=100,
                text=text,
                received_at=0.0,
                reply_to_user_id=None,
                send_reply=send_reply,
            )
        )
        return handled, responses
