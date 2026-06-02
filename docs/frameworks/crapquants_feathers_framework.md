# CRAPQuants — Feathers Framework
## Diagnostic Ruleset Extracted from "Working Effectively with Legacy Code" (Michael C. Feathers, 2005)

> **Purpose:** This document defines the quantifiable anti-patterns, diagnostic heuristics, and measurable signals from Feathers' book that CRAPQuants will encode as automated detectors. Each entry maps to the `cov(m)` side of the CRAP formula — Feathers attacks the *testability* dimension.

> **Core Thesis (Feathers' Definition):** "Legacy code is simply code without tests. Code without tests is bad code. It doesn't matter how well written it is; it doesn't matter how pretty or object-oriented or well-encapsulated it is."

---

## 1. FOUNDATIONAL CONCEPTS

### 1.1 The Legacy Code Change Algorithm
Feathers' five-step algorithm is the operational backbone. CRAPQuants maps to steps 1-3:

| Step | Feathers' Name | CRAPQuants Role |
|------|---------------|-----------------|
| 1 | Identify change points | CRAP score > threshold identifies these |
| 2 | Find test points | Effect analysis + pinch point detection |
| 3 | Break dependencies | Dependency-breaking technique recommendation |
| 4 | Write tests | CRAPload calculates minimum test effort |
| 5 | Make changes and refactor | CRAP delta tracks improvement |

### 1.2 The Legacy Code Dilemma
> "When we change code, we should have tests in place. To put tests in place, we often have to change code."

**CRAPQuants signal:** Functions with CRAP > 30 AND high dependency count = "Dilemma Zone." The tool should flag these specially — they need dependency-breaking before testing is possible.

### 1.3 Edit and Pray vs. Cover and Modify
Feathers defines two change strategies:
- **Edit and Pray:** Change code, manually poke around to verify. No safety net.
- **Cover and Modify:** Put tests around code first, then change with feedback.

**CRAPQuants signal:** Any function with `cov(m) = 0%` AND `comp(m) > 5` is in "Edit and Pray" territory. The tool should label this explicitly.

---

## 2. DETECTABLE ANTI-PATTERNS (Static Analysis)

### 2.1 Monster Methods
Feathers categorizes large, complex methods into two varieties:

#### 2.1.1 Bulleted Methods
- **Definition:** Methods with nearly no indentation — a sequence of code chunks like a bulleted list.
- **Detection heuristic:** Low max nesting depth BUT high line count AND high CC.
- **CRAPQuants signal:** `line_count > 50 AND max_nesting_depth <= 3 AND CC > 10`
- **Recommended action:** Extract Method per chunk (Fowler). Relatively safer because low nesting means sections are more independent.

#### 2.1.2 Snarled Methods
- **Definition:** Methods dominated by a single large, indented section with deep nesting.
- **Detection heuristic:** High max nesting depth AND high CC.
- **CRAPQuants signal:** `max_nesting_depth >= 4 AND CC > 10`
- **Recommended action:** Introduce Sensing Variable first, then Extract Method. Higher risk than Bulleted because of interleaved state.
- **Feathers' test:** "Try to line up the blocks in a long method. If you start to feel vertigo, you've run into a snarled method."

#### 2.1.3 Detection Formula for Monster Classification
```
if CC > 10:
    if max_nesting_depth >= 4:
        monster_type = "SNARLED"
        risk_multiplier = 1.5  # Snarled is harder to decompose safely
    elif line_count > 50:
        monster_type = "BULLETED"
        risk_multiplier = 1.2
    else:
        monster_type = "COMPLEX_BUT_COMPACT"
        risk_multiplier = 1.0
```

### 2.2 Class Too Big — Responsibility Detection Heuristics
Feathers provides seven heuristics for detecting over-responsibility. CRAPQuants can automate four of them:

#### Heuristic #1: Method Grouping
- **Detection:** Cluster methods by name similarity (prefix/suffix analysis).
- **Signal:** If a class has 3+ method name clusters with distinct prefixes, it likely has multiple responsibilities.
- **Example:** Methods `validate_*`, `format_*`, `persist_*` in one class = 3 responsibilities.

#### Heuristic #2: Hidden Methods (Private Method Proliferation)
- **Detection:** Count private/protected methods vs public methods.
- **Signal:** `private_method_count > 2 * public_method_count` suggests "another class dying to get out."
- **Feathers' insight:** "If you have the urge to test a private method, the method shouldn't be private; it is part of a separate responsibility."

#### Heuristic #4: Internal Relationships (Feature Sketches)
- **Detection:** Build a graph of which methods access which instance variables. Look for disconnected clusters.
- **Signal:** If the method-variable graph has 2+ connected components, each component is a candidate for extraction.
- **CRAPQuants implementation:** Parse AST, build `method → {instance_variables_used}` map, find clusters.

#### Heuristic #6: Scratch Refactoring
- Not automatable, but CRAPQuants can suggest: "This class has N responsibilities detected — consider scratch refactoring to explore decomposition."

### 2.3 The Sensing and Separation Problem
Feathers defines two reasons to break dependencies:
1. **Sensing:** Can't access values the code computes (effects are hidden).
2. **Separation:** Can't even get the code into a test harness to run.

**CRAPQuants detection:**
- **Sensing problem:** Function modifies state through side effects (writes to globals, files, databases, network) but returns `None`/`void`. Detection: `return_type == None AND has_side_effects == True`
- **Separation problem:** Function's constructor/initialization requires external dependencies (database connections, network sockets, hardware). Detection: Constructor parameter analysis — count non-primitive, non-stdlib parameters.

---

## 3. QUANTIFIABLE METRICS

### 3.1 CRAPLoad — Minimum Effort to De-CRAP
From the original Crap4J FAQ, adapted for Python:

```python
def calculate_crapload(crap_score: float, complexity: int, coverage: float, threshold: float = 30.0) -> int:
    """
    CRAPload = minimum work units to get below threshold.
    
    For every point of uncovered complexity: +1 test needed.
    For every unit of complexity over threshold: +1 extract-method refactoring.
    """
    if crap_score < threshold:
        return 0
    
    crapload = 0
    # Tests needed to cover uncovered paths
    crapload += int(complexity * (1.0 - coverage))
    # Refactorings needed to reduce complexity below threshold
    crapload += int(complexity / threshold)
    
    return crapload
```

### 3.2 Complexity-Coverage Threshold Table (from Crap4J)
Functions exceeding these coverage requirements for their CC are flagged:

| Cyclomatic Complexity | Min Coverage to Stay Below CRAP 30 |
|-----------------------|------------------------------------|
| 0 – 5                | 0%                                 |
| 6 – 10               | 42%                                |
| 11 – 15              | 57%                                |
| 16 – 20              | 71%                                |
| 21 – 25              | 80%                                |
| 26 – 30              | 100%                               |
| 31+                   | **Refactor required** — no amount of coverage helps |

### 3.3 Effect Propagation Depth
Feathers' Effect Sketches track how changes propagate through a system.

**CRAPQuants metric:** For a function `f`, count the transitive closure of functions that could be affected by changes to `f`. This is the "effect radius."
- `effect_radius <= 3`: Low propagation risk
- `effect_radius 4-8`: Medium — needs pinch point testing
- `effect_radius > 8`: High — changes here are dangerous

### 3.4 Dependency Depth for Testability
Count the number of dependencies that must be broken before a function can be tested in isolation.

```
dependency_depth(f) = count of non-stdlib, non-primitive parameters 
                    + count of global/module-level state accessed
                    + count of I/O operations (file, network, database)
```

- `dependency_depth = 0`: Immediately testable
- `dependency_depth 1-3`: Light dependency breaking needed
- `dependency_depth 4+`: Significant dependency breaking needed — flag as "Separation Problem"

---

## 4. DIAGNOSTIC TAGS (Feathers-Derived)

Each high-CRAP function gets tagged with applicable Feathers diagnostics:

| Tag | Condition | Feathers Reference | Recommended Action |
|-----|-----------|-------------------|-------------------|
| `LEGACY_DILEMMA` | CRAP > 30 AND dependency_depth >= 4 | Ch2: Legacy Code Dilemma | Break dependencies first (Ch25 catalog) |
| `EDIT_AND_PRAY` | cov = 0% AND CC > 5 | Ch2: Working with Feedback | Write characterization tests (Ch13) |
| `MONSTER_BULLETED` | CC > 10 AND nesting <= 3 AND lines > 50 | Ch22: Varieties of Monsters | Extract Method per chunk |
| `MONSTER_SNARLED` | CC > 10 AND nesting >= 4 | Ch22: Varieties of Monsters | Introduce Sensing Variable, then Extract |
| `HIDDEN_CLASS` | private_methods > 2 × public_methods | Ch20: Heuristic #2 | Extract class for private method cluster |
| `MULTI_RESPONSIBILITY` | 3+ method name clusters detected | Ch20: Heuristic #1 | Group methods, extract per responsibility |
| `SENSING_PROBLEM` | returns None AND has_side_effects | Ch3: Sensing and Separation | Introduce fake/mock collaborator |
| `SEPARATION_PROBLEM` | constructor needs external deps | Ch3: Sensing and Separation | Parameterize Constructor or Extract Interface |
| `PINCH_POINT_CANDIDATE` | effect_radius > 5 AND is_public | Ch12: Interception Points | Test at this natural encapsulation boundary |
| `CHARACTERIZATION_NEEDED` | cov = 0% AND CRAP > 30 | Ch13: Characterization Tests | Write tests documenting actual behavior first |
| `REFACTOR_MANDATORY` | CC >= 31 | Crap4J threshold table | No amount of testing helps — must reduce complexity |
| `FEATURE_ENVY` | method accesses more external state than internal | Ch20: Heuristic #4 | Move method to the class it envies |

---

## 5. DEPENDENCY-BREAKING TECHNIQUE RECOMMENDATIONS

Feathers' Ch25 catalogs 24 dependency-breaking techniques. CRAPQuants maps detectable patterns to recommended techniques:

### 5.1 Python-Applicable Techniques (from the 24 in catalog)

| Technique | Feathers Page | Python Equivalent | When to Recommend |
|-----------|--------------|-------------------|-------------------|
| Adapt Parameter | 326 | Create a wrapper/adapter class | Parameter type is hard to instantiate in tests |
| Break Out Method Object | 330 | Extract class from long method | Monster method uses instance data extensively |
| Encapsulate Global References | 339 | Wrap module-level globals in a class | Function accesses module-level mutable state |
| Expose Static Method | 345 | Make method `@staticmethod` | Method doesn't use `self` but is bound to class |
| Extract and Override Call | 348 | Extract method, override in test subclass | Method makes hard-to-test external call |
| Extract Interface | 362 | Define `Protocol` (PEP 544) or ABC | Constructor depends on concrete external class |
| Introduce Instance Delegator | 369 | Create instance method delegating to class method | Static methods block testing |
| Parameterize Constructor | 379 | Add optional parameter with default | Constructor creates its own hard dependencies |
| Parameterize Method | 383 | Add parameter instead of using global | Method reads global/module state directly |
| Subclass and Override Method | 401 | Create test subclass overriding specific method | Need to neutralize one specific behavior for testing |
| Primitivize Parameter | 385 | Pass primitive data instead of complex object | Complex parameter object is hard to create |
| Replace Global Reference with Getter | 399 | Replace direct global access with getter method | Global access scattered through method |

### 5.2 Recommendation Logic
```
if tag == "SEPARATION_PROBLEM":
    if constructor_creates_dependencies:
        recommend("Parameterize Constructor")
    elif depends_on_concrete_class:
        recommend("Extract Interface / Protocol")
    
if tag == "SENSING_PROBLEM":
    if modifies_global_state:
        recommend("Encapsulate Global References")
    elif returns_none_but_has_effects:
        recommend("Extract and Override Call")

if tag == "MONSTER_SNARLED":
    if uses_instance_data:
        recommend("Break Out Method Object")
    else:
        recommend("Expose Static Method, then Extract")

if tag == "MONSTER_BULLETED":
    recommend("Extract Method per section")
```

---

## 6. CHARACTERIZATION TEST WORKFLOW (Ch13 Algorithm)

When CRAPQuants identifies a function needing characterization tests, it should output guidance following Feathers' algorithm:

### 6.1 Feathers' Characterization Test Algorithm
1. Use the code in a test harness.
2. Write an assertion you know will fail.
3. Let the failure tell you what the behavior is.
4. Change the test to expect the actual behavior.
5. Repeat.

### 6.2 Characterization Test Heuristics (for CRAPQuants output)
When generating test suggestions for high-CRAP functions:

1. **Tangled logic:** Introduce sensing variables to verify execution of specific branches.
2. **Responsibility inventory:** List things that can go wrong; formulate tests that trigger them.
3. **Boundary values:** Test extreme/edge inputs.
4. **Class invariants:** Identify conditions that should be true at all times during the object's lifetime.
5. **The Method Use Rule:** "Before you use a method in a legacy system, check to see if there are tests for it. If there aren't, write them."

---

## 7. FEATHERS-CRAP INTEGRATION SCORES

### 7.1 Feathers Risk Score (FRS)
A composite score layered on top of CRAP, encoding Feathers' testability assessment:

```
FRS(f) = CRAP(f) 
       × monster_multiplier(f)      # 1.0 / 1.2 / 1.5 per §2.1.3
       × (1 + dependency_depth(f) / 10)  # Higher deps = harder to test
       × responsibility_factor(f)    # 1.0 if single, 1.3 if multi-responsibility class
```

**Interpretation:**
- FRS < 30: Manageable — standard CRAP territory
- FRS 30-60: High risk — needs characterization tests before any change
- FRS 60-100: Critical — Legacy Code Dilemma zone, break dependencies first
- FRS > 100: Urgent — monster method in untested, high-dependency code

### 7.2 Testability Index (TI)
Inverse of how hard it is to get the function under test:

```
TI(f) = 100 - (dependency_depth(f) × 10) - (sensing_problems × 15) - (separation_problems × 20)
```

Clamped to [0, 100]. A function with TI < 30 is in Feathers' "can't even get it into a test harness" territory.

---

## 8. MAPPING TO CRAP FORMULA SIDES

| Feathers Concept | CRAP Variable | What It Attacks |
|-----------------|---------------|-----------------|
| Characterization Tests | `cov(m)` | Raises coverage by documenting actual behavior |
| Sensing / Fake Objects | `cov(m)` | Enables testing → raises coverage |
| Dependency Breaking | `cov(m)` | Removes barriers to testing → enables coverage |
| Sprout Method/Class | `comp(m)` | New code goes in new method/class → keeps CC low |
| Wrap Method/Class | `comp(m)` | Wraps existing behavior → isolates complexity |
| Extract Method (Monster decomposition) | `comp(m)` | Directly reduces cyclomatic complexity |
| Pinch Point Testing | `cov(m)` | Tests at natural boundary cover multiple functions |
| Effect Sketch / Propagation | diagnostic | Identifies WHERE to test, not a formula input |
| Single Responsibility | diagnostic | Identifies WHAT to extract, not a formula input |

---

## 9. IMPLEMENTATION NOTES FOR CRAPQuants v1

### 9.1 What Can Be Detected Via Python AST (radon + ast module)
- Cyclomatic complexity per function ✓ (radon)
- Line count per function ✓ (radon raw metrics)
- Max nesting depth ✓ (custom AST visitor)
- Parameter count and types ✓ (ast.FunctionDef)
- Return type annotation ✓ (ast.FunctionDef.returns)
- Private/public method ratio ✓ (name convention `_` prefix)
- Method name clustering ✓ (string similarity / prefix grouping)
- Global/module state access ✓ (ast.Global, ast.Name resolution)
- Instance variable usage per method ✓ (ast.Attribute on `self`)
- Side effect indicators ✓ (file I/O, network calls, database calls via known stdlib/library function names)
- Decorator analysis (`@staticmethod`, `@classmethod`) ✓

### 9.2 What Requires coverage.py Integration
- Per-function coverage percentage (from LCOV/JSON/XML output)
- Branch coverage data
- Uncovered line identification for CRAPload calculation

### 9.3 What Requires Git Integration (Future / v2)
- Effect propagation across files (call graph analysis)
- Broken Windows detection (CRAP trend over commits)
- Hunt & Thomas trending signals

---

*Document version: 1.0*  
*Source: Working Effectively with Legacy Code, Michael C. Feathers (Prentice Hall, 2005)*  
*Framework for: CRAPQuants — Dockyard Techlabs*  
*Dedicated as Seva to Lord Sri Krishna*
