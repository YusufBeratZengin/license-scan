"""Unit tests for NOTICE / THIRD_PARTY attribution file generator."""

import unittest

from license_scan.models import ComplianceStatus, Dependency, ScanResult
from license_scan.notice import generate_notice


class TestNoticeGenerator(unittest.TestCase):
    """Test generating attribution notice files."""

    def test_generate_notice_with_license_text(self) -> None:
        deps = [
            Dependency(
                name="requests",
                version="2.31.0",
                ecosystem="python",
                raw_license="Apache-2.0",
                normalized_license="Apache-2.0",
                status=ComplianceStatus.ALLOWED,
                license_text="Copyright 2019 Kenneth Reitz\nLicensed under the Apache License, Version 2.0",
                homepage="https://requests.readthedocs.io",
            ),
            Dependency(
                name="urllib3",
                version="2.0.7",
                ecosystem="python",
                raw_license="MIT",
                normalized_license="MIT",
                status=ComplianceStatus.ALLOWED,
            ),
        ]
        result = ScanResult(dependencies=deps)
        notice_out = generate_notice(result, project_name="TestApp")

        self.assertIn("THIRD-PARTY SOFTWARE LICENSES AND ATTRIBUTIONS", notice_out)
        self.assertIn("TestApp incorporates third-party open-source components.", notice_out)
        self.assertIn("Component: requests", notice_out)
        self.assertIn("Version:   2.31.0", notice_out)
        self.assertIn("Homepage:  https://requests.readthedocs.io", notice_out)
        self.assertIn("Copyright 2019 Kenneth Reitz", notice_out)
        self.assertIn("Component: urllib3", notice_out)
        self.assertIn("License declared as MIT", notice_out)


if __name__ == "__main__":
    unittest.main()
