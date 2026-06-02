# CRAPQuants — Fowler Framework
## Refactoring Recommendation Engine Extracted from "Refactoring: Improving the Design of Existing Code" (Martin Fowler, with Kent Beck)

> **Purpose:** This document defines the smell-to-refactoring mapping that CRAPQuants uses as its **action prescription engine**. While Feathers tells you *why* code is untested, Ousterhout tells you *what's wrong* with the design, and Hunt & Thomas tell you *whether the culture is healthy*, Fowler tells you *exactly what transformation to apply*.

> **Core Thesis:** "Refactoring is a disciplined technique for restructuring an existing body of code, altering its internal structure without changing its external behavior." The critical parts: (1) disciplined, not free-for-all, (2) external behavior does not change.

> **CRAPQuants Role:** The refactoring recommendation engine. When CRAPQuants detects a problem via Feathers/Ousterhout/Hunt&Thomas tags, the Fowler Framework prescribes the specific named transformation. Each recommendation links directly to a measurable CRAP outcome.

---

## 1. THE 22 CODE SMELLS — Complete Catalog with Detection + Prescription

Fowler (with Kent Beck) defines 22 code smells. Each maps to detectable signals and specific refactoring prescriptions. CRAPQuants automates detection for all 22.

### SMELL-01: Duplicated Code
**Detection:** AST structural clone detection; same expressions in 2+ methods.
**CRAP Impact:** Multiplied complexity — same CC appears N times.
**Prescriptions by context:**
| Context | Refactoring |
|---------|------------|
| Same expression in 2 methods, same class | **Extract Method** → invoke from both |
| Same expression in 2 sibling subclasses | **Extract Method** + **Pull Up Method** |
| Similar but not identical code | **Extract Method** to separate similar/different + **Form Template Method** |
| Same algorithm, different implementation | **Substitute Algorithm** (pick clearer one) |
| Duplicated code in unrelated classes | **Extract Class** → use as component in both |

### SMELL-02: Long Method
**Detection:** `line_count > 30` OR `CC > 10` (configurable thresholds).
**CRAP Impact:** Directly increases `comp(m)` in the CRAP formula.
**Prescriptions by symptom:**
| Symptom | Refactoring |
|---------|------------|
| Code block with comment explaining it | **Extract Method** (name from comment intent) |
| Many temps blocking extraction | **Replace Temp with Query** first |
| Long parameter list blocking extraction | **Introduce Parameter Object** or **Preserve Whole Object** |
| Still too many temps/params after above | **Replace Method with Method Object** |
| Conditional expressions | **Decompose Conditional** |
| Loops | **Extract Method** (loop + body → own method) |

**Fowler's key heuristic:** "Whenever we feel the need to comment something, we write a method instead."

### SMELL-03: Large Class
**Detection:** `method_count > 20` OR `instance_variable_count > 10` (configurable).
**CRAP Impact:** System-level complexity increase; breeding ground for duplication.
**Prescriptions:**
| Symptom | Refactoring |
|---------|------------|
| Common prefixes/suffixes on variables | **Extract Class** (group related variables) |
| Component makes sense as subclass | **Extract Subclass** |
| Different clients use different subsets | **Extract Interface** per client group |
| GUI class with embedded domain logic | **Separate Domain from Presentation** |

### SMELL-04: Long Parameter List
**Detection:** `param_count > 4` (configurable).
**CRAP Impact:** High cognitive load, interface complexity.
**Prescriptions:**
| Symptom | Refactoring |
|---------|------------|
| Can get data from known object | **Replace Parameter with Method** |
| Multiple params from same object | **Preserve Whole Object** |
| Unrelated data items always together | **Introduce Parameter Object** |

### SMELL-05: Divergent Change
**Detection:** One class changes for multiple unrelated reasons. Heuristic: 2+ distinct modification patterns in git history for same class.
**CRAP Impact:** Accumulated complexity from multiple concerns.
**Prescription:** **Extract Class** — one per reason for change.

