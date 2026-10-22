# license-scan

Offline dependency license inventory and compliance scanner for Node.js and Python projects with allow/deny policies for CI.

## Overview

Software projects often incorporate hundreds of transitive third-party dependencies. Shipping proprietary closed-source applications with incompatible licenses (such as GPL/AGPL in binary distributions) or unvetted dependencies introduces legal and compliance liabilities.

`license-scan` provides a fast, offline dependency license inventory scanner with zero runtime dependencies. It inspects Node.js (`package-lock.json` v2/v3 and `node_modules`) and Python installed packages (`importlib.metadata` distributions), normalizes licenses to canonical SPDX identifiers, evaluates SPDX boolean expressions (`AND`, `OR`, `WITH`), enforces compliance against customizable policy files (`license-scan.json`), and generates reports and third-party attribution notices (`NOTICE` / `THIRD_PARTY`).

## Features

- Zero runtime dependencies: uses only the Python standard library (`>=3.10`).
- Multi-ecosystem detection:
  - Node.js: parses `package-lock.json` (v2 and v3 format) and scans `node_modules` (`package.json`, legacy `licenses` arrays, and license file sniffing).
  - Python: reads installed distributions via `importlib.metadata` (`License`, `License-Expression` per PEP 639, Trove classifiers, and license files) for the active environment or any specified `site-packages` directory.
- SPDX normalization and expression parsing:
  - Built-in canonical alias table (`Apache 2.0` -> `Apache-2.0`, `MIT License` -> `MIT`, etc.).
  - Full boolean expression parsing supporting `AND`, `OR`, `WITH`, and nested parentheses.
  - Accurate dual-licensing evaluation: an `OR` dual-license expression is compliant if at least one branch satisfies the policy.
  - License text sniffer for identifying licenses when metadata is missing.
- Policy enforcement (`license-scan.json`):
  - `allow`, `deny`, and `review` lists with wildcard pattern matching (e.g. `GPL-*`).
  - Per-package exceptions with explicit justification reason.
  - Strict mode flag (`--strict`) to reject packages requiring manual review or unknown licenses.
  - Exit code `1` on denied licenses for automated CI gates.
- Multiple output formats:
  - Formatted terminal table.
  - Machine-readable JSON and CSV.
  - GitHub-flavored Markdown.
  - Attribution notice file generator (`NOTICE` / `THIRD_PARTY`).

## Installation

### From Source or Wheel

```bash
git clone https://github.com/YusufBeratZengin/license-scan.git
cd license-scan
pip install .
```

### Standalone / Editable Development

Because `license-scan` has zero runtime dependencies, you can run it directly with any Python 3.10+ installation:

```bash
python -m license_scan --help
```

## Quick Start

### 1. Initialize a Policy File

Generate a starter `license-scan.json` in your repository:

```bash
license-scan --init-policy
```

### 2. Scan the Current Project

Scan all detected Node and Python dependencies in the current workspace:

```bash
license-scan .
```

### 3. Exclude Development Dependencies

For production binary builds, exclude development-only packages:

```bash
license-scan . --prod
```

### 4. Generate Attribution Notices

Produce a third-party attribution notice file:

```bash
license-scan . --notice -o NOTICE
```

## Command-Line Usage

```text
usage: license-scan [-h] [-p FILE] [-e {all,node,python}]
                    [-f {table,json,csv,markdown,notice}] [-o FILE]
                    [--site-packages DIR] [--prod] [--strict] [--notice]
                    [--init-policy] [-v] [-q]
                    [path]

positional arguments:
  path                  Target directory, package-lock.json file, or site-packages path to scan (default: current directory).

options:
  -h, --help            Show this help message and exit.
  -p, --policy FILE     Path to license-scan.json policy file.
  -e, --ecosystem {all,node,python}
                        Target package ecosystem to inspect (default: all).
  -f, --format {table,json,csv,markdown,notice}
                        Output format (default: table).
  -o, --output FILE     Write scan output to a file instead of stdout.
  --site-packages DIR   Explicit path to Python site-packages directory.
  --prod, --no-dev      Exclude development dependencies.
  --strict              Treat REVIEW and UNKNOWN licenses as failures (exit 1).
  --notice              Shortcut to output attribution NOTICE format.
  --init-policy         Generate a starter license-scan.json policy file and exit.
  -v, --version         Show program's version number and exit.
  -q, --quiet           Suppress informational output.
```

