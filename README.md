# license-scan

[![CI](https://github.com/YusufBeratZengin/license-scan/actions/workflows/ci.yml/badge.svg)](https://github.com/YusufBeratZengin/license-scan/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/license-scan.svg?color=blue)](https://pypi.org/project/license-scan/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**[English](README.md)** | **[Türkçe](README.tr.md)**

> Fast, zero-dependency offline dependency license inventory and compliance scanner for Node.js and Python projects.

<p align="center">
  <img src="docs/demo.svg" alt="license-scan terminal demo" width="880">
</p>

## Why license-scan?

- **Zero Runtime Dependencies & 100% Offline:** Built entirely with the Python standard library (`>=3.10`). It performs zero network calls, sends no telemetry, and requires no API keys or third-party SaaS services.
- **Multi-Ecosystem AST Expression Evaluation:** Unifies Node.js (`package-lock.json` v1/v2/v3, `node_modules`) and Python (`importlib.metadata`, PEP 639) under an AST-based SPDX parser handling boolean expressions (`AND`, `OR`, `WITH`, and nested parentheses) with dual-licensing logic.
- **Automated CI Governance & Attribution:** Evaluates dependencies against customizable policy rules (`allow`, `deny`, `review`, and per-package `exceptions`), fails CI pipelines with exit code `1` on compliance violations, and generates ready-to-publish attribution files (`NOTICE` / `THIRD_PARTY`).

---

## Quick Start

### 1. Installation

Install via pip:

```bash
pip install license-scan
```

Or run directly without installing (requires Python 3.10+):

```bash
python -m license_scan --help
```

### 2. Initialize Policy

Generate a default `license-scan.json` policy file in your repository:

```bash
license-scan --init-policy
```

### 3. Scan Your Workspace

Scan all detected Node.js and Python dependencies in the current directory:

```bash
license-scan .
```

### 4. Production-Only Binary Check

Exclude development dependencies (`devDependencies` in Node.js):

```bash
license-scan . --prod
```

### 5. Generate Attribution Notice

Create a third-party attribution notice file:

```bash
license-scan . --notice -o NOTICE
```

---

## Usage Examples

### Enforcing Strict CI Compliance

In CI workflows, enable `--strict` mode to treat unreviewed (`REVIEW`) or unrecognized (`UNKNOWN`) licenses as failures (exit code `1`):

```bash
license-scan . --prod --strict
```

### Targeting a Specific Ecosystem

Inspect only Node.js or Python packages:

```bash
# Node.js only
license-scan ./package-lock.json -e node

# Python only
license-scan . -e python
```

### Inspecting an Isolated Virtual Environment

Point directly to an arbitrary Python `site-packages` directory:

```bash
license-scan . --site-packages .venv/lib/python3.11/site-packages
```

### Exporting Machine-Readable Reports

Generate JSON, CSV, or Markdown summaries for compliance audits:

```bash
# JSON export
license-scan . -f json -o compliance-report.json

# CSV export
license-scan . -f csv -o licenses.csv

# Markdown report for PR comments
license-scan . -f markdown -o report.md
```

### CLI Reference

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

---

## Configuration (`license-scan.json`)

`license-scan` looks for `license-scan.json` (or `.license-scan.json`) in the current directory, or a file specified via `-p / --policy`.

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
      "reason": "Internal developer utility; never bundled or distributed to end customers."
    }
  }
}
```

### Policy Evaluation Logic

1. **Exceptions First:** If a package matches an entry in `exceptions` (case-insensitive) and satisfies the license constraint, it is evaluated as `ALLOWED`.
2. **Deny List Precedence:** Matches against the `deny` list (supports wildcards, e.g. `GPL-*`) take precedence and evaluate as `DENIED`.
3. **Review Flagging:** Licenses listed in `review` evaluate as `REVIEW`.
4. **Allow List:** Licenses explicitly defined in `allow` evaluate as `ALLOWED`.
5. **SPDX Expression Resolution:**
   - **`OR` (Dual Licensing):** Compliant if at least one choice is `ALLOWED`.
   - **`AND` (Combined Licensing):** Requires all components to be compliant. If any branch is `DENIED`, the overall status is `DENIED`.
6. **Exit Codes:** If any dependency is `DENIED` (or in `REVIEW`/`UNKNOWN` when `--strict` is enabled), `license-scan` exits with code `1`.

---

## Continuous Integration (CI)

### GitHub Actions

Add a license compliance check to `.github/workflows/ci.yml`:

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

---

## FAQ & Limitations

### Does license-scan transmit any project data over the network?
No. `license-scan` operates 100% offline. It does not query remote package registries, external APIs, or analytics endpoints.

### Which lockfile formats and package managers are supported?
- **Node.js:** `package-lock.json` (versions 1, 2, and 3) and direct `node_modules` inspection (including scoped `@org/package` structures and embedded `LICENSE` file sniffing).
- **Python:** Installed environments via standard `importlib.metadata` distributions (`License`, PEP 639 `License-Expression`, Trove classifiers, and `.dist-info` license files).

### How does dual-licensing evaluation work?
When a package declares dual-licensing using an `OR` expression (e.g., `(MIT OR GPL-3.0-only)`), `license-scan` treats the dependency as compliant as long as at least one of the options is allowed by your policy, reflecting typical open-source downstream licensing terms.

### What are the limitations?
- `license-scan` inspects local lockfiles and installed packages; it does not resolve uninstalled or unpinned requirement manifests (such as bare `requirements.txt` without an active environment).
- `license-scan` is a developer governance utility, not a substitute for qualified legal counsel.

---

## Contributing

Contributions, bug reports, and suggestions are welcome!

1. Fork and clone the repository.
2. Install test dependencies:
   ```bash
   pip install -e .[test]
   ```
3. Run tests with coverage:
   ```bash
   pytest --cov
   ```
4. Verify linting and typing:
   ```bash
   ruff check src tests
   mypy src
   ```

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for full guidelines.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

Copyright (c) 2026 Yusuf Berat Zengin.
