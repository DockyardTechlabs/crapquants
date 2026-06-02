# CRAPQuants — Hunt & Thomas Framework
## Diagnostic Ruleset Extracted from "The Pragmatic Programmer, 20th Anniversary Edition" (Andrew Hunt & David Thomas)

> **Purpose:** This document defines the quantifiable engineering culture principles, tips, and measurable signals from Hunt & Thomas's book that CRAPQuants will encode. Unlike Feathers (cov) and Ousterhout (comp), Hunt & Thomas operate at the **engineering culture layer** — they define the organizational and behavioral discipline that sustains quality over time.

> **Core Thesis:** "Good Design Is Easier to Change Than Bad Design" (ETC — Easier to Change). Every design principle is a special case of ETC.

> **CRAPQuants Role:** Hunt & Thomas provide the *sustainability engine* — the signals that tell you whether your codebase is getting healthier or decaying, whether your team is strategic or tactical, and whether your Broken Windows are being fixed.

---

## 1. THE FIVE FOUNDATIONAL PRINCIPLES

### 1.1 ETC — Easier to Change (Tip 14)
> "A thing is well designed if it adapts to the people who use it. For code, that means it must adapt by changing."

**CRAPQuants signal:** CRAP score delta over time. If CRAP is decreasing, the code is becoming easier to change. If increasing, it's becoming harder.

**Metric:** `etc_trend = slope of CRAP scores over last N commits`
- Negative slope = improving (ETC-aligned)
- Positive slope = degrading (ETC-violated)
- Flat = maintained

### 1.2 DRY — Don't Repeat Yourself (Tip 15)
> "Every piece of knowledge must have a single, unambiguous, authoritative representation within a system."

**Critical clarification from 2nd edition:** "DRY is about the duplication of *knowledge*, of *intent*. It's about expressing the same thing in two different places, possibly in two totally different ways."

**Hunt & Thomas's acid test:** "When some single facet of the code has to change, do you find yourself making that change in multiple places?"

**CRAPQuants detection:**
- Structural clone detection (AST subtree similarity)
- Functions with identical control flow but different data
- Magic constants/strings repeated across files
- Same validation logic in multiple locations
- **NOT DRY violation:** Same code structure but different *knowledge* (e.g., two validators with identical code but validating different domain concepts)

**Metric:** `dry_violation_count` per module
**Threshold:** `dry_violations > 3` per module = DRY red flag

### 1.3 Orthogonality (Tip 17)
> "Eliminate Effects Between Unrelated Things."

Two components are orthogonal if changes in one don't affect the other. Non-orthogonal systems are harder to change because a change in one area causes unexpected ripple effects.

**CRAPQuants detection:**
- Coupling analysis: functions that modify shared mutable state
- Fan-out to unrelated modules
- Functions that combine I/O, business logic, and presentation
- **Metric:** `orthogonality_violations = count of functions that cross 2+ responsibility boundaries`

**Hunt & Thomas's test:** "If I dramatically change the requirements behind a particular function, how many modules are affected?" If the answer is "one," your design is orthogonal.

### 1.4 Broken Windows (Tip 5)
> "Don't Live with Broken Windows."

A broken window — bad design, wrong decision, poor code — left unrepaired instills a sense of abandonment. Neglect accelerates rot faster than any other factor.

**CRAPQuants signal:** Functions with CRAP > 30 that have been above threshold for more than N commits without improvement = "Broken Windows."

**Metric:**
```python
def broken_window_score(function_crap_history: list) -> int:
    """Count consecutive commits where CRAP exceeded threshold."""
    consecutive = 0
    for crap in reversed(function_crap_history):
        if crap > 30:
            consecutive += 1
        else:
            break
    return consecutive
```
- `broken_window_score <= 3`: Recently introduced, likely being addressed
- `broken_window_score 4-10`: Settling in, needs attention
- `broken_window_score > 10`: Established rot — highest priority

### 1.5 Software Entropy / Technical Debt
> "Some folks might call it by the more optimistic term 'technical debt,' with the implied notion that they'll pay it back someday. They probably won't."

