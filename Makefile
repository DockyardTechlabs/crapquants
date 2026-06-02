# CRAPQuants Makefile
# Standard commands for development, testing, and analysis

.PHONY: help install install-dev test lint analyze analyze-json analyze-md baseline clean

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
CRAPQUANTS := $(VENV)/bin/crapquants

help: ## Show this help message
	@echo "CRAPQuants v1.0.0 — Development Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

$(VENV)/bin/activate:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip

install: $(VENV)/bin/activate ## Install CRAPQuants (production dependencies)
	$(PIP) install --only-binary :all: -r requirements.txt
	$(PIP) install -e .
	@echo ""
	@echo "✅ CRAPQuants installed. Run: crapquants analyze ./src"

install-dev: $(VENV)/bin/activate ## Install CRAPQuants + dev/test dependencies
	$(PIP) install --only-binary :all: -r requirements-dev.txt
	$(PIP) install -e ".[dev]"
	@echo ""
	@echo "✅ CRAPQuants installed (dev mode). Run: make test"

# ---------------------------------------------------------------------------
# Testing
# ---------------------------------------------------------------------------

test: ## Run all tests (329 tests)
	$(PYTHON) -m pytest tests/ -v --tb=short

test-quick: ## Run tests (quiet output)
	$(PYTHON) -m pytest tests/ -q

test-cov: ## Run tests with coverage report
	$(PYTHON) -m pytest tests/ --cov=src/crapquants --cov-report=json --cov-report=term-missing

# ---------------------------------------------------------------------------
# Analysis — run CRAPQuants on your code
# ---------------------------------------------------------------------------

analyze: ## Analyze src/ with table output (default)
	$(CRAPQUANTS) analyze src/ --level standard

analyze-cov: ## Analyze with coverage data (run test-cov first)
	$(CRAPQUANTS) analyze src/ -c coverage.json --level standard

analyze-json: ## Analyze and output JSON report
	$(CRAPQUANTS) analyze src/ -f json -o crapquants_report.json
	@echo "Report: crapquants_report.json"

analyze-md: ## Analyze and output Markdown report
	$(CRAPQUANTS) analyze src/ -f markdown -o crapquants_report.md
	@echo "Report: crapquants_report.md"

analyze-sarif: ## Analyze and output SARIF report (for GitHub Code Scanning)
	$(CRAPQUANTS) analyze src/ -f sarif -o crapquants_report.sarif
	@echo "Report: crapquants_report.sarif"

analyze-gha: ## Analyze with GitHub Actions annotations
	$(CRAPQUANTS) analyze src/ -f github_actions

# ---------------------------------------------------------------------------
# Baseline regression detection
# ---------------------------------------------------------------------------

baseline: ## Save current scores as baseline
	$(CRAPQUANTS) analyze src/ -c coverage.json --save-baseline data/baseline.json
	@echo "Baseline saved to data/baseline.json"

check: ## Compare current scores against baseline (CI gate)
	$(CRAPQUANTS) analyze src/ -c coverage.json --baseline data/baseline.json

# ---------------------------------------------------------------------------
# Self-analysis (CRAPQuants analyzing itself)
# ---------------------------------------------------------------------------

self-analyze: test-cov ## Run CRAPQuants on its own source code
	$(CRAPQUANTS) analyze src/crapquants/ -c coverage.json --level standard

# ---------------------------------------------------------------------------
# Maintenance
# ---------------------------------------------------------------------------

pin: ## Regenerate pinned requirements with hashes (Rule #20)
	$(VENV)/bin/pip-compile requirements.in --generate-hashes --output-file=requirements.txt
	$(VENV)/bin/pip-compile requirements-dev.in --generate-hashes --output-file=requirements-dev.txt

clean: ## Remove build artifacts, caches, and virtual environment
	rm -rf $(VENV) build/ dist/ *.egg-info/
	rm -rf .pytest_cache/ htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -f coverage.json coverage.xml .coverage
	rm -f crapquants_report.*
	@echo "Cleaned."
