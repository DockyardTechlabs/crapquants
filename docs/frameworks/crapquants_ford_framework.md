# CRAPQuants — Ford Framework (Supplementary)
## Architecture Fitness Functions Extracted from "Building Evolutionary Architectures, 2nd Ed." (Neal Ford, Rebecca Parsons, Patrick Kua, Pramod Sadalage)

> **Purpose:** This supplementary framework fills the **Architecture Fitness Functions** gap. Ford's core insight: architecture characteristics must be protected by automated, executable tests — fitness functions — or they will degrade over time. CRAPQuants itself IS an architectural fitness function for code quality.

> **Core Thesis:** "An evolutionary software architecture supports guided, incremental change across multiple dimensions." Fitness functions are the mechanism that makes the change *guided* rather than random.

> **CRAPQuants Role:** (1) CRAPQuants is itself an architectural fitness function (protecting the "maintainability" dimension). (2) CRAPQuants can enforce additional architectural fitness functions as part of its analysis — layering rules, dependency direction, cycle detection, and coupling constraints.

---

## 1. WHAT IS AN ARCHITECTURAL FITNESS FUNCTION

Ford's definition: An objective function used to evaluate how close a system is to achieving its architectural aims. The architectural equivalent of a unit test, but for structural and "-ility" characteristics rather than business logic.

**Key properties:**
- Fitness functions protect *architectural characteristics* (performance, security, scalability, maintainability, etc.)
- They must be executable and automated wherever possible
- They run in CI/CD pipelines alongside unit tests
- They produce pass/fail or metric results

**Why this matters for CRAPQuants:** The entire CRAPQuants tool is a fitness function for the "maintainability" and "code quality" architectural dimensions. Ford's framework tells us how to categorize, document, and integrate CRAPQuants into the broader architectural governance ecosystem.

---

## 2. FITNESS FUNCTION CATEGORIES

Ford defines six classification axes. CRAPQuants maps to each:

| Axis | Options | CRAPQuants Classification |
|------|---------|--------------------------|
| **Scope** | Atomic vs Holistic | **Both** — per-function CRAP is atomic; PHS (codebase health) is holistic |
| **Cadence** | Triggered vs Continual vs Temporal | **Triggered** — runs on PR/commit in CI pipeline |
| **Result** | Static vs Dynamic | **Static** — fixed threshold (CRAP > 30 = fail) |
| **Invocation** | Automated vs Manual | **Automated** — CI gate, no human needed |
| **Proactivity** | Intentional vs Emergent | **Intentional** — defined at project setup |
| **Coverage** | System-wide vs Per-component | **System-wide** — scans all Python files |

---

## 3. ARCHITECTURAL FITNESS FUNCTIONS CRAPQuants CAN ENFORCE

Beyond its core CRAP scoring, CRAPQuants can enforce these architectural fitness functions via Python AST + import graph analysis:

### 3.1 Layering Rules (Dependency Direction)
**What:** Enforce that module A never imports from module B.
**Example:** `domain/` must never import from `infrastructure/`; `api/` must never import from `database/`.
**Detection:** Parse `import` and `from ... import` statements, build directed graph, check against rules.

```python
# .crapquants_arch.toml
[layering_rules]
forbidden = [
    { from = "domain/*", to = "infrastructure/*" },
    { from = "api/*", to = "database/*" },
    { from = "services/*", to = "views/*" },
]
```

**Tag:** `LAYER_VIOLATION` — Module imports from forbidden layer.

### 3.2 Cycle Detection (No Circular Dependencies)
**What:** Detect circular import dependencies between modules/packages.
**Detection:** Build import graph, run topological sort, report cycles.
**Tag:** `DEPENDENCY_CYCLE` — Circular dependency detected between modules.

### 3.3 Component Coupling Limits
**What:** Enforce maximum fan-out per module.
**Example:** No module should import from more than 10 other internal modules.
**Detection:** Count distinct internal imports per module.