**CRAPQuants signal:** Aggregate CRAP score trend across entire codebase. Entropy is the total system complexity growth rate.

**Metric:** `entropy_rate = (total_crap_today - total_crap_30_days_ago) / total_functions`

---

## 2. HUNT & THOMAS TIPS MAPPED TO CRAPQUANTS

### Category A: Design & Structure Tips

| Tip # | Tip Text | CRAPQuants Detection | Signal Type |
|-------|----------|---------------------|-------------|
| 14 | Good Design Is Easier to Change | CRAP trend (slope) | Trend |
| 15 | DRY—Don't Repeat Yourself | Clone detection, repeated constants | Static |
| 16 | Make It Easy to Reuse | Functions with high fan-in = reusable | Static |
| 17 | Eliminate Effects Between Unrelated Things | Cross-boundary coupling analysis | Static |
| 18 | There Are No Final Decisions | Hardcoded dependencies, no interfaces | Static |
| 44 | Decoupled Code Is Easier to Change | Coupling metrics (fan-out, shared state) | Static |
| 45 | Tell, Don't Ask | Getter chains in calling code | Static |
| 46 | Don't Chain Method Calls | Method chain length > 3 | Static |
| 47 | Avoid Global Data | Module-level mutable globals | Static |
| 50 | Don't Hoard State; Pass It Around | Functions with excessive instance state access | Static |

### Category B: Quality & Testing Tips

| Tip # | Tip Text | CRAPQuants Detection | Signal Type |
|-------|----------|---------------------|-------------|
| 5 | Don't Live with Broken Windows | broken_window_score > 10 | Trend |
| 31 | Failing Test Before Fixing Code | Coverage increase on bug-fix commits | Git |
| 62 | Don't Program by Coincidence | Functions with CC > 10, 0% coverage, no docs | Composite |
| 65 | Refactor Early, Refactor Often | Commits that reduce CRAP | Git |
| 66 | Testing Is Not About Finding Bugs | Coverage as design feedback signal | Philosophy |
| 67 | A Test Is the First User of Your Code | Testability Index (from Feathers Framework) | Static |
| 69 | Design to Test | TI > 70 = designed for test | Static |
| 70 | Test Your Software, or Your Users Will | Functions with CRAP > 30, production use | Composite |
| 90 | Test Early, Test Often, Test Automatically | CI coverage gate presence | Infrastructure |
| 91 | Coding Ain't Done 'Til All the Tests Run | Coverage completeness metric | Static |
| 93 | Test State Coverage, Not Code Coverage | Branch coverage vs line coverage ratio | Static |
| 94 | Find Bugs Once | Regression test for each fixed bug | Process |

### Category C: Safety & Paranoia Tips

| Tip # | Tip Text | CRAPQuants Detection | Signal Type |
|-------|----------|---------------------|-------------|
| 36 | You Can't Write Perfect Software | Error handling ratio per function | Static |
| 37 | Design with Contracts | Functions with precondition/postcondition checks | Static |
| 38 | Crash Early | Functions that swallow exceptions silently | Static |
| 39 | Use Assertions to Prevent the Impossible | Assert statement count per complex function | Static |
| 42 | Take Small Steps—Always | Commit size analysis (lines changed per commit) | Git |
| 72 | Keep It Simple and Minimize Attack Surfaces | Public API surface area analysis | Static |

### Category D: Naming & Communication Tips

| Tip # | Tip Text | CRAPQuants Detection | Signal Type |
|-------|----------|---------------------|-------------|
| 13 | Build Documentation In, Don't Bolt It On | Docstring presence ratio | Static |
| 74 | Name Well; Rename When Needed | Vague name count (from Ousterhout RF-11) | Static |

---

## 3. PROGRAMMING BY COINCIDENCE DETECTOR (Tip 62)

Hunt & Thomas's "Programming by Coincidence" is one of the most powerful anti-patterns for CRAPQuants. A function programmed by coincidence has these characteristics:

