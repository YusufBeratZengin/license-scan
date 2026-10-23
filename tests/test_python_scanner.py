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

    def test_scan_dir_with_dist_info_no_explicit_option(self) -> None:
        deps = self.scanner.scan(self.fixtures_dir, ScanOptions())
        names = {d.name.lower() for d in deps}
        self.assertIn("requests", names)

    def test_find_virtualenv_site_packages(self) -> None:
        import tempfile

        from license_scan.scanners.python import _find_virtualenv_site_packages

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self.assertIsNone(_find_virtualenv_site_packages(root))

            # Test Windows layout
            win_site = root / ".venv" / "Lib" / "site-packages"
            win_site.mkdir(parents=True)
            self.assertEqual(_find_virtualenv_site_packages(root), win_site)

            # Test POSIX layout in a separate directory
            with tempfile.TemporaryDirectory() as tmpdir_posix:
                root_posix = Path(tmpdir_posix)
                posix_site = root_posix / "venv" / "lib" / "python3.11" / "site-packages"
                posix_site.mkdir(parents=True)
                self.assertEqual(_find_virtualenv_site_packages(root_posix), posix_site)

    def test_extract_license_from_classifiers(self) -> None:
        from license_scan.scanners.python import _extract_license_from_classifiers

        classifiers = [
            "Development Status :: 5 - Production/Stable",
            "Classifier: License :: OSI Approved :: MIT License",
        ]
        self.assertEqual(_extract_license_from_classifiers(classifiers), "MIT")

        classifiers_bsd = [
            "License :: OSI Approved :: BSD License",
        ]
        self.assertEqual(_extract_license_from_classifiers(classifiers_bsd), "BSD-3-Clause")

        classifiers_none = ["Topic :: Utilities"]
        self.assertIsNone(_extract_license_from_classifiers(classifiers_none))

    def test_can_scan_various_indicators(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            self.assertFalse(self.scanner.can_scan(p))

            (p / "setup.py").write_text("# setup", encoding="utf-8")
            self.assertTrue(self.scanner.can_scan(p))

            p2 = Path(tmpdir) / "sub"
            p2.mkdir()
            (p2 / "pyproject.toml").write_text("# toml", encoding="utf-8")
            self.assertTrue(self.scanner.can_scan(p2))

    def test_scan_auto_detect_venv(self) -> None:
        import shutil
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            venv_site = root / ".venv" / "Lib" / "site-packages"
            venv_site.mkdir(parents=True)
            # Copy one fixture into this venv
            sample_src = self.fixtures_dir / "requests-2.31.0.dist-info"
            shutil.copytree(sample_src, venv_site / "requests-2.31.0.dist-info")

            deps = self.scanner.scan(root, ScanOptions())
            names = [d.name.lower() for d in deps]
            self.assertIn("requests", names)


if __name__ == "__main__":
    unittest.main()
