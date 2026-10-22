# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-10-22

### Added
- Zero-dependency core runner for Python 3.10+.
- Node.js ecosystem scanner supporting:
  - `package-lock.json` lockfile formats v2 and v3.
  - Legacy `package-lock.json` v1 fallback resolution.
  - `node_modules` directory scanning with scoped packages (`@scope/pkg`).
  - Legacy `licenses` array in `package.json`.
  - Heuristic license text sniffing (`LICENSE`, `COPYING`, etc.).
- Python ecosystem scanner via `importlib.metadata`:
  - Reading `License`, `License-Expression` (PEP 639), and Trove classifiers.
  - License file text extraction and inspection.
  - Active environment and explicit `--site-packages` path scanning.
  - Automatic `.venv` / `venv` directory discovery.
- SPDX normalization and expression engine:
  - Built-in canonical alias lookup table for common licenses.
  - Recursive descent parser for SPDX expressions supporting `AND`, `OR`, `WITH`, and nested parentheses.
  - Dual-licensing compliance logic (`OR` branches evaluated with user choice).
- Policy configuration engine (`license-scan.json`):
  - `allow`, `deny`, and `review` lists with wildcard matching (`GPL-*`).
  - Per-package compliance exceptions with required reason justification.
  - Strict mode enforcement via `--strict` flag.
  - Built-in `--init-policy` generator.
- Multi-format report generators:
  - Terminal table formatting with aligned columns.
  - Machine-readable JSON output.
  - Standardized CSV export.
  - Markdown compliance report.
  - Third-party attribution file generator (`NOTICE` / `THIRD_PARTY`).
- CLI tool (`license-scan`) with exit code 1 on policy failures.
- Unit test suite with lockfile and fake `site-packages` fixtures.
- GitHub Actions CI matrix testing across Ubuntu and Windows with Python 3.10, 3.11, 3.12, and 3.13.
