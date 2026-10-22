"""SPDX identifier normalization, expression parsing, and policy evaluation."""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from typing import Optional, Sequence

from license_scan.models import ComplianceStatus

# Common license string aliases mapped to canonical SPDX identifiers
SPDX_ALIASES: dict[str, str] = {
    # MIT
    "mit": "MIT",
    "mit license": "MIT",
    "the mit license": "MIT",
    "mit-license": "MIT",
    "license :: osi approved :: mit license": "MIT",
    # Apache
    "apache": "Apache-2.0",
    "apache 2": "Apache-2.0",
    "apache 2.0": "Apache-2.0",
    "apache-2": "Apache-2.0",
    "apache-2.0": "Apache-2.0",
    "apache license 2.0": "Apache-2.0",
    "apache license, version 2.0": "Apache-2.0",
    "apache software license": "Apache-2.0",
    "asl 2.0": "Apache-2.0",
    "license :: osi approved :: apache software license": "Apache-2.0",
    # BSD 3-Clause
    "bsd": "BSD-3-Clause",
    "bsd license": "BSD-3-Clause",
    "bsd-3-clause": "BSD-3-Clause",
    "bsd 3-clause": "BSD-3-Clause",
    "3-clause bsd": "BSD-3-Clause",
    "3-clause bsd license": "BSD-3-Clause",
    "new bsd license": "BSD-3-Clause",
    "modified bsd license": "BSD-3-Clause",
    "license :: osi approved :: bsd license": "BSD-3-Clause",
    # BSD 2-Clause
    "bsd-2-clause": "BSD-2-Clause",
    "bsd 2-clause": "BSD-2-Clause",
    "2-clause bsd": "BSD-2-Clause",
    "simplified bsd license": "BSD-2-Clause",
    "freebsd license": "BSD-2-Clause",
    # 0BSD
    "0bsd": "0BSD",
    "zero-clause bsd": "0BSD",
    "free public license 1.0.0": "0BSD",
    # ISC
    "isc": "ISC",
    "isc license": "ISC",
    "license :: osi approved :: isc license (iscl)": "ISC",
    # Python Software Foundation
    "psf": "PSF-2.0",
    "psf-2.0": "PSF-2.0",
    "psf license": "PSF-2.0",
    "python software foundation license": "PSF-2.0",
    "license :: osi approved :: python software foundation license": "PSF-2.0",
    # CC0 & Unlicense
    "cc0": "CC0-1.0",
    "cc0-1.0": "CC0-1.0",
    "creative commons zero": "CC0-1.0",
    "creative commons zero v1.0 universal": "CC0-1.0",
    "unlicense": "Unlicense",
    "the unlicense": "Unlicense",
    # Mozilla Public License
    "mpl-2.0": "MPL-2.0",
    "mpl 2.0": "MPL-2.0",
    "mozilla public license 2.0": "MPL-2.0",
    "license :: osi approved :: mozilla public license 2.0 (mpl 2.0)": "MPL-2.0",
    # Eclipse Public License
    "epl-2.0": "EPL-2.0",
    "eclipse public license 2.0": "EPL-2.0",
    # GNU GPL
    "gpl-1.0-only": "GPL-1.0-only",
    "gpl-1.0-or-later": "GPL-1.0-or-later",
    "gpl-2.0": "GPL-2.0-only",
    "gpl-2.0-only": "GPL-2.0-only",
    "gplv2": "GPL-2.0-only",
    "gpl 2.0": "GPL-2.0-only",
    "gnu gpl v2": "GPL-2.0-only",
    "license :: osi approved :: gnu general public license v2 (gplv2)": "GPL-2.0-only",
    "gpl-2.0+": "GPL-2.0-or-later",
    "gpl-2.0-or-later": "GPL-2.0-or-later",
    "gplv2+": "GPL-2.0-or-later",
    "gpl-3.0": "GPL-3.0-only",
    "gpl-3.0-only": "GPL-3.0-only",
    "gplv3": "GPL-3.0-only",
    "gpl 3.0": "GPL-3.0-only",
    "gnu gpl v3": "GPL-3.0-only",
    "license :: osi approved :: gnu general public license v3 (gplv3)": "GPL-3.0-only",
    "gpl-3.0+": "GPL-3.0-or-later",
    "gpl-3.0-or-later": "GPL-3.0-or-later",
    "gplv3+": "GPL-3.0-or-later",
    # GNU LGPL
    "lgpl-2.1": "LGPL-2.1-only",
    "lgpl-2.1-only": "LGPL-2.1-only",
    "lgplv2.1": "LGPL-2.1-only",
    "lgpl-2.1+": "LGPL-2.1-or-later",
    "lgpl-2.1-or-later": "LGPL-2.1-or-later",
    "lgplv2.1+": "LGPL-2.1-or-later",
    "lgpl-3.0": "LGPL-3.0-only",
    "lgpl-3.0-only": "LGPL-3.0-only",
    "lgplv3": "LGPL-3.0-only",
    "lgpl-3.0+": "LGPL-3.0-or-later",
    "lgpl-3.0-or-later": "LGPL-3.0-or-later",
    "lgplv3+": "LGPL-3.0-or-later",
    # GNU AGPL
    "agpl-3.0": "AGPL-3.0-only",
    "agpl-3.0-only": "AGPL-3.0-only",
    "agplv3": "AGPL-3.0-only",
    "agpl-3.0+": "AGPL-3.0-or-later",
    "agpl-3.0-or-later": "AGPL-3.0-or-later",
    "agplv3+": "AGPL-3.0-or-later",
    # Zlib / WTFPL
    "zlib": "Zlib",
    "zlib license": "Zlib",
    "wtfpl": "WTFPL",
    # Proprietary / Unlicensed
    "proprietary": "PROPRIETARY",
    "unlicensed": "UNLICENSED",
    "see license": "UNKNOWN",
    "custom": "UNKNOWN",
    "unknown": "UNKNOWN",
}


