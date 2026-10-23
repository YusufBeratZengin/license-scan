"""Command-line interface for license-scan."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from license_scan import __version__
from license_scan.formatters import (
    format_csv,
    format_json,
    format_markdown,
    format_table,
)
from license_scan.models import Dependency, ScanResult
from license_scan.notice import generate_notice
from license_scan.policy import Policy
from license_scan.scanners.base import ScanOptions
from license_scan.scanners.node import NodeScanner
from license_scan.scanners.python import PythonScanner


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="license-scan",
        description="Offline dependency license inventory and compliance scanner for Node and Python projects.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Target directory, package-lock.json file, or site-packages path to scan (default: current directory).",
    )
    parser.add_argument(
        "-p",
        "--policy",
        metavar="FILE",
        help="Path to license-scan.json policy file (default: license-scan.json if present, else built-in policy).",
    )
    parser.add_argument(
        "-e",
        "--ecosystem",
        choices=["all", "node", "python"],
        default="all",
        help="Target package ecosystem to inspect (default: all).",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["table", "json", "csv", "markdown", "notice"],
        default="table",
        help="Output format (default: table).",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="Write scan output to a file instead of stdout.",
    )
    parser.add_argument(
        "--site-packages",
        metavar="DIR",
        help="Explicit path to Python site-packages directory.",
    )
    parser.add_argument(
        "--prod",
        "--no-dev",
        action="store_true",
        dest="prod_only",
        help="Exclude development dependencies.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat REVIEW and UNKNOWN licenses as failures (exit 1).",
    )
    parser.add_argument(
        "--notice",
        action="store_true",
        help="Shortcut to output attribution NOTICE format.",
    )
    parser.add_argument(
        "--init-policy",
        action="store_true",
        help="Generate a starter license-scan.json policy file and exit.",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress informational output.",
    )

    return parser


def run_scan(
    target_path: Path,
    ecosystem: str,
    policy: Policy,
    options: ScanOptions,
    strict: bool = False,
) -> ScanResult:
    """Run scanners for selected ecosystems and evaluate dependencies."""
    dependencies: list[Dependency] = []

    # Node scanner
    if ecosystem in ("all", "node"):
        node_scanner = NodeScanner()
        if ecosystem == "node" or node_scanner.can_scan(target_path):
            deps = node_scanner.scan(target_path, options)
            dependencies.extend(deps)

    # Python scanner
    if ecosystem in ("all", "python"):
        python_scanner = PythonScanner()
        if ecosystem == "python" or python_scanner.can_scan(target_path) or options.site_packages:
            deps = python_scanner.scan(target_path, options)
            dependencies.extend(deps)

    # Evaluate compliance with policy
    policy.evaluate_all(dependencies)

    result = ScanResult(
        dependencies=dependencies,
        policy_path=policy.loaded_from,
        root_path=str(target_path),
    )
    result.compute_summary(strict=strict)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    """CLI execution entrypoint."""
    parser = create_parser()
    args = parser.parse_args(argv)

    # Policy initialization helper
    if args.init_policy:
        out_policy = args.policy or "license-scan.json"
        dest = Policy.save_default_file(out_policy)
        if not args.quiet:
            print(f"Generated policy configuration at {dest}")
        return 0

    target = Path(args.path)
    if not target.exists() and not args.site_packages:
        sys.stderr.write(f"Error: Target path '{args.path}' does not exist.\n")
        return 2

    # Load policy
    try:
        policy = Policy.load(args.policy)
    except FileNotFoundError as err:
        sys.stderr.write(f"Error: {err}\n")
        return 2
    except Exception as err:  # noqa: BLE001
        sys.stderr.write(f"Error parsing policy file: {err}\n")
        return 2

    output_fmt = "notice" if args.notice else args.format

    options = ScanOptions(
        include_dev=not args.prod_only,
        site_packages=args.site_packages,
        collect_license_texts=True,
    )

    result = run_scan(
        target_path=target,
        ecosystem=args.ecosystem,
        policy=policy,
        options=options,
        strict=args.strict,
    )

    # Format output
    if output_fmt == "json":
        formatted = format_json(result)
    elif output_fmt == "csv":
        formatted = format_csv(result)
    elif output_fmt == "markdown":
        formatted = format_markdown(result)
    elif output_fmt == "notice":
        formatted = generate_notice(result)
    else:
        formatted = format_table(result)

    # Deliver output
    if args.output:
        try:
            out_path = Path(args.output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(formatted + "\n", encoding="utf-8")
            if not args.quiet:
                print(f"Output written to {out_path}")
        except Exception as err:  # noqa: BLE001
            sys.stderr.write(f"Error writing to output file '{args.output}': {err}\n")
            return 2
    elif not args.quiet:
        print(formatted)

    # Return 1 if policy check failed
    return 0 if result.summary.passed else 1