**Detection heuristic (composite):**
```python
def is_programming_by_coincidence(func) -> bool:
    """
    A function programmed by coincidence:
    - Works, but nobody knows why
    - Has high complexity but no tests
    - Has no documentation explaining intent
    - Has no assertions or contracts
    - May have dead code or redundant calls
    """
    return (
        func.cc > 8
        and func.coverage == 0
        and func.docstring is None
        and func.assert_count == 0
        and func.has_unreachable_code
    )
```

**Tag:** `COINCIDENCE_PROGRAMMING`
**CRAPQuants action:** Flag with highest urgency. These functions are the most dangerous because they appear to work but have no verification of *why* they work. Any change could break them in non-obvious ways.

---

## 4. THE PRAGMATIC STARTER KIT (Topic 51)

Hunt & Thomas define three critical legs of the stool:

### 4.1 Version Control
> "Always Use Version Control" (Tip 28)

**CRAPQuants role:** Git integration for trend analysis. Without version control history, CRAPQuants can only do point-in-time analysis, not trend detection.

### 4.2 Regression Testing
> "Test Early, Test Often, Test Automatically" (Tip 90)

**CRAPQuants role:** Coverage data (from coverage.py) is one half of the CRAP formula. The Starter Kit mandates its existence.

### 4.3 Full Automation
> "Don't Use Manual Procedures" (Tip 95)

**CRAPQuants role:** CRAPQuants itself IS the automation. Running it in CI (baseline + regression mode) automates the quality gate that Hunt & Thomas demand.

**Starter Kit Completeness Score:**
```python
def starter_kit_score(project) -> int:
    """0-100 score for Pragmatic Starter Kit compliance."""
    score = 0
    if project.has_version_control: score += 33
    if project.has_automated_tests: score += 33
    if project.has_ci_pipeline: score += 17
    if project.has_crap_gate: score += 17
    return score
```

---

## 5. REFACTORING TRIGGERS (Topic 40)

Hunt & Thomas list specific conditions that should trigger refactoring. CRAPQuants maps each to a detectable signal:

| Trigger | H&T Description | CRAPQuants Detection |
|---------|----------------|---------------------|
| Duplication | DRY violation discovered | Clone detection, `dry_violation_count > 0` |
| Nonorthogonal design | Something could be more orthogonal | `orthogonality_violations > 0` |
| Outdated knowledge | Requirements drifted, knowledge stale | Function modified frequently but CRAP not improving |
| Usage | Real usage patterns differ from planned | Function fan-in patterns changed |
| Performance | Need to move functionality for optimization | Performance profiling data (external) |
| Tests pass | You have a green test suite as safety net | `coverage > 80%` enables safe refactoring |

**CRAPQuants trigger rule:** When a function has `coverage >= 70%` AND any of the above triggers detected → recommend refactoring with specific Fowler technique (from Fowler Framework, pending).

---

## 6. TRACER BULLET DEVELOPMENT (Topic 12, Tip 20)

> "Use Tracer Bullets to Find the Target."

Tracer bullets are not prototypes — they are real, lean, end-to-end implementations. They let you see if you're aiming at the right target.

**CRAPQuants analogy:** The baseline-regression workflow IS a tracer bullet for code quality. You establish a baseline, then each commit either hits or misses the quality target. CRAPQuants provides the visible tracer showing where your changes land.

**Metric:** `tracer_accuracy = percentage of commits that maintain or improve CRAP baseline`

---

## 7. HUNT & THOMAS DIAGNOSTIC TAGS