def normalize_spdx_id(identifier: str) -> str:
    """Normalize a license name or alias to canonical SPDX ID."""
    cleaned = identifier.strip()
    if not cleaned:
        return "UNKNOWN"

    lower = cleaned.lower()
    if lower in SPDX_ALIASES:
        return SPDX_ALIASES[lower]

    # Clean enclosing quotes or parentheses if simple single token
    if (
        (cleaned.startswith('"') and cleaned.endswith('"'))
        or (cleaned.startswith("'") and cleaned.endswith("'"))
        or (
            cleaned.startswith("(")
            and cleaned.endswith(")")
            and "(" not in cleaned[1:-1]
            and ")" not in cleaned[1:-1]
        )
    ):
        return normalize_spdx_id(cleaned[1:-1])

    # Return uppercase/cleaned form if looks like an SPDX identifier
    return cleaned


def matches_license_pattern(license_id: str, pattern: str) -> bool:
    """Match a license ID against exact name or wildcard pattern (e.g. GPL-*)."""
    norm_id = normalize_spdx_id(license_id).lower()
    norm_pattern = pattern.strip().lower()

    if norm_id == norm_pattern:
        return True

    return fnmatch.fnmatchcase(norm_id, norm_pattern)


def matches_any_pattern(license_id: str, patterns: Sequence[str]) -> bool:
    """Check if a license ID matches any pattern in a list."""
    return any(matches_license_pattern(license_id, pat) for pat in patterns)


