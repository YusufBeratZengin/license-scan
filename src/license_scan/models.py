"""Data models for license-scan."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ComplianceStatus(str, Enum):
    """Compliance decision status for a dependency."""

    ALLOWED = "ALLOWED"
    DENIED = "DENIED"
    REVIEW = "REVIEW"
    UNKNOWN = "UNKNOWN"

    def __str__(self) -> str:
        return self.value


class Ecosystem(str, Enum):
    """Supported package ecosystem."""

    NODE = "node"
    PYTHON = "python"

    def __str__(self) -> str:
        return self.value


@dataclass
class Dependency:
    """Represents an analyzed project dependency."""

    name: str
    version: str
    ecosystem: str
    raw_license: str = "UNKNOWN"
    normalized_license: str = "UNKNOWN"
    status: ComplianceStatus = ComplianceStatus.UNKNOWN
    reason: str = ""
    is_dev: bool = False
    license_files: list[str] = field(default_factory=list)
    license_text: Optional[str] = None
    location: Optional[str] = None
    homepage: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert dependency to serializable dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "ecosystem": self.ecosystem,
            "raw_license": self.raw_license,
            "normalized_license": self.normalized_license,
            "status": str(self.status),
            "reason": self.reason,
            "is_dev": self.is_dev,
            "license_files": self.license_files,
            "has_license_text": bool(self.license_text),
            "location": self.location,
            "homepage": self.homepage,
        }


@dataclass
class Summary:
    """Aggregated scan statistics."""

    total: int = 0
    allowed: int = 0
    denied: int = 0
    review: int = 0
    unknown: int = 0
    passed: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert summary to dictionary."""
        return {
            "total": self.total,
            "allowed": self.allowed,
            "denied": self.denied,
            "review": self.review,
            "unknown": self.unknown,
            "passed": self.passed,
        }


@dataclass
class ScanResult:
    """Full scan output containing dependencies and aggregate metrics."""

    dependencies: list[Dependency] = field(default_factory=list)
    summary: Summary = field(default_factory=Summary)
    policy_path: Optional[str] = None
    root_path: str = "."

    def compute_summary(self, strict: bool = False) -> None:
        """Compute summary counts from dependency list."""
        self.summary.total = len(self.dependencies)
        self.summary.allowed = sum(
            1 for d in self.dependencies if d.status == ComplianceStatus.ALLOWED
        )
        self.summary.denied = sum(
            1 for d in self.dependencies if d.status == ComplianceStatus.DENIED
        )
        self.summary.review = sum(
            1 for d in self.dependencies if d.status == ComplianceStatus.REVIEW
        )
        self.summary.unknown = sum(
            1 for d in self.dependencies if d.status == ComplianceStatus.UNKNOWN
        )

        if self.summary.denied > 0:
            self.summary.passed = False
        elif strict and (self.summary.review > 0 or self.summary.unknown > 0):
            self.summary.passed = False
        else:
            self.summary.passed = True

    def to_dict(self) -> dict[str, Any]:
        """Convert scan result to dictionary."""
        return {
            "root_path": self.root_path,
            "policy_path": self.policy_path,
            "summary": self.summary.to_dict(),
            "dependencies": [d.to_dict() for d in self.dependencies],
        }
