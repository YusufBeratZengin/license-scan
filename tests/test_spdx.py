"""Unit tests for SPDX normalizer, expression parser, and policy evaluation."""

import unittest

from license_scan.models import ComplianceStatus
from license_scan.spdx import (
    matches_any_pattern,
    matches_license_pattern,
    normalize_spdx_id,
    parse_spdx_expression,
    sniff_license_text,
)


class TestSpdxNormalizer(unittest.TestCase):
    """Test SPDX license ID normalization and pattern matching."""

    def test_normalize_aliases(self) -> None:
        self.assertEqual(normalize_spdx_id("mit"), "MIT")
        self.assertEqual(normalize_spdx_id("The MIT License"), "MIT")
        self.assertEqual(normalize_spdx_id("Apache 2.0"), "Apache-2.0")
        self.assertEqual(normalize_spdx_id("Apache License, Version 2.0"), "Apache-2.0")
        self.assertEqual(normalize_spdx_id("asl 2.0"), "Apache-2.0")
        self.assertEqual(normalize_spdx_id("BSD 3-Clause"), "BSD-3-Clause")
        self.assertEqual(normalize_spdx_id("Simplified BSD License"), "BSD-2-Clause")
        self.assertEqual(normalize_spdx_id("isc"), "ISC")
        self.assertEqual(normalize_spdx_id("0bsd"), "0BSD")
        self.assertEqual(normalize_spdx_id("gplv3"), "GPL-3.0-only")
        self.assertEqual(normalize_spdx_id("gpl-3.0+"), "GPL-3.0-or-later")
        self.assertEqual(normalize_spdx_id("lgpl-2.1"), "LGPL-2.1-only")
        self.assertEqual(normalize_spdx_id(""), "UNKNOWN")
        self.assertEqual(normalize_spdx_id("custom-unknown-lic"), "custom-unknown-lic")

    def test_wildcard_matching(self) -> None:
        self.assertTrue(matches_license_pattern("GPL-3.0-only", "GPL-*"))
        self.assertTrue(matches_license_pattern("GPL-2.0-or-later", "GPL-*"))
        self.assertFalse(matches_license_pattern("MIT", "GPL-*"))
        self.assertTrue(matches_any_pattern("MIT", ["Apache-2.0", "MIT", "BSD*"]))
        self.assertTrue(matches_any_pattern("BSD-3-Clause", ["BSD*"]))


class TestLicenseSniffer(unittest.TestCase):
    """Test sniffing license from license text files."""

    def test_sniff_mit(self) -> None:
        text = "Permission is hereby granted, free of charge, to any person obtaining a copy"
        self.assertEqual(sniff_license_text(text), "MIT")

    def test_sniff_apache(self) -> None:
        text = "Licensed under the Apache License, Version 2.0 (the 'License')"
        self.assertEqual(sniff_license_text(text), "Apache-2.0")

    def test_sniff_bsd_3_clause(self) -> None:
        text = (
            "Redistribution and use in source and binary forms\n"
            "Neither the name of the copyright holder nor the names"
        )
        self.assertEqual(sniff_license_text(text), "BSD-3-Clause")

    def test_sniff_bsd_2_clause(self) -> None:
        text = (
            "Redistribution and use in source and binary forms\n"
            "This software is provided 2-clause"
        )
        self.assertEqual(sniff_license_text(text), "BSD-2-Clause")

    def test_sniff_gpl(self) -> None:
        text = "GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007"
        self.assertEqual(sniff_license_text(text), "GPL-3.0-only")


class TestSpdxExpressionParser(unittest.TestCase):
    """Test SPDX expression parsing and AST structure."""

    def test_single_license(self) -> None:
        ast = parse_spdx_expression("MIT")
        self.assertEqual(ast.to_string(), "MIT")
        self.assertEqual(ast.all_licenses(), {"MIT"})

    def test_or_expression(self) -> None:
        ast = parse_spdx_expression("MIT OR Apache-2.0")
        self.assertEqual(ast.to_string(), "(MIT OR Apache-2.0)")
        self.assertEqual(ast.all_licenses(), {"MIT", "Apache-2.0"})

    def test_and_expression(self) -> None:
        ast = parse_spdx_expression("MIT AND BSD-3-Clause")
        self.assertEqual(ast.to_string(), "(MIT AND BSD-3-Clause)")

    def test_with_exception(self) -> None:
        ast = parse_spdx_expression("GPL-3.0-only WITH Classpath-exception-2.0")
        self.assertEqual(ast.to_string(), "GPL-3.0-only WITH Classpath-exception-2.0")

    def test_parentheses_precedence(self) -> None:
        ast = parse_spdx_expression("(MIT OR BSD-2-Clause) AND Apache-2.0")
        self.assertEqual(ast.to_string(), "((MIT OR BSD-2-Clause) AND Apache-2.0)")

    def test_slash_dual_syntax(self) -> None:
        ast = parse_spdx_expression("MIT / Apache-2.0")
        self.assertEqual(ast.to_string(), "(MIT OR Apache-2.0)")


class TestSpdxEvaluation(unittest.TestCase):
    """Test evaluation of parsed expressions against allow/deny lists."""

    def setUp(self) -> None:
        self.allow = ["MIT", "Apache-2.0", "BSD-3-Clause"]
        self.deny = ["GPL-*"]
        self.review = ["MPL-2.0"]

    def test_single_allowed(self) -> None:
        ast = parse_spdx_expression("MIT")
        res = ast.evaluate(self.allow, self.deny, self.review)
        self.assertEqual(res.status, ComplianceStatus.ALLOWED)

    def test_single_denied(self) -> None:
        ast = parse_spdx_expression("GPL-3.0-only")
        res = ast.evaluate(self.allow, self.deny, self.review)
        self.assertEqual(res.status, ComplianceStatus.DENIED)

    def test_single_review(self) -> None:
        ast = parse_spdx_expression("MPL-2.0")
        res = ast.evaluate(self.allow, self.deny, self.review)
        self.assertEqual(res.status, ComplianceStatus.REVIEW)

    def test_or_with_allowed_option(self) -> None:
        # Dual license: MIT or GPL-3.0. Since MIT is allowed, user can choose MIT
        ast = parse_spdx_expression("MIT OR GPL-3.0-only")
        res = ast.evaluate(self.allow, self.deny, self.review)
        self.assertEqual(res.status, ComplianceStatus.ALLOWED)
        self.assertEqual(res.effective_license, "MIT")

    def test_or_both_denied(self) -> None:
        ast = parse_spdx_expression("GPL-2.0-only OR GPL-3.0-only")
        res = ast.evaluate(self.allow, self.deny, self.review)
        self.assertEqual(res.status, ComplianceStatus.DENIED)

    def test_and_one_denied(self) -> None:
        # AND requires both to be accepted. If one is denied, the package is denied
        ast = parse_spdx_expression("MIT AND GPL-3.0-only")
        res = ast.evaluate(self.allow, self.deny, self.review)
        self.assertEqual(res.status, ComplianceStatus.DENIED)

    def test_and_both_allowed(self) -> None:
        ast = parse_spdx_expression("MIT AND Apache-2.0")
        res = ast.evaluate(self.allow, self.deny, self.review)
        self.assertEqual(res.status, ComplianceStatus.ALLOWED)


if __name__ == "__main__":
    unittest.main()
