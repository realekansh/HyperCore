import unittest
from datetime import timedelta

from hypercore.core.formatter import (
    format_duration,
    format_latency_ms,
    make_ping_response,
    make_rows_response,
)
from hypercore.core.platforms import PlatformCapabilities


HTML_CAPABILITIES = PlatformCapabilities(
    can_edit_source_message=True,
    can_edit_response_message=True,
    preferred_parse_mode="HTML",
)

PLAIN_CAPABILITIES = PlatformCapabilities(
    can_edit_source_message=False,
    can_edit_response_message=False,
    preferred_parse_mode=None,
)


class FormatterTests(unittest.TestCase):
    def test_make_ping_response_uses_html_when_supported(self) -> None:
        response = make_ping_response("104.249ms", capabilities=HTML_CAPABILITIES)

        self.assertEqual(response.text, "<b>Pong!</b>\n<code>104.249ms</code>")
        self.assertEqual(response.parse_mode, "HTML")
        self.assertTrue(response.edit)

    def test_make_rows_response_falls_back_to_plain_text(self) -> None:
        response = make_rows_response(
            [("Uptime", "1m 5s"), ("Ping", "8.100ms")],
            capabilities=PLAIN_CAPABILITIES,
            edit=False,
        )

        self.assertEqual(response.text, "Uptime: 1m 5s\nPing: 8.100ms")
        self.assertIsNone(response.parse_mode)
        self.assertFalse(response.edit)

    def test_format_duration_uses_compact_units(self) -> None:
        self.assertEqual(format_duration(timedelta(seconds=7)), "7s")
        self.assertEqual(format_duration(timedelta(seconds=65)), "1m 5s")
        self.assertEqual(format_duration(timedelta(seconds=3661)), "1h 1m 1s")
        self.assertEqual(format_duration(timedelta(days=1, seconds=3661)), "1d 1h 1m 1s")

    def test_format_latency_ms_has_minimum_floor(self) -> None:
        self.assertEqual(format_latency_ms(10.0, now=10.0), "0.001ms")
        self.assertEqual(format_latency_ms(10.0, now=10.104249), "104.249ms")