## Policy Configuration (`license-scan.json`)

The policy configuration controls allowed, denied, and review-flagged licenses.

```json
{
  "$schema": "https://raw.githubusercontent.com/YusufBeratZengin/license-scan/main/schema.json",
  "allow": [
    "MIT",
    "Apache-2.0",
    "BSD-3-Clause",
    "BSD-2-Clause",
    "ISC",
    "0BSD",
    "CC0-1.0",
    "Unlicense",
    "PSF-2.0",
    "Zlib"
  ],
  "deny": [
    "GPL-1.0*",
    "GPL-2.0*",
    "GPL-3.0*",
    "AGPL-1.0*",
    "AGPL-3.0*",
    "SSPL-1.0*",
    "CPAL-1.0*",
    "OSL-3.0*"
  ],
  "review": [
    "MPL-2.0",
    "LGPL-2.1*",
    "LGPL-3.0*",
    "EPL-1.0",
    "EPL-2.0",
    "EUPL-1.2"
  ],
  "allow_unknown": false,
  "exceptions": {
    "internal-build-tool": {
      "license": "GPL-3.0-only",
      "reason": "Internal developer utility; never bundled or distributed to customers."
    }
  }
}
```

### Policy Evaluation Logic

1. **Exceptions First:** If the package name matches an entry in `exceptions` (case-insensitive) and the license matches (or no license restriction is specified in the exception), the package is marked `ALLOWED`.
2. **SPDX Expression Resolution:**
   - Single license: Checked against `deny` (wildcards supported), then `review`, then `allow`.
   - `OR` (Dual licensing): If any branch is `ALLOWED`, the dependency is compliant. If all branches are denied, it is marked `DENIED`.
   - `AND` (Combined licensing): All parts must be compliant. If any branch is `DENIED`, the dependency is `DENIED`.
3. **Exit Code:** If any dependency resolves to `DENIED`, `license-scan` exits with code `1`. When `--strict` is enabled, dependencies in `REVIEW` or `UNKNOWN` state also trigger exit code `1`.

## Continuous Integration (CI)

### GitHub Actions

Add a license check step to your CI workflow:

```yaml
name: License Compliance

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  license-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: |
          npm ci --production
      - name: Run license-scan
        run: |
          python -m license_scan . --prod --strict
```

### GitLab CI

```yaml
license_scan:
  stage: test
  image: python:3.11-slim
  script:
    - python -m license_scan . --strict
```

## Running Tests

Run the test suite using Python's built-in `unittest` runner:

```bash
python -m unittest discover -s tests -v
```

## Project Architecture

```text
src/license_scan/
├── __init__.py         # Package entry and version
├── __main__.py         # python -m license_scan invocation
├── cli.py              # CLI argument parser and command execution
├── models.py           # Dependency, ScanResult, and ComplianceStatus models
├── spdx.py             # Alias normalizer, text sniffer, and expression AST/parser
├── policy.py           # Policy loader, exception matching, and rule evaluation
├── formatters.py       # Table, JSON, CSV, and Markdown formatters
├── notice.py           # Attribution notice generator
└── scanners/
    ├── __init__.py     # Scanner registry
    ├── base.py         # BaseScanner interface and ScanOptions
    ├── node.py         # Node.js package-lock and node_modules scanner
    └── python.py       # Python importlib.metadata distribution scanner
```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

Copyright (c) 2026 Yusuf Berat Zengin.
