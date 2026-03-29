"""Telegram bot runtime for HyperCore."""

from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING, Any

from hypercore.core.commands import CommandResponse
from hypercore.core.config import CORE_NAME, CORE_VERSION
from hypercore.core.formatter import make_rows_response
from hypercore.core.platforms import PlatformCapabilities, PlatformInfo

if TYPE_CHECKING:
    from hypercore.core.kernel import HyperCoreKernel


DEFAULT_BOT_COMMAND_PREFIX = "/"
BOT_COMMAND_PREFIX_ALIASES = (".",)


class TelegramBot:
    def __init__(self, core: "HyperCoreKernel", token: str) -> None:
        self._core = core
        self._token = token
        self._application: Any = None
        self._platform_info = PlatformInfo(
            key="bot",
            display_name="Telegram Bot API",
            version="unknown",
            capabilities=PlatformCapabilities(
                can_edit_source_message=False,
                can_edit_response_message=True,
                preferred_parse_mode="HTML",
            ),
            command_prefixes=_build_command_prefixes(
                DEFAULT_BOT_COMMAND_PREFIX,
                *BOT_COMMAND_PREFIX_ALIASES,
            ),
        )
        self.is_running = False

    async def start(self) -> None:
        try:
            import telegram
            from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
        except ImportError as exc:
            raise RuntimeError(
                "python-telegram-bot is required when BOT_TOKEN is configured."
            ) from exc

        self._platform_info = PlatformInfo(
            key="bot",
            display_name="Telegram Bot API",
            version=getattr(telegram, "__version__", "unknown"),
            capabilities=self._platform_info.capabilities,
            command_prefixes=self._platform_info.command_prefixes,
        )

        self._application = ApplicationBuilder().token(self._token).build()
        self._application.add_handler(CommandHandler("start", self._handle_start))

        command_names = list(self._core.registry.command_names_for_platform("bot"))
        if command_names:
            self._application.add_handler(
                CommandHandler(command_names, self._handle_command)
            )

        legacy_prefixes = tuple(
            prefix
            for prefix in self._platform_info.command_prefixes
            if prefix != self._platform_info.primary_command_prefix
        )
        if legacy_prefixes:
            self._application.add_handler(
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND
                    & filters.Regex(_build_prefix_pattern(legacy_prefixes)),
                    self._handle_prefixed_message,
                )
            )

        await self._application.initialize()
        await self._application.start()
        if self._application.updater is None:
            raise RuntimeError("Bot updater is unavailable.")
        await self._application.updater.start_polling(drop_pending_updates=True)
        self.is_running = True

        me = await self._application.bot.get_me()
        identity = f"@{me.username}" if getattr(me, "username", None) else str(me.id)
        self._core.logger.info("Bot connected as %s", identity)

    async def stop(self) -> None:
        if self._application is None:
            return
        if self._application.updater is not None:
            await self._application.updater.stop()
        await self._application.stop()
        await self._application.shutdown()
        self.is_running = False

    async def _handle_start(self, update: Any, context: Any) -> None:
        del context
        message = getattr(update, "effective_message", None)
        if message is None:
            return

        payload = make_rows_response(
            [
                ("Core", f"{CORE_NAME} v{CORE_VERSION}"),
                ("Platform", self._platform_info.display_name),
                ("Prefix", self._platform_info.primary_command_prefix),
                (
                    "Try",
                    " ".join(
                        [
                            f"{self._platform_info.primary_command_prefix}ping",
                            f"{self._platform_info.primary_command_prefix}uptime",
                            f"{self._platform_info.primary_command_prefix}stats",
                        ]
                    ),
                ),
            ],
            capabilities=self._platform_info.capabilities,
            edit=False,
        )
        parse_mode = payload.parse_mode
        if parse_mode is not None:
            parse_mode = parse_mode.upper()
        await message.reply_text(payload.text, parse_mode=parse_mode)

    async def _handle_command(self, update: Any, context: Any) -> None:
        text = _normalize_command_text(
            getattr(getattr(update, "effective_message", None), "text", None) or "",
            primary_prefix=self._platform_info.primary_command_prefix,
        )
        if not text:
            return
        await self._dispatch_message(update, text)

    async def _handle_prefixed_message(self, update: Any, context: Any) -> None:
        del context
        text = getattr(getattr(update, "effective_message", None), "text", None) or ""
        if not text:
            return
        await self._dispatch_message(update, text)

    async def _dispatch_message(self, update: Any, text: str) -> None:
        message = getattr(update, "effective_message", None)
        user = getattr(update, "effective_user", None)
        chat = getattr(update, "effective_chat", None)
        if message is None or user is None:
            return

        received_at = time.perf_counter()

        reply_to_message = getattr(message, "reply_to_message", None)
        reply_to_user_id = None
        if reply_to_message is not None and getattr(reply_to_message, "from_user", None) is not None:
            reply_to_user_id = reply_to_message.from_user.id

        response_message: Any | None = None

        async def send_reply(payload: CommandResponse) -> None:
            nonlocal response_message
            parse_mode = payload.parse_mode
            if parse_mode is not None:
                parse_mode = parse_mode.upper()
            if (
                payload.edit
                and response_message is not None
                and self._platform_info.capabilities.can_edit_response_message
            ):
                response_message = await response_message.edit_text(
                    payload.text,
                    parse_mode=parse_mode,
                )
                return
            response_message = await message.reply_text(
                payload.text,
                parse_mode=parse_mode,
            )

        await self._core.handle_incoming_message(
            platform=self._platform_info.key,
            platform_info=self._platform_info,
            sender_id=user.id,
            chat_id=getattr(chat, "id", None),
            text=text,
            received_at=received_at,
            reply_to_user_id=reply_to_user_id,
            send_reply=send_reply,
        )


def _build_command_prefixes(
    primary_prefix: str,
    *aliases: str,
) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered_prefixes: list[str] = []
    for prefix in (primary_prefix, *aliases):
        normalized = prefix.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered_prefixes.append(normalized)
    if ordered_prefixes:
        return tuple(ordered_prefixes)
    return (DEFAULT_BOT_COMMAND_PREFIX,)


def _build_prefix_pattern(prefixes: tuple[str, ...]) -> str:
    escaped = [re.escape(prefix) for prefix in prefixes if prefix]
    return rf"^(?:{'|'.join(escaped)})"


def _normalize_command_text(text: str, *, primary_prefix: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("/"):
        return stripped

    command_token, _, arg_text = stripped.partition(" ")
    command_name = command_token[1:].split("@", 1)[0]
    if not command_name:
        return ""
    if arg_text:
        return f"{primary_prefix}{command_name} {arg_text}"
    return f"{primary_prefix}{command_name}"


__all__ = ["TelegramBot"]
