# CRAPQuants — Ousterhout Framework
## Diagnostic Ruleset Extracted from "A Philosophy of Software Design, 2nd Ed." (John Ousterhout, Stanford)

> **Purpose:** This document defines the quantifiable design principles, red flags, and measurable signals from Ousterhout's book that CRAPQuants will encode as automated detectors. Each entry maps primarily to the `comp(m)` side of the CRAP formula — Ousterhout attacks the *structural complexity* dimension.

> **Core Thesis:** "Complexity is anything related to the structure of a software system that makes it hard to understand and modify the system." Complexity is caused by two things: **dependencies** and **obscurity**. It accumulates incrementally.

> **Ousterhout's Complexity Formula:** `C = Σ(cₚ × tₚ)` — The overall complexity of a system is the complexity of each part `p` weighted by the fraction of time developers spend working on that part. This means CRAPQuants should weight CRAP scores by change frequency.

---

## 1. THE THREE SYMPTOMS OF COMPLEXITY

Ousterhout defines three manifestations of complexity that CRAPQuants can detect:

### 1.1 Change Amplification
A seemingly simple change requires code modifications in many different places.

**CRAPQuants detection:**
- Count functions/classes that must change together (co-change analysis via git history)
- Count files with duplicated logic patterns (DRY violations)
- **Metric:** `change_amplification_factor = count of files typically modified together for a single logical change`

### 1.2 Cognitive Load
How much a developer needs to know to complete a task.

**CRAPQuants detection (static analysis proxies):**
- Parameter count of function (high param count = high cognitive load)
- Number of global/module-level variables accessed
- Number of distinct types/modules imported and used
- Cyclomatic complexity (already in CRAP formula)
- **Metric:** `cognitive_load_proxy = CC + param_count + globals_accessed + distinct_imports_used`

### 1.3 Unknown Unknowns
Not obvious which code must be modified or what information is needed.

**CRAPQuants detection:**
- Functions with side effects not reflected in return type or name
- Missing type annotations (Python-specific)
- Functions with no docstring that have CC > 5
- **Metric:** `unknown_unknowns_risk = (has_side_effects AND no_return_annotation) + (CC > 5 AND no_docstring) + (accesses_globals AND globals_not_documented)`

---

## 2. THE TWO CAUSES OF COMPLEXITY

### 2.1 Dependencies
A piece of code cannot be understood and modified in isolation.

**CRAPQuants detection:**
- Fan-out: count of distinct modules/classes a function calls
- Fan-in: count of callers of a function
- Coupling depth: longest chain of dependencies
- **Metric:** `dependency_score = fan_out + (coupling_depth × 2)`

### 2.2 Obscurity
Important information is not obvious.

**CRAPQuants detection:**
- Generic/vague variable names (single letter, `temp`, `data`, `result`, `val`, `info`, `obj`)
- Missing type annotations on function signatures
- Functions with no docstring
- Inconsistent naming patterns within a module
- **Metric:** `obscurity_score = vague_name_count + missing_annotations + missing_docstrings`

---

## 3. OUSTERHOUT'S RED FLAGS (All 14 — Automated Detection)

These are Ousterhout's own distilled red flags from the book's summary. CRAPQuants encodes each as a detectable signal:

### RF-01: Shallow Module
> "The interface for a class or method isn't much simpler than its implementation."

**Detection:**
```
depth_ratio = implementation_lines / interface_complexity
# interface_complexity = param_count + return_complexity + exception_count
if depth_ratio < 3:
    flag("SHALLOW_MODULE")
```
A function with 5 parameters, 2 return paths, 1 exception = interface_complexity of 8. If the implementation is only 10 lines, depth_ratio = 1.25 → shallow.

**Threshold:** `depth_ratio < 3.0` = Shallow Module red flag

### RF-02: Information Leakage
> "A design decision is reflected in multiple modules."

**Detection:**
- Same magic constants/strings appearing in multiple files
- Same data format parsing logic in multiple functions
- Multiple functions with identical parameter signatures operating on same data
- **Heuristic:** If 2+ functions in different classes share 3+ parameter names/types → likely information leakage

### RF-03: Temporal Decomposition
> "Code structure based on order of operations, not information hiding."

