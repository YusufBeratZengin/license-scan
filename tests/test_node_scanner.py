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

    def test_extract_license_helpers(self) -> None:
        from license_scan.scanners.node import _extract_license_from_pkg_json

        self.assertEqual(_extract_license_from_pkg_json({"license": {"type": "MIT"}}), "MIT")
        self.assertIn("MIT", _extract_license_from_pkg_json({"licenses": [{"type": "MIT"}, {"type": "BSD-3-Clause"}]}))
        self.assertIn("ISC", _extract_license_from_pkg_json({"licenses": ["MIT", "ISC"]}))
        self.assertEqual(_extract_license_from_pkg_json({}), "UNKNOWN")

    def test_scan_lockfile_v1(self) -> None:
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "package-lock.json"
            lock_path.write_text(
                json.dumps({
                    "name": "sample-v1",
                    "lockfileVersion": 1,
                    "dependencies": {
                        "lib-prod": {"version": "1.0.0", "dev": False},
                        "lib-dev": {
                            "version": "2.0.0",
                            "dev": True,
                            "dependencies": {
                                "lib-nested": {"version": "3.0.0", "dev": True}
                            }
                        }
                    }
                }),
                encoding="utf-8",
            )
            # Prod only
            deps_prod = self.scanner.scan(lock_path, ScanOptions(include_dev=False))
            self.assertEqual(len(deps_prod), 1)
            self.assertEqual(deps_prod[0].name, "lib-prod")

            # Dev included
            deps_all = self.scanner.scan(lock_path, ScanOptions(include_dev=True))
            names = [d.name for d in deps_all]
            self.assertIn("lib-prod", names)
            self.assertIn("lib-dev", names)
            self.assertIn("lib-nested", names)

    def test_corrupted_lockfile(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            corrupt = Path(tmpdir) / "package-lock.json"
            corrupt.write_text("{broken json", encoding="utf-8")
            deps = self.scanner.scan(corrupt, ScanOptions())
            self.assertEqual(deps, [])

    def test_scan_lockfile_with_on_disk_package(self) -> None:
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            lock_path = root / "package-lock.json"
            lock_path.write_text(
                json.dumps({
                    "name": "project",
                    "lockfileVersion": 2,
                    "packages": {
                        "": {"name": "project"},
                        "node_modules/on-disk-pkg": {
                            "version": "1.2.0"
                        }
                    }
                }),
                encoding="utf-8",
            )
            pkg_dir = root / "node_modules" / "on-disk-pkg"
            pkg_dir.mkdir(parents=True)
            (pkg_dir / "package.json").write_text(
                json.dumps({
                    "name": "on-disk-pkg",
                    "version": "1.2.0",
                    "license": "BSD-3-Clause",
                    "homepage": "https://example.com/on-disk"
                }),
                encoding="utf-8",
            )
            (pkg_dir / "LICENSE").write_text("Redistribution and use in source and binary forms... 3-clause", encoding="utf-8")

            deps = self.scanner.scan(lock_path, ScanOptions(collect_license_texts=True))
            self.assertEqual(len(deps), 1)
            self.assertEqual(deps[0].name, "on-disk-pkg")
            self.assertEqual(deps[0].normalized_license, "BSD-3-Clause")
            self.assertEqual(deps[0].homepage, "https://example.com/on-disk")
            self.assertIsNotNone(deps[0].license_text)


if __name__ == "__main__":
    unittest.main()
