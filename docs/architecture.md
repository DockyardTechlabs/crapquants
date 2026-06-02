# CRAPQuants v1 — Architecture Document
## CRAP + Quantitative Connective Tissue for Python Code Quality

> **Project:** CRAPQuants
> **Owner:** Dockyard Techlabs (Tushar Ghorpade)
> **License:** MIT
> **Language:** Python 3.11+
> **Status:** Architecture — Awaiting Approval Before Code
> **Dedicated as Seva to Lord Sri Krishna**

---

## 1. PROJECT IDENTITY

**Name:** CRAPQuants
**Tagline:** "The Python-native CRAP metric tool with book-integrated diagnostics and architectural fitness functions."
**What it is:** An interactive CLI tool that computes CRAP scores for Python codebases and enriches them with diagnostic tags derived from six foundational software engineering books, behavioral code analysis, and architectural fitness functions.
**What it is NOT:** An AI tool. CRAPQuants is pure deterministic static analysis. AI-powered explanations are an optional, provider-agnostic add-on.

---

## 2. THEORETICAL FOUNDATIONS

CRAPQuants is built on the quantitative frameworks extracted from these sources:

| # | Framework | Source | Author(s) | What It Provides |
|---|-----------|--------|-----------|-----------------|
| 1 | Feathers | Working Effectively with Legacy Code | Michael Feathers | FRS (testability risk), TI, CRAPload, 12 dependency-breaking techniques, monster classification |
| 2 | Ousterhout | A Philosophy of Software Design, 2nd Ed | John Ousterhout | ORS (design quality risk), 14 red flags, 16 design principles, depth_ratio |
| 3 | Hunt & Thomas | The Pragmatic Programmer, 20th Anniversary Ed | Andrew Hunt, David Thomas | PHS (codebase health), broken_window_score, entropy_rate, coincidence detector |
| 4 | Fowler | Refactoring: Improving the Design of Existing Code | Martin Fowler, Kent Beck | 22 code smells, 72 named refactorings, smell-to-tag-to-refactoring mapping engine |
| 5 | Tornhill | Your Code as a Crime Scene, 2nd Ed | Adam Tornhill | TBS (behavioral risk), hotspot analysis, change coupling, truck factor, complexity trends |
| 6 | Ford | Building Evolutionary Architectures, 2nd Ed | Neal Ford, Rebecca Parsons, Patrick Kua, Pramod Sadalage | Architectural fitness functions, layering rules, cycle detection |
| 7 | SonarSource | Cognitive Complexity Whitepaper v1.7 | G. Ann Campbell | Cognitive Complexity algorithm (nesting-incremental) |

---

## 3. ANALYSIS LEVELS

Users select their desired depth at startup or via config:

| Level | Name | What Runs | Speed | Dependencies |
|-------|------|-----------|-------|-------------|
| 1 | Quick | CRAP score (CC + coverage) | Fast (~seconds) | radon, coverage.py output |
| 2 | Standard | CRAP + all 6 framework tags + Cognitive Complexity + ABC + Halstead/MI | Medium (~seconds) | radon |
| 3 | Deep | Standard + git-based hotspots, trends, change coupling, truck factor | Slower (~10-30s) | radon + git |
| 4 | Full | Deep + mutation testing + SAST security scanning | Slow (~minutes) | radon + git + mutmut (optional) + semgrep (optional) |

Each framework and metric can also be individually toggled on/off via config or CLI flags.

---

## 4. SCORING ARCHITECTURE

### 4.1 Base Metrics (Per Function)
| Metric | Source | Python Detection |
|--------|--------|-----------------|
| Cyclomatic Complexity (CC) | McCabe/radon | `radon` library |
| Cognitive Complexity (CogC) | SonarSource spec | Custom AST visitor |
| ABC Metric | Custom | Custom AST visitor (Assign/Call/Compare counts) |
| Coverage % | coverage.py | LCOV/JSON/XML output parsing |
| Halstead Metrics | radon | `radon` library |
| Maintainability Index (MI) | radon | `radon` library |
| Lines of Code | radon | `radon` raw metrics |
| Max Nesting Depth | Custom | Custom AST visitor |
| Parameter Count | Custom | `ast.FunctionDef.args` |

### 4.2 CRAP Formula
```
CRAP(f) = CC(f)² × (1 − cov(f)/100)³ + CC(f)
```
Threshold: CRAP > 30 = CRAPpy.