**Detection:**
- Functions named with sequential prefixes: `step1_`, `phase2_`, `first_`, `then_`
- Functions that must be called in specific order without enforcement
- **Heuristic:** If a module has 3+ functions with sequence-implying names → temporal decomposition

### RF-04: Overexposure
> "An API forces callers to be aware of rarely used features to use common features."

**Detection:**
- Functions with many parameters where most have defaults or are rarely used
- Classes with many public methods where usage is concentrated on 2-3 methods
- **Metric:** `overexposure_ratio = total_public_methods / commonly_used_methods`
- **Threshold:** `overexposure_ratio > 4.0` = Overexposure red flag

### RF-05: Pass-Through Method
> "A method does almost nothing except pass its arguments to another method with similar signature."

**Detection:**
- Function body is 1-3 lines
- Function calls exactly one other function
- The called function has similar or identical parameter names
- **Heuristic:** `body_lines <= 3 AND single_call AND param_overlap > 0.7`

### RF-06: Repetition
> "A nontrivial piece of code is repeated over and over."

**Detection:**
- AST subtree similarity detection (structural clone detection)
- Functions with identical control flow patterns
- Copy-paste indicators: identical multi-line blocks across functions
- **Metric:** `repetition_count = number of structurally similar code blocks of 5+ lines`

### RF-07: Special-General Mixture
> "Special-purpose code not cleanly separated from general-purpose code."

**Detection:**
- Functions containing both generic utility logic AND domain-specific conditionals
- `if` branches that handle one specific case alongside general processing
- **Heuristic:** Function has both generic parameter types AND hardcoded domain constants

### RF-08: Conjoined Methods
> "Two methods have so many dependencies that it's hard to understand one without the other."

**Detection:**
- Two functions in same class that share 60%+ of the same instance variables
- Two functions that are always modified in the same commit
- **Metric:** `conjoinment = shared_variables / total_variables_used_by_both`
- **Threshold:** `conjoinment > 0.6` = Conjoined Methods red flag

### RF-09: Comment Repeats Code
> "All information in a comment is immediately obvious from the code."

**Detection (Python-specific):**
- Docstring that merely restates the function name and parameters
- Comments like `# increment counter` above `counter += 1`
- **Heuristic:** High token overlap between comment text and adjacent code tokens

### RF-10: Implementation Documentation Contaminates Interface
> "Interface comment describes implementation details not needed by users."

**Detection:**
- Docstring mentions internal variable names, algorithm details, or performance characteristics not relevant to callers
- **Heuristic:** Docstring contains references to private attributes (`_` prefixed names)

### RF-11: Vague Name
> "Name so imprecise it doesn't convey much useful information."

**Detection:**
- Single-character variable names (outside list comprehensions and loop indices)
- Generic names: `data`, `result`, `temp`, `val`, `info`, `obj`, `item`, `thing`, `stuff`, `handler`, `manager`, `processor`, `helper`, `utils`
- **Metric:** `vague_name_count` per function

### RF-12: Hard to Pick Name
> "It's difficult to come up with a precise and intuitive name."

**Detection (indirect):**
- Functions with overly long names (> 40 chars) — suggests the concept is too diffuse
- Functions with names containing `and` or `or` — suggests multiple responsibilities
- **Heuristic:** `name_contains("_and_") OR name_contains("_or_") OR len(name) > 40`

### RF-13: Hard to Describe
> "Documentation for a variable or method must be long to be complete."

**Detection:**
- Docstring length > 10 lines for a function with < 20 lines of code
- **Metric:** `description_ratio = docstring_lines / code_lines`
- **Threshold:** `description_ratio > 0.5` AND `code_lines < 20` = Hard to Describe red flag

### RF-14: Nonobvious Code
> "Behavior or meaning of code cannot be understood easily."

**Detection (composite):**
- High CC + no comments + no type annotations + vague names
- **Metric:** `nonobvious_score = CC_above_5 + missing_types + missing_comments + vague_names`
- **Threshold:** `nonobvious_score >= 3` = Nonobvious Code red flag

---

## 4. OUSTERHOUT'S DESIGN PRINCIPLES (16 — Mapped to Detection)

### DP-01: Complexity is Incremental
> "You have to sweat the small stuff."

**CRAPQuants role:** Track CRAP score trends over time. Any individual increase may seem small, but accumulated increases signal decay. Baseline-regression mode catches this.

