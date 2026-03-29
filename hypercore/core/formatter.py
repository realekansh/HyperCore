"""Reusable command formatting helpers for HyperCore."""

from __future__ import annotations

import time
from datetime import timedelta
from html import escape
from typing import Iterable

from hypercore.core.commands import CommandResponse
from hypercore.core.platforms import PlatformCapabilities

_HTML_PARSE_MODE = "HTML"


def make_ping_response(
    latency_text: str,
    *,
    capabilities: PlatformCapabilities | None = None,
) -> CommandResponse:
    if _supports_html(capabilities):
        return html_response(
            "\n".join(
                [
                    "<b>Pong!</b>",
                    code(latency_text),
                ]
            )
        )
    return CommandResponse(text=f"Pong!\n{latency_text}")


def make_uptime_response(
    uptime_text: str,
    latency_text: str,
    *,
    capabilities: PlatformCapabilities | None = None,
) -> CommandResponse:
    return make_rows_response(
        [
            ("Uptime", uptime_text),
            ("Ping", latency_text),
        ],
        capabilities=capabilities,
    )


def make_rows_response(
    rows: Iterable[tuple[str, str]],
    *,
    capabilities: PlatformCapabilities | None = None,
    edit: bool = True,
) -> CommandResponse:
    row_list = list(rows)
    if _supports_html(capabilities):
        return html_response(
            "\n".join(make_row(label, value) for label, value in row_list),
            edit=edit,
        )
    return CommandResponse(
        text="\n".join(make_plain_row(label, value) for label, value in row_list),
        edit=edit,
    )


def make_status_response(
    label: str,
    value: str,
    *,
    capabilities: PlatformCapabilities | None = None,
    edit: bool = True,
) -> CommandResponse:
    return make_rows_response(
        [(label, value)],
        capabilities=capabilities,
        edit=edit,
    )


def format_duration(delta: timedelta) -> str:
    total_seconds = max(int(delta.total_seconds()), 0)
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts: list[str] = []
    if days:
        parts.extend(
            [
                f"{days}d",
                f"{hours}h",
                f"{minutes}m",
                f"{seconds}s",
            ]
        )
    elif hours:
        parts.extend([f"{hours}h", f"{minutes}m", f"{seconds}s"])
    elif minutes:
        parts.extend([f"{minutes}m", f"{seconds}s"])
    else:
        parts.append(f"{seconds}s")
    return " ".join(parts)


def format_latency_ms(received_at: float, *, now: float | None = None) -> str:
    current_time = time.perf_counter() if now is None else now
    elapsed_ms = max((current_time - received_at) * 1000, 0.001)
    return f"{elapsed_ms:.3f}ms"


def html_response(text: str, *, edit: bool = True) -> CommandResponse:
    return CommandResponse(text=text, parse_mode=_HTML_PARSE_MODE, edit=edit)


def make_row(label: str, value: str) -> str:
    return f"{bold(label + ':')} {code(value)}"


def make_plain_row(label: str, value: str) -> str:
    return f"{label}: {value}"


def bold(text: str) -> str:
    return f"<b>{escape(text)}</b>"


def code(text: str) -> str:
    return f"<code>{escape(text)}</code>"


def _supports_html(capabilities: PlatformCapabilities | None) -> bool:
    if capabilities is None:
        return True
    return capabilities.supports_html


__all__ = [
    "bold",
    "code",
    "format_duration",
    "format_latency_ms",
    "html_response",
    "make_ping_response",
    "make_plain_row",
    "make_row",
    "make_rows_response",
    "make_status_response",
    "make_uptime_response",
]