def sniff_license_text(text: str) -> Optional[str]:
    """Sniff license identifier from the body text of a LICENSE or NOTICE file."""
    if not text:
        return None

    lower = text.lower()

    # Apache 2.0
    if "apache license" in lower and (
        "version 2.0" in lower or "v2.0" in lower or "licenses/license-2.0" in lower
    ):
        return "Apache-2.0"

    # Affero GPL
    if "gnu affero general public license" in lower:
        return "AGPL-3.0-only"

    # Lesser GPL
    if "gnu lesser general public license" in lower:
        if "version 3" in lower:
            return "LGPL-3.0-only"
        if "version 2.1" in lower:
            return "LGPL-2.1-only"
        return "LGPL-3.0-only"

    # Standard GPL
    if "gnu general public license" in lower:
        if "version 3" in lower:
            return "GPL-3.0-only"
        if "version 2" in lower:
            return "GPL-2.0-only"
        return "GPL-3.0-only"

    # MIT
    if "permission is hereby granted, free of charge" in lower:
        return "MIT"
    if "mit license" in lower:
        return "MIT"

    # 0BSD
    if "zero-clause bsd" in lower or "permission to use, copy, modify, and/or distribute this software for any purpose with or without fee is hereby granted" in lower:
        return "0BSD"

    # ISC
    if "permission to use, copy, modify, and/or distribute this software for any purpose" in lower:
        return "ISC"

    # BSD 3-Clause vs 2-Clause
    if "redistribution and use in source and binary forms" in lower:
        if "neither the name" in lower or "3-clause" in lower:
            return "BSD-3-Clause"
        if "2-clause" in lower or "simplified" in lower:
            return "BSD-2-Clause"
        return "BSD-3-Clause"

    # Mozilla Public License
    if "mozilla public license" in lower and "2.0" in lower:
        return "MPL-2.0"

    # Unlicense
    if "this is free and unencumbered software released into the public domain" in lower or "unlicense" in lower:
        return "Unlicense"

    # CC0
    if "creative commons zero" in lower or "cc0 1.0 universal" in lower:
        return "CC0-1.0"

    # Python PSF
    if "python software foundation" in lower and "license agreement" in lower:
        return "PSF-2.0"

    # Zlib
    if "this software is provided 'as-is'" in lower and "zlib license" in lower:
        return "Zlib"

    return None


# ---------------------------------------------------------------------------
# SPDX Expression AST and Parser
# ---------------------------------------------------------------------------

@dataclass
class EvaluationDecision:
    """Result of evaluating an SPDX expression or license against policy."""

    status: ComplianceStatus
    reason: str
    effective_license: str


class SpdxNode:
    """Base AST node for parsed SPDX expressions."""

    def evaluate(
        self,
        allow: Sequence[str],
        deny: Sequence[str],
        review: Sequence[str],
        allow_unknown: bool = False,
    ) -> EvaluationDecision:
        raise NotImplementedError

    def all_licenses(self) -> set[str]:
        raise NotImplementedError

    def to_string(self) -> str:
        raise NotImplementedError


class SpdxLicenseNode(SpdxNode):
    """Leaf node representing a single SPDX license ID, optionally WITH exception."""

    def __init__(self, license_id: str, exception: Optional[str] = None) -> None:
        self.license_id = normalize_spdx_id(license_id)
        self.exception = exception.strip() if exception else None

    def all_licenses(self) -> set[str]:
        return {self.license_id}

    def to_string(self) -> str:
        if self.exception:
            return f"{self.license_id} WITH {self.exception}"
        return self.license_id

    def evaluate(
        self,
        allow: Sequence[str],
        deny: Sequence[str],
        review: Sequence[str],
        allow_unknown: bool = False,
    ) -> EvaluationDecision:
        full_repr = self.to_string()
        lid = self.license_id

        # 1. Deny check
        if matches_any_pattern(lid, deny) or (self.exception and matches_any_pattern(full_repr, deny)):
            return EvaluationDecision(
                status=ComplianceStatus.DENIED,
                reason=f"License '{full_repr}' is explicitly denied by policy",
                effective_license=full_repr,
            )

        # 2. Review check
        if matches_any_pattern(lid, review) or (self.exception and matches_any_pattern(full_repr, review)):
            return EvaluationDecision(
                status=ComplianceStatus.REVIEW,
                reason=f"License '{full_repr}' requires review",
                effective_license=full_repr,
            )

        # 3. Allow check
        if matches_any_pattern(lid, allow) or (self.exception and matches_any_pattern(full_repr, allow)):
            return EvaluationDecision(
                status=ComplianceStatus.ALLOWED,
                reason=f"License '{full_repr}' is allowed by policy",
                effective_license=full_repr,
            )

        # 4. Unknown/unrecognized check
        if lid in ("UNKNOWN", "PROPRIETARY", "UNLICENSED"):
            if allow_unknown:
                return EvaluationDecision(
                    status=ComplianceStatus.ALLOWED,
                    reason=f"License '{full_repr}' allowed by allow_unknown policy",
                    effective_license=full_repr,
                )
            return EvaluationDecision(
                status=ComplianceStatus.UNKNOWN,
                reason=f"License '{full_repr}' is unknown/unrecognized",
                effective_license=full_repr,
            )

        # Not in allow, review, or deny
        return EvaluationDecision(
            status=ComplianceStatus.DENIED,
            reason=f"License '{full_repr}' is not present in allowed policy",
            effective_license=full_repr,
        )


