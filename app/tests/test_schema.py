"""desktop-mini-bot v0.2.1 — short-JSON schema parse / to_wire tests.

Covers aliases, fences, and unknown-action rejection.
Part of the lightweight no-vision Linux CUA (stdlib only).
MIT / jor-teron.
"""

import unittest

from desktop_mini_bot.schema import SchemaError, parse_action, to_wire


# --- schema ---

class SchemaTests(unittest.TestCase):
    """Validate parse_action expansion and to_wire compaction."""

    def test_short_click(self):
        """Short click wire expands and round-trips via to_wire."""
        a = parse_action('{"a":"click","ref":"b1"}')
        self.assertEqual(a["action"], "click")
        self.assertEqual(a["ref"], "b1")
        self.assertEqual(to_wire(a), {"a": "click", "ref": "b1"})

    def test_find_and_done(self):
        """find role/name and done summary parse correctly."""
        a = parse_action('{"a":"find","r":"button","n":"Save"}')
        self.assertEqual(a["role"], "button")
        d = parse_action('{"a":"done","s":"ok"}')
        self.assertEqual(d["summary"], "ok")

    def test_open_url(self):
        """open_url short key u maps to url and back."""
        a = parse_action('{"a":"open_url","u":"https://example.com"}')
        self.assertEqual(a["url"], "https://example.com")
        self.assertEqual(to_wire(a)["u"], "https://example.com")

    def test_fence_and_prose(self):
        """Markdown fenced JSON with surrounding prose still parses."""
        a = parse_action('Sure.\n```json\n{"a":"type","txt":"hi","ref":"t1"}\n```\n')
        self.assertEqual(a["action"], "type")
        self.assertEqual(a["text"], "hi")

    def test_unknown(self):
        """Unknown action names raise SchemaError."""
        with self.assertRaises(SchemaError):
            parse_action('{"a":"explode"}')


if __name__ == "__main__":
    unittest.main()
