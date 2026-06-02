"""
Custom AST visitors for metrics not available in radon.

Implements:
    1. Cognitive Complexity (SonarSource spec v1.7, G. Ann Campbell)
    2. ABC Metric (Assignments, Branches, Conditions)
    3. Max nesting depth per function
    4. Parameter count per function

All detection is pure Python AST — no external dependencies.
"""

from __future__ import annotations

import ast
import math
from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Data classes for results
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CognitiveComplexityResult:
    """Cognitive Complexity score for a single function."""

    name: str
    line_start: int
    score: int
    max_nesting: int


@dataclass(frozen=True)
class ABCResult:
    """ABC metric for a single function."""

    name: str
    line_start: int
    assignments: int
    branches: int
    conditions: int
    scalar: float
    parameter_count: int


# ---------------------------------------------------------------------------
# Cognitive Complexity Visitor (SonarSource spec v1.7)
# ---------------------------------------------------------------------------

class _CognitiveComplexityVisitor(ast.NodeVisitor):
    """
    Computes Cognitive Complexity per the SonarSource specification v1.7.

    Three rules:
        1. Ignore shorthand (methods, null-coalescing, decorators)
        2. +1 for each break in linear flow
        3. +nesting_level for nested flow-break structures

    Increment types:
        A. Nesting — assessed for nesting control flow inside each other
        B. Structural — control flow that gets nesting increment AND increases nesting
        C. Fundamental — statements not subject to nesting increment
        D. Hybrid — not subject to nesting increment but increases nesting level
    """

    def __init__(self, function_name: str = "") -> None:
        self.score: int = 0
        self.nesting: int = 0
        self.max_nesting: int = 0
        self._function_name: str = function_name  # For recursion detection
        self._decorator_nesting_exempt: set[int] = set()  # Line numbers of nested defs exempt from nesting

    def _increment(self, structural: bool = True) -> None:
        """Add 1 + nesting_level if structural, else just 1."""
        if structural:
            self.score += 1 + self.nesting
        else:
            self.score += 1

    def _visit_with_nesting(self, node: ast.AST) -> None:
        """Visit a node that increases nesting level."""
        self.nesting += 1
        self.max_nesting = max(self.max_nesting, self.nesting)
        self.generic_visit(node)
        self.nesting -= 1

    # --- Structural increments (increment + nesting) ---

    def visit_If(self, node: ast.If) -> None:
        """if: +1 structural, increases nesting."""
        self._increment(structural=True)
        # Visit body with increased nesting
        self.nesting += 1
        self.max_nesting = max(self.max_nesting, self.nesting)
        for child in node.body:
            self.visit(child)
        self.nesting -= 1

        # Handle elif/else chains
        for handler in node.orelse:
            if isinstance(handler, ast.If):
                # elif: +1 hybrid (no nesting penalty, but increases nesting)
                self.score += 1
                self.nesting += 1
                self.max_nesting = max(self.max_nesting, self.nesting)
                for child in handler.body:
                    self.visit(child)
                self.nesting -= 1
                # Process further elif/else in this handler
                for sub in handler.orelse:
                    if isinstance(sub, ast.If):
                        self.score += 1
                        self.nesting += 1
                        self.max_nesting = max(self.max_nesting, self.nesting)
                        for child in sub.body:
                            self.visit(child)
                        self.nesting -= 1
                        self._visit_orelse_chain(sub.orelse)
                    else:
                        self.visit(sub)
            else:
                # else: +1 hybrid (no nesting penalty, increases nesting)
                self.score += 1
                self.nesting += 1
                self.max_nesting = max(self.max_nesting, self.nesting)
                self.visit(handler)
                self.nesting -= 1

    def _visit_orelse_chain(self, orelse: list[ast.stmt]) -> None:
        """Recursively handle elif/else chains."""
        for handler in orelse:
            if isinstance(handler, ast.If):
                self.score += 1
                self.nesting += 1
                self.max_nesting = max(self.max_nesting, self.nesting)
                for child in handler.body:
                    self.visit(child)
                self.nesting -= 1
                self._visit_orelse_chain(handler.orelse)
            else:
                self.score += 1
                self.nesting += 1
                self.max_nesting = max(self.max_nesting, self.nesting)
                self.visit(handler)
                self.nesting -= 1

    def visit_For(self, node: ast.For) -> None:
        """for: +1 structural, increases nesting."""
        self._increment(structural=True)
        self._visit_with_nesting(node)

    def visit_While(self, node: ast.While) -> None:
        """while: +1 structural, increases nesting."""
        self._increment(structural=True)
        self._visit_with_nesting(node)

    def visit_Match(self, node: ast.AST) -> None:
        """match/case (Python 3.10+): +1 structural, increases nesting."""
        self._increment(structural=True)
        self._visit_with_nesting(node)

    # --- Hybrid increments (increment, no nesting penalty, but increases nesting) ---

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        """except/catch: +1 structural, increases nesting."""
        self._increment(structural=True)
        self._visit_with_nesting(node)

    # --- Fundamental increments (no nesting penalty) ---

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        """
        Sequences of logical operators.

        Per SonarSource spec: increment for each *sequence* of like operators,
        not each operator. Mixed operators get +1 per switch.

        a and b and c → +1 (one sequence of 'and')
        a or b or c   → +1 (one sequence of 'or')
        a and b or c  → +2 (switch from 'and' to 'or')
        """
        self.score += 1  # At least one sequence
        # BoolOp in Python AST flattens same-operator chains,
        # so a nested BoolOp means a different operator type
        for value in node.values:
            if isinstance(value, ast.BoolOp) and type(value.op) != type(node.op):
                self.score += 1
            self.visit(value)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        """Ternary operator: +1 structural, increases nesting."""
        self._increment(structural=True)
        self.nesting += 1
        self.max_nesting = max(self.max_nesting, self.nesting)
        self.visit(node.body)
        self.visit(node.test)
        self.visit(node.orelse)
        self.nesting -= 1

    # --- Recursion detection (fundamental increment, no nesting penalty) ---

    def visit_Call(self, node: ast.Call) -> None:
        """
        Recursion: +1 fundamental for direct recursion.

        Per SonarSource spec: 'Cognitive Complexity adds a fundamental increment
        for each method in a recursion cycle, whether direct or indirect.'

        We detect direct recursion (function calls its own name).
        Indirect recursion requires cross-function call graph (v2).
        """
        if self._function_name:
            if isinstance(node.func, ast.Name) and node.func.id == self._function_name:
                self.score += 1  # Fundamental increment, no nesting penalty
        self.generic_visit(node)

    # --- Nesting incrementors (no score, but increase nesting level) ---

    def visit_Lambda(self, node: ast.Lambda) -> None:
        """Lambda: no increment, but increases nesting level."""
        self.nesting += 1
        self.max_nesting = max(self.max_nesting, self.nesting)
        self.generic_visit(node)
        self.nesting -= 1

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """
        Nested function: no structural increment, but increases nesting level.

        Python decorator exception (SonarSource spec Appendix A):
        A function containing ONLY nested def + return is a decorator —
        the inner function starts at nesting=0.

        Any FunctionDef encountered by this visitor IS a nested function.
        The top-level function being analyzed is never visited as a FunctionDef —
        compute_cognitive_complexity iterates its body children directly.
        """
        if node.lineno in self._decorator_nesting_exempt:
            # Decorator exception: don't increment nesting
            self._mark_decorator_children(node)
            self.generic_visit(node)
        else:
            # Normal nested function: increases nesting level
            self.nesting += 1
            self.max_nesting = max(self.max_nesting, self.nesting)
            self._mark_decorator_children(node)
            self.generic_visit(node)
            self.nesting -= 1

    visit_AsyncFunctionDef = visit_FunctionDef

    def _mark_decorator_children(self, node: ast.FunctionDef) -> None:
        """
        Check if a function is a pure decorator (body = only FunctionDef + Return).
        If so, mark its nested FunctionDef children as exempt from nesting increment.
        """
        body = node.body
        is_pure_decorator = all(
            isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Return))
            for stmt in body
        )
        if is_pure_decorator:
            for stmt in body:
                if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    self._decorator_nesting_exempt.add(stmt.lineno)