class SpdxOrNode(SpdxNode):
    """OR node: Dual or multiple licensing. Allowed if at least one branch is compliant."""

    def __init__(self, left: SpdxNode, right: SpdxNode) -> None:
        self.left = left
        self.right = right

    def all_licenses(self) -> set[str]:
        return self.left.all_licenses() | self.right.all_licenses()

    def to_string(self) -> str:
        return f"({self.left.to_string()} OR {self.right.to_string()})"

    def evaluate(
        self,
        allow: Sequence[str],
        deny: Sequence[str],
        review: Sequence[str],
        allow_unknown: bool = False,
    ) -> EvaluationDecision:
        res_left = self.left.evaluate(allow, deny, review, allow_unknown)
        if res_left.status == ComplianceStatus.ALLOWED:
            return EvaluationDecision(
                status=ComplianceStatus.ALLOWED,
                reason=f"Dual license satisfied via {res_left.effective_license}",
                effective_license=res_left.effective_license,
            )

        res_right = self.right.evaluate(allow, deny, review, allow_unknown)
        if res_right.status == ComplianceStatus.ALLOWED:
            return EvaluationDecision(
                status=ComplianceStatus.ALLOWED,
                reason=f"Dual license satisfied via {res_right.effective_license}",
                effective_license=res_right.effective_license,
            )

        # If either is under review and neither allowed
        if res_left.status == ComplianceStatus.REVIEW:
            return res_left
        if res_right.status == ComplianceStatus.REVIEW:
            return res_right

        # Both denied or unknown
        return EvaluationDecision(
            status=ComplianceStatus.DENIED,
            reason=f"No compliant option in ({res_left.reason}; {res_right.reason})",
            effective_license=self.to_string(),
        )


class SpdxAndNode(SpdxNode):
    """AND node: Combined work requiring compliance with both branches."""

    def __init__(self, left: SpdxNode, right: SpdxNode) -> None:
        self.left = left
        self.right = right

    def all_licenses(self) -> set[str]:
        return self.left.all_licenses() | self.right.all_licenses()

    def to_string(self) -> str:
        return f"({self.left.to_string()} AND {self.right.to_string()})"

    def evaluate(
        self,
        allow: Sequence[str],
        deny: Sequence[str],
        review: Sequence[str],
        allow_unknown: bool = False,
    ) -> EvaluationDecision:
        res_left = self.left.evaluate(allow, deny, review, allow_unknown)
        res_right = self.right.evaluate(allow, deny, review, allow_unknown)

        if res_left.status == ComplianceStatus.DENIED:
            return EvaluationDecision(
                status=ComplianceStatus.DENIED,
                reason=f"Combination contains denied license: {res_left.reason}",
                effective_license=self.to_string(),
            )
        if res_right.status == ComplianceStatus.DENIED:
            return EvaluationDecision(
                status=ComplianceStatus.DENIED,
                reason=f"Combination contains denied license: {res_right.reason}",
                effective_license=self.to_string(),
            )

        if res_left.status == ComplianceStatus.REVIEW or res_right.status == ComplianceStatus.REVIEW:
            return EvaluationDecision(
                status=ComplianceStatus.REVIEW,
                reason=f"Combination requires review: {res_left.reason}; {res_right.reason}",
                effective_license=self.to_string(),
            )

        if res_left.status == ComplianceStatus.ALLOWED and res_right.status == ComplianceStatus.ALLOWED:
            return EvaluationDecision(
                status=ComplianceStatus.ALLOWED,
                reason="All licenses in combined expression are allowed",
                effective_license=self.to_string(),
            )

        return EvaluationDecision(
            status=ComplianceStatus.UNKNOWN,
            reason=f"Combination contains unknown status: {res_left.reason}; {res_right.reason}",
            effective_license=self.to_string(),
        )


