"""Telegram userbot runtime for HyperCore."""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from hypercore.core.commands import CommandResponse
from hypercore.core.platforms import PlatformCapabilities, PlatformInfo

if TYPE_CHECKING:
    from hypercore.core.env_loader import PlatformEnv
    from hypercore.core.kernel import HyperCoreKernel


class TelegramUserbot:
    def __init__(self, core: "HyperCoreKernel", env: "PlatformEnv") -> None:
        self._core = core
        self._env = env
        self._client: Any = None
        self._platform_info = PlatformInfo(
            key="userbot",
            display_name="Telethon",
            version="unknown",
            capabilities=PlatformCapabilities(
                can_edit_source_message=True,
                can_edit_response_message=True,
                preferred_parse_mode="HTML",
            ),
            command_prefixes=(".",),
        )
        self.owner_id: int | None = None
        self.is_running = False

    async def start(self) -> None:
        telethon, TelegramClient, events = _load_telethon()

        self._platform_info = PlatformInfo(
            key="userbot",
            display_name="Telethon",
            version=getattr(telethon, "__version__", "unknown"),
            capabilities=self._platform_info.capabilities,
            command_prefixes=self._platform_info.command_prefixes,
        )

        session_name = str(_session_path(self._core.root_path))
        self._client = TelegramClient(session_name, self._env.api_id, self._env.api_hash)

        @self._client.on(events.NewMessage)
        async def _message_handler(event: Any) -> None:
            await self._handle_message(event)

        await self._client.start()
        me = await self._client.get_me()
        if me is None or getattr(me, "id", None) is None:
            raise RuntimeError("Failed to resolve the userbot identity.")

        self.owner_id = int(me.id)
        self.is_running = True
        identity = getattr(me, "username", None) or getattr(me, "first_name", None) or str(me.id)
        self._core.logger.info("Userbot connected as %s", identity)

    async def stop(self) -> None:
        if self._client is None:
            return
        await self._client.disconnect()
        self.is_running = False

    async def _handle_message(self, event: Any) -> None:
        text = getattr(event, "raw_text", None) or ""
        if not text.startswith(self._platform_info.primary_command_prefix):
            return
        received_at = time.perf_counter()

        reply_to_user_id = None
        if getattr(event, "is_reply", False):
            reply_message = await event.get_reply_message()
            if reply_message is not None:
                reply_to_user_id = getattr(reply_message, "sender_id", None)

        async def send_reply(payload: CommandResponse) -> None:
            parse_mode = None
            if payload.parse_mode is not None:
                parse_mode = payload.parse_mode.lower()
            if payload.edit and self._platform_info.capabilities.can_edit_source_message:
                try:
                    await event.edit(payload.text, parse_mode=parse_mode)
                    return
                except Exception:
                    pass
            await event.reply(payload.text, parse_mode=parse_mode)

        await self._core.handle_incoming_message(
            platform=self._platform_info.key,
            platform_info=self._platform_info,
            sender_id=getattr(event, "sender_id", None),
            chat_id=getattr(event, "chat_id", None),
            text=text,
            received_at=received_at,
            reply_to_user_id=reply_to_user_id,
            send_reply=send_reply,
        )

    @staticmethod
    async def resolve_owner_identity(root_path: Path, env: "PlatformEnv") -> tuple[int, str]:
        telethon, TelegramClient, _ = _load_telethon()
        session_name = str(_session_path(root_path))
        client = TelegramClient(session_name, env.api_id, env.api_hash)
        await client.start()
        try:
            me = await client.get_me()
            if me is None or getattr(me, "id", None) is None:
                raise RuntimeError("Failed to resolve the userbot identity.")
            owner_id = int(me.id)
            version = getattr(telethon, "__version__", "unknown")
            return owner_id, version
        finally:
            await client.disconnect()


def _session_path(root_path: Path) -> Path:
    session_dir = (root_path / "runtime").resolve()
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir / "hypercore_userbot"


def _load_telethon():
    try:
        import telethon
        from telethon import TelegramClient, events
    except ImportError as exc:
        raise RuntimeError("telethon is required for the userbot runtime.") from exc
    return telethon, TelegramClient, events


__all__ = ["TelegramUserbot"]
