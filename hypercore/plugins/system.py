"""System commands for HyperCore."""

from __future__ import annotations

from hypercore.core.commands import CommandAccess, CommandContext, CommandResponse
from hypercore.core.config import CORE_VERSION
from hypercore.core.errors import UsageError
from hypercore.core.formatter import (
    format_duration,
    format_latency_ms,
    make_ping_response,
    make_rows_response,
    make_status_response,
    make_uptime_response,
)
from hypercore.core.plugin_manifest import PluginManifest


PLUGIN_MANIFEST = PluginManifest(
    name="system",
    version=CORE_VERSION,
    description="Core runtime control and health commands.",
    commands=("ping", "uptime", "stats", "update", "restart", "shutdown"),
    platforms=("bot", "userbot"),
)


def setup(core: object) -> None:
    core.registry.register(
        "ping",
        ping_command,
        access=CommandAccess.SUDO,
        description="Check command response latency.",
        usage="ping",
        platforms=("bot", "userbot"),
    )
    core.registry.register(
        "uptime",
        uptime_command,
        access=CommandAccess.SUDO,
        description="Show current core uptime and command latency.",
        usage="uptime",
        platforms=("bot", "userbot"),
    )
    core.registry.register(
        "stats",
        stats_command,
        access=CommandAccess.SUDO,
        description="Show core runtime and storage status.",
        usage="stats",
        platforms=("bot", "userbot"),
    )
    core.registry.register(
        "update",
        update_command,
        access=CommandAccess.OWNER,
        description="Pull the latest core changes from git.",
        usage="update -core",
        platforms=("bot", "userbot"),
    )
    core.registry.register(
        "restart",
        restart_command,
        access=CommandAccess.OWNER,
        description="Restart the current HyperCore process.",
        usage="restart",
        platforms=("bot", "userbot"),
    )
    core.registry.register(
        "shutdown",
        shutdown_command,
        access=CommandAccess.OWNER,
        description="Stop the current HyperCore process.",
        usage="shutdown",
        platforms=("bot", "userbot"),
    )


async def ping_command(ctx: CommandContext) -> CommandResponse:
    return make_ping_response(
        format_latency_ms(ctx.received_at),
        capabilities=ctx.capabilities,
    )


async def uptime_command(ctx: CommandContext) -> CommandResponse:
    return make_uptime_response(
        format_duration(ctx.core.uptime),
        format_latency_ms(ctx.received_at),
        capabilities=ctx.capabilities,
    )


async def stats_command(ctx: CommandContext) -> CommandResponse:
    status = await ctx.core.status_service.collect(ctx.platform_info)
    return make_rows_response(
        [
            ("Core", f"{status.core_name} v{status.core_version}"),
            ("Platform", status.request_platform_name),
            ("Python Version", status.python_version),
            ("Platform Version", status.request_platform_version),
            ("Plugins", str(status.plugin_count)),
            ("Database", status.database_status),
        ],
        capabilities=ctx.capabilities,
    )


async def update_command(ctx: CommandContext) -> CommandResponse | None:
    if ctx.args != ["-core"]:
        raise UsageError(ctx.command_ref("update", "-core"))

    result = await ctx.core.perform_core_update()
    if not result.success:
        return make_status_response(
            "Update",
            result.message,
            capabilities=ctx.capabilities,
        )
    if not result.changed:
        return make_status_response(
            "Update",
            result.message,
            capabilities=ctx.capabilities,
        )

    await ctx.reply(
        make_rows_response(
            [
                ("Update", "Core update complete"),
                ("Restart", "Starting"),
            ],
            capabilities=ctx.capabilities,
        )
    )
    ctx.core.request_restart()
    return None


async def restart_command(ctx: CommandContext) -> None:
    await ctx.reply(
        make_status_response(
            "Restart",
            "Starting",
            capabilities=ctx.capabilities,
        )
    )
    ctx.core.request_restart()


async def shutdown_command(ctx: CommandContext) -> None:
    await ctx.reply(
        make_status_response(
            "Shutdown",
            "Stopping",
            capabilities=ctx.capabilities,
        )
    )
    ctx.core.request_shutdown()
