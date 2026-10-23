"""Unit tests for the command-line interface."""

import json
import tempfile
import unittest
from pathlib import Path

from license_scan.cli import main


class TestCLI(unittest.TestCase):
    """Test CLI commands, flags, and exit codes."""

    def setUp(self) -> None:
        self.fixtures_dir = Path(__file__).parent / "fixtures"
        self.node_v2_lock = self.fixtures_dir / "node" / "v2" / "package-lock.json"
        self.node_v3_lock = self.fixtures_dir / "node" / "v3" / "package-lock.json"
        self.py_site = self.fixtures_dir / "python" / "fake_site_packages"
        self.policy_allow = self.fixtures_dir / "policies" / "allow_permissive.json"
        self.policy_exceptions = self.fixtures_dir / "policies" / "with_exceptions.json"

    def test_version_flag(self) -> None:
        with self.assertRaises(SystemExit) as cm:
            main(["--version"])
        self.assertEqual(cm.exception.code, 0)

    def test_init_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "test-policy.json"
            code = main(["--init-policy", "-p", str(out_file), "-q"])
            self.assertEqual(code, 0)
            self.assertTrue(out_file.is_file())
            content = json.loads(out_file.read_text(encoding="utf-8"))
            self.assertIn("allow", content)
            self.assertIn("deny", content)

    def test_node_scan_fails_on_denied_gpl(self) -> None:
        code = main([
            str(self.node_v2_lock),
            "-p",
            str(self.policy_allow),
            "-e",
            "node",
            "-q",
        ])
        self.assertEqual(code, 1)

    def test_node_scan_passes_with_exceptions(self) -> None:
        code = main([
            str(self.node_v2_lock),
            "-p",
            str(self.policy_exceptions),
            "-e",
            "node",
            "-q",
        ])
        self.assertEqual(code, 0)

    def test_python_scan_fails_on_denied_gpl(self) -> None:
        code = main([
            "--site-packages",
            str(self.py_site),
            "-p",
            str(self.policy_allow),
            "-e",
            "python",
            "-q",
        ])
        self.assertEqual(code, 1)

    def test_python_scan_passes_with_exceptions(self) -> None:
        code = main([
            "--site-packages",
            str(self.py_site),
            "-p",
            str(self.policy_exceptions),
            "-e",
            "python",
            "-q",
        ])
        self.assertEqual(code, 0)

    def test_output_file_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "report.json"
            code = main([
                str(self.node_v3_lock),
                "-p",
                str(self.policy_allow),
                "-e",
                "node",
                "-f",
                "json",
                "-o",
                str(out_path),
                "-q",
            ])
            self.assertEqual(code, 0)
            self.assertTrue(out_path.is_file())
            data = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertTrue(data["summary"]["passed"])

    def test_output_file_csv_and_markdown_and_notice(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "report.csv"
            code = main([
                str(self.node_v3_lock),
                "-p",
                str(self.policy_allow),
                "-e",
                "node",
                "-f",
                "csv",
                "-o",
                str(csv_path),
                "-q",
            ])
            self.assertEqual(code, 0)
            self.assertTrue(csv_path.is_file())

            md_path = Path(tmpdir) / "report.md"
            code = main([
                str(self.node_v3_lock),
                "-p",
                str(self.policy_allow),
                "-e",
                "node",
                "-f",
                "markdown",
                "-o",
                str(md_path),
                "-q",
            ])
            self.assertEqual(code, 0)
            self.assertTrue(md_path.is_file())

            notice_path = Path(tmpdir) / "NOTICE"
            code = main([
                str(self.node_v3_lock),
                "-p",
                str(self.policy_allow),
                "-e",
                "node",
                "--notice",
                "-o",
                str(notice_path),
                "-q",
            ])
            self.assertEqual(code, 0)
            self.assertTrue(notice_path.is_file())

    def test_strict_mode_fails_on_review(self) -> None:
        # In node v3 lockfile, mpl-pkg has MPL-2.0 which is in review list
        code_normal = main([
            str(self.node_v3_lock),
            "-p",
            str(self.policy_allow),
            "-e",
            "node",
            "-q",
        ])
        self.assertEqual(code_normal, 0)

        code_strict = main([
            str(self.node_v3_lock),
            "-p",
            str(self.policy_allow),
            "-e",
            "node",
            "--strict",
            "-q",
        ])
        self.assertEqual(code_strict, 1)

    def test_invalid_target_path(self) -> None:
        code = main(["/path/that/does/not/exist/123456", "-q"])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
