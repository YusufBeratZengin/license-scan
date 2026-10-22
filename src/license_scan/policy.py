"""Policy configuration and compliance evaluation for dependencies."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from license_scan.models import ComplianceStatus, Dependency
from license_scan.spdx import matches_license_pattern, parse_spdx_expression

DEFAULT_ALLOW: list[str] = [
    "MIT",
    "Apache-2.0",
    "BSD-3-Clause",
    "BSD-2-Clause",
    "ISC",
    "0BSD",
    "CC0-1.0",
    "Unlicense",
    "PSF-2.0",
    "Zlib",
]

DEFAULT_DENY: list[str] = [
    "GPL-1.0*",
    "GPL-2.0*",
    "GPL-3.0*",
    "AGPL-1.0*",
    "AGPL-3.0*",
    "SSPL-1.0*",
    "CPAL-1.0*",
    "OSL-3.0*",
]

DEFAULT_REVIEW: list[str] = [
    "MPL-2.0",
    "LGPL-2.1*",
    "LGPL-3.0*",
    "EPL-1.0",
    "EPL-2.0",
    "EUPL-1.2",
]


@dataclass
class PolicyException:
    """Exception rule for a specific dependency."""

    reason: str
    license: Optional[str] = None


@dataclass
class Policy:
    """License compliance policy."""

    allow: list[str] = field(default_factory=lambda: list(DEFAULT_ALLOW))
    deny: list[str] = field(default_factory=lambda: list(DEFAULT_DENY))
    review: list[str] = field(default_factory=lambda: list(DEFAULT_REVIEW))
    allow_unknown: bool = False
    exceptions: dict[str, PolicyException] = field(default_factory=dict)
    loaded_from: Optional[str] = None

    @classmethod
    def load(cls, path: Optional[str | Path] = None) -> Policy:
        """Load policy from file, search default names, or return default."""
        target_path: Optional[Path] = None

        if path:
            candidate = Path(path)
            if candidate.is_file():
                target_path = candidate
            else:
                raise FileNotFoundError(f"Policy file not found: {path}")
        else:
            # Search common names
            for name in ["license-scan.json", ".license-scan.json"]:
                p = Path(name)
                if p.is_file():
                    target_path = p
                    break

        if target_path is None:
            return cls(loaded_from=None)

        with target_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        allow = data.get("allow", DEFAULT_ALLOW)
        deny = data.get("deny", DEFAULT_DENY)
        review = data.get("review", DEFAULT_REVIEW)
        allow_unknown = bool(data.get("allow_unknown", False))

        raw_exceptions = data.get("exceptions", {})
        exceptions: dict[str, PolicyException] = {}
        for name, entry in raw_exceptions.items():
            key = name.strip().lower()
            if isinstance(entry, dict):
                exceptions[key] = PolicyException(
                    reason=entry.get("reason", "Approved exception"),
                    license=entry.get("license"),
                )
            elif isinstance(entry, str):
                exceptions[key] = PolicyException(reason=entry)

        return cls(
            allow=allow,
            deny=deny,
            review=review,
            allow_unknown=allow_unknown,
            exceptions=exceptions,
            loaded_from=str(target_path),
        )

    def evaluate_dependency(self, dep: Dependency) -> None:
        """Evaluate a single dependency and mutate its status and reason."""
        pkg_key = dep.name.strip().lower()

        # Check per-package exceptions first
        if pkg_key in self.exceptions:
            exc = self.exceptions[pkg_key]
            if exc.license is None or matches_license_pattern(
                dep.normalized_license, exc.license
            ):
                dep.status = ComplianceStatus.ALLOWED
                dep.reason = f"Exception granted: {exc.reason}"
                return

        # Parse SPDX expression and evaluate
        raw = dep.raw_license or dep.normalized_license or "UNKNOWN"
        ast = parse_spdx_expression(raw)
        decision = ast.evaluate(
            allow=self.allow,
            deny=self.deny,
            review=self.review,
            allow_unknown=self.allow_unknown,
        )

        dep.status = decision.status
        dep.reason = decision.reason
        if decision.effective_license:
            dep.normalized_license = decision.effective_license

    def evaluate_all(self, dependencies: list[Dependency]) -> None:
        """Evaluate compliance for an entire list of dependencies."""
        for dep in dependencies:
            self.evaluate_dependency(dep)

    @classmethod
    def create_default_dict(cls) -> dict[str, Any]:
        """Generate default configuration dictionary."""
        return {
            "$schema": "https://raw.githubusercontent.com/YusufBeratZengin/license-scan/main/schema.json",
            "allow": list(DEFAULT_ALLOW),
            "deny": list(DEFAULT_DENY),
            "review": list(DEFAULT_REVIEW),
            "allow_unknown": False,
            "exceptions": {
                "example-pkg": {
                    "license": "GPL-3.0-only",
                    "reason": "Internal dev/build CLI tool only",
                }
            },
        }

    @classmethod
    def save_default_file(cls, path: str | Path = "license-scan.json") -> Path:
        """Write a fresh starter policy file."""
        target = Path(path)
        content = json.dumps(cls.create_default_dict(), indent=2) + "\n"
        target.write_text(content, encoding="utf-8")
        return target
