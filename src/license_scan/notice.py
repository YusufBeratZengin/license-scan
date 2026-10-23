"""NOTICE and THIRD_PARTY attribution file generator."""

from __future__ import annotations

from license_scan.models import ScanResult


def generate_notice(result: ScanResult, project_name: str | None = None) -> str:
    """Generate attribution notice file content for all scanned dependencies."""
    pname = project_name or "This software"
    sep = "=" * 80
    subsep = "-" * 80

    lines: list[str] = []
    lines.append(sep)
    lines.append("THIRD-PARTY SOFTWARE LICENSES AND ATTRIBUTIONS")
    lines.append(sep)
    lines.append("")
    lines.append(
        f"{pname} incorporates third-party open-source components.\n"
        "The authors of these components and their corresponding licenses "
        "are listed below."
    )
    lines.append("")

    if not result.dependencies:
        lines.append("No third-party dependencies recorded.")
        lines.append("")
        return "\n".join(lines)

    for dep in result.dependencies:
        lines.append(subsep)
        lines.append(f"Component: {dep.name}")
        lines.append(f"Version:   {dep.version}")
        lines.append(f"Ecosystem: {dep.ecosystem}")
        lic = dep.normalized_license or dep.raw_license or "UNKNOWN"
        lines.append(f"License:   {lic}")
        if dep.homepage:
            lines.append(f"Homepage:  {dep.homepage}")
        lines.append("")

        if dep.license_text and dep.license_text.strip():
            lines.append(dep.license_text.strip())
        else:
            lines.append(
                f"License declared as {lic}. For complete terms, refer to component source."
            )
        lines.append("")

    lines.append(sep)
    return "\n".join(lines)