### DP-02: Working Code Isn't Enough
> Strategic vs Tactical programming.

**CRAPQuants role:** Functions with CRAP > 30 that have been modified recently but whose CRAP didn't decrease = tactical programming indicator. Tag: `TACTICAL_CHANGE`.

### DP-03: Make Continual Small Investments
> "Spend 10-20% of development time on design improvements."

**CRAPQuants role:** Track percentage of commits that reduce CRAP scores vs increase them. Healthy ratio: 30%+ of commits should be CRAP-neutral or CRAP-reducing.

### DP-04: Modules Should Be Deep
> "Lot of functionality hidden behind a simple interface."

**Detection:** `depth_ratio` from RF-01. Deep = `depth_ratio > 10`. Shallow = `depth_ratio < 3`.

### DP-05: Interfaces Should Make Common Usage Simple
**Detection:** Overexposure ratio from RF-04.

### DP-06: Simple Interface > Simple Implementation
> "It is more important for a module to have a simple interface than a simple implementation."

**CRAPQuants interpretation:** A function with CC=15 but only 2 parameters and a clear return type is better than a function with CC=3 but 8 parameters. The CRAP score alone doesn't capture this — the Ousterhout Framework adds interface complexity as a modifier.

**Metric:**
```
ousterhout_adjusted_crap = CRAP(f) × (1 + interface_complexity(f) / 20)
# Where interface_complexity = param_count + exception_types + return_complexity
```

### DP-07: General-Purpose Modules Are Deeper
> "Over-specialization may be the single greatest cause of complexity in software."

**Detection:**
- Functions with domain-specific hardcoded values
- Functions that can only be called from one specific context
- **Heuristic:** `fan_in == 1 AND param_count > 3` → overly specialized

### DP-08: Separate General-Purpose and Special-Purpose Code
**Detection:** RF-07 (Special-General Mixture)

### DP-09: Different Layers Should Have Different Abstractions
**Detection:** RF-05 (Pass-Through Methods). If adjacent layers have identical signatures, the abstraction isn't changing between layers.

### DP-10: Pull Complexity Downward
> "It's better for module developers to suffer than module users."

**Detection:**
- Functions that throw/raise exceptions for conditions they could handle internally
- Functions that export configuration parameters instead of computing reasonable defaults
- **Heuristic:** `exception_count > 2 AND most_exceptions_are_input_validation` → pushing complexity upward

### DP-11: Define Errors Out of Existence
> "Exception handling is one of the worst sources of complexity."

**Detection:**
- Count of `try/except` blocks per function
- Count of distinct exception types raised
- Functions where > 40% of code is error handling
- **Metric:** `error_handling_ratio = error_handling_lines / total_lines`
- **Threshold:** `error_handling_ratio > 0.4` = excessive error handling complexity

### DP-12: Design It Twice
**CRAPQuants role:** Not directly detectable, but can be encouraged in output: "This function scores CRAP > 30 — consider designing the interface twice before refactoring."

### DP-13: Comments Should Describe Things Not Obvious from Code
**Detection:** RF-09 (Comment Repeats Code), RF-10 (Implementation Contaminates Interface)

### DP-14: Software Should Be Designed for Ease of Reading
> "Not ease of writing."

**CRAPQuants role:** Core philosophy aligned with Rule #36. High CRAP = hard to read. The CRAP formula itself encodes this principle.

### DP-15: Increments Should Be Abstractions, Not Features
> "The increments of software development should be abstractions, not features."

**Detection:**
- Commits that add features without introducing new abstractions (functions/classes)
- Large functions that grow by appending code rather than extracting abstractions
- **Heuristic (git integration):** If a function's line count increased by > 20% in a commit without new function extraction → feature accumulation without abstraction

### DP-16: Separate What Matters from What Doesn't
**CRAPQuants role:** Weight CRAP scores by usage frequency. A function with CRAP 40 that's called 100 times/day matters more than one with CRAP 80 that hasn't been touched in 2 years.

---

## 5. OUSTERHOUT-SPECIFIC DIAGNOSTIC TAGS

Each high-CRAP function gets tagged with applicable Ousterhout diagnostics:

