"""Unit tests for Node scanner."""

import unittest
from pathlib import Path

from license_scan.scanners.base import ScanOptions
from license_scan.scanners.node import NodeScanner


class TestNodeScanner(unittest.TestCase):
    """Test Node.js package-lock and node_modules scanning."""

    def setUp(self) -> None:
        self.fixtures_dir = Path(__file__).parent / "fixtures" / "node"
        self.scanner = NodeScanner()

    def test_can_scan(self) -> None:
        self.assertTrue(self.scanner.can_scan(self.fixtures_dir / "v2"))
        self.assertTrue(self.scanner.can_scan(self.fixtures_dir / "v3"))
        self.assertTrue(
            self.scanner.can_scan(self.fixtures_dir / "v2" / "package-lock.json")
        )
        self.assertFalse(self.scanner.can_scan(Path("/nonexistent/random/path")))

    def test_scan_lockfile_v2_with_dev(self) -> None:
        lockfile = self.fixtures_dir / "v2" / "package-lock.json"
        deps = self.scanner.scan(lockfile, ScanOptions(include_dev=True))
        dep_names = {d.name: d for d in deps}

        self.assertIn("express", dep_names)
        self.assertEqual(dep_names["express"].normalized_license, "MIT")
        self.assertFalse(dep_names["express"].is_dev)

        self.assertIn("debug", dep_names)
        self.assertEqual(dep_names["debug"].normalized_license, "MIT")
        self.assertTrue(dep_names["debug"].is_dev)

        self.assertIn("gpl-lib", dep_names)
        self.assertEqual(dep_names["gpl-lib"].normalized_license, "GPL-3.0-only")

    def test_scan_lockfile_v2_prod_only(self) -> None:
        lockfile = self.fixtures_dir / "v2" / "package-lock.json"
        deps = self.scanner.scan(lockfile, ScanOptions(include_dev=False))
        dep_names = {d.name: d for d in deps}

        self.assertIn("express", dep_names)
        self.assertIn("gpl-lib", dep_names)
        self.assertNotIn("debug", dep_names)

    def test_scan_lockfile_v3(self) -> None:
        lockfile = self.fixtures_dir / "v3" / "package-lock.json"
        deps = self.scanner.scan(lockfile, ScanOptions())
        dep_names = {d.name: d for d in deps}

        self.assertIn("@scope/pkg", dep_names)
        self.assertEqual(dep_names["@scope/pkg"].normalized_license, "Apache-2.0")

        self.assertIn("dual-pkg", dep_names)
        self.assertEqual(
            dep_names["dual-pkg"].raw_license, "(MIT OR GPL-2.0-only)"
        )

        self.assertIn("mpl-pkg", dep_names)
        self.assertEqual(dep_names["mpl-pkg"].normalized_license, "MPL-2.0")

    def test_scan_node_modules_directory(self) -> None:
        nm_dir = self.fixtures_dir / "node_modules_sample"
        deps = self.scanner.scan(nm_dir, ScanOptions(collect_license_texts=True))
        dep_names = {d.name: d for d in deps}

        # pkg_mit has LICENSE file and license field
        self.assertIn("pkg_mit", dep_names)
        self.assertEqual(dep_names["pkg_mit"].normalized_license, "MIT")
        self.assertIsNotNone(dep_names["pkg_mit"].license_text)

        # pkg_legacy has licenses array
        self.assertIn("pkg_legacy", dep_names)
        self.assertIn("Apache-2.0", dep_names["pkg_legacy"].normalized_license)

        # pkg_sniff has no license field, but LICENSE.txt sniffs to Apache-2.0
        self.assertIn("pkg_sniff", dep_names)
        self.assertEqual(dep_names["pkg_sniff"].normalized_license, "Apache-2.0")

        # @scoped/sample scoped package
        self.assertIn("@scoped/sample", dep_names)
        self.assertEqual(dep_names["@scoped/sample"].normalized_license, "0BSD")


if __name__ == "__main__":
    unittest.main()