# ---------------------------------------------------------------------------
# ABC Metric Visitor
# ---------------------------------------------------------------------------

class _ABCVisitor(ast.NodeVisitor):
    """
    Computes the ABC metric for a function.

    A = Assignments: ast.Assign, ast.AugAssign, ast.AnnAssign, ast.NamedExpr
    B = Branches: ast.Call (function/method calls)
    C = Conditions: ast.If, ast.IfExp, ast.BoolOp, ast.Compare, ast.While conditions

    ABC scalar = sqrt(A² + B² + C²)
    """

    def __init__(self) -> None:
        self.assignments: int = 0
        self.branches: int = 0
        self.conditions: int = 0

    def visit_Assign(self, node: ast.Assign) -> None:
        self.assignments += 1
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self.assignments += 1
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is not None:
            self.assignments += 1
        self.generic_visit(node)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        self.assignments += 1
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        self.branches += 1
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        self.conditions += 1
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self.conditions += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        # Each BoolOp with N values has N-1 operators
        self.conditions += len(node.values) - 1
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        self.conditions += len(node.ops)
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self.conditions += 1
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        self.conditions += 1
        self.generic_visit(node)

    @property
    def scalar(self) -> float:
        return round(
            math.sqrt(
                self.assignments ** 2 + self.branches ** 2 + self.conditions ** 2
            ),
            2,
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_cognitive_complexity(source: str) -> list[CognitiveComplexityResult]:
    """
    Compute Cognitive Complexity for all top-level functions in source.

    Args:
        source: Python source code string.

    Returns:
        List of CognitiveComplexityResult, one per function.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        logger.warning("cogc_parse_failed")
        return []

    results: list[CognitiveComplexityResult] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            visitor = _CognitiveComplexityVisitor(function_name=node.name)
            # Mark decorator children before visiting (SonarSource Appendix A)
            visitor._mark_decorator_children(node)
            # Visit function body (not the function itself — SonarSource: no cost of entry)
            for child in node.body:
                visitor.visit(child)

            results.append(
                CognitiveComplexityResult(
                    name=node.name,
                    line_start=node.lineno,
                    score=visitor.score,
                    max_nesting=visitor.max_nesting,
                )
            )

    return results


def compute_abc(source: str) -> list[ABCResult]:
    """
    Compute ABC metric for all top-level functions in source.

    Args:
        source: Python source code string.

    Returns:
        List of ABCResult, one per function.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        logger.warning("abc_parse_failed")
        return []

    results: list[ABCResult] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            visitor = _ABCVisitor()
            visitor.visit(node)

            # Parameter count
            args = node.args
            param_count = (
                len(args.args)
                + len(args.posonlyargs)
                + len(args.kwonlyargs)
                + (1 if args.vararg else 0)
                + (1 if args.kwarg else 0)
            )
            # Exclude 'self' and 'cls'
            if args.args and args.args[0].arg in ("self", "cls"):
                param_count -= 1

            results.append(
                ABCResult(
                    name=node.name,
                    line_start=node.lineno,
                    assignments=visitor.assignments,
                    branches=visitor.branches,
                    conditions=visitor.conditions,
                    scalar=visitor.scalar,
                    parameter_count=param_count,
                )
            )

    return results
