"""Unit tests for Python scanner."""

import unittest
from pathlib import Path

from license_scan.scanners.base import ScanOptions
from license_scan.scanners.python import PythonScanner


class TestPythonScanner(unittest.TestCase):
    """Test Python installed distributions scanner using fake site-packages."""

    def setUp(self) -> None:
        self.fixtures_dir = (
            Path(__file__).parent / "fixtures" / "python" / "fake_site_packages"
        )
        self.scanner = PythonScanner()

    def test_can_scan(self) -> None:
        self.assertTrue(self.scanner.can_scan(self.fixtures_dir))

    def test_scan_fake_site_packages(self) -> None:
        deps = self.scanner.scan(
            self.fixtures_dir,
            ScanOptions(
                site_packages=str(self.fixtures_dir),
                collect_license_texts=True,
            ),
        )
        dep_names = {d.name.lower(): d for d in deps}

        # requests
        self.assertIn("requests", dep_names)
        req = dep_names["requests"]
        self.assertEqual(req.version, "2.31.0")
        self.assertEqual(req.normalized_license, "Apache-2.0")
        self.assertIsNotNone(req.license_text)
        self.assertIn("Kenneth Reitz", req.license_text or "")

        # urllib3
        self.assertIn("urllib3", dep_names)
        u3 = dep_names["urllib3"]
        self.assertEqual(u3.version, "2.0.7")
        self.assertEqual(u3.normalized_license, "MIT")
        self.assertIsNotNone(u3.license_text)

        # gpl-tool
        self.assertIn("gpl-tool", dep_names)
        gpl = dep_names["gpl-tool"]
        self.assertEqual(gpl.normalized_license, "GPL-3.0-only")

        # dual-pkg (PEP 639 License-Expression)
        self.assertIn("dual-pkg", dep_names)
        dp = dep_names["dual-pkg"]
        self.assertEqual(dp.raw_license, "MIT OR Apache-2.0")

        # sniff-only (missing License field, sniffed from LICENSE)
        self.assertIn("sniff-only", dep_names)
        so = dep_names["sniff-only"]
        self.assertEqual(so.normalized_license, "BSD-3-Clause")


if __name__ == "__main__":
    unittest.main()
