#!/usr/bin/env python3
"""Generate a static terminal-style SVG showing real CLI execution and output."""

from __future__ import annotations

import html
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def run_cli_and_capture() -> list[str]:
    """Execute real license-scan CLI on a multi-ecosystem demo workspace."""
    repo_root = Path(__file__).resolve().parent.parent

    with tempfile.TemporaryDirectory() as tmp:
        demo_dir = Path(tmp)

        # 1. Package-lock.json (Node.js dependencies)
        lock_data = {
            "name": "web-service",
            "version": "1.0.0",
            "lockfileVersion": 3,
            "packages": {
                "": {"name": "web-service", "version": "1.0.0"},
                "node_modules/@types/node": {
                    "version": "20.11.24",
                    "license": "MIT",
                    "dev": True,
                },
                "node_modules/express": {"version": "4.19.2", "license": "MIT"},
                "node_modules/lodash": {"version": "4.17.21", "license": "MIT"},
                "node_modules/typescript": {
                    "version": "5.4.5",
                    "license": "Apache-2.0",
                    "dev": True,
                },
            },
        }
        (demo_dir / "package-lock.json").write_text(
            json.dumps(lock_data, indent=2), encoding="utf-8"
        )

        # 2. Python site-packages (.venv layout)
        site_packages = demo_dir / ".venv" / "Lib" / "site-packages"
        site_packages.mkdir(parents=True)

        def add_python_dist(name: str, version: str, license_val: str) -> None:
            dist_dir = site_packages / f"{name}-{version}.dist-info"
            dist_dir.mkdir(parents=True)
            metadata = (
                f"Metadata-Version: 2.1\n"
                f"Name: {name}\n"
                f"Version: {version}\n"
                f"License: {license_val}\n"
            )
            (dist_dir / "METADATA").write_text(metadata, encoding="utf-8")

        add_python_dist("certifi", "2024.2.2", "MPL-2.0")
        add_python_dist("cryptography", "42.0.5", "Apache-2.0 OR BSD-3-Clause")
        add_python_dist("fastapi", "0.110.0", "MIT")
        add_python_dist("pydantic", "2.6.4", "MIT")
        add_python_dist("requests", "2.31.0", "Apache-2.0")
        add_python_dist("urllib3", "2.0.7", "MIT")

        # Run license-scan CLI
        proc = subprocess.run(
            [sys.executable, "-m", "license_scan", "."],
            cwd=str(demo_dir),
            capture_output=True,
            text=True,
            env={"PYTHONPATH": str(repo_root / "src")},
            check=False,
        )

        raw_output = proc.stdout
        lines = [line.rstrip() for line in raw_output.splitlines() if line.strip()]

        # Ensure correct em-dash display in title banner
        clean_lines: list[str] = []
        for line in lines:
            if "license-scan" in line and "Dependency License Inventory" in line:
                clean_lines.append("license-scan — Dependency License Inventory")
            else:
                clean_lines.append(line)

        return clean_lines


