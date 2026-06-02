"""Tests for security smell detection (AST-based and Semgrep)."""

import pytest

from crapquants.security.ast_security import scan_source, SecurityFinding
from crapquants.security.semgrep_runner import is_semgrep_available, _parse_semgrep_json
from crapquants.security.security_tags import finding_to_tag, findings_to_tags
from crapquants.frameworks.tags import Severity


class TestASTSecurityEval:
    def test_eval_detected(self):
        source = "x = eval(user_input)\n"
        findings = scan_source(source)
        assert any(f.rule_id == "EVAL_USAGE" for f in findings)

    def test_eval_literal_ignored(self):
        """eval('literal_string') is lower risk — skipped."""
        source = "x = eval('1 + 2')\n"
        findings = scan_source(source)
        assert not any(f.rule_id == "EVAL_USAGE" for f in findings)

    def test_exec_detected(self):
        source = "exec(dynamic_code)\n"
        findings = scan_source(source)
        assert any(f.rule_id == "EXEC_USAGE" for f in findings)


class TestASTSecurityPickle:
    def test_pickle_loads_detected(self):
        source = "import pickle\ndata = pickle.loads(payload)\n"
        findings = scan_source(source)
        assert any(f.rule_id == "PICKLE_DESERIALIZE" for f in findings)

    def test_pickle_load_detected(self):
        source = "import pickle\ndata = pickle.load(open('file', 'rb'))\n"
        findings = scan_source(source)
        assert any(f.rule_id == "PICKLE_DESERIALIZE" for f in findings)

    def test_marshal_detected(self):
        source = "import marshal\ndata = marshal.loads(payload)\n"
        findings = scan_source(source)
        assert any(f.rule_id == "MARSHAL_DESERIALIZE" for f in findings)


class TestASTSecurityShell:
    def test_subprocess_shell_true_detected(self):
        source = "import subprocess\nsubprocess.call('ls', shell=True)\n"
        findings = scan_source(source)
        assert any(f.rule_id == "SHELL_INJECTION" for f in findings)

    def test_subprocess_shell_false_clean(self):
        source = "import subprocess\nsubprocess.call(['ls'], shell=False)\n"
        findings = scan_source(source)
        assert not any(f.rule_id == "SHELL_INJECTION" for f in findings)

    def test_os_system_detected(self):
        source = "import os\nos.system(user_cmd)\n"
        findings = scan_source(source)
        assert any(f.rule_id == "SHELL_INJECTION" for f in findings)

    def test_subprocess_run_shell_true(self):
        source = "import subprocess\nsubprocess.run('echo hello', shell=True)\n"
        findings = scan_source(source)
        assert any(f.rule_id == "SHELL_INJECTION" for f in findings)


class TestASTSecurityYaml:
    def test_yaml_load_unsafe_detected(self):
        source = "import yaml\ndata = yaml.load(content)\n"
        findings = scan_source(source)
        assert any(f.rule_id == "UNSAFE_YAML" for f in findings)

    def test_yaml_safe_load_clean(self):
        """yaml.safe_load is fine — it's a different function name."""
        source = "import yaml\ndata = yaml.safe_load(content)\n"
        findings = scan_source(source)
        assert not any(f.rule_id == "UNSAFE_YAML" for f in findings)

    def test_yaml_load_with_safeloader_clean(self):
        source = "import yaml\ndata = yaml.load(content, Loader=yaml.SafeLoader)\n"
        findings = scan_source(source)
        assert not any(f.rule_id == "UNSAFE_YAML" for f in findings)


class TestASTSecurityHardcodedSecrets:
    def test_password_detected(self):
        source = "password = 'supersecret123'\n"
        findings = scan_source(source)
        assert any(f.rule_id == "HARDCODED_SECRET" for f in findings)

    def test_api_key_detected(self):
        source = "api_key = 'sk-1234567890'\n"
        findings = scan_source(source)
        assert any(f.rule_id == "HARDCODED_SECRET" for f in findings)

    def test_token_detected(self):
        source = "token = 'eyJhbGciOiJIUzI1NiJ9'\n"
        findings = scan_source(source)
        assert any(f.rule_id == "HARDCODED_SECRET" for f in findings)

    def test_empty_password_ignored(self):
        """Empty string assignment is not a secret."""
        source = "password = ''\n"
        findings = scan_source(source)
        assert not any(f.rule_id == "HARDCODED_SECRET" for f in findings)

    def test_non_secret_variable_clean(self):
        source = "username = 'admin'\n"
        findings = scan_source(source)
        assert not any(f.rule_id == "HARDCODED_SECRET" for f in findings)

    def test_env_var_clean(self):
        """Reading from env is the correct pattern."""
        source = "import os\npassword = os.environ.get('DB_PASSWORD')\n"
        findings = scan_source(source)
        assert not any(f.rule_id == "HARDCODED_SECRET" for f in findings)


