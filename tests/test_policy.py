"""Unit tests for policy configuration and exception handling."""

import json
import tempfile
import unittest
from pathlib import Path

from license_scan.models import ComplianceStatus, Dependency
from license_scan.policy import Policy, PolicyException


class TestPolicy(unittest.TestCase):
    """Test policy loading, default rules, and exceptions."""

    def test_default_policy(self) -> None:
        policy = Policy.load(None)
        self.assertIn("MIT", policy.allow)
        self.assertIn("Apache-2.0", policy.allow)
        self.assertIn("GPL-3.0*", policy.deny)

    def test_load_from_json_file(self) -> None:
        policy_path = (
            Path(__file__).parent / "fixtures" / "policies" / "allow_permissive.json"
        )
        policy = Policy.load(policy_path)
        self.assertEqual(policy.allow, ["MIT", "Apache-2.0", "BSD-3-Clause", "0BSD"])
        self.assertEqual(policy.deny, ["GPL-*", "AGPL-*"])
        self.assertFalse(policy.allow_unknown)

    def test_evaluate_allowed_dependency(self) -> None:
        policy = Policy()
        dep = Dependency(
            name="express",
            version="4.18.2",
            ecosystem="node",
            raw_license="MIT",
            normalized_license="MIT",
        )
        policy.evaluate_dependency(dep)
        self.assertEqual(dep.status, ComplianceStatus.ALLOWED)

    def test_evaluate_denied_dependency(self) -> None:
        policy = Policy()
        dep = Dependency(
            name="gpl-tool",
            version="1.0.0",
            ecosystem="python",
            raw_license="GPL-3.0-only",
            normalized_license="GPL-3.0-only",
        )
        policy.evaluate_dependency(dep)
        self.assertEqual(dep.status, ComplianceStatus.DENIED)

    def test_exception_overrides_denied_license(self) -> None:
        policy = Policy(
            exceptions={
                "gpl-tool": PolicyException(
                    reason="Approved internal build tool",
                    license="GPL-3.0-only",
                )
            }
        )
        dep = Dependency(
            name="gpl-tool",
            version="1.0.0",
            ecosystem="python",
            raw_license="GPL-3.0-only",
            normalized_license="GPL-3.0-only",
        )
        policy.evaluate_dependency(dep)
        self.assertEqual(dep.status, ComplianceStatus.ALLOWED)
        self.assertIn("Approved internal build tool", dep.reason)

    def test_save_default_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "license-scan.json"
            Policy.save_default_file(target)
            self.assertTrue(target.is_file())
            data = json.loads(target.read_text(encoding="utf-8"))
            self.assertIn("allow", data)
            self.assertIn("deny", data)


if __name__ == "__main__":
    unittest.main()
