"""Scanner for Node.js projects (package-lock.json and node_modules)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from license_scan.models import ComplianceStatus, Dependency
from license_scan.scanners.base import BaseScanner, ScanOptions
from license_scan.spdx import normalize_spdx_id, parse_spdx_expression, sniff_license_text

LICENSE_FILENAMES = (
    "license",
    "license.txt",
    "license.md",
    "licence",
    "licence.txt",
    "licence.md",
    "copying",
    "copying.txt",
    "notice",
    "notice.txt",
)


def _extract_pkg_name(node_modules_path: str) -> str:
    """Extract canonical package name from a node_modules relative path."""
    # Examples:
    # "node_modules/foo" -> "foo"
    # "node_modules/@scope/pkg" -> "@scope/pkg"
    # "node_modules/a/node_modules/b" -> "b"
    # "node_modules/a/node_modules/@scope/b" -> "@scope/b"
    parts = node_modules_path.split("node_modules/")
    last = parts[-1].strip("/")
    return last


def _extract_license_from_pkg_json(pkg_data: dict[str, Any]) -> str:
    """Extract and normalize license string from package.json data."""
    # 1. Standard SPDX string
    lic = pkg_data.get("license")
    if isinstance(lic, str) and lic.strip():
        return lic.strip()

    # 2. Legacy object: {"type": "MIT", "url": "..."}
    if isinstance(lic, dict):
        lic_type = lic.get("type")
        if isinstance(lic_type, str) and lic_type.strip():
            return lic_type.strip()

    # 3. Legacy array: "licenses": [{"type": "MIT"}, {"type": "Apache-2.0"}]
    lics = pkg_data.get("licenses")
    if isinstance(lics, list) and lics:
        extracted = []
        for item in lics:
            if isinstance(item, dict) and "type" in item:
                extracted.append(normalize_spdx_id(str(item["type"]).strip()))
            elif isinstance(item, str) and item.strip():
                extracted.append(normalize_spdx_id(item.strip()))
        if extracted:
            return " OR ".join(extracted)

    return "UNKNOWN"


def _read_license_file(pkg_dir: Path) -> tuple[list[str], Optional[str], Optional[str]]:
    """Scan directory for license files; return (found_files, text, sniffed_id)."""
    found_files: list[str] = []
    text_content: Optional[str] = None
    sniffed: Optional[str] = None

    if not pkg_dir.is_dir():
        return found_files, text_content, sniffed

    try:
        for entry in pkg_dir.iterdir():
            if entry.is_file() and entry.name.lower() in LICENSE_FILENAMES:
                found_files.append(entry.name)
                if text_content is None:
                    try:
                        content = entry.read_text(encoding="utf-8", errors="replace")
                        text_content = content
                        sniffed = sniff_license_text(content)
                    except Exception:
                        pass
    except Exception:
        pass

    return found_files, text_content, sniffed


class NodeScanner(BaseScanner):
    """Scanner for npm / Node.js projects."""

    @property
    def name(self) -> str:
        return "node"

    def can_scan(self, path: Path) -> bool:
        if path.is_file():
            return path.name in ("package-lock.json", "package.json")
        if not path.is_dir():
            return False
        if (path / "package-lock.json").exists() or (path / "node_modules").is_dir():
            return True
        try:
            return any((p / "package.json").is_file() for p in path.iterdir() if p.is_dir())
        except Exception:
            return False

    def scan(self, path: Path, options: ScanOptions) -> list[Dependency]:
        target_dir = path if path.is_dir() else path.parent
        lockfile_path = path if path.is_file() and path.name == "package-lock.json" else target_dir / "package-lock.json"

        deps_by_key: dict[tuple[str, str], Dependency] = {}

        if lockfile_path.exists():
            self._scan_lockfile(lockfile_path, target_dir, options, deps_by_key)
        elif (target_dir / "node_modules").is_dir():
            self._scan_node_modules_dir(target_dir / "node_modules", options, deps_by_key)
        elif target_dir.is_dir():
            # Target directory itself may be a node_modules collection
            try:
                has_pkgs = any((p / "package.json").is_file() for p in target_dir.iterdir() if p.is_dir())
                if has_pkgs:
                    self._scan_node_modules_dir(target_dir, options, deps_by_key)
            except Exception:
                pass

        return sorted(deps_by_key.values(), key=lambda d: d.name.lower())

    def _scan_lockfile(
        self,
        lockfile_path: Path,
        base_dir: Path,
        options: ScanOptions,
        deps_by_key: dict[tuple[str, str], Dependency],
    ) -> None:
        try:
            with lockfile_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return

        packages = data.get("packages")
        if isinstance(packages, dict):
            # Lockfile v2 / v3
            for key, val in packages.items():
                if key == "" or not isinstance(val, dict):
                    # Skip root project
                    continue

                pkg_name = val.get("name") or _extract_pkg_name(key)
                if not pkg_name:
                    continue

                version = str(val.get("version", "unknown"))
                is_dev = bool(val.get("dev", False))

                if not options.include_dev and is_dev:
                    continue

                raw_license = "UNKNOWN"
                if "license" in val and isinstance(val["license"], str):
                    raw_license = val["license"]

                # Check on-disk node_modules directory for package.json or license files
                pkg_disk_dir = base_dir / key
                license_files: list[str] = []
                license_text: Optional[str] = None
                homepage: Optional[str] = None

                if pkg_disk_dir.is_dir():
                    pkg_json = pkg_disk_dir / "package.json"
                    if pkg_json.is_file():
                        try:
                            with pkg_json.open("r", encoding="utf-8") as pf:
                                pj_data = json.load(pf)
                                if raw_license == "UNKNOWN":
                                    raw_license = _extract_license_from_pkg_json(pj_data)
                                homepage = pj_data.get("homepage") or pj_data.get("repository", {}).get("url") if isinstance(pj_data.get("repository"), dict) else pj_data.get("repository")
                        except Exception:
                            pass

                    lfiles, ltext, sniffed = _read_license_file(pkg_disk_dir)
                    license_files = lfiles
                    if options.collect_license_texts:
                        license_text = ltext
                    if raw_license == "UNKNOWN" and sniffed:
                        raw_license = sniffed

                try:
                    normalized = parse_spdx_expression(raw_license).to_string()
                except Exception:
                    normalized = normalize_spdx_id(raw_license)
                dep = Dependency(
                    name=pkg_name,
                    version=version,
                    ecosystem="node",
                    raw_license=raw_license,
                    normalized_license=normalized,
                    status=ComplianceStatus.UNKNOWN,
                    is_dev=is_dev,
                    license_files=license_files,
                    license_text=license_text,
                    location=str(pkg_disk_dir) if pkg_disk_dir.exists() else None,
                    homepage=homepage,
                )
                deps_by_key[(pkg_name, version)] = dep
        else:
            # Fallback to Lockfile v1 dependencies tree
            dependencies = data.get("dependencies", {})
            self._scan_v1_dependencies(dependencies, base_dir, options, deps_by_key)

    def _scan_v1_dependencies(
        self,
        deps_dict: dict[str, Any],
        base_dir: Path,
        options: ScanOptions,
        deps_by_key: dict[tuple[str, str], Dependency],
    ) -> None:
        for name, val in deps_dict.items():
            if not isinstance(val, dict):
                continue
            version = str(val.get("version", "unknown"))
            is_dev = bool(val.get("dev", False))

            if not options.include_dev and is_dev:
                continue

            pkg_disk_dir = base_dir / "node_modules" / name
            raw_license = "UNKNOWN"
            license_files: list[str] = []
            license_text: Optional[str] = None
            homepage: Optional[str] = None

            if pkg_disk_dir.is_dir():
                pkg_json = pkg_disk_dir / "package.json"
                if pkg_json.is_file():
                    try:
                        with pkg_json.open("r", encoding="utf-8") as pf:
                            pj_data = json.load(pf)
                            raw_license = _extract_license_from_pkg_json(pj_data)
                            homepage = pj_data.get("homepage")
                    except Exception:
                        pass
                lfiles, ltext, sniffed = _read_license_file(pkg_disk_dir)
                license_files = lfiles
                if options.collect_license_texts:
                    license_text = ltext
                if raw_license == "UNKNOWN" and sniffed:
                    raw_license = sniffed

            try:
                normalized = parse_spdx_expression(raw_license).to_string()
            except Exception:
                normalized = normalize_spdx_id(raw_license)
            deps_by_key[(name, version)] = Dependency(
                name=name,
                version=version,
                ecosystem="node",
                raw_license=raw_license,
                normalized_license=normalized,
                status=ComplianceStatus.UNKNOWN,
                is_dev=is_dev,
                license_files=license_files,
                license_text=license_text,
                location=str(pkg_disk_dir) if pkg_disk_dir.exists() else None,
                homepage=homepage,
            )

            # Recurse into nested dependencies if present
            nested = val.get("dependencies")
            if isinstance(nested, dict):
                self._scan_v1_dependencies(nested, base_dir, options, deps_by_key)

    def _scan_node_modules_dir(
        self,
        node_modules_dir: Path,
        options: ScanOptions,
        deps_by_key: dict[tuple[str, str], Dependency],
    ) -> None:
        if not node_modules_dir.is_dir():
            return

        for item in node_modules_dir.iterdir():
            if not item.is_dir() or item.name.startswith("."):
                continue

            if item.name.startswith("@"):
                # Scoped package directory
                for subitem in item.iterdir():
                    if subitem.is_dir() and not subitem.name.startswith("."):
                        self._process_node_pkg_dir(subitem, f"{item.name}/{subitem.name}", options, deps_by_key)
            else:
                self._process_node_pkg_dir(item, item.name, options, deps_by_key)

    def _process_node_pkg_dir(
        self,
        pkg_dir: Path,
        pkg_name: str,
        options: ScanOptions,
        deps_by_key: dict[tuple[str, str], Dependency],
    ) -> None:
        pkg_json = pkg_dir / "package.json"
        version = "unknown"
        raw_license = "UNKNOWN"
        homepage = None

        if pkg_json.is_file():
            try:
                with pkg_json.open("r", encoding="utf-8") as f:
                    pj_data = json.load(f)
                    version = str(pj_data.get("version", "unknown"))
                    raw_license = _extract_license_from_pkg_json(pj_data)
                    homepage = pj_data.get("homepage") or (pj_data.get("repository", {}).get("url") if isinstance(pj_data.get("repository"), dict) else pj_data.get("repository"))
            except Exception:
                pass

        lfiles, ltext, sniffed = _read_license_file(pkg_dir)
        if raw_license == "UNKNOWN" and sniffed:
            raw_license = sniffed

        try:
            normalized = parse_spdx_expression(raw_license).to_string()
        except Exception:
            normalized = normalize_spdx_id(raw_license)
        dep = Dependency(
            name=pkg_name,
            version=version,
            ecosystem="node",
            raw_license=raw_license,
            normalized_license=normalized,
            status=ComplianceStatus.UNKNOWN,
            is_dev=False,
            license_files=lfiles,
            license_text=ltext if options.collect_license_texts else None,
            location=str(pkg_dir),
            homepage=homepage,
        )
        deps_by_key[(pkg_name, version)] = dep