### SMELL-06: Shotgun Surgery
**Detection:** One logical change requires modifying many classes. Heuristic: git commits touching 5+ files for single feature.
**CRAP Impact:** Distributed complexity, high change amplification.
**Prescriptions:** **Move Method** + **Move Field** to consolidate; if no home exists, **Extract Class** → create one; then **Inline Class** to merge small fragments.

### SMELL-07: Feature Envy
**Detection:** Method calls 3+ getters on another class to compute a value. Heuristic: `external_attribute_access > internal_attribute_access`.
**CRAP Impact:** Wrong location increases coupling, makes testing harder.
**Prescriptions:**
| Symptom | Refactoring |
|---------|------------|
| Whole method envies another class | **Move Method** |
| Part of method envies | **Extract Method** on envious part, then **Move Method** |

### SMELL-08: Data Clumps
**Detection:** Same 3+ parameters appear together in multiple method signatures or as co-occurring fields.
**CRAP Impact:** Repeated parameter lists = interface complexity.
**Prescriptions:** **Extract Class** on fields → create value object; **Introduce Parameter Object** or **Preserve Whole Object** on method signatures.
**Fowler's test:** "Delete one value — do the others still make sense alone? If not, you have a data clump."

### SMELL-09: Primitive Obsession
**Detection:** Using `str`, `int`, `float` where a domain object would be appropriate. Heuristic: same primitive validated/formatted in multiple places.
**CRAP Impact:** Scattered validation logic, duplicated complexity.
**Prescriptions:**
| Symptom | Refactoring |
|---------|------------|
| Individual data value | **Replace Data Value with Object** |
| Type code without behavior | **Replace Type Code with Class** |
| Type code with behavior (conditionals) | **Replace Type Code with Subclasses** or **Replace Type Code with State/Strategy** |
| Grouped primitives | **Extract Class** |
| Primitives in params | **Introduce Parameter Object** |

### SMELL-10: Switch Statements (Conditional Chains)
**Detection:** `if/elif` chains or `match/case` on type codes; same switch in multiple locations.
**CRAP Impact:** Directly inflates cyclomatic complexity.
**Prescriptions:**
| Symptom | Refactoring |
|---------|------------|
| Switch on type code, behavior varies | **Extract Method** + **Move Method** + **Replace Conditional with Polymorphism** |
| Few stable cases, single method | **Replace Parameter with Explicit Methods** |
| Null case in conditional | **Introduce Null Object** |

**CRAP reduction:** Replacing a 6-branch conditional (CC=6) with polymorphism distributes to 6 methods each with CC=1. CRAP per function drops from ~42 (CC=6, 0% cov) to ~2 per method.

### SMELL-11: Parallel Inheritance Hierarchies
**Detection:** Creating subclass in hierarchy A requires subclass in hierarchy B. Heuristic: matching class name prefixes across hierarchies.
**CRAP Impact:** Shotgun surgery variant; doubled complexity.
**Prescription:** **Move Method** + **Move Field** until one hierarchy disappears.