### 4.3 Composite Scores (Per Function)
| Score | Framework | Formula Summary |
|-------|-----------|----------------|
| **FRS** | Feathers | CRAP × monster_multiplier × dependency_depth_factor × responsibility_factor |
| **ORS** | Ousterhout | CRAP × depth_factor × obscurity_factor × red_flag_factor |
| **TBS** | Tornhill | CRAP × activity_weight × trend_weight × knowledge_weight × coupling_weight |

**Final per-function score:** `CQ_score(f) = max(FRS, ORS, TBS)` — worst assessment wins.

### 4.4 Codebase-Level Score
| Score | Framework | What It Measures |
|-------|-----------|-----------------|
| **PHS** | Hunt & Thomas | Pragmatic Health Score (0-100): broken windows, entropy, DRY, orthogonality, coincidence, starter kit |

### 4.5 Refactoring Recommendations
When any diagnostic tag fires, the Fowler Framework maps it to specific named refactorings, prioritized by CRAP impact (CC reducers first, then coverage enablers, then interface simplifiers).

### 4.6 Fitness Functions
Ford Framework: CRAP threshold gate, CRAP regression gate, cycle detection, layering rules, coupling limits — all configurable in `.crapquants_arch.toml`.

---

## 5. PROJECT STRUCTURE