class SpdxTokenizer:
    """Tokenize an SPDX license expression string into discrete tokens."""

    TOKEN_RE = re.compile(
        r"""
        (?P<LPAREN>\()|
        (?P<RPAREN>\))|
        (?P<AND>\bAND\b)|
        (?P<OR>\bOR\b)|
        (?P<WITH>\bWITH\b)|
        (?P<SLASH>/)|
        (?P<COMMA>,)|
        (?P<IDENT>[^\s\(\),/]+)
        """,
        re.VERBOSE | re.IGNORECASE,
    )

    def __init__(self, text: str) -> None:
        self.text = text.strip()
        self.tokens: list[tuple[str, str]] = []
        self._tokenize()
        self.pos = 0

    def _tokenize(self) -> None:
        for match in self.TOKEN_RE.finditer(self.text):
            kind = match.lastgroup
            val = match.group(kind)  # type: ignore[arg-type]
            if kind in ("SLASH", "COMMA"):
                # Treat slash or comma between licenses as OR
                self.tokens.append(("OR", "OR"))
            elif kind in ("AND", "OR", "WITH"):
                self.tokens.append((kind, val.upper()))
            elif kind in ("LPAREN", "RPAREN"):
                self.tokens.append((kind, val))
            elif kind == "IDENT":
                self.tokens.append(("IDENT", val))

    def peek(self) -> Optional[tuple[str, str]]:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def consume(self) -> tuple[str, str]:
        tok = self.peek()
        if tok is None:
            raise ValueError("Unexpected end of expression")
        self.pos += 1
        return tok


class SpdxParser:
    """Recursive-descent parser for SPDX license expressions."""

    def __init__(self, tokenizer: SpdxTokenizer) -> None:
        self.tokenizer = tokenizer

    def parse(self) -> SpdxNode:
        if not self.tokenizer.tokens:
            return SpdxLicenseNode("UNKNOWN")
        node = self._parse_or()
        return node

    def _parse_or(self) -> SpdxNode:
        node = self._parse_and()
        while True:
            tok = self.tokenizer.peek()
            if tok and tok[0] == "OR":
                self.tokenizer.consume()
                right = self._parse_and()
                node = SpdxOrNode(node, right)
            else:
                break
        return node

    def _parse_and(self) -> SpdxNode:
        node = self._parse_with()
        while True:
            tok = self.tokenizer.peek()
            if tok and tok[0] == "AND":
                self.tokenizer.consume()
                right = self._parse_with()
                node = SpdxAndNode(node, right)
            else:
                break
        return node

    def _parse_with(self) -> SpdxNode:
        node = self._parse_primary()
        tok = self.tokenizer.peek()
        if tok and tok[0] == "WITH":
            self.tokenizer.consume()
            exc_tok = self.tokenizer.peek()
            if exc_tok and exc_tok[0] == "IDENT":
                exc_val = self.tokenizer.consume()[1]
                if isinstance(node, SpdxLicenseNode):
                    node.exception = exc_val
        return node

    def _parse_primary(self) -> SpdxNode:
        tok = self.tokenizer.peek()
        if tok is None:
            return SpdxLicenseNode("UNKNOWN")

        if tok[0] == "LPAREN":
            self.tokenizer.consume()
            expr = self._parse_or()
            next_tok = self.tokenizer.peek()
            if next_tok and next_tok[0] == "RPAREN":
                self.tokenizer.consume()
            return expr

        if tok[0] == "IDENT":
            ident_parts = [self.tokenizer.consume()[1]]
            # Accumulate consecutive ident parts if multi-word license name
            while True:
                peeked = self.tokenizer.peek()
                if peeked and peeked[0] == "IDENT":
                    ident_parts.append(self.tokenizer.consume()[1])
                else:
                    break
            raw_id = " ".join(ident_parts)
            return SpdxLicenseNode(raw_id)

        # Fallback
        self.tokenizer.consume()
        return SpdxLicenseNode("UNKNOWN")


def parse_spdx_expression(expr_str: str) -> SpdxNode:
    """Parse an SPDX expression string into an AST."""
    if not expr_str or not expr_str.strip():
        return SpdxLicenseNode("UNKNOWN")

    try:
        tokenizer = SpdxTokenizer(expr_str)
        parser = SpdxParser(tokenizer)
        return parser.parse()
    except Exception:
        # Fallback to normalized single license if syntax fails
        return SpdxLicenseNode(expr_str)