### SMELL-12: Lazy Class
**Detection:** Class with very few methods, low total CC, minimal functionality. Heuristic: `total_class_CC < 5 AND method_count <= 3`.
**CRAP Impact:** Interface overhead without benefit (Ousterhout's "shallow module").
**Prescriptions:** **Collapse Hierarchy** (if subclass) or **Inline Class** (merge into user).

### SMELL-13: Speculative Generality
**Detection:** Abstract classes with single implementor; parameters/methods unused except in tests; factory methods creating single type.
**CRAP Impact:** Unnecessary complexity (Ousterhout DP-35: complexity is a cost).
**Prescriptions:** **Collapse Hierarchy** (unused abstractions), **Inline Class** (unnecessary delegation), **Remove Parameter** (unused params), **Rename Method** (overly abstract names).

### SMELL-14: Temporary Field
**Detection:** Instance variable set only in certain methods, `None`/unset in others. Heuristic: field assigned in < 50% of methods, read in > 50%.
**CRAP Impact:** Unknown unknowns — variable state is unpredictable.
**Prescriptions:** **Extract Class** (orphan variables + their methods → Method Object), **Introduce Null Object** (for when variables aren't valid).

### SMELL-15: Message Chains
**Detection:** `a.b().c().d()` — chain of 3+ attribute/method accesses. Heuristic: `ast.Attribute` chain length > 3.
**CRAP Impact:** Coupling to navigation structure (Hunt & Thomas Tip 46).
**Prescriptions:** **Hide Delegate** at strategic point in chain; **Extract Method** + **Move Method** to push logic down the chain.

### SMELL-16: Middle Man
**Detection:** Class where > 50% of methods delegate to single other class without adding value.
**CRAP Impact:** Shallow module — interface overhead without hiding (Ousterhout RF-05).
**Prescriptions:** **Remove Middle Man** (talk to delegate directly); if few methods: **Inline Method**; if behavior to add: **Replace Delegation with Inheritance**.

### SMELL-17: Inappropriate Intimacy
**Detection:** Two classes accessing each other's private internals extensively. Heuristic: bidirectional coupling + access to `_`-prefixed attributes.
**CRAP Impact:** High coupling, change amplification.
**Prescriptions:** **Move Method** + **Move Field** to separate; **Change Bidirectional to Unidirectional**; **Extract Class** for shared interests; **Hide Delegate**.

### SMELL-18: Alternative Classes with Different Interfaces
**Detection:** Two classes with similar functionality but different method names/signatures.
**CRAP Impact:** Duplicated intent, confusing API.
**Prescriptions:** **Rename Method** to align; **Move Method** until protocols match; if redundant: **Extract Superclass**.

### SMELL-19: Incomplete Library Class
**Detection:** External library class missing needed functionality.
**CRAP Impact:** Workarounds add complexity in client code.
**Prescriptions:** Few methods: **Introduce Foreign Method** (standalone function); many methods: **Introduce Local Extension** (subclass or wrapper).

### SMELL-20: Data Class
**Detection:** Class with only fields + getters/setters, no behavior. Heuristic: `behavioral_method_count == 0 AND property_count > 3`.
**CRAP Impact:** Feature Envy in other classes manipulating this data.
**Prescriptions:** **Encapsulate Field** → **Encapsulate Collection** → **Remove Setting Method** where possible → **Move Method** (pull behavior into data class) → eventually **Hide Method** on getters/setters.

### SMELL-21: Refused Bequest
**Detection:** Subclass overrides parent methods to do nothing, or uses only small fraction of inherited interface.
**CRAP Impact:** Misleading inheritance, violated contracts.
**Prescriptions:** If causing confusion: **Push Down Method** + **Push Down Field** to sibling; if refusing interface: **Replace Inheritance with Delegation**.

### SMELL-22: Comments as Deodorant
**Detection:** Dense comments preceding complex code blocks. Heuristic: `comment_density > 0.5 AND adjacent_CC > 5`.
**CRAP Impact:** Indicates untreated smell underneath.
**Prescriptions:** **Extract Method** (name from comment intent); if method exists but comment needed: **Rename Method**; if stating invariants: **Introduce Assertion**.
**Fowler's tip:** "When you feel the need to write a comment, first try to refactor the code so that any comment becomes superfluous."

---

## 2. THE COMPLETE REFACTORING CATALOG — 72 Named Transformations

Organized by category with Python equivalents and CRAP impact:

### Category A: Composing Methods (9 refactorings) — Directly Reduces CC
| # | Refactoring | Python Equivalent | CC Impact | When CRAPQuants Recommends |
|---|------------|-------------------|-----------|---------------------------|
| 1 | Extract Method | Extract function/method | CC ↓ per function | `CC > 10` OR `line_count > 30` |
| 2 | Inline Method | Merge trivial function into caller | CC ↓ (removes shallow method) | `depth_ratio < 2 AND line_count <= 3` |
| 3 | Inline Temp | Remove single-use temp variable | Negligible | Prerequisite for other refactorings |
| 4 | Replace Temp with Query | Temp → method call | CC neutral, testability ↑ | Temp blocks Extract Method |
| 5 | Introduce Explaining Variable | Complex expression → named variable | CC neutral, readability ↑ | `nonobvious_score >= 3` |
| 6 | Split Temporary Variable | One temp, two purposes → two temps | CC neutral, clarity ↑ | Variable assigned 2+ times for different purposes |
| 7 | Remove Assignments to Parameters | Don't mutate params | CC neutral, clarity ↑ | Param assigned inside function body |
| 8 | Replace Method with Method Object | Long method → class | CC ↓ per method (distributes) | `CC > 15 AND temp_count > 5` (Monster method) |
| 9 | Substitute Algorithm | Replace with clearer version | CC varies | Same result, clearer implementation available |

### Category B: Moving Features Between Objects (8 refactorings) — Reduces Coupling
| # | Refactoring | Python Equivalent | Coupling Impact | When CRAPQuants Recommends |
|---|------------|-------------------|----------------|---------------------------|
| 10 | Move Method | Move function to class it uses most | Coupling ↓ | `FEATURE_ENVY` tag |
| 11 | Move Field | Move attribute to class that uses it more | Coupling ↓ | Field accessed more from other class |
| 12 | Extract Class | Split class into two | Cohesion ↑ | `MULTI_RESPONSIBILITY` or `method_count > 20` |
| 13 | Inline Class | Merge underused class into user | Removes shallow module | `LAZY_CLASS` or `total_class_CC < 5` |
| 14 | Hide Delegate | Wrapper method hides navigation | Coupling ↓ | `MESSAGE_CHAIN` length > 3 |
| 15 | Remove Middle Man | Expose delegate directly | Removes shallow delegation | `MIDDLE_MAN` > 50% delegation |
| 16 | Introduce Foreign Method | Add utility function for library gap | - | Library class missing needed method |
| 17 | Introduce Local Extension | Subclass/wrapper for library | - | Many methods missing from library |

### Category C: Organizing Data (16 refactorings) — Reduces Obscurity
| # | Refactoring | CC Impact | When CRAPQuants Recommends |
|---|------------|-----------|---------------------------|
| 18 | Self Encapsulate Field | Neutral | Internal field access needs indirection |
| 19 | Replace Data Value with Object | Neutral | `PRIMITIVE_OBSESSION` |
| 20 | Change Value to Reference | Neutral | Identity matters for data objects |
| 21 | Change Reference to Value | Neutral | Equality matters, reference causes issues |
| 22 | Replace Array with Object | Neutral | Array used with positional meaning |
| 23 | Duplicate Observed Data | Neutral | GUI-domain separation needed |
| 24 | Change Unidirectional → Bidirectional | Neutral | Both sides need navigation |
| 25 | Change Bidirectional → Unidirectional | Coupling ↓ | `INAPPROPRIATE_INTIMACY` |
| 26 | Replace Magic Number with Symbolic Constant | Clarity ↑ | Magic numbers in code |
| 27 | Encapsulate Field | Coupling ↓ | Public field access |
| 28 | Encapsulate Collection | Coupling ↓ | Raw collection exposed |
| 29 | Replace Record with Data Class | Neutral | Dict used as struct |
| 30 | Replace Type Code with Class | CC neutral | Non-behavioral type codes |
| 31 | Replace Type Code with Subclasses | CC ↓ | Behavioral type codes |
| 32 | Replace Type Code with State/Strategy | CC ↓ | Type code changes at runtime |
| 33 | Replace Subclass with Fields | CC neutral | Subclasses differ only in constant data |

### Category D: Simplifying Conditional Expressions (8 refactorings) — Directly Reduces CC
| # | Refactoring | CC Impact | When CRAPQuants Recommends |
|---|------------|-----------|---------------------------|
| 34 | **Decompose Conditional** | CC ↓↓ | `CC > 8 AND has_nested_conditionals` |
| 35 | Consolidate Conditional Expression | CC ↓ | Multiple conditions → same result |
| 36 | Consolidate Duplicate Conditional Fragments | CC neutral | Same code in all branches |
| 37 | Remove Control Flag | CC ↓ | Boolean flag controlling loop/conditional |
| 38 | **Replace Nested Conditional with Guard Clauses** | CC ↓↓ | `nesting_depth >= 3` |
| 39 | **Replace Conditional with Polymorphism** | CC ↓↓↓ | `SWITCH_SMELL` or `elif` chain > 3 |
| 40 | Introduce Null Object | CC ↓ | Null checks scattered through code |
| 41 | **Introduce Assertion** | CC neutral, safety ↑ | `NO_CONTRACTS` tag |

### Category E: Making Method Calls Simpler (15 refactorings) — Reduces Interface Complexity
| # | Refactoring | Interface Impact | When CRAPQuants Recommends |
|---|------------|-----------------|---------------------------|
| 42 | Rename Method | Clarity ↑ | `VAGUE_NAMING` tag |
| 43 | Add Parameter | Interface grows | Only when necessary |
| 44 | Remove Parameter | Interface ↓ | Unused parameter |
| 45 | **Separate Query from Modifier** | Side effects ↓ | Function both returns value AND modifies state |
| 46 | Parameterize Method | CC ↓ | Multiple methods differ only by value |
| 47 | Replace Parameter with Explicit Methods | Clarity ↑ | Parameter selects behavior (flag argument) |
| 48 | **Preserve Whole Object** | Interface ↓ | 3+ params from same object |
| 49 | Replace Parameter with Method | Interface ↓ | Param derivable from known object |
| 50 | **Introduce Parameter Object** | Interface ↓↓ | `param_count > 4` or `DATA_CLUMP` |
| 51 | Remove Setting Method | Immutability ↑ | Field should be set only in constructor |
| 52 | Hide Method | Interface ↓ | Method used only internally |
| 53 | Replace Constructor with Factory Method | Flexibility ↑ | Complex creation logic |
| 54 | Encapsulate Downcast | Safety ↑ | Caller forced to cast return value |
| 55 | Replace Error Code with Exception | Clarity ↑ | Error communicated via return value |
| 56 | Replace Exception with Test | CC ↓ | Exception used for expected condition |

### Category F: Dealing with Generalization (11 refactorings) — Restructures Hierarchy
| # | Refactoring | When CRAPQuants Recommends |
|---|------------|---------------------------|
| 57 | Pull Up Field | Same field in multiple subclasses |
| 58 | Pull Up Method | Same method in multiple subclasses |
| 59 | Pull Up Constructor Body | Duplicate constructor logic |
| 60 | Push Down Method | Method relevant only to specific subclass |
| 61 | Push Down Field | Field relevant only to specific subclass |
| 62 | Extract Subclass | Class has features used only in some instances |
| 63 | Extract Superclass | Two classes with similar features |
| 64 | Extract Interface (→ Protocol) | Multiple clients use different subsets |
| 65 | Collapse Hierarchy | Subclass not different enough |
| 66 | Form Template Method | Two methods similar steps, different details |
| 67 | Replace Inheritance with Delegation | Subclass uses only part of parent interface |
| 68 | Replace Delegation with Inheritance | Delegating class uses entire delegate interface |

### Category G: Big Refactorings (4 refactorings) — Architectural Transformations
| # | Refactoring | When CRAPQuants Recommends |
|---|------------|---------------------------|
| 69 | **Tease Apart Inheritance** | Inheritance doing two jobs simultaneously |
| 70 | Convert Procedural Design to Objects | Functions + data structures without encapsulation |
| 71 | **Separate Domain from Presentation** | Business logic mixed with I/O/UI |
| 72 | Extract Hierarchy | Class doing too much with many conditionals |

---

## 3. THE SMELL → TAG → REFACTORING MAPPING ENGINE

This is the core of CRAPQuants' recommendation system. When a diagnostic tag fires (from any of the four frameworks), the Fowler Framework maps it to specific refactorings:

```python
REFACTORING_RECOMMENDATIONS = {
    # Feathers Framework tags
    "MONSTER_BULLETED": [
        ("Extract Method", "One extraction per code section/bullet"),
    ],
    "MONSTER_SNARLED": [
        ("Replace Method with Method Object", "Convert to class to untangle state"),
        ("Introduce Explaining Variable", "Name intermediate results"),
        ("Decompose Conditional", "Simplify nested branches"),
    ],
    "LEGACY_DILEMMA": [
        ("Extract Interface", "Create Protocol for dependency injection"),
        ("Parameterize Constructor", "Break hard dependencies"),
    ],
    "SENSING_PROBLEM": [
        ("Separate Query from Modifier", "Split read from write"),
        ("Extract Method", "Isolate side-effecting code"),
    ],
    "SEPARATION_PROBLEM": [
        ("Extract Interface", "Define Protocol for testability"),
        ("Replace Constructor with Factory Method", "Enable test doubles"),
    ],
    "HIDDEN_CLASS": [
        ("Extract Class", "Promote private method cluster to own class"),
    ],
    "MULTI_RESPONSIBILITY": [
        ("Extract Class", "One class per responsibility group"),
    ],
    
    # Ousterhout Framework tags
    "SHALLOW_MODULE": [
        ("Inline Method", "Merge trivial wrappers into caller"),
        ("Inline Class", "Merge shallow class into user"),
    ],
    "INFO_LEAKAGE": [
        ("Extract Class", "Consolidate leaked knowledge into single module"),
        ("Move Method", "Co-locate related logic"),
    ],
    "PASS_THROUGH": [
        ("Inline Method", "Remove passthrough, call delegate directly"),
        ("Remove Middle Man", "Expose delegate to callers"),
    ],
    "OVEREXPOSED_API": [
        ("Hide Method", "Make rarely-used methods private"),
        ("Extract Interface", "Create focused interface per client"),
    ],
    "CONJOINED": [
        ("Extract Method", "Extract shared logic"),
        ("Move Method", "Relocate dependent method"),
    ],
    "COMPLEXITY_UPWARD": [
        ("Replace Error Code with Exception", "Clean error channel"),
        ("Replace Exception with Test", "Eliminate exception for expected cases"),
        ("Introduce Null Object", "Remove null checks"),
    ],
    "VAGUE_NAMING": [
        ("Rename Method", "Choose precise, intention-revealing name"),
    ],
    "NONOBVIOUS": [
        ("Introduce Explaining Variable", "Name complex expressions"),
        ("Extract Method", "Name code sections by intent"),
        ("Decompose Conditional", "Clarify conditional logic"),
    ],
    
    # Hunt & Thomas Framework tags
    "BROKEN_WINDOW": [
        ("Extract Method", "Start decomposing — any improvement breaks the rot"),
    ],
    "DRY_VIOLATION": [
        ("Extract Method", "Unify duplicated code"),
        ("Pull Up Method", "If in sibling classes"),
        ("Extract Class", "If in unrelated classes"),
        ("Form Template Method", "If similar but not identical"),
    ],
    "NON_ORTHOGONAL": [
        ("Move Method", "Separate concerns"),
        ("Extract Class", "Isolate independent concerns"),
        ("Separate Domain from Presentation", "If mixing UI/logic"),
    ],
    "COINCIDENCE_CODE": [
        ("Extract Method", "Name code sections to clarify intent"),
        ("Introduce Assertion", "Document assumptions explicitly"),
        ("Substitute Algorithm", "Replace with understood approach"),
    ],
    "GLOBAL_COUPLING": [
        ("Replace Magic Number with Symbolic Constant", "Name magic values"),
        ("Encapsulate Field", "Hide globals behind accessor"),
        ("Introduce Parameter Object", "Pass grouped globals as object"),
    ],
    "SWALLOWED_EXCEPTION": [
        ("Replace Error Code with Exception", "Proper error signaling"),
    ],
    "NO_CONTRACTS": [
        ("Introduce Assertion", "Add pre/postconditions"),
    ],
}
```

---

## 4. CRAP IMPACT CLASSIFICATION

Each refactoring has a predictable effect on the CRAP formula:

### CC Reducers (directly lower `comp(m)`)
| Refactoring | Typical CC Reduction | Mechanism |
|------------|---------------------|-----------|
| Extract Method | -3 to -10 per extraction | Splits CC across new methods |
| Decompose Conditional | -2 to -5 | Names condition + branches |
| Replace Conditional with Polymorphism | -5 to -20 | Eliminates conditional entirely |
| Replace Nested Conditional with Guard Clauses | -2 to -4 | Removes nesting levels |
| Replace Method with Method Object | -10 to -30 | Distributes CC across class methods |
| Remove Control Flag | -1 to -3 | Replaces flag with break/return |
| Consolidate Conditional Expression | -1 to -3 | Merges redundant conditions |

### Coverage Enablers (indirectly raise `cov(m)`)
| Refactoring | Coverage Effect | Mechanism |
|------------|----------------|-----------|
| Extract Interface | Enables mocking/faking | Testability ↑ |
| Parameterize Constructor | Enables dependency injection | Testability ↑ |
| Separate Query from Modifier | Enables testing reads without writes | Testability ↑ |
| Replace Constructor with Factory Method | Enables test double creation | Testability ↑ |
| Introduce Parameter Object | Simplifies test setup | Test effort ↓ |

### Interface Simplifiers (reduce Ousterhout interface_complexity)
| Refactoring | Interface Effect | Mechanism |
|------------|-----------------|-----------|
| Introduce Parameter Object | Params 5+ → 1 | Groups related params |
| Preserve Whole Object | Params 3+ → 1 | Passes object instead of fields |
| Remove Parameter | Params -1 | Removes unused |
| Hide Method | Public surface ↓ | Makes internal-only methods private |

---

## 5. THE REFACTORING PRIORITY ALGORITHM

When multiple refactorings are recommended, CRAPQuants should prioritize by CRAP impact:

```python
def prioritize_refactorings(recommendations: list, func_crap: float, func_cc: int, func_cov: float) -> list:
    """
    Priority order:
    1. CC Reducers — if CC > 15, these give biggest CRAP drop
    2. Coverage Enablers — if CC <= 15 but cov < 50%, enable testing
    3. Interface Simplifiers — if CRAP < 30 but design is poor
    4. Clarity improvements — naming, explaining variables
    """
    priority_1 = []  # CC > 15: reduce complexity first
    priority_2 = []  # CC <= 15, cov < 50%: enable testing
    priority_3 = []  # CRAP < 30: improve design quality  
    priority_4 = []  # Polish
    
    cc_reducers = {"Extract Method", "Decompose Conditional", 
                   "Replace Conditional with Polymorphism",
                   "Replace Nested Conditional with Guard Clauses",
                   "Replace Method with Method Object"}
    
    coverage_enablers = {"Extract Interface", "Parameterize Constructor",
                         "Separate Query from Modifier",
                         "Replace Constructor with Factory Method"}
    
    for rec in recommendations:
        name = rec[0]
        if func_cc > 15 and name in cc_reducers:
            priority_1.append(rec)
        elif func_cc <= 15 and func_cov < 50 and name in coverage_enablers:
            priority_2.append(rec)
        elif func_crap < 30 and name not in cc_reducers:
            priority_3.append(rec)
        else:
            priority_4.append(rec)
    
    return priority_1 + priority_2 + priority_3 + priority_4
```

---

## 6. FOWLER'S REFACTORING PRINCIPLES (Chapter 2)

### When to Refactor
Fowler's three rules, encoded as CRAPQuants triggers:

1. **The Rule of Three:** "The first time you do something, you just do it. The second time you do something similar, you wince at the duplication. The third time, you refactor."
   - CRAPQuants: `dry_violation_count >= 3` → automatic recommendation

2. **Refactor When You Add a Feature:** Adding a feature is easier if the code is well-structured.
   - CRAPQuants: When CRAP > 30 on a function being modified → recommend refactoring before feature work

3. **Refactor When You Fix a Bug:** If code is hard enough to produce a bug, it's hard enough to warrant refactoring.
   - CRAPQuants: Bug-fix commits on high-CRAP functions → flag for refactoring

### When NOT to Refactor
- **When code is a mess requiring rewrite:** CRAP > 200 with `dependency_depth > 10` → "Consider rewrite"
- **When close to deadline:** CRAPQuants can set "advisory only" mode for deadline sprints
- **When tests don't exist:** Feathers' techniques (characterization tests) must come first

---

## 7. MAPPING TO CRAP FORMULA

| Fowler Concept | CRAP Variable | What It Attacks |
|---------------|---------------|-----------------|
| Extract Method | `comp(m)` ↓ | Splits CC across smaller functions |
| Decompose Conditional | `comp(m)` ↓ | Names and isolates condition branches |
| Replace Conditional with Polymorphism | `comp(m)` ↓↓↓ | Eliminates branching entirely |
| Replace Method with Method Object | `comp(m)` ↓↓ | Distributes CC across class |
| Extract Interface | `cov(m)` ↑ (enables) | Makes testing possible |
| Parameterize Constructor | `cov(m)` ↑ (enables) | Enables dependency injection |
| Substitute Algorithm | `comp(m)` varies | Replaces with clearer algorithm |
| Introduce Assertion | neither directly | Documents invariants for safety |
| All 22 smell detections | diagnostic | Identifies WHERE to apply transformations |

---

## 8. CROSS-REFERENCE: ALL FOUR FRAMEWORKS — COMPLETE PICTURE

| When CRAPQuants Detects | Feathers Diagnoses | Ousterhout Diagnoses | Hunt & Thomas Diagnoses | Fowler Prescribes |
|------------------------|-------------------|---------------------|------------------------|------------------|
| CC=20, cov=0% | MONSTER + EDIT_AND_PRAY | NONOBVIOUS + TACTICAL | BROKEN_WINDOW + COINCIDENCE | 1. Characterize (Feathers), 2. Extract Method, 3. Decompose Conditional |
| CC=3, cov=100%, 3 clones | Safe to change | Check if shallow | DRY_VIOLATION | Extract Method + Pull Up Method |
| CC=8, cov=0%, hard deps | SEPARATION_PROBLEM | COMPLEXITY_UPWARD | NO_SAFETY_NET | Extract Interface + Parameterize Constructor → then test → then Extract Method |
| CC=25, cov=90% | Low risk (tested) | High cognitive load | Refactor Ready (safe) | Replace Conditional with Polymorphism + Replace Method with Method Object |
| CC=5, cov=80%, 8 params | Low CRAP, testable | OVEREXPOSED_API | Fine | Introduce Parameter Object + Preserve Whole Object |
| CC=15, cov=0%, 15 commits old | LEGACY_DILEMMA | TACTICAL_TORNADO | BROKEN_WINDOW (critical) | 1. Break deps (Feathers), 2. Characterize, 3. Decompose Conditional, 4. Extract Method |

---

*Document version: 1.0*
*Source: Refactoring: Improving the Design of Existing Code, Martin Fowler with Kent Beck et al. (Addison-Wesley, 1999)*
*Framework for: CRAPQuants — Dockyard Techlabs*
*Dedicated as Seva to Lord Sri Krishna*
