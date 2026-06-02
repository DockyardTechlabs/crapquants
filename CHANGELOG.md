# Changelog

All notable changes to CRAPQuants are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Baseline comparison no longer collapses same-named methods within a single file.
  The lookup key now includes the line number (file:function:line), matching how
  save.py stores entries. Previously, multiple methods sharing a name in one file
  (e.g. visit_Call in two visitor classes) were counted once, undercounting the
  aggregate CRAP and producing a non-zero self-comparison delta.

### Changed
- CI self-analyze step now uses the baseline regression gate: pre-existing CRAPpy
  functions no longer fail the build; only new regressions (new CRAPpy functions or
  an aggregate CRAP increase) cause a failure.

## [1.0.0] — 2026

First public release.

### Added
- Core CRAP metric engine: `CC² × (1 − coverage/100)³ + CC`
- Cyclomatic Complexity, Cognitive Complexity (SonarSource v1.7), and ABC metric via custom AST visitors
- Cognitive Complexity recursion detection and Python decorator exception (SonarSource Appendix A)
- Coverage parsing for coverage.py JSON and LCOV formats
- Six book-derived diagnostic frameworks:
  - Feathers (testability risk, monster classification)
  - Ousterhout (design quality, red flags)
  - Hunt & Thomas (codebase health, broken windows)
  - Fowler (code smells, named refactoring prescriptions)
  - Tornhill (behavioral analysis, hotspots, change coupling, truck factor)
  - Ford (architectural fitness functions)
- Five report formats: terminal table, JSON, Markdown, SARIF 2.1.0, GitHub Actions annotations
- Self-documenting "How to Read This Report" glossary in every format
- Baseline save/compare with hash-chained entries for regression detection
- Git history analysis: churn, hotspots, change coupling, truck factor, complexity trends
- Git-wired behavioral tags (HOTSPOT_ACTIVE, TREND_DETERIORATING, KNOWLEDGE_SILO_CONFIRMED, CHANGE_COUPLED, CHURN_HOTSPOT)
- Two-tier security scanning: always-on AST smells (eval/exec, pickle, hardcoded secrets, shell injection, unsafe YAML) plus optional Semgrep integration
- Optional AI-powered explanations (OpenAI, Anthropic, Nvidia NIMs, Ollama)
- Optional mutation testing via mutmut
- Interactive CLI with 4 analysis levels (quick/standard/deep/full)
- Pragmatic Health Score (PHS) for codebase-level health
- 343 passing tests
- Companion Claude skill (published separately at dockyardtechlabs/crapquants-skill)

[1.0.0]: https://github.com/dockyardtechlabs/crapquants/releases/tag/v1.0.0