class TestASTSecurityGeneral:
    def test_clean_code_no_findings(self):
        source = (
            "def safe_func(x):\n"
            "    return x + 1\n"
        )
        findings = scan_source(source)
        assert len(findings) == 0

    def test_syntax_error_returns_empty(self):
        findings = scan_source("def f(:\n")
        assert len(findings) == 0

    def test_finding_has_cwe(self):
        source = "x = eval(user_input)\n"
        findings = scan_source(source)
        eval_finding = [f for f in findings if f.rule_id == "EVAL_USAGE"][0]
        assert eval_finding.cwe == "CWE-95"

    def test_finding_has_line_number(self):
        source = "x = 1\ny = eval(z)\n"
        findings = scan_source(source)
        eval_finding = [f for f in findings if f.rule_id == "EVAL_USAGE"][0]
        assert eval_finding.line == 2

    def test_multiple_findings_in_one_file(self):
        source = (
            "import pickle\n"
            "password = 'secret'\n"
            "data = pickle.loads(payload)\n"
            "x = eval(user_input)\n"
        )
        findings = scan_source(source)
        rule_ids = {f.rule_id for f in findings}
        assert "HARDCODED_SECRET" in rule_ids
        assert "PICKLE_DESERIALIZE" in rule_ids
        assert "EVAL_USAGE" in rule_ids


class TestSemgrepRunner:
    def test_semgrep_availability_check(self):
        """Just verify the check runs without error."""
        result = is_semgrep_available()
        assert isinstance(result, bool)

    def test_parse_semgrep_json_valid(self):
        sample_json = '{"results": [{"check_id": "python.lang.security.eval", "path": "test.py", "start": {"line": 5}, "end": {"line": 5}, "extra": {"severity": "ERROR", "message": "eval is dangerous", "metadata": {"cwe": ["CWE-95"]}}}]}'
        findings = _parse_semgrep_json(sample_json)
        assert len(findings) == 1
        assert "SEMGREP" in findings[0].rule_id
        assert findings[0].line == 5

    def test_parse_semgrep_json_empty(self):
        findings = _parse_semgrep_json('{"results": []}')
        assert len(findings) == 0

    def test_parse_semgrep_json_invalid(self):
        findings = _parse_semgrep_json("not json")
        assert len(findings) == 0


class TestSecurityTags:
    def test_finding_to_tag(self):
        finding = SecurityFinding(
            rule_id="EVAL_USAGE", file_path="test.py",
            line=5, end_line=5, severity="high",
            message="eval() is dangerous", cwe="CWE-95",
        )
        tag = finding_to_tag(finding)
        assert tag.tag_id == "SECURITY_EVAL_USAGE"
        assert tag.severity == Severity.HIGH
        assert "CWE-95" in tag.description
        assert len(tag.recommendations) > 0

    def test_findings_to_tags_batch(self):
        findings = [
            SecurityFinding("EVAL_USAGE", "a.py", 1, 1, "high", "msg1"),
            SecurityFinding("HARDCODED_SECRET", "b.py", 2, 2, "high", "msg2"),
        ]
        tags = findings_to_tags(findings)
        assert len(tags) == 2
        assert tags[0].tag_id == "SECURITY_EVAL_USAGE"
        assert tags[1].tag_id == "SECURITY_HARDCODED_SECRET"

    def test_unknown_rule_gets_default_recs(self):
        finding = SecurityFinding("UNKNOWN_RULE", "x.py", 1, 1, "warning", "msg")
        tag = finding_to_tag(finding)
        assert tag.tag_id == "SECURITY_UNKNOWN_RULE"
        assert tag.severity == Severity.WARNING
