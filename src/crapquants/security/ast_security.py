"""
AST-based security smell detector — Tier 1 (always-on).

Detects basic security anti-patterns via Python AST analysis.
No external dependencies. Runs on all analysis levels (1-4).

Detects:
    - eval() / exec() with non-literal arguments
    - pickle.loads() / pickle.load() (insecure deserialization)
    - Hardcoded secret patterns (password/token/key assigned to string literals)
    - subprocess/os.system with shell=True (shell injection)
    - yaml.load() without SafeLoader (arbitrary code execution)
    - marshal.loads() (insecure deserialization)
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class SecurityFinding:
    """A single security smell finding."""

    rule_id: str
    file_path: str
    line: int
    end_line: int
    severity: str  # "high" | "warning" | "info"
    message: str
    cwe: str | None = None  # CWE reference if applicable


# Secret-indicating variable name patterns
_SECRET_NAMES = frozenset({
    "password", "passwd", "pwd", "secret", "api_key", "apikey",
    "api_secret", "apisecret", "token", "access_token", "auth_token",
    "private_key", "privatekey", "secret_key", "secretkey",
    "db_password", "database_password", "connection_string",
    "aws_secret", "aws_access_key",
})

# Dangerous function calls
_DANGEROUS_CALLS = {
    "eval": ("EVAL_USAGE", "high", "CWE-95",
             "eval() executes arbitrary code. Use ast.literal_eval() for safe parsing."),
    "exec": ("EXEC_USAGE", "high", "CWE-95",
             "exec() executes arbitrary code. Avoid or sandbox strictly."),
}

# Dangerous module.function calls
_DANGEROUS_ATTR_CALLS = {
    ("pickle", "loads"): ("PICKLE_DESERIALIZE", "high", "CWE-502",
                          "pickle.loads() can execute arbitrary code during deserialization. Use json or msgpack."),
    ("pickle", "load"): ("PICKLE_DESERIALIZE", "high", "CWE-502",
                         "pickle.load() can execute arbitrary code during deserialization. Use json or msgpack."),
    ("marshal", "loads"): ("MARSHAL_DESERIALIZE", "high", "CWE-502",
                           "marshal.loads() is not safe for untrusted data."),
    ("marshal", "load"): ("MARSHAL_DESERIALIZE", "high", "CWE-502",
                          "marshal.load() is not safe for untrusted data."),
    ("os", "system"): ("SHELL_INJECTION", "high", "CWE-78",
                       "os.system() is vulnerable to shell injection. Use subprocess with shell=False."),
}


class _SecurityVisitor(ast.NodeVisitor):
    """AST visitor for security smell detection."""

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self.findings: list[SecurityFinding] = []
        self._imports: dict[str, str] = {}  # alias → module name

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.asname or alias.name
            self._imports[name] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            for alias in node.names:
                name = alias.asname or alias.name
                self._imports[name] = f"{node.module}.{alias.name}"
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        self._check_dangerous_call(node)
        self._check_dangerous_attr_call(node)
        self._check_shell_true(node)
        self._check_yaml_unsafe(node)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        self._check_hardcoded_secret(node)
        self.generic_visit(node)

    def _check_dangerous_call(self, node: ast.Call) -> None:
        """Check for eval(), exec() calls."""
        if isinstance(node.func, ast.Name) and node.func.id in _DANGEROUS_CALLS:
            # Skip if argument is a string literal (ast.literal_eval pattern)
            if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                return  # Literal string — low risk

            rule_id, severity, cwe, msg = _DANGEROUS_CALLS[node.func.id]
            self.findings.append(SecurityFinding(
                rule_id=rule_id, file_path=self.file_path,
                line=node.lineno, end_line=node.end_lineno or node.lineno,
                severity=severity, message=msg, cwe=cwe,
            ))

    def _check_dangerous_attr_call(self, node: ast.Call) -> None:
        """Check for pickle.loads(), marshal.loads(), os.system() etc."""
        if not isinstance(node.func, ast.Attribute):
            return

        attr = node.func.attr
        if isinstance(node.func.value, ast.Name):
            module = node.func.value.id
            resolved = self._imports.get(module, module)
            base_module = resolved.split(".")[0]

            key = (base_module, attr)
            if key in _DANGEROUS_ATTR_CALLS:
                rule_id, severity, cwe, msg = _DANGEROUS_ATTR_CALLS[key]
                self.findings.append(SecurityFinding(
                    rule_id=rule_id, file_path=self.file_path,
                    line=node.lineno, end_line=node.end_lineno or node.lineno,
                    severity=severity, message=msg, cwe=cwe,
                ))

    def _check_shell_true(self, node: ast.Call) -> None:
        """Check for subprocess.call/run/Popen with shell=True."""
        if not isinstance(node.func, ast.Attribute):
            return

        attr = node.func.attr
        if attr in ("call", "run", "Popen", "check_output", "check_call"):
            if isinstance(node.func.value, ast.Name):
                module = node.func.value.id
                if module == "subprocess" or self._imports.get(module, "").startswith("subprocess"):
                    for kw in node.keywords:
                        if kw.arg == "shell":
                            if isinstance(kw.value, ast.Constant) and kw.value.value is True:
                                self.findings.append(SecurityFinding(
                                    rule_id="SHELL_INJECTION",
                                    file_path=self.file_path,
                                    line=node.lineno,
                                    end_line=node.end_lineno or node.lineno,
                                    severity="high",
                                    message="subprocess with shell=True is vulnerable to shell injection. Use shell=False with a list of args.",
                                    cwe="CWE-78",
                                ))

    def _check_yaml_unsafe(self, node: ast.Call) -> None:
        """Check for yaml.load() without SafeLoader."""
        if not isinstance(node.func, ast.Attribute):
            return

        if node.func.attr == "load":
            if isinstance(node.func.value, ast.Name):
                module = node.func.value.id
                if module == "yaml" or self._imports.get(module, "").startswith("yaml"):
                    # Check if Loader=SafeLoader is specified
                    has_safe_loader = False
                    for kw in node.keywords:
                        if kw.arg == "Loader":
                            if isinstance(kw.value, ast.Attribute) and "Safe" in kw.value.attr:
                                has_safe_loader = True
                            elif isinstance(kw.value, ast.Name) and "Safe" in kw.value.id:
                                has_safe_loader = True

                    if not has_safe_loader:
                        self.findings.append(SecurityFinding(
                            rule_id="UNSAFE_YAML",
                            file_path=self.file_path,
                            line=node.lineno,
                            end_line=node.end_lineno or node.lineno,
                            severity="high",
                            message="yaml.load() without SafeLoader can execute arbitrary code. Use yaml.safe_load() or yaml.load(data, Loader=SafeLoader).",
                            cwe="CWE-502",
                        ))

    def _check_hardcoded_secret(self, node: ast.Assign) -> None:
        """Check for hardcoded secrets in variable assignments."""
        for target in node.targets:
            name = None
            if isinstance(target, ast.Name):
                name = target.id.lower()
            elif isinstance(target, ast.Attribute):
                name = target.attr.lower()

            if name and name in _SECRET_NAMES:
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    if len(node.value.value) > 0:
                        self.findings.append(SecurityFinding(
                            rule_id="HARDCODED_SECRET",
                            file_path=self.file_path,
                            line=node.lineno,
                            end_line=node.end_lineno or node.lineno,
                            severity="high",
                            message=f"Hardcoded secret in variable '{name}'. Use environment variables or a secrets manager (Rule #10, #21).",
                            cwe="CWE-798",
                        ))


def scan_file(file_path: str | Path) -> list[SecurityFinding]:
    """
    Scan a Python file for security smells using AST analysis.

    Args:
        file_path: Path to Python source file.

    Returns:
        List of SecurityFinding objects.
    """
    file_path = Path(file_path)
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError) as e:
        logger.warning("security_scan_failed", file=str(file_path), error=str(e))
        return []

    visitor = _SecurityVisitor(str(file_path))
    visitor.visit(tree)

    if visitor.findings:
        logger.info("security_findings", file=str(file_path), count=len(visitor.findings))

    return visitor.findings


def scan_source(source: str, file_path: str = "<string>") -> list[SecurityFinding]:
    """
    Scan Python source code string for security smells.

    Args:
        source: Python source code.
        file_path: Virtual file path for reporting.

    Returns:
        List of SecurityFinding objects.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    visitor = _SecurityVisitor(file_path)
    visitor.visit(tree)
    return visitor.findings