| Tag | Condition | H&T Reference | Recommended Action |
|-----|-----------|--------------|-------------------|
| `BROKEN_WINDOW` | CRAP > 30 for 10+ consecutive commits | Tip 5: Don't Live with Broken Windows | Prioritize — rot is spreading |
| `DRY_VIOLATION` | Structural clones detected | Tip 15: DRY | Extract shared abstraction |
| `NON_ORTHOGONAL` | Function crosses 2+ responsibility boundaries | Tip 17: Orthogonality | Separate concerns |
| `COINCIDENCE_CODE` | High CC, 0% coverage, no docs, no assertions | Tip 62: Don't Program by Coincidence | Write characterization tests immediately |
| `ENTROPY_RISING` | Codebase aggregate CRAP increasing over time | Software Entropy | Apply Broken Windows theory — fix worst offenders |
| `REFACTOR_READY` | Coverage >= 70% AND design trigger detected | Tip 65: Refactor Early, Often | Apply specific refactoring (Fowler catalog) |
| `NO_SAFETY_NET` | Function changed frequently but has 0% coverage | Tip 70: Test or Users Will | Write tests before next change |
| `GLOBAL_COUPLING` | Function accesses 3+ module-level globals | Tip 47: Avoid Global Data | Encapsulate globals, parameterize |
| `CHAIN_VIOLATION` | Method chain length > 3 | Tip 46: Don't Chain | Apply Tell, Don't Ask |
| `SWALLOWED_EXCEPTION` | Empty except/catch blocks | Tip 38: Crash Early | Handle or propagate, don't swallow |
| `NO_CONTRACTS` | Complex function (CC > 10) with no assertions | Tip 37: Design with Contracts | Add precondition/postcondition checks |
| `STARTER_KIT_MISSING` | No tests OR no CI OR no coverage gate | Tip 90: Starter Kit | Establish the three-legged stool |

---

## 8. CODEBASE HEALTH DASHBOARD (Hunt & Thomas Metrics)

CRAPQuants v1 should produce a codebase-level health report using Hunt & Thomas indicators:

```python
@dataclass
class CodebaseHealth:
    """Hunt & Thomas Codebase Health Report."""
    
    # Broken Windows
    broken_window_count: int          # Functions with CRAP > 30 for 10+ commits
    broken_window_percentage: float   # broken_window_count / total_functions
    
    # Entropy
    entropy_rate: float               # CRAP growth rate over last 30 days
    entropy_direction: str            # "improving" | "stable" | "degrading"
    
    # DRY
    dry_violation_count: int          # Structural clones detected
    dry_violation_ratio: float        # violations / total_functions
    
    # Orthogonality
    non_orthogonal_count: int         # Functions crossing responsibility boundaries
    average_coupling: float           # Mean fan-out per function
    
    # Coincidence
    coincidence_count: int            # Functions matching coincidence pattern
    
    # Starter Kit
    starter_kit_score: int            # 0-100 compliance score
    
    # ETC Trend
    etc_trend: float                  # Slope of CRAP over time (negative = good)
    
    # Overall
    pragmatic_health_score: float     # 0-100 composite
```

**Pragmatic Health Score calculation:**
```python
def pragmatic_health_score(health: CodebaseHealth) -> float:
    score = 100.0
    score -= health.broken_window_percentage * 30  # Heavy penalty
    score -= max(0, health.entropy_rate * 100)     # Penalty for rising entropy
    score -= health.dry_violation_ratio * 20       # DRY violations
    score -= min(20, health.coincidence_count * 5) # Coincidence code
    score -= (100 - health.starter_kit_score) * 0.2  # Starter kit completeness
    return max(0, min(100, score))
```

---

## 9. MAPPING TO CRAP FORMULA SIDES

| Hunt & Thomas Concept | CRAP Variable | What It Attacks |
|----------------------|---------------|-----------------|
| ETC (Easier to Change) | Both `comp(m)` AND `cov(m)` | The meta-principle — all improvements serve ETC |
| DRY | `comp(m)` | Duplication = multiplied complexity |
| Orthogonality | `comp(m)` | Non-orthogonal code = amplified change impact |
| Broken Windows | Neither directly | Cultural decay signal — predicts future CRAP increase |
| Tracer Bullets | `cov(m)` | End-to-end coverage as quality tracer |
| Design by Contract | `cov(m)` | Assertions ARE implicit tests |
| Crash Early | `comp(m)` | Reduces error-handling complexity |
| Refactoring | `comp(m)` ↓ | Directly reduces cyclomatic complexity |
| Programming by Coincidence | Both | Worst case: high `comp(m)`, zero `cov(m)` |
| Starter Kit | `cov(m)` | Establishes the infrastructure for coverage |

