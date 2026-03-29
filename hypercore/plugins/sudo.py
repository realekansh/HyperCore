"""Sudo management commands for HyperCore."""

from __future__ import annotations

from hypercore.core.commands import CommandAccess, CommandContext
from hypercore.core.config import CORE_VERSION
from hypercore.core.errors import UsageError
from hypercore.core.plugin_manifest import PluginManifest


PLUGIN_MANIFEST = PluginManifest(
    name="sudo",
    version=CORE_VERSION,
    description="Owner-only sudo management commands.",
    commands=("addsudo", "rmsudo", "vsudos"),
    platforms=("bot", "userbot"),
)


def setup(core: object) -> None:
    core.registry.register(
        "addsudo",
        addsudo_command,
        access=CommandAccess.OWNER,
        description="Grant sudo access to a Telegram user ID.",
        usage="addsudo <user_id>",
        platforms=("bot", "userbot"),
    )
    core.registry.register(
        "rmsudo",
        rmsudo_command,
        access=CommandAccess.OWNER,
        description="Remove sudo access from a Telegram user ID.",
        usage="rmsudo <user_id>",
        platforms=("bot", "userbot"),
    )
    core.registry.register(
        "vsudos",
        vsudos_command,
        access=CommandAccess.OWNER,
        description="List all configured sudo user IDs.",
        usage="vsudos",
        platforms=("bot", "userbot"),
    )


async def addsudo_command(ctx: CommandContext) -> str:
    target_id = _resolve_target_id(ctx)
    if ctx.core.owner_id is not None and target_id == ctx.core.owner_id:
        return "Owner access is already built in."

    added = await ctx.core.store.add_sudo(target_id)
    if added:
        return f"Added sudo user: {target_id}"
    return f"User is already sudo: {target_id}"


async def rmsudo_command(ctx: CommandContext) -> str:
    target_id = _resolve_target_id(ctx)
    if ctx.core.owner_id is not None and target_id == ctx.core.owner_id:
        return "Owner access cannot be removed."

    removed = await ctx.core.store.remove_sudo(target_id)
    if removed:
        return f"Removed sudo user: {target_id}"
    return f"User is not sudo: {target_id}"


async def vsudos_command(ctx: CommandContext) -> str:
    sudo_ids = await ctx.core.store.list_sudos()
    if not sudo_ids:
        return "No sudo users configured."
    lines = ["Sudo users:"]
    lines.extend(str(user_id) for user_id in sudo_ids)
    return "\n".join(lines)


def _resolve_target_id(ctx: CommandContext) -> int:
    if ctx.args:
        try:
            return int(ctx.args[0])
        except ValueError as exc:
            raise UsageError(
                "Provide a numeric Telegram user ID or reply to a user message."
            ) from exc

    if ctx.reply_to_user_id is not None:
        return int(ctx.reply_to_user_id)

    raise UsageError("Provide a numeric Telegram user ID or reply to a user message.")