| Tag | Condition | Ousterhout Reference | Recommended Action |
|-----|-----------|---------------------|-------------------|
| `SHALLOW_MODULE` | depth_ratio < 3.0 | Ch4: Deep vs Shallow | Merge with caller or deepen functionality |
| `INFO_LEAKAGE` | Same logic in 2+ locations | Ch5: Information Leakage | Consolidate into single module |
| `TEMPORAL_DECOMP` | Sequence-named functions | Ch5: Temporal Decomposition | Restructure around information hiding |
| `OVEREXPOSED_API` | overexposure_ratio > 4.0 | Ch4/6: Overexposure | Simplify interface, hide rarely-used features |
| `PASS_THROUGH` | Delegation-only method | Ch7: Pass-Through Methods | Eliminate or merge layers |
| `CONJOINED` | conjoinment > 0.6 | Ch9: Conjoined Methods | Merge methods or extract shared state |
| `CLASSITIS` | Many tiny classes, shallow | Ch4: Classitis | Consolidate into fewer, deeper modules |
| `TACTICAL_TORNADO` | CRAP increased in recent changes | Ch3: Tactical Programming | Invest 10-20% in design improvement |
| `COMPLEXITY_UPWARD` | error_handling_ratio > 0.4 | Ch8/10: Pull Complexity Down | Handle errors internally, define errors out |
| `VAGUE_NAMING` | vague_name_count > 3 per function | Ch14: Choosing Names | Rename with precise, descriptive names |
| `NONOBVIOUS` | nonobvious_score >= 3 | Ch18: Code Should Be Obvious | Add types, comments, and simplify logic |
| `DEEP_MODULE` | depth_ratio > 10.0 AND CRAP < 30 | Ch4: Positive signal | This is good design — flag for recognition |

---

## 6. OUSTERHOUT RISK SCORE (ORS)

A composite score layered on top of CRAP, encoding Ousterhout's design quality assessment:

```python
def ousterhout_risk_score(
    crap: float,
    depth_ratio: float,
    cognitive_load_proxy: int,
    obscurity_score: int,
    red_flag_count: int
) -> float:
    """
    ORS combines CRAP with Ousterhout's structural quality signals.
    
    - depth_ratio: higher is better (deep modules), lower is worse (shallow)
    - cognitive_load_proxy: CC + params + globals + imports
    - obscurity_score: vague names + missing types + missing docs
    - red_flag_count: number of Ousterhout red flags triggered
    """
    # Depth penalty: shallow modules amplify risk
    depth_factor = max(1.0, 5.0 / max(depth_ratio, 0.1))  # 1.0 for deep, up to 5.0 for very shallow
    
    # Obscurity penalty
    obscurity_factor = 1.0 + (obscurity_score / 10.0)
    
    # Red flag penalty
    red_flag_factor = 1.0 + (red_flag_count * 0.15)
    
    return crap * depth_factor * obscurity_factor * red_flag_factor
```

**Interpretation:**
- ORS < 30: Clean design, well-structured
- ORS 30-60: Design concerns, address during next change
- ORS 60-100: Significant design problems, prioritize refactoring
- ORS > 100: Critical — deep structural issues compounding testability problems

---

## 7. TACTICAL vs STRATEGIC INDICATOR

Ousterhout's Ch3 distinction maps to a per-developer or per-codebase metric:

```python
def tactical_strategic_ratio(commits: list) -> float:
    """
    Ratio of commits that increase vs decrease aggregate CRAP.
    
    Returns: float between -1.0 (fully tactical) and +1.0 (fully strategic)
    """
    increasing = sum(1 for c in commits if c.crap_delta > 0)
    decreasing = sum(1 for c in commits if c.crap_delta < 0)
    neutral = sum(1 for c in commits if c.crap_delta == 0)
    total = len(commits)
    
    if total == 0:
        return 0.0
    
    return (decreasing - increasing) / total

# Interpretation:
# > 0.2: Strategic culture (more improving commits than degrading)
# -0.2 to 0.2: Mixed
# < -0.2: Tactical culture (complexity accumulating)
```

---

## 8. MAPPING TO CRAP FORMULA SIDES

