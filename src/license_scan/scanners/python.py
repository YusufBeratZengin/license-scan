"""Scanner for Python distributions via importlib.metadata."""

from __future__ import annotations

import glob
import importlib.metadata as im
from pathlib import Path
from typing import Optional

from license_scan.models import ComplianceStatus, Dependency
from license_scan.scanners.base import BaseScanner, ScanOptions
from license_scan.spdx import normalize_spdx_id, sniff_license_text

LICENSE_CANDIDATE_NAMES = (
    "LICENSE",
    "LICENSE.txt",
    "LICENSE.rst",
    "LICENSE.md",
    "LICENCE",
    "LICENCE.txt",
    "LICENCE.rst",
    "LICENCE.md",
    "COPYING",
    "COPYING.txt",
    "NOTICE",
    "NOTICE.txt",
)


def _find_virtualenv_site_packages(root: Path) -> Optional[Path]:
    """Auto-detect virtual environment site-packages folder under root."""
    # Check common virtualenv folders: .venv, venv, env
    for venv_name in [".venv", "venv", "env"]:
        candidate_base = root / venv_name
        if not candidate_base.is_dir():
            continue

        # Windows layout: .venv/Lib/site-packages
        win_site = candidate_base / "Lib" / "site-packages"
        if win_site.is_dir():
            return win_site

        # POSIX layout: .venv/lib/pythonX.Y/site-packages
        posix_glob = list(candidate_base.glob("lib/python*/site-packages"))
        if posix_glob and posix_glob[0].is_dir():
            return posix_glob[0]

    return None


def _extract_license_from_classifiers(classifiers: list[str]) -> Optional[str]:
    """Extract license name from PEP 301 classifier strings."""
    for c in classifiers:
        lower = c.strip().lower()
        if lower.startswith("classifier: license ::") or lower.startswith("license ::"):
            # Strip prefix
            parts = c.split("::")
            if len(parts) >= 3:
                # e.g. "License :: OSI Approved :: MIT License"
                tail = parts[-1].strip()
                normalized = normalize_spdx_id(tail)
                if normalized != "UNKNOWN":
                    return normalized
            # Try normalizing full classifier
            norm_full = normalize_spdx_id(c)
            if norm_full != "UNKNOWN":
                return norm_full
    return None


def _extract_license_file_content(
    dist: im.Distribution,
) -> tuple[list[str], Optional[str], Optional[str]]:
    """Inspect distribution files for license files and text."""
    found_files: list[str] = []
    text_content: Optional[str] = None
    sniffed: Optional[str] = None

    # Check via dist.read_text
    for name in LICENSE_CANDIDATE_NAMES:
        try:
            content = dist.read_text(name)
            if content and content.strip():
                found_files.append(name)
                if text_content is None:
                    text_content = content
                    sniffed = sniff_license_text(content)
        except Exception:
            pass

    # Check files attribute if available
    try:
        files = dist.files
        if files:
            for p in files:
                fname = Path(str(p)).name
                if fname.upper() in [c.upper() for c in LICENSE_CANDIDATE_NAMES]:
                    if fname not in found_files:
                        found_files.append(fname)
                    if text_content is None:
                        try:
                            content = p.read_text(encoding="utf-8", errors="replace")
                            text_content = content
                            sniffed = sniff_license_text(content)
                        except Exception:
                            pass
    except Exception:
        pass

    return found_files, text_content, sniffed


class PythonScanner(BaseScanner):
    """Scanner for Python packages installed in site-packages or active environment."""

    @property
    def name(self) -> str:
        return "python"

    def can_scan(self, path: Path) -> bool:
        # Check if direct site-packages / dist-info folder
        if path.is_dir():
            if any(path.glob("*.dist-info")):
                return True
            if (path / "pyproject.toml").is_file() or (path / "setup.py").is_file():
                return True
            if _find_virtualenv_site_packages(path) is not None:
                return True
        return False

    def scan(self, path: Path, options: ScanOptions) -> list[Dependency]:
        site_packages_path: Optional[str] = options.site_packages

        if site_packages_path is None:
            if path.is_dir() and any(path.glob("*.dist-info")):
                # Target path itself contains .dist-info folders
                site_packages_path = str(path.resolve())
            else:
                detected = _find_virtualenv_site_packages(path)
                if detected:
                    site_packages_path = str(detected.resolve())

        # If site_packages_path is resolved, query distributions with path=[site_packages_path]
        if site_packages_path:
            dists = list(im.distributions(path=[site_packages_path]))
        else:
            # Query current active Python environment
            dists = list(im.distributions())

        deps: list[Dependency] = []
        seen: set[str] = set()

        for dist in dists:
            try:
                metadata = dist.metadata
                if not metadata:
                    continue
                name = metadata.get("Name")
                if not name:
                    continue

                pkg_key = name.lower()
                if pkg_key in seen:
                    continue
                seen.add(pkg_key)

                version = metadata.get("Version", "unknown")

                # 1. License-Expression (PEP 639)
                raw_license = metadata.get("License-Expression")

                # 2. License field
                if not raw_license or raw_license.strip().upper() == "UNKNOWN":
                    lic_field = metadata.get("License")
                    if lic_field and lic_field.strip().upper() != "UNKNOWN":
                        # If License field contains full text or very long paragraph, don't use as ID
                        if len(lic_field.strip().splitlines()) <= 2 and len(lic_field) < 80:
                            raw_license = lic_field.strip()

                # 3. Classifiers
                classifiers = metadata.get_all("Classifier") or []
                classifier_lic = _extract_license_from_classifiers(classifiers)

                # 4. License files
                lfiles, ltext, sniffed = _extract_license_file_content(dist)

                final_raw = raw_license or classifier_lic or sniffed or "UNKNOWN"
                normalized = normalize_spdx_id(final_raw)

                # Extract Project-URL or Home-page
                homepage = metadata.get("Home-page")
                if not homepage:
                    for proj_url in metadata.get_all("Project-URL") or []:
                        parts = proj_url.split(",", 1)
                        if len(parts) == 2:
                            homepage = parts[1].strip()
                            break

                dep = Dependency(
                    name=name,
                    version=version,
                    ecosystem="python",
                    raw_license=final_raw,
                    normalized_license=normalized,
                    status=ComplianceStatus.UNKNOWN,
                    is_dev=False,
                    license_files=lfiles,
                    license_text=ltext if options.collect_license_texts else None,
                    location=str(getattr(dist, "_path", "")) if hasattr(dist, "_path") else None,
                    homepage=homepage,
                )
                deps.append(dep)
            except Exception:
                continue

        return sorted(deps, key=lambda d: d.name.lower())