---

## 10. CROSS-REFERENCE: ALL THREE FRAMEWORKS

| Situation | Feathers Says | Ousterhout Says | Hunt & Thomas Says | CRAPQuants Combined |
|-----------|--------------|----------------|-------------------|-------------------|
| CRAP > 30, 0% coverage, 15+ commits old | "Legacy code — characterize" | "Tactical programming" | "Broken Window — fix NOW" | Tag: `BROKEN_WINDOW` + `EDIT_AND_PRAY` + `TACTICAL_TORNADO`. Priority: CRITICAL |
| CRAP = 5, 100% coverage, but DRY violation | "Safe to change" | "Check if shallow" | "Fix the DRY violation" | Tag: `DRY_VIOLATION`. Low CRAP doesn't excuse duplicated knowledge. |
| CRAP = 80, 0% coverage, no docs, no assertions | "Monster method, break deps" | "Nonobvious, high cognitive load" | "Programming by Coincidence" | Tag: `COINCIDENCE_CODE` + `MONSTER_SNARLED` + `NONOBVIOUS`. CRAPload + dependency-breaking recommendation. |
| Coverage increasing, CRAP decreasing over time | "Getting under test" | "Strategic programming" | "ETC trend positive, no Broken Windows" | All green. Pragmatic Health Score rising. |
| New function added with CC=20, no tests | "Sprout Method" | "Shallow if interface is complex" | "Coding ain't done til tests run" | Tag: `NO_SAFETY_NET`. Block merge in CI. |

---

## 11. IMPLEMENTATION NOTES FOR CRAPQuants v1

### 11.1 Static Analysis (Python AST)
- DRY: Structural clone detection via AST subtree hashing
- Orthogonality: Cross-boundary coupling via import/call analysis
- Coincidence: Composite detector (CC + coverage + docs + assertions)
- Globals: `ast.Global` and module-level `ast.Name` resolution
- Method chains: `ast.Attribute` chain length analysis
- Swallowed exceptions: Empty `ast.ExceptHandler` bodies
- Assertions: `ast.Assert` count per function

### 11.2 Git Integration (v1 stretch / v2)
- Broken Windows: CRAP history per function over commits
- Entropy: Aggregate CRAP trend over time
- ETC trend: CRAP slope calculation
- Refactoring triggers: Change frequency + CRAP delta correlation
- Small steps: Commit size analysis

### 11.3 New Metrics Beyond CRAP
1. `broken_window_score` — Consecutive commits above CRAP threshold
2. `dry_violation_count` — Structural clones per module
3. `orthogonality_violations` — Cross-boundary coupling count
4. `coincidence_score` — Composite anti-pattern detector
5. `entropy_rate` — Codebase CRAP growth rate
6. `starter_kit_score` — Pragmatic Starter Kit compliance
7. `pragmatic_health_score` — Composite codebase health (0-100)

### 11.4 Combined CRAPQuants v1 Score Architecture
The three frameworks produce independent scores:
- **FRS** (Feathers Risk Score): Testability-weighted CRAP
- **ORS** (Ousterhout Risk Score): Design-quality-weighted CRAP
- **PHS** (Pragmatic Health Score): Codebase-level sustainability

**Per-function score:** `CQ_function = max(FRS, ORS)`
**Per-codebase score:** `CQ_codebase = PHS`

The fourth framework (Fowler) will add the **refactoring recommendation engine** — mapping detected problems to specific named transformations.

---

*Document version: 1.0*
*Source: The Pragmatic Programmer, 20th Anniversary Edition, Andrew Hunt & David Thomas (Addison-Wesley, 2019)*
*Framework for: CRAPQuants — Dockyard Techlabs*
*Dedicated as Seva to Lord Sri Krishna*
