"""Output formatters for scan results (Table, JSON, CSV, Markdown)."""

from __future__ import annotations

import csv
import io
import json

from license_scan.models import ScanResult


def format_table(result: ScanResult, verbose: bool = False) -> str:
    """Format scan results into a clean, aligned terminal table."""
    lines: list[str] = []
    separator_len = 88
    lines.append("=" * separator_len)
    lines.append("license-scan — Dependency License Inventory")
    lines.append("=" * separator_len)

    if not result.dependencies:
        lines.append("No dependencies found.")
        lines.append("-" * separator_len)
        return "\n".join(lines)

    # Column widths
    col_status = 8
    col_eco = 8
    col_pkg = 24
    col_ver = 12
    col_lic = 18

    header = (
        f"{'STATUS':<{col_status}} "
        f"{'ECO':<{col_eco}} "
        f"{'PACKAGE':<{col_pkg}} "
        f"{'VERSION':<{col_ver}} "
        f"{'LICENSE':<{col_lic}} "
        f"REASON / DETAILS"
    )
    lines.append(header)
    lines.append("-" * separator_len)

    for dep in result.dependencies:
        status_str = str(dep.status)
        pkg_display = dep.name[: col_pkg - 1]
        ver_display = dep.version[: col_ver - 1]
        lic_display = (dep.normalized_license or dep.raw_license)[: col_lic - 1]
        reason_display = dep.reason

        row = (
            f"{status_str:<{col_status}} "
            f"{dep.ecosystem:<{col_eco}} "
            f"{pkg_display:<{col_pkg}} "
            f"{ver_display:<{col_ver}} "
            f"{lic_display:<{col_lic}} "
            f"{reason_display}"
        )
        lines.append(row)

    lines.append("-" * separator_len)
    s = result.summary
    summary_text = (
        f"Summary: {s.total} total | {s.allowed} allowed | "
        f"{s.denied} denied | {s.review} review | {s.unknown} unknown"
    )
    lines.append(summary_text)

    if s.passed:
        lines.append("Result: PASSED")
    else:
        lines.append("Result: FAILED (compliance policy violations detected)")

    lines.append("=" * separator_len)
    return "\n".join(lines)


def format_json(result: ScanResult, indent: int = 2) -> str:
    """Format scan results as JSON."""
    return json.dumps(result.to_dict(), indent=indent)


def format_csv(result: ScanResult) -> str:
    """Format scan results as CSV."""
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["ecosystem", "package", "version", "license", "status", "reason"])

    for dep in result.dependencies:
        writer.writerow([
            dep.ecosystem,
            dep.name,
            dep.version,
            dep.normalized_license or dep.raw_license,
            str(dep.status),
            dep.reason,
        ])

    return output.getvalue()


def format_markdown(result: ScanResult) -> str:
    """Format scan results as Markdown."""
    lines: list[str] = []
    s = result.summary
    status_label = "PASSED" if s.passed else "FAILED"

    lines.append("# License Scan Compliance Report")
    lines.append("")
    lines.append(f"**Result:** `{status_label}`")
    lines.append("")
    lines.append(
        f"- **Total Dependencies:** {s.total}\n"
        f"- **Allowed:** {s.allowed}\n"
        f"- **Denied:** {s.denied}\n"
        f"- **Review Required:** {s.review}\n"
        f"- **Unknown:** {s.unknown}"
    )
    lines.append("")

    if not result.dependencies:
        lines.append("No dependencies detected.")
        return "\n".join(lines)

    lines.append("| Status | Ecosystem | Package | Version | License | Reason / Details |")
    lines.append("|:---|:---|:---|:---|:---|:---|")

    for dep in result.dependencies:
        lic = dep.normalized_license or dep.raw_license
        reason = dep.reason.replace("|", "\\|")
        lines.append(
            f"| `{dep.status}` | {dep.ecosystem} | `{dep.name}` | {dep.version} | `{lic}` | {reason} |"
        )

    lines.append("")
    return "\n".join(lines)
