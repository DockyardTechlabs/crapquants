# Contributing to CRAPQuants

Thank you for considering contributing to CRAPQuants! This guide will help you get started.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/dockyardtechlabs/crapquants.git
cd crapquants

# Install with dev dependencies
make install-dev

# Activate the virtual environment
source .venv/bin/activate

# Verify everything works
make test
```

## Project Structure

```
crapquants/
├── src/crapquants/       # Source code
│   ├── cli.py            # CLI entry point
│   ├── core/             # CRAP formula, AST visitors, coverage, merge
│   ├── frameworks/       # 6 book-derived diagnostic frameworks
│   ├── reporting/        # 5 output formats + glossary
│   ├── baseline/         # Save/compare for regression detection
│   ├── git/              # Hotspots, coupling, truck factor, trends
│   ├── security/         # AST security smells + Semgrep
│   ├── ai_explain/       # Optional AI explanations
│   ├── mutation/         # Optional mutmut integration
│   └── utils/            # Logging, path normalization
├── tests/                # Test suite (329 tests)
├── docs/                 # Architecture + framework documents
└── .claude/skills/       # Claude Code skill
```

## Development Workflow

1. Create a feature branch from `main`
2. Write your code following the conventions below
3. Write tests — every new file gets its own test file
4. Run `make test` — all 329+ tests must pass
5. Run `make self-analyze` — CRAPQuants on its own code must not regress
6. Submit a PR

## Conventions

These rules are non-negotiable for this project:

- **Rule #7:** Test after each file. No file moves forward without passing tests.
- **Rule #12:** Always use a virtual environment. No global installs.
- **Rule #19:** `pip install --only-binary :all:` for all packages.
- **Rule #20:** Hash-pinned requirements via `pip-compile --generate-hashes`.
- **Rule #21:** No secrets in code or config. Runtime environment variables only.
- **Rule #22:** Explicit `[build-system]` in pyproject.toml.
- **Rule #24:** Audit logs are append-only with hash chaining.
- **Rule #25:** Config files treated as executable code — reviewed with same scrutiny.
- **Rule #51:** GitHub Actions pinned to full commit SHA, never mutable tags.

## Adding a New Diagnostic Tag

1. Choose the appropriate framework module in `src/crapquants/frameworks/`
2. Add the detection logic in the `analyze()` function
3. Create a `DiagnosticTag` with: tag_id, framework, severity, description, recommendations
4. Add the tag to `references/tags.md` in the skill directory
5. Add the tag to `REFACTORING_MAP` in `fowler.py` if it has a named refactoring
6. Write tests covering: trigger condition, non-trigger, recommendations present
7. Update the glossary in `reporting/glossary.py` if a new framework explanation is needed

## Adding a New Report Format

1. Create the file in `src/crapquants/reporting/`
2. Follow the pattern: `generate_X_report()` + `write_X_report()` functions
3. Include the glossary from `reporting/glossary.py`
4. Wire it into `cli.py` (add to `OutputFormat` enum + output section)
5. Write tests covering: output structure, file write, content correctness

## Running Tests

```bash
make test          # Full suite (329 tests)
make test-quick    # Quiet output
make test-cov      # With coverage report
```

## Questions?

Open an issue on GitHub or reach out to the maintainers.

---

*Dedicated as Seva to Lord Sri Krishna*