```python
[coupling_limits]
max_fan_out = 10        # No module imports > 10 others
max_fan_in = 15         # No module imported by > 15 others
```

**Tag:** `EXCESSIVE_COUPLING` — Module exceeds coupling threshold.

### 3.4 Package Cohesion
**What:** Detect modules that are used together but live in different packages (or vice versa — modules in same package that are never used together).
**Detection:** Combine import graph with Tornhill change coupling data.
**Tag:** `LOW_COHESION` — Package contains modules with no internal co-usage.

### 3.5 API Surface Control
**What:** Track public API surface growth over time. Prevent interface bloat.
**Detection:** Count public functions/classes per module across git history.
**Tag:** `API_BLOAT` — Public API surface grew by > 20% in analysis window.

---

## 4. THE FITNESS FUNCTION REGISTRY

CRAPQuants v1 should maintain a registry of all active fitness functions with their metadata:

```python
@dataclass
class FitnessFunction:
    """Ford-style fitness function registration."""
    name: str                     # e.g., "crap_threshold"
    dimension: str                # e.g., "maintainability"
    scope: str                    # "atomic" | "holistic"
    cadence: str                  # "triggered" | "continual"
    result_type: str              # "static" | "dynamic"
    threshold: Any                # e.g., 30 for CRAP
    description: str
    
# CRAPQuants built-in fitness functions
BUILTIN_FITNESS_FUNCTIONS = [
    FitnessFunction(
        name="crap_threshold",
        dimension="maintainability",
        scope="atomic",
        cadence="triggered",
        result_type="static",
        threshold=30,
        description="No function should exceed CRAP score of 30",
    ),
    FitnessFunction(
        name="crap_regression",
        dimension="maintainability",
        scope="holistic",
        cadence="triggered",
        result_type="static",
        threshold=0,  # delta must be <= 0
        description="Aggregate CRAP must not increase between baseline and current",
    ),
    FitnessFunction(
        name="no_dependency_cycles",
        dimension="modularity",
        scope="holistic",
        cadence="triggered",
        result_type="static",
        threshold=0,  # zero cycles allowed
        description="No circular dependencies between packages",
    ),
    FitnessFunction(
        name="layer_compliance",
        dimension="architecture",
        scope="holistic",
        cadence="triggered",
        result_type="static",
        threshold=0,  # zero violations
        description="No imports violating layering rules",
    ),
    FitnessFunction(
        name="coupling_limit",
        dimension="modularity",
        scope="atomic",
        cadence="triggered",
        result_type="static",
        threshold=10,
        description="No module imports from more than 10 internal modules",
    ),
]
```

---

## 5. FORD'S KEY PRINCIPLES FOR CRAPQuants

### 5.1 Evolvability as Meta-Characteristic
Ford: "Evolvability is a meta-characteristic — an architectural wrapper that protects all the other architectural characteristics."

**CRAPQuants interpretation:** CRAPQuants protects *maintainability*, which in turn protects *evolvability*. Code with low CRAP is easier to change. The CRAP baseline-regression gate prevents erosion of the maintainability dimension.

### 5.2 Last Responsible Moment
Ford: Defer architectural decisions until the last responsible moment — when you have the most information.

**CRAPQuants interpretation:** Don't enforce all architectural fitness functions from day one. Start with CRAP threshold + regression. Add layering rules and cycle detection as the architecture stabilizes. The fitness function registry is extensible.

### 5.3 Architect for Testability
Ford: "If an architect designs a system that is difficult to test, the system will gradually drift away from its intended architecture."

**CRAPQuants interpretation:** The Feathers Testability Index (TI) directly measures this. Functions with TI < 30 are architecturally problematic because they resist testing, which resists governance.

### 5.4 Bit Rot Prevention
Ford: "An unfortunate decay, often called bit rot, occurs in many organizations. Architects choose particular architectural patterns but those characteristics often accidentally degrade over time."