```
crapquants/
├── pyproject.toml                    # Build system (PEP 621), [build-system] explicit
├── README.md                         # Project overview, theoretical foundations, usage
├── LICENSE                           # MIT
├── .crapquants.toml                  # Default project config (sample)
├── .crapquants_arch.toml             # Architectural fitness function rules (sample)
├── requirements.in                   # Source dependencies
├── requirements.txt                  # Hash-pinned (pip-compile --generate-hashes)
│
├── src/
│   └── crapquants/
│       ├── __init__.py               # Version, metadata
│       ├── cli.py                    # Interactive CLI (typer) — entry point
│       ├── config.py                 # Config loading (.crapquants.toml), pydantic models
│       │
│       ├── core/                     # Core metric computation
│       │   ├── __init__.py
│       │   ├── crap.py               # CRAP formula: comp² × (1−cov/100)³ + comp
│       │   ├── coverage_parser.py    # Parse LCOV/JSON/XML from coverage.py
│       │   ├── complexity.py         # CC (via radon), Cognitive Complexity, ABC metric
│       │   ├── halstead.py           # Halstead + MI (via radon)
│       │   ├── ast_visitors.py       # Custom AST visitors (CogC, ABC, nesting, params, etc.)
│       │   └── merge.py              # Join complexity + coverage data (path normalization)
│       │
│       ├── frameworks/               # Book-derived diagnostic frameworks
│       │   ├── __init__.py
│       │   ├── feathers.py           # FRS, TI, CRAPload, monster classification, dep-breaking recs
│       │   ├── ousterhout.py         # ORS, 14 red flags, depth_ratio, cognitive_load_proxy
│       │   ├── hunt_thomas.py        # PHS, broken_window_score, entropy, DRY, coincidence
│       │   ├── fowler.py             # 22 smells, tag→refactoring mapping, priority algorithm
│       │   ├── tornhill.py           # TBS, hotspot analysis, change coupling, truck factor, trends
│       │   └── ford.py               # Fitness function registry, layering rules, cycle detection
│       │
│       ├── git/                      # Git history analysis (Level 3+)
│       │   ├── __init__.py
│       │   ├── log_parser.py         # Parse git log --numstat output
│       │   ├── churn.py              # Change frequency per file
│       │   ├── coupling.py           # Change coupling detection
│       │   ├── trends.py             # Complexity trend over commits
│       │   └── knowledge.py          # Truck factor, knowledge maps
│       │
│       ├── mutation/                  # Mutation testing integration (Level 4, optional)
│       │   ├── __init__.py
│       │   └── mutmut_runner.py      # Invoke mutmut via subprocess, parse results
│       │
│       ├── security/                  # SAST security scanning (Level 4, optional)
│       │   ├── __init__.py
│       │   ├── semgrep_runner.py     # Invoke semgrep via subprocess, parse JSON results
│       │   ├── ast_security.py      # Fallback AST-based security smells (eval/exec/pickle/secrets)
│       │   └── security_tags.py     # SECURITY_SMELL tag definitions + Ford fitness function mapping
│       │
│       ├── ai_explain/               # Optional AI-powered explanations
│       │   ├── __init__.py
│       │   ├── provider.py           # Provider-agnostic interface (OpenAI, Claude, NIMs, Ollama)
│       │   └── explainer.py          # Build prompt from function + tags + refactoring, get explanation
│       │
│       ├── reporting/                # Output formatting
│       │   ├── __init__.py
│       │   ├── table.py              # Human-readable table output (rich)
│       │   ├── json_report.py        # JSON with versioned schema envelope
│       │   ├── markdown_report.py    # Markdown report
│       │   ├── sarif.py              # SARIF 2.1.0 for GitHub Code Scanning
│       │   ├── github_actions.py     # GitHub Actions annotations (::warning, ::error)
│       │   └── pr_comment.py         # PR comment with sticky markers
│       │
│       ├── baseline/                 # Baseline/regression mode
│       │   ├── __init__.py
│       │   ├── save.py               # Save current scores as baseline
│       │   └── compare.py            # Compare current vs baseline, detect regressions
│       │
│       └── utils/                    # Shared utilities
│           ├── __init__.py
│           ├── logging.py            # structlog configuration
│           └── path_normalize.py     # Path normalization (LCOV ↔ filesystem)
│
├── tests/                            # Test suite
│   ├── __init__.py
│   ├── conftest.py                   # Shared fixtures
│   ├── test_crap.py                  # CRAP formula tests
│   ├── test_complexity.py            # CC, CogC, ABC tests
│   ├── test_coverage_parser.py       # Coverage parsing tests
│   ├── test_merge.py                 # Path normalization + merge tests
│   ├── test_feathers.py              # Feathers framework tests
│   ├── test_ousterhout.py            # Ousterhout framework tests
│   ├── test_hunt_thomas.py           # Hunt & Thomas framework tests
│   ├── test_fowler.py                # Fowler framework tests
│   ├── test_tornhill.py              # Tornhill framework tests
│   ├── test_ford.py                  # Ford framework tests
│   ├── test_ast_visitors.py          # AST visitor tests
│   ├── test_baseline.py              # Baseline/regression tests
│   ├── test_security.py              # Security smell detection tests (AST + Semgrep)
│   ├── test_cli.py                   # CLI integration tests
│   └── fixtures/                     # Test fixtures (sample .py files, coverage reports)
│       ├── sample_simple.py
│       ├── sample_monster.py
│       ├── sample_snarled.py
│       ├── sample_security_smells.py  # eval/exec/pickle/hardcoded secret samples
│       ├── coverage_lcov.info
│       └── coverage_json.json
│
├── docs/                             # Documentation
│   ├── architecture.md               # This document
│   ├── frameworks/                   # The 7 framework documents (already created)
│   │   ├── feathers_framework.md
│   │   ├── ousterhout_framework.md
│   │   ├── hunt_thomas_framework.md
│   │   ├── fowler_framework.md
│   │   ├── tornhill_framework.md
│   │   ├── ford_framework.md
│   │   └── cognitive_complexity.md
│   └── user_guide.md                # Usage guide
│
├── logs/                             # Runtime logs (structlog, JSON lines)
│   └── .gitkeep
│
└── data/                             # Baselines, reports
    └── .gitkeep
```

---

## 6. DEPENDENCY STACK

| Package | Purpose | License | Install Method |
|---------|---------|---------|---------------|
| `radon` | CC, Halstead, MI, raw metrics | MIT | `pip install --only-binary :all:` |
| `coverage` | Coverage data (already installed in most projects) | Apache-2.0 | Peer dependency |
| `typer` | Interactive CLI | MIT | `pip install --only-binary :all:` |
| `rich` | Terminal tables, progress bars, syntax highlighting | MIT | `pip install --only-binary :all:` |
| `pydantic` | Config validation, data models | MIT | `pip install --only-binary :all:` |
| `structlog` | Structured logging | MIT | `pip install --only-binary :all:` |
| `polars` | Data joining (coverage + complexity merge) | MIT | `pip install --only-binary :all:` |
| `tomli` | TOML config parsing (Python < 3.11) | MIT | `pip install --only-binary :all:` |

**Optional:**
| Package | Purpose | License | When Needed |
|---------|---------|---------|-------------|
| `mutmut` | Mutation testing (Level 4) | BSD-3 | Only if user selects Level 4 |
| `semgrep` | SAST security scanning (Level 4) | LGPL-2.1 (CLI) | Only if user enables security scanning; system install, not pip |
| `openai` / `anthropic` | AI explanations | MIT / MIT | Only if user enables `--ai-explain` |

