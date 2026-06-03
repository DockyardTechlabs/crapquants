# CRAPQuants

<p align="center">
     <img src="docs/CRAPQuants1.png" alt="CRAPQuants Logo" width="300">
</p>


**CRAP + Quantitative Connective Tissue for Python Code Quality**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests: 329 passing](https://img.shields.io/badge/tests-329%20passing-brightgreen.svg)]()

> The Python-native CRAP metric tool with book-integrated diagnostics and architectural fitness functions.

CRAPQuants computes **CRAP scores** (Change Risk Anti-Patterns) for Python codebases by combining cyclomatic complexity with test coverage, then enriches results with diagnostic tags derived from **six foundational software engineering books**.

**No AI required.** Pure deterministic static analysis. Works fully offline.

---

## What is CRAP?

**CRAP(m) = CC² × (1 − coverage/100)³ + CC**

A function with high complexity AND low test coverage is risky to change. CRAP captures this tradeoff in a single number:

| Score | Meaning |
|-------|---------|
| 1–10 | **Clean** — low risk, easy to change safely |
| 11–30 | **Moderate** — manageable, consider adding tests |
| 31–60 | **CRAPpy** — high risk, prioritize for refactoring or testing |
| 61+ | **Critical** — very high risk, changes here are dangerous |

---

## Installation

### Option A: Quick Install (recommended)

```bash
git clone https://github.com/dockyardtechlabs/crapquants.git
cd crapquants
make install
```

This creates a virtual environment, installs all dependencies with hash verification, and registers the `crapquants` command.

### Option B: Manual Install

```bash
git clone https://github.com/dockyardtechlabs/crapquants.git
cd crapquants
python3 -m venv .venv
source .venv/bin/activate
pip install --only-binary :all: -r requirements.txt
pip install -e .
```

### Option C: Development Install (includes test tools)

```bash
git clone https://github.com/dockyardtechlabs/crapquants.git
cd crapquants
make install-dev
make test    # Verify: 329 tests should pass
```

### Verify Installation

```bash
source .venv/bin/activate
crapquants version
# Output: CRAPQuants v1.0.0
```

---

## Quick Start

```bash
# Activate the virtual environment
source .venv/bin/activate

# Analyze your Python code
crapquants analyze ./src

# With test coverage data (much more accurate)
pytest --cov=src --cov-report=json
crapquants analyze ./src --coverage coverage.json

# Quick mode (CRAP scores only, fastest)
crapquants analyze ./src --level quick
```

---

## Output Formats

CRAPQuants generates reports in 5 formats. Choose one per run:

```bash
# Terminal table (default) — colorized, interactive
crapquants analyze ./src

# JSON — for dashboards and programmatic use
crapquants analyze ./src -f json -o report.json

# Markdown — for PR comments and documentation
crapquants analyze ./src -f markdown -o report.md

# SARIF 2.1.0 — for GitHub Code Scanning
crapquants analyze ./src -f sarif -o report.sarif

# GitHub Actions — inline PR annotations
crapquants analyze ./src -f github_actions
```

Every report includes a **"How to Read This Report"** glossary — first-time readers understand all metrics without external documentation.

---

## Features

### 4 Analysis Levels

| Level | Flag | What Runs | Speed |
|-------|------|-----------|-------|
| Quick | `--level quick` | CRAP scores only | ~seconds |
| Standard | `--level standard` | CRAP + 6 framework tags + CogC + ABC | ~seconds |
| Deep | `--level deep` | Standard + git hotspots & trends | ~10-30s |
| Full | `--level full` | Deep + mutation testing + SAST | ~minutes |

### Baseline Regression Detection

```bash
# Save baseline on main branch
crapquants analyze ./src -c coverage.json --save-baseline data/baseline.json

# Compare on PR — exit code 1 if any regression
crapquants analyze ./src -c coverage.json --baseline data/baseline.json
```

Detects: new CRAPpy functions, worsened scores, improvements, fixed functions, aggregate CRAP delta.

### Security Scanning (Two-Tier)

**Tier 1 — AST-based (always on):** eval/exec (CWE-95), pickle (CWE-502), hardcoded secrets (CWE-798), shell injection (CWE-78), unsafe YAML (CWE-502).

**Tier 2 — Semgrep (optional):** Comprehensive SAST when Semgrep is installed.

### AI-Powered Explanations (Optional)

```bash
export CRAPQUANTS_OPENAI_API_KEY=sk-...
crapquants analyze ./src --ai-explain --ai-provider openai
```

Supports OpenAI, Anthropic Claude, Nvidia NIMs, and Ollama (local). API keys are read at runtime only — never stored in config files.

---

## Theoretical Foundations

CRAPQuants diagnostic tags come from six foundational software engineering books. Each tag carries its source attribution in the report.

| # | Framework | Source | Author(s) |
|---|-----------|--------|-----------|
| 1 | **Feathers** | Working Effectively with Legacy Code | Michael Feathers |
| 2 | **Ousterhout** | A Philosophy of Software Design, 2nd Ed | John Ousterhout |
| 3 | **Hunt & Thomas** | The Pragmatic Programmer, 20th Anniversary Ed | Andrew Hunt, David Thomas |
| 4 | **Fowler** | Refactoring | Martin Fowler, Kent Beck |
| 5 | **Tornhill** | Your Code as a Crime Scene, 2nd Ed | Adam Tornhill |
| 6 | **Ford** | Building Evolutionary Architectures, 2nd Ed | Neal Ford, Rebecca Parsons, Patrick Kua, Pramod Sadalage |
| 7 | **SonarSource** | Cognitive Complexity Whitepaper v1.7 | G. Ann Campbell |

### Scoring Architecture

| Score | Framework | What It Measures |
|-------|-----------|-----------------|
| **FRS** | Feathers | Testability risk (coverage side) |
| **ORS** | Ousterhout | Design quality risk (complexity side) |
| **TBS** | Tornhill | Behavioral risk (activity side) |
| **PHS** | Hunt & Thomas | Codebase sustainability (0-100) |
| **CQ_score** | All | max(FRS, ORS, TBS) — worst assessment wins |

---

## CI/CD Integration

### GitHub Actions

```yaml
name: CRAPQuants Quality Gate
on: [pull_request]

permissions:
  contents: read
  checks: write

jobs:
  crapquants:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # v4
        with:
          fetch-depth: 0

      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065  # v5
        with:
          python-version: '3.11'

      - name: Install & Run
        run: |
          python -m venv .venv
          source .venv/bin/activate
          pip install --only-binary :all: -r requirements.txt
          pip install -e .
          pytest --cov=src --cov-report=json -q
          crapquants analyze ./src -c coverage.json --baseline data/baseline.json -f github_actions
```

---

## Make Commands

```bash
make help           # Show all available commands
make install        # Install (production)
make install-dev    # Install (development + testing)
make test           # Run all 329 tests
make test-cov       # Run tests with coverage
make analyze        # Analyze src/ (table output)
make analyze-json   # Analyze → JSON report
make analyze-md     # Analyze → Markdown report
make analyze-sarif  # Analyze → SARIF report
make baseline       # Save current baseline
make check          # Compare against baseline (CI gate)
make self-analyze   # CRAPQuants on its own code
make clean          # Remove build artifacts
```

---

## Project Structure

```
crapquants/
├── src/crapquants/           # Source code (44 files)
│   ├── cli.py                # CLI entry point
│   ├── core/                 # CRAP formula, AST visitors, coverage, merge
│   ├── frameworks/           # 6 book-derived diagnostic frameworks
│   ├── reporting/            # 5 output formats + glossary
│   ├── baseline/             # Save/compare for regression detection
│   ├── git/                  # Hotspots, change coupling, truck factor, trends
│   ├── security/             # AST security smells + Semgrep
│   ├── ai_explain/           # Optional AI-powered explanations
│   ├── mutation/             # Optional mutmut integration
│   └── utils/                # Logging, path normalization
├── tests/                    # 329 tests (17 test files)
├── docs/                     # Architecture + 7 framework documents
├── .claude/skills/           # Claude Code skill (for AI-assisted workflows)
├── .github/workflows/        # CI pipeline (SHA-pinned actions)
├── pyproject.toml            # Build system (PEP 621)
├── requirements.txt          # Hash-pinned dependencies (Rule #20)
├── requirements-dev.txt      # Dev dependencies (hash-pinned)
├── Makefile                  # Developer workflow commands
├── CONTRIBUTING.md           # Contributor guide
└── LICENSE                   # MIT
```

---

## Dependencies

All MIT/Apache/BSD licensed. All installed with `--only-binary :all:` and hash-pinned.

| Package | Purpose | License |
|---------|---------|---------|
| radon | CC, Halstead, MI metrics | MIT |
| pydantic | Config validation | MIT |
| structlog | Structured logging | MIT |
| rich | Terminal tables and formatting | MIT |
| typer | CLI framework | MIT |
| polars | Data operations | MIT |

**Optional (not required for core functionality):**

| Package | Purpose | When Needed |
|---------|---------|-------------|
| mutmut | Mutation testing | `--level full` |
| semgrep | SAST scanning | `--level full` |
| httpx | AI explain HTTP calls | `--ai-explain` |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, conventions, and workflow.

---

## License

The CRAPQuants **code** is released under the MIT License — see [LICENSE](LICENSE). You are free to use, modify, and redistribute the code, including commercially, provided you retain the copyright notice.

## Name & Branding

While the code is MIT-licensed and freely reusable, **"CRAPQuants" as a project name, together with its associated branding and identity, belongs to Dockyard Techlabs.** The MIT license covers the source code, not the project's name or brand.

This means:
- You **may** fork the code, build on it, and ship your own tool — under your own name.
- You **may** state that your tool is "based on CRAPQuants" or "a fork of CRAPQuants."
- You **may not** redistribute a copy or fork under the name "CRAPQuants" in a way that implies it is the official project, nor use the name to present a derivative as the original.

The canonical project lives at:
- **GitHub:** https://github.com/dockyardtechlabs/crapquants
- **PyPI:** https://pypi.org/project/crapquants/

If you encounter a copy distributed as "CRAPQuants" that strips the copyright notice from [LICENSE](LICENSE), that is a license violation and may be reported to GitHub.

## Provenance

This is the original CRAPQuants project, authored by Tushar Ghorpade / Dockyard Techlabs. Authenticity can be verified through:
- The continuous commit history on the canonical GitHub repository
- Tagged, timestamped releases starting from v1.0.0
- The official PyPI package published by Dockyard Techlabs

## Acknowledgements

The CRAP metric was created by **Alberto Savoia** and **Bob Evans** at Google (2007). CRAPQuants stands on the shoulders of the authors listed in Theoretical Foundations. We are grateful for their contributions to software engineering.

---

*Built by [Dockyard Techlabs](https://github.com/dockyardtechlabs) — Dedicated as Seva to Lord Sri Krishna*