**CRAPQuants interpretation:** This is exactly what CRAP baseline-regression prevents. The Hunt & Thomas `BROKEN_WINDOW` tag + Tornhill `DETERIORATING` trend tag catch bit rot in progress.

---

## 6. FORD DIAGNOSTIC TAGS

| Tag | Condition | Ford Reference | Recommended Action |
|-----|-----------|---------------|-------------------|
| `LAYER_VIOLATION` | Import crosses forbidden boundary | Ch2: Layering fitness function | Move module or refactor dependency |
| `DEPENDENCY_CYCLE` | Circular import detected | Ch2: Cycle detection | Break cycle via interface/abstraction |
| `EXCESSIVE_COUPLING` | Fan-out > threshold | Ch5: Architectural Quanta | Extract facade or mediator |
| `LOW_COHESION` | Package members never co-used | Ch5: Functional Cohesion | Reorganize package boundaries |
| `API_BLOAT` | Public surface grew > 20% | Ch7: Evolvability | Hide internal methods, extract interface |
| `FITNESS_REGRESSION` | Any fitness function previously passing now fails | Ch2: Fitness Functions | Investigate and fix before merge |

---

## 7. IMPLEMENTATION NOTES

### 7.1 What Can Be Detected Via Python AST
- **Import graph:** `ast.Import`, `ast.ImportFrom` → build directed graph
- **Cycle detection:** Topological sort on import graph (Kahn's algorithm or DFS)
- **Fan-out/fan-in:** Count edges in import graph per node
- **Public API surface:** Count non-`_`-prefixed functions/classes per module
- **Layering rules:** Pattern matching on import paths against rules in `.crapquants_arch.toml`

### 7.2 Configuration File
Architecture fitness functions are project-specific. CRAPQuants reads them from `.crapquants_arch.toml`:

```toml
[fitness_functions]
crap_threshold = 30
max_fan_out = 10
max_fan_in = 15
allow_cycles = false

[layering_rules]
# "from" module pattern must not import "to" module pattern
[[layering_rules.forbidden]]
from = "domain/*"
to = "infrastructure/*"

[[layering_rules.forbidden]]
from = "api/*"
to = "database/*"
```

Per Rule #25: This config file is treated as executable code and must be reviewed with the same scrutiny as source code.

### 7.3 Scope for CRAPQuants v1 vs v2
- **v1:** CRAP threshold, CRAP regression, basic cycle detection, basic layering rules
- **v2:** Full coupling analysis, cohesion scoring, API surface tracking, fitness function registry with custom user-defined functions

---

## 8. CRAPQuants AS A FORD-STYLE FITNESS FUNCTION PLATFORM

The final insight from Ford: **CRAPQuants is not just a metric tool — it's a fitness function platform.** It starts with CRAP scoring but extends to enforce any measurable architectural characteristic:

| Dimension | Fitness Function | Source Framework |
|-----------|-----------------|-----------------|
| Maintainability | CRAP threshold | Core CRAP formula |
| Testability | TI > 30 | Feathers |
| Design Quality | ORS < 60 | Ousterhout |
| Sustainability | PHS > 60 | Hunt & Thomas |
| Behavioral Risk | TBS < 100 | Tornhill |
| Modularity | No cycles, coupling limits | Ford |
| Architecture | Layering compliance | Ford |
| Refactoring Guidance | Smell → refactoring mapping | Fowler |

Each row is a fitness function that CRAPQuants can evaluate and gate on in CI.

---

*Document version: 1.0*
*Source: Building Evolutionary Architectures, 2nd Edition, Neal Ford, Rebecca Parsons, Patrick Kua, Pramod Sadalage (O'Reilly, 2023)*
*Framework for: CRAPQuants — Dockyard Techlabs*
*Dedicated as Seva to Lord Sri Krishna*
