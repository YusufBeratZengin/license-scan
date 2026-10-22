# Contributing to license-scan

Thank you for your interest in contributing to `license-scan`.

## Core Principles

- Zero Runtime Dependencies: The tool must remain fully functional using only the Python Standard Library (`>=3.10`). Do not introduce external runtime dependencies in `dependencies` in `pyproject.toml`.
- Cross-Platform: All code must operate reliably across Linux, macOS, and Windows environments (including path handling and line endings).
- Comprehensive Test Coverage: All new features, ecosystem improvements, and bug fixes must include unit tests.

## Development Workflow

1. Fork the repository on GitHub:
   `https://github.com/YusufBeratZengin/license-scan`
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YusufBeratZengin/license-scan.git
   cd license-scan
   ```
3. Create a feature branch:
   ```bash
   git checkout -b feat/my-improvement
   ```
4. Verify your changes against the test suite:
   ```bash
   python -m unittest discover -s tests -v
   ```
5. Ensure Python bytecode compiles cleanly without syntax warnings:
   ```bash
   python -m compileall src tests
   ```

## Commit Conventions

We follow Conventional Commits:

- `feat:` A new feature or scanner capability.
- `fix:` A bug fix in parser, policy, or scanner logic.
- `docs:` Documentation updates.
- `test:` Adding or refining unit tests and fixtures.
- `refactor:` Code reorganization without behavioral change.
- `chore:` Maintenance tasks or CI pipeline updates.

## Pull Requests

- Keep pull requests focused on a single logical change.
- Ensure all CI tests pass before requesting review.
- Provide clear descriptions of problem and solution in the PR description.
