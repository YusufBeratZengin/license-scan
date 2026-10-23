"""Unit tests for formatters (table, json, csv, markdown)."""

import json
import unittest

from license_scan.formatters import (
    format_csv,
    format_json,
    format_markdown,
    format_table,
)
from license_scan.models import ComplianceStatus, Dependency, ScanResult


class TestFormatters(unittest.TestCase):
    """Test output formatting functionality."""

    def setUp(self) -> None:
        self.deps = [
            Dependency(
                name="express",
                version="4.18.2",
                ecosystem="node",
                raw_license="MIT",
                normalized_license="MIT",
                status=ComplianceStatus.ALLOWED,
                reason="License 'MIT' is allowed by policy",
            ),
            Dependency(
                name="gpl-tool",
                version="1.0.0",
                ecosystem="python",
                raw_license="GPL-3.0-only",
                normalized_license="GPL-3.0-only",
                status=ComplianceStatus.DENIED,
                reason="License 'GPL-3.0-only' is explicitly denied by policy",
            ),
        ]
        self.result = ScanResult(dependencies=self.deps)
        self.result.compute_summary()

    def test_format_table(self) -> None:
        out = format_table(self.result)
        self.assertIn("express", out)
        self.assertIn("gpl-tool", out)
        self.assertIn("ALLOWED", out)
        self.assertIn("DENIED", out)
        self.assertIn("Result: FAILED", out)

    def test_format_json(self) -> None:
        out = format_json(self.result)
        data = json.loads(out)
        self.assertIn("summary", data)
        self.assertEqual(data["summary"]["total"], 2)
        self.assertEqual(data["summary"]["allowed"], 1)
        self.assertEqual(data["summary"]["denied"], 1)
        self.assertFalse(data["summary"]["passed"])
        self.assertEqual(len(data["dependencies"]), 2)

    def test_format_csv(self) -> None:
        out = format_csv(self.result)
        lines = out.strip().split("\n")
        self.assertEqual(lines[0], "ecosystem,package,version,license,status,reason")
        self.assertEqual(len(lines), 3)
        self.assertIn("express", lines[1])
        self.assertIn("gpl-tool", lines[2])

    def test_format_markdown(self) -> None:
        out = format_markdown(self.result)
        self.assertIn("# License Scan Compliance Report", out)
        self.assertIn("| `ALLOWED` | node | `express` | 4.18.2 | `MIT`", out)
        self.assertIn("**Result:** `FAILED`", out)

    def test_format_empty_results(self) -> None:
        empty_res = ScanResult(dependencies=[])
        empty_res.compute_summary()
        table_out = format_table(empty_res)
        self.assertIn("No dependencies found.", table_out)

        md_out = format_markdown(empty_res)
        self.assertIn("No dependencies detected.", md_out)

    def test_ecosystem_str(self) -> None:
        from license_scan.models import Ecosystem

        self.assertEqual(str(Ecosystem.NODE), "node")
        self.assertEqual(str(Ecosystem.PYTHON), "python")


if __name__ == "__main__":
    unittest.main()