**Note on Semgrep:** Semgrep CLI is installed system-wide (`pip install semgrep` or `brew install semgrep`), NOT as a CRAPQuants Python dependency. CRAPQuants invokes it via `subprocess` and parses JSON output. If Semgrep is not installed, CRAPQuants falls back to basic AST-based security smell detection (eval/exec/pickle/hardcoded secrets pattern matching).

**Build system:** `pyproject.toml` with explicit `[build-system]` (Rule #22). Hash-pinned via `pip-compile --generate-hashes` (Rule #20). All installs use `--only-binary :all:` (Rule #19).

---

## 7. DATA FLOW

```
                                    ┌─────────────────────┐
                                    │   User's .py files   │
                                    └─────────┬───────────┘
                                              │
                              ┌───────────────┼───────────────┐
                              │               │               │
                              ▼               ▼               ▼
                    ┌─────────────┐  ┌──────────────┐  ┌────────────┐
                    │   radon     │  │  AST Visitors │  │ coverage   │
                    │ (CC, MI,    │  │ (CogC, ABC,  │  │  .py       │
                    │  Halstead)  │  │  nesting,    │  │ (LCOV/JSON)│
                    └──────┬──────┘  │  params...)  │  └─────┬──────┘
                           │        └──────┬───────┘        │
                           │               │                │
                           └───────────────┼────────────────┘
                                           │
                                    ┌──────▼──────┐
                                    │   merge.py   │  ← Path normalization
                                    │ (join data)  │
                                    └──────┬──────┘
                                           │
                              ┌────────────┼────────────────┐
                              │            │                │
                              ▼            ▼                ▼
                    ┌──────────────┐ ┌──────────┐ ┌──────────────┐
                    │  CRAP Formula │ │Frameworks│ │  Git Analysis│
                    │  (core/crap) │ │(all 6)   │ │  (Level 3+)  │
                    └──────┬───────┘ └────┬─────┘ └──────┬───────┘
                           │              │              │
                           └──────────────┼──────────────┘
                                          │
                                   ┌──────▼──────┐
                                   │  Scoring    │
                                   │ FRS/ORS/TBS │
                                   │ CQ_score    │
                                   │ PHS         │
                                   └──────┬──────┘
                                          │
                              ┌───────────┼───────────┐
                              │           │           │
                              ▼           ▼           ▼
                    ┌──────────┐  ┌────────────┐  ┌─────────┐
                    │ Baseline │  │ Reporting  │  │   AI    │
                    │ Compare  │  │ (table/    │  │ Explain │
                    │ (CI gate)│  │ JSON/SARIF │  │(optional│
                    └──────────┘  │ /MD/GHA)   │  └─────────┘
                                  └────────────┘
```

---

## 8. INTERACTIVE CLI FLOW

```
$ crapquants analyze

🔍 CRAPQuants v1.0.0 — Code Quality Analysis

? Select analysis level:
  ● Quick (CRAP only)
  ○ Standard (CRAP + framework tags)
  ○ Deep (+ git hotspots & trends)
  ○ Full (+ mutation testing)

? Path to analyze: [./src]
? Coverage report path: [./coverage.json]
? Output format:
  ● Table (terminal)
  ○ JSON
  ○ Markdown
  ○ SARIF
  ○ GitHub Actions

? Enable AI explanations? [y/N]: N
? Compare against baseline? [y/N]: y
? Baseline file: [./data/baseline.json]

Analyzing 47 Python files...
████████████████████████████████████ 100%

═══════════════════════════════════════════════════
 CRAPQuants Report — Standard Analysis
═══════════════════════════════════════════════════

 Codebase Health (PHS): 72/100 — Moderate
 Functions analyzed: 312
 Functions above CRAP 30: 8
 Broken Windows: 3
 Entropy trend: STABLE

 Top 5 Hotspots:
 ┌─────────────────────────────────┬──────┬─────┬───────┬──────────────────────────────┐
 │ Function                        │ CRAP │ CQ  │ CogC  │ Tags                          │
 ├─────────────────────────────────┼──────┼─────┼───────┼──────────────────────────────┤
 │ fno_analyzer.score_stock()      │ 78.2 │ 112 │  24   │ [Feathers] MONSTER_SNARLED    │
 │                                 │      │     │       │ [Ousterhout] NONOBVIOUS       │
 │                                 │      │     │       │ [H&T] BROKEN_WINDOW           │
 │                                 │      │     │       │ [Fowler] → Decompose Cond.    │
 ├─────────────────────────────────┼──────┼─────┼───────┼──────────────────────────────┤
 │ ...                             │ ...  │ ... │  ...  │ ...                           │
 └─────────────────────────────────┴──────┴─────┴───────┴──────────────────────────────┘

 Baseline comparison: 2 regressions detected ❌
 CI gate: FAIL
```

---

## 9. CONFIGURATION

### 9.1 `.crapquants.toml` (Project Config)
```toml
[crapquants]
version = "1.0"
analysis_level = "standard"      # quick | standard | deep | full
coverage_report = "coverage.json"
coverage_format = "json"         # json | lcov | xml
source_paths = ["src/"]
exclude_patterns = ["**/test_*", "**/__pycache__/*"]
baseline_path = "data/baseline.json"

[thresholds]
crap = 30                        # CRAP score threshold
cognitive_complexity = 15        # CogC threshold
abc = 30                         # ABC scalar threshold
max_fan_out = 10                 # Import fan-out limit

[frameworks]
feathers = true
ousterhout = true
hunt_thomas = true
fowler = true
tornhill = true                  # Requires git history
ford = true

[git]
analysis_window_days = 365
min_commits_for_trend = 5

[ai_explain]
enabled = false
provider = "anthropic"           # openai | anthropic | nvidia_nims | ollama
model = "claude-sonnet-4-20250514"
# API key injected at runtime via CRAPQUANTS_AI_API_KEY env var (Rule #21)

[reporting]
format = "table"                 # table | json | markdown | sarif | github_actions
show_passing = false             # Only show functions above threshold
top_n = 20                       # Show top N worst functions

[mutation]
enabled = false                  # Level 4 only
test_command = "pytest tests/"

[security]
semgrep_enabled = false          # Level 4 only; requires semgrep installed on system
semgrep_config = "auto"          # Semgrep ruleset: "auto" (recommended), "p/python", or path to custom rules
ast_security_fallback = true     # Always-on AST-based security smell detection (eval/exec/pickle/secrets)
```

### 9.2 `.crapquants_arch.toml` (Architecture Fitness Functions)
```toml
[fitness_functions]
allow_cycles = false
crap_regression_allowed = false

[[layering_rules.forbidden]]
from = "domain/*"
to = "infrastructure/*"

[[layering_rules.forbidden]]
from = "api/*"
to = "database/*"
```

---

## 10. CI/CD INTEGRATION

### GitHub Actions Example
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
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # v4 (SHA-pinned, Rule #51)
        with:
          fetch-depth: 0  # Full history for git analysis
      
      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065  # v5
        with:
          python-version: '3.11'
      
      - name: Install & Run
        run: |
          python -m venv .venv
          source .venv/bin/activate
          pip install --only-binary :all: -r requirements.txt
          pytest --cov=src --cov-report=json
          crapquants analyze --level standard --coverage coverage.json --format github_actions --baseline data/baseline.json
```

---

## 11. LOGGING & AUDIT

Per Rules #2, #24:
- **Structured logging:** `structlog` with JSON output to `logs/crapquants.jsonl`
- **Audit log:** Append-only JSON lines with hash chaining for each analysis run
- **Log fields:** timestamp, analysis_level, files_analyzed, functions_analyzed, crap_above_threshold, phs_score, baseline_comparison_result, git_commit_hash

---

## 12. SECURITY CONSIDERATIONS

| Rule | Implementation |
|------|---------------|
| #10 (No hardcoded secrets) | API keys only via runtime env vars |
| #21 (Secrets at runtime only) | `CRAPQUANTS_AI_API_KEY` read at invocation, never stored |
| #25 (Config as code) | `.crapquants.toml` reviewed with same scrutiny as source |
| #26 (No auth before consent) | AI explain requires explicit `--ai-explain` flag |
| #28 (No endpoint overrides from repo) | AI provider URLs hardcoded in `provider.py`, not configurable from project files |
| SAST integration | Semgrep invoked via subprocess, never as imported library. CRAPQuants does NOT send code to external services — Semgrep runs locally. Semgrep's own network calls (rule fetching for `auto` config) are Semgrep's responsibility, not CRAPQuants'. |

### 12.1 Security Smell Detection (Two-Tier)

**Tier 1 — AST-based (always-on, Levels 1-4):**
Built-in Python AST analysis detects basic security anti-patterns without any external tool:
- `eval()` / `exec()` usage with non-literal arguments
- `pickle.loads()` / `pickle.load()` from untrusted sources
- Hardcoded secret patterns (variables named `password`, `secret`, `api_key`, `token` assigned string literals)
- `subprocess.call()` / `os.system()` with shell=True
- `yaml.load()` without `Loader=SafeLoader`

**Tier 2 — Semgrep (optional, Level 4):**
When Semgrep is installed and enabled, CRAPQuants runs `semgrep --config auto --json --quiet` against source paths and parses the JSON output. Semgrep provides comprehensive SAST coverage (SQL injection, XSS, insecure deserialization, path traversal, etc.) beyond what AST pattern matching can detect.

**Tags produced:** `SECURITY_SMELL_EVAL`, `SECURITY_SMELL_PICKLE`, `SECURITY_SMELL_HARDCODED_SECRET`, `SECURITY_SMELL_SHELL_INJECTION`, `SECURITY_SMELL_UNSAFE_YAML`, plus Semgrep-native findings mapped to `SECURITY_SEMGREP_{rule_id}`.

---

## 13. DEVELOPMENT WORKFLOW

### Build Order (per Rule #59 — step by step)
1. **Phase 1:** `core/` — CRAP formula, coverage parser, AST visitors, merge layer. Test each file.
2. **Phase 2:** `frameworks/` — One framework at a time (Feathers → Ousterhout → Hunt&Thomas → Fowler → Tornhill → Ford). Test each file.
3. **Phase 3:** `reporting/` — Table output first, then JSON, then others. Test each.
4. **Phase 4:** `cli.py` — Interactive CLI with typer. Integration test.
5. **Phase 5:** `baseline/` — Save/compare. Test.
6. **Phase 6:** `git/` — Git log parsing, hotspots, trends. Test.
7. **Phase 7:** `security/` — AST-based security smells first (always-on), then Semgrep integration (optional). Test.
8. **Phase 8:** `ai_explain/` — Optional module. Test with mocks.
9. **Phase 9:** `mutation/` — Optional mutmut integration. Test.
10. **Phase 10:** CI integration, documentation, packaging.

### Virtual Environment (Rule #12)
Every development session uses a dedicated venv. No global installs.

### Testing (Rule #7)
After completing each individual code file, a test run validates correctness. No file moves to next without passing tests.

---

## 14. VERSIONING & ROADMAP

### v1.0 (This Architecture)
- CRAP formula with coverage.py integration
- All 6 framework diagnostic tags
- Cognitive Complexity, ABC, Halstead/MI (via radon)
- Interactive CLI with 4 analysis levels
- Baseline/regression mode
- JSON, table, Markdown, SARIF, GitHub Actions output
- Basic git hotspot analysis
- Architecture fitness functions (cycles, layering)
- AST-based security smell detection (always-on)
- Semgrep SAST integration (optional, Level 4)

### v1.1
- AI-powered explanations (optional, provider-agnostic)
- PR comment output with sticky markers
- Watch mode (re-analyze on file save)

### v2.0
- Full git integration (trends, change coupling, truck factor)
- Mutation testing integration (mutmut)
- Architecture fitness function registry (user-defined)
- API surface tracking
- Package cohesion analysis
- Web dashboard (optional)

---

## 15. APPROVAL CHECKLIST

Before proceeding to code, confirm:

- [ ] Project structure acceptable
- [ ] Dependency stack acceptable (all MIT/Apache/BSD)
- [ ] Analysis levels (1-4) correctly scoped
- [ ] Scoring architecture (FRS/ORS/TBS/PHS/CQ_score) approved
- [ ] CLI flow acceptable
- [ ] Config file format acceptable
- [ ] CI integration approach acceptable
- [ ] Build order (Phase 1-9) acceptable
- [ ] v1 scope vs v1.1/v2 boundary acceptable
- [ ] AI integration approach (optional, runtime-only keys) acceptable
- [ ] Author attribution approach acceptable
- [ ] Interactive CLI confirmed (not non-interactive)

---

*Architecture Document v1.0*
*CRAPQuants — Dockyard Techlabs*
*Dedicated as Seva to Lord Sri Krishna*