def render_svg(command: str, output_lines: list[str]) -> str:
    """Render terminal output into a polished, accessible dark-mode SVG."""
    font_size = 13
    line_height = 20
    char_width = 7.8
    margin_top = 50
    margin_left = 22
    margin_bottom = 20

    # Calculate dimensions
    max_line_len = max(len(command) + 2, max(len(line) for line in output_lines))
    svg_width = int(max(840, max_line_len * char_width + margin_left * 2))
    total_text_lines = 1 + len(output_lines)  # prompt + output
    svg_height = margin_top + total_text_lines * line_height + margin_bottom

    svg_parts: list[str] = []
    svg_parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_width} {svg_height}" '
        f'width="{svg_width}" height="{svg_height}">'
    )
    svg_parts.append("""  <defs>
    <filter id="shadow" x="-5%" y="-5%" width="110%" height="110%">
      <feDropShadow dx="0" dy="8" stdDeviation="16" flood-color="#000000" flood-opacity="0.45"/>
    </filter>
  </defs>""")

    # Window container
    svg_parts.append(f"""  <!-- Window Frame -->
  <rect x="0" y="0" width="{svg_width}" height="{svg_height}" rx="10" fill="#0d1117" stroke="#30363d" stroke-width="1.5" filter="url(#shadow)"/>
  <path d="M 0 10 C 0 4.477 4.477 0 10 0 L {svg_width - 10} 0 C {svg_width - 4.477} 0 {svg_width} 4.477 {svg_width} 10 L {svg_width} 36 L 0 36 Z" fill="#161b22"/>
  <line x1="0" y1="36" x2="{svg_width}" y2="36" stroke="#30363d" stroke-width="1"/>""")

    # 3 dots
    svg_parts.append("""  <!-- Window Controls -->
  <circle cx="20" cy="18" r="6" fill="#ff5f56" stroke="#e0443e" stroke-width="0.5"/>
  <circle cx="40" cy="18" r="6" fill="#ffbd2e" stroke="#dea123" stroke-width="0.5"/>
  <circle cx="60" cy="18" r="6" fill="#27c93f" stroke="#1aab29" stroke-width="0.5"/>""")

    # Window title
    svg_parts.append(f"""  <!-- Window Title -->
  <text x="{svg_width // 2}" y="22" fill="#8b949e" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif" font-size="12" text-anchor="middle" font-weight="500">license-scan — bash</text>""")

    # Terminal text
    svg_parts.append(f"""  <!-- Terminal Text -->
  <g font-family="ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace" font-size="{font_size}">""")

    # Command prompt
    curr_y = margin_top + 4
    svg_parts.append(
        f'    <text x="{margin_left}" y="{curr_y}">'
        f'<tspan fill="#7d8590">user@host:~/project$ </tspan>'
        f'<tspan fill="#58a6ff" font-weight="bold">{html.escape(command)}</tspan>'
        f'</text>'
    )
    curr_y += line_height

    # Output lines
    for line in output_lines:
        escaped_line = html.escape(line)

        if line.startswith(("===", "---")):
            styled_content = f'<tspan fill="#6e7681">{escaped_line}</tspan>'
        elif "Dependency License Inventory" in line:
            styled_content = f'<tspan fill="#58a6ff" font-weight="bold">{escaped_line}</tspan>'
        elif line.startswith("STATUS   ECO"):
            styled_content = f'<tspan fill="#f0f6fc" font-weight="bold">{escaped_line}</tspan>'
        elif line.startswith("ALLOWED"):
            col_status = line[:9]
            col_eco = line[9:18]
            col_pkg = line[18:43]
            col_ver = line[43:56]
            col_lic = line[56:75]
            col_reason = line[75:]

            styled_content = (
                f'<tspan fill="#3fb950" font-weight="bold">{html.escape(col_status)}</tspan>'
                f'<tspan fill="#79c0ff">{html.escape(col_eco)}</tspan>'
                f'<tspan fill="#c9d1d9">{html.escape(col_pkg)}</tspan>'
                f'<tspan fill="#8b949e">{html.escape(col_ver)}</tspan>'
                f'<tspan fill="#58a6ff">{html.escape(col_lic)}</tspan>'
                f'<tspan fill="#8b949e">{html.escape(col_reason)}</tspan>'
            )
        elif line.startswith("REVIEW"):
            col_status = line[:9]
            col_eco = line[9:18]
            col_pkg = line[18:43]
            col_ver = line[43:56]
            col_lic = line[56:75]
            col_reason = line[75:]

            styled_content = (
                f'<tspan fill="#d29922" font-weight="bold">{html.escape(col_status)}</tspan>'
                f'<tspan fill="#79c0ff">{html.escape(col_eco)}</tspan>'
                f'<tspan fill="#c9d1d9">{html.escape(col_pkg)}</tspan>'
                f'<tspan fill="#8b949e">{html.escape(col_ver)}</tspan>'
                f'<tspan fill="#d29922">{html.escape(col_lic)}</tspan>'
                f'<tspan fill="#d29922">{html.escape(col_reason)}</tspan>'
            )
        elif line.startswith("DENIED"):
            col_status = line[:9]
            col_eco = line[9:18]
            col_pkg = line[18:43]
            col_ver = line[43:56]
            col_lic = line[56:75]
            col_reason = line[75:]

            styled_content = (
                f'<tspan fill="#f85149" font-weight="bold">{html.escape(col_status)}</tspan>'
                f'<tspan fill="#79c0ff">{html.escape(col_eco)}</tspan>'
                f'<tspan fill="#c9d1d9">{html.escape(col_pkg)}</tspan>'
                f'<tspan fill="#8b949e">{html.escape(col_ver)}</tspan>'
                f'<tspan fill="#f85149">{html.escape(col_lic)}</tspan>'
                f'<tspan fill="#f85149">{html.escape(col_reason)}</tspan>'
            )
        elif line.startswith("Summary:"):
            styled_content = f'<tspan fill="#c9d1d9" font-weight="500">{escaped_line}</tspan>'
        elif "Result: PASSED" in line:
            styled_content = (
                '<tspan fill="#c9d1d9">Result: </tspan>'
                '<tspan fill="#3fb950" font-weight="bold">PASSED</tspan>'
            )
        elif "Result: FAILED" in line:
            styled_content = (
                '<tspan fill="#c9d1d9">Result: </tspan>'
                '<tspan fill="#f85149" font-weight="bold">FAILED</tspan>'
            )
        else:
            styled_content = f'<tspan fill="#c9d1d9">{escaped_line}</tspan>'

        svg_parts.append(f'    <text x="{margin_left}" y="{curr_y}">{styled_content}</text>')
        curr_y += line_height

    svg_parts.append("  </g>")
    svg_parts.append("</svg>")
    return "\n".join(svg_parts) + "\n"


def main() -> None:
    print("Executing license-scan CLI to capture real output...")
    command = "license-scan ."
    output_lines = run_cli_and_capture()
    print(f"Captured {len(output_lines)} lines of CLI output.")

    svg_content = render_svg(command, output_lines)

    docs_dir = Path(__file__).resolve().parent.parent / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    out_svg = docs_dir / "demo.svg"
    out_svg.write_text(svg_content, encoding="utf-8")
    print(f"Generated demo SVG at {out_svg}")


if __name__ == "__main__":
    main()
