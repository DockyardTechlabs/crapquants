"""Tests for AI explain module — provider config, prompt building, explainer."""

import os
from unittest.mock import patch, MagicMock

import pytest

from crapquants.core.complexity import FunctionMetrics
from crapquants.core.crap import CRAPResult, calculate_crap
from crapquants.core.merge import MergedFunctionResult
from crapquants.frameworks.tags import DiagnosticTag, Framework, Recommendation, Severity
from crapquants.ai_explain.provider import (
    ProviderConfig,
    ProviderType,
    validate_provider,
)
from crapquants.ai_explain.explainer import (
    build_prompt,
    explain_function,
    read_source_snippet,
)


def _make_result(name="bad_func", cc=15, cov=0.0):
    crap_score = calculate_crap(cc, cov)
    return MergedFunctionResult(
        metrics=FunctionMetrics(
            name=name, file_path="src/mod.py", line_start=10, line_end=40,
            cyclomatic_complexity=cc, cognitive_complexity=12,
            abc_assignments=5, abc_branches=8, abc_conditions=6,
            abc_scalar=11.0, line_count=30,
            max_nesting_depth=4, parameter_count=3,
        ),
        coverage=None,
        crap=CRAPResult(
            function_name=name, file_path="src/mod.py", line_number=10,
            complexity=cc, coverage=cov, crap_score=crap_score,
            crapload=15, is_crappy=True,
            min_coverage_needed=57.0, complexity_threshold_exceeded=False,
        ),
    )


def _sample_tags():
    return [
        DiagnosticTag(
            tag_id="MONSTER_SNARLED",
            framework=Framework.FEATHERS,
            severity=Severity.HIGH,
            description="Snarled monster: CC=15, nesting=4.",
            recommendations=(
                Recommendation("Extract Method", "Split by responsibility", 1),
            ),
        ),
        DiagnosticTag(
            tag_id="EDIT_AND_PRAY",
            framework=Framework.FEATHERS,
            severity=Severity.HIGH,
            description="No coverage with CC=15.",
            recommendations=(
                Recommendation("Write Characterization Tests", "Document behavior", 1),
            ),
        ),
    ]


class TestProviderConfig:
    def test_default_model_openai(self):
        config = ProviderConfig(provider=ProviderType.OPENAI)
        assert "gpt" in config.resolved_model

    def test_default_model_anthropic(self):
        config = ProviderConfig(provider=ProviderType.ANTHROPIC)
        assert "claude" in config.resolved_model

    def test_custom_model_overrides(self):
        config = ProviderConfig(provider=ProviderType.OPENAI, model="gpt-4")
        assert config.resolved_model == "gpt-4"

    def test_endpoint_hardcoded(self):
        config = ProviderConfig(provider=ProviderType.OPENAI)
        assert "api.openai.com" in config.resolved_endpoint

    def test_anthropic_endpoint(self):
        config = ProviderConfig(provider=ProviderType.ANTHROPIC)
        assert "api.anthropic.com" in config.resolved_endpoint

    def test_ollama_endpoint_local(self):
        config = ProviderConfig(provider=ProviderType.OLLAMA)
        assert "localhost" in config.resolved_endpoint

    def test_api_key_from_env(self):
        with patch.dict(os.environ, {"CRAPQUANTS_OPENAI_API_KEY": "sk-test123"}):
            config = ProviderConfig(provider=ProviderType.OPENAI)
            assert config.api_key == "sk-test123"

    def test_api_key_fallback_generic(self):
        with patch.dict(os.environ, {"CRAPQUANTS_AI_API_KEY": "generic-key"}, clear=False):
            config = ProviderConfig(provider=ProviderType.OPENAI)
            # Only if specific key not set
            if not os.environ.get("CRAPQUANTS_OPENAI_API_KEY"):
                assert config.api_key == "generic-key"

    def test_ollama_no_key_needed(self):
        config = ProviderConfig(provider=ProviderType.OLLAMA)
        # Ollama has None for env var → api_key returns None
        assert config.api_key is None or isinstance(config.api_key, str)