| Ousterhout Concept | CRAP Variable | What It Attacks |
|-------------------|---------------|-----------------|
| Deep Modules | `comp(m)` | Deep modules have lower effective CC per exposed interface unit |
| Shallow Modules | `comp(m)` | Shallow modules add CC (interface overhead) without hiding complexity |
| Information Hiding | `comp(m)` | Better hiding = less visible complexity per module |
| Information Leakage | `comp(m)` | Leaked info = duplicated complexity across modules |
| Pass-Through Methods | `comp(m)` | Add CC without adding value |
| Define Errors Out | `comp(m)` | Reduces exception-driven CC branches |
| Pull Complexity Down | `comp(m)` | Concentrates CC in fewer, deeper modules |
| Tactical Programming | `comp(m)` ↑ AND `cov(m)` ↓ | Increases both sides: more complex, less tested |
| Strategic Programming | `comp(m)` ↓ AND `cov(m)` ↑ | Decreases both: simpler, better tested |
| Cognitive Load | diagnostic | Measures *effective* difficulty beyond raw CC |
| Unknown Unknowns | diagnostic | Identifies WHERE bugs will hide |
| Classitis | `comp(m)` | System-level CC increase from interface proliferation |

---

## 9. CROSS-REFERENCE: OUSTERHOUT ↔ FEATHERS

These two frameworks are complementary. Where they intersect:

| Situation | Feathers Says | Ousterhout Says | CRAPQuants Action |
|-----------|--------------|----------------|-------------------|
| Function CC=15, 0% coverage | "Legacy code — write characterization tests" | "Probably a shallow module or tactical programming" | Tag: `EDIT_AND_PRAY` + `TACTICAL_TORNADO`. CRAPload estimates test effort. ORS identifies structural cause. |
| Function CC=5, 100% coverage | "Safe to change" | "Check if it's deep or shallow" | If depth_ratio < 3: `SHALLOW_MODULE` — well-tested but poorly designed. Consider merging. |
| Function CC=25, 90% coverage | "Technically below CRAP threshold" | "Still complex — may have unknown unknowns" | ORS applies obscurity/red-flag penalties. Flag if nonobvious. |
| Monster method, snarled | "Break Out Method Object" | "Pull complexity down, make it deeper" | Combined recommendation: Extract into deep module with clean interface. |
| Class with 50 methods | "Use Sprout Class to avoid making it worse" | "Classitis prevention — make fewer, deeper classes" | Combined: Group methods (Feathers H#1), extract deep modules (Ousterhout DP-04). |

---

## 10. IMPLEMENTATION NOTES FOR CRAPQuants v1

### 10.1 What Can Be Detected Via Python AST
All 14 red flags have at least partial automated detection:
- **Fully automatable (AST only):** RF-01, RF-05, RF-06, RF-11, RF-12, RF-13, RF-14
- **Partially automatable (AST + heuristics):** RF-02, RF-03, RF-04, RF-07, RF-08, RF-09, RF-10
- **Requires git history (v2):** Change amplification, tactical/strategic ratio, DP-15

### 10.2 New Metrics Beyond CRAP
CRAPQuants v1 adds these Ousterhout-derived metrics alongside the base CRAP score:
1. `depth_ratio` — Module depth (implementation lines / interface complexity)
2. `cognitive_load_proxy` — CC + params + globals + imports
3. `obscurity_score` — Vague names + missing types + missing docs
4. `red_flag_count` — Number of Ousterhout red flags triggered
5. `ORS` — Ousterhout Risk Score (composite)
6. `interface_complexity` — Parameter count + exception types + return complexity

### 10.3 Complementarity with Feathers Framework
- Feathers Framework provides: FRS (Feathers Risk Score), TI (Testability Index), CRAPload, Monster classification, dependency-breaking recommendations
- Ousterhout Framework provides: ORS (Ousterhout Risk Score), depth_ratio, red flag detection, tactical/strategic indicators
- **Combined CRAPQuants score:** `CQ_score = max(FRS, ORS)` — take the worse of the two assessments. A function might be fine by Feathers' criteria (testable) but terrible by Ousterhout's (shallow, leaky). CRAPQuants catches both.

---

*Document version: 1.0*
*Source: A Philosophy of Software Design, 2nd Edition, John Ousterhout (Yaknyam Press, Stanford)*
*Framework for: CRAPQuants — Dockyard Techlabs*
*Dedicated as Seva to Lord Sri Krishna*
