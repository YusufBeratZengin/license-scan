"""Base scanner abstract class and scan options."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from license_scan.models import Dependency


@dataclass
class ScanOptions:
    """Options controlling scanner behavior."""

    include_dev: bool = True
    site_packages: Optional[str] = None
    collect_license_texts: bool = True


class BaseScanner(ABC):
    """Abstract base class for ecosystem dependency scanners."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the ecosystem."""
        raise NotImplementedError

    @abstractmethod
    def can_scan(self, path: Path) -> bool:
        """Check if this scanner can process the given target directory or file."""
        raise NotImplementedError

    @abstractmethod
    def scan(self, path: Path, options: ScanOptions) -> list[Dependency]:
        """Scan dependencies and return list of Dependency objects."""
        raise NotImplementedError