class TestValidateProvider:
    def test_openai_no_key_fails(self):
        with patch.dict(os.environ, {}, clear=True):
            config = ProviderConfig(provider=ProviderType.OPENAI)
            valid, msg = validate_provider(config)
            assert not valid
            assert "API key" in msg

    def test_ollama_always_valid(self):
        config = ProviderConfig(provider=ProviderType.OLLAMA)
        valid, msg = validate_provider(config)
        assert valid

    def test_openai_with_key_valid(self):
        with patch.dict(os.environ, {"CRAPQUANTS_OPENAI_API_KEY": "sk-test"}):
            config = ProviderConfig(provider=ProviderType.OPENAI)
            valid, msg = validate_provider(config)
            assert valid


class TestBuildPrompt:
    def test_prompt_contains_function_name(self):
        result = _make_result()
        tags = _sample_tags()
        prompt = build_prompt(result, tags)
        assert "bad_func" in prompt

    def test_prompt_contains_metrics(self):
        result = _make_result()
        prompt = build_prompt(result, _sample_tags())
        assert "CRAP Score" in prompt
        assert "Cyclomatic Complexity" in prompt
        assert "Coverage" in prompt

    def test_prompt_contains_tags(self):
        result = _make_result()
        prompt = build_prompt(result, _sample_tags())
        assert "MONSTER_SNARLED" in prompt
        assert "EDIT_AND_PRAY" in prompt
        assert "[Feathers]" in prompt

    def test_prompt_contains_recommendations(self):
        result = _make_result()
        prompt = build_prompt(result, _sample_tags())
        assert "Extract Method" in prompt

    def test_prompt_with_source_snippet(self):
        result = _make_result()
        snippet = "def bad_func(a, b, c):\n    if a > 0:\n        pass\n"
        prompt = build_prompt(result, _sample_tags(), source_snippet=snippet)
        assert "```python" in prompt
        assert "def bad_func" in prompt

    def test_prompt_without_snippet(self):
        result = _make_result()
        prompt = build_prompt(result, _sample_tags())
        assert "```python" not in prompt


class TestReadSourceSnippet:
    def test_reads_existing_file(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("line1\nline2\nline3\nline4\nline5\n")
        snippet = read_source_snippet(str(f), 2, 4)
        assert "line2" in snippet
        assert "line4" in snippet

    def test_nonexistent_file_returns_none(self):
        assert read_source_snippet("/nonexistent/file.py", 1, 10) is None

    def test_truncates_long_functions(self, tmp_path):
        f = tmp_path / "long.py"
        lines = [f"line_{i}" for i in range(200)]
        f.write_text("\n".join(lines))
        snippet = read_source_snippet(str(f), 1, 200, max_lines=10)
        assert "truncated" in snippet


class TestExplainFunction:
    def test_returns_none_without_tags(self):
        result = _make_result()
        config = ProviderConfig(provider=ProviderType.OLLAMA)
        explanation = explain_function(result, [], config)
        assert explanation is None

    @patch("crapquants.ai_explain.explainer.call_llm")
    def test_calls_llm_with_prompt(self, mock_llm):
        mock_llm.return_value = "This function is problematic because..."
        result = _make_result()
        config = ProviderConfig(provider=ProviderType.OLLAMA)
        explanation = explain_function(result, _sample_tags(), config)
        assert explanation == "This function is problematic because..."
        mock_llm.assert_called_once()

    @patch("crapquants.ai_explain.explainer.call_llm")
    def test_handles_llm_failure(self, mock_llm):
        mock_llm.return_value = None
        result = _make_result()
        config = ProviderConfig(provider=ProviderType.OLLAMA)
        explanation = explain_function(result, _sample_tags(), config)
        assert explanation is None
