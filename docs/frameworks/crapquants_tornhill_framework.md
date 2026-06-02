# CRAPQuants — Tornhill Framework (Supplementary)
## Behavioral Code Analysis Extracted from "Your Code as a Crime Scene, 2nd Ed." (Adam Tornhill, 2024)

> **Purpose:** This supplementary framework fills the **Hotspot Analysis**, **Code Churn**, **Change Coupling**, and **Truck Factor** gaps identified in the CRAPQuants gap analysis. Tornhill's core insight: static code metrics alone are inadequate — you must combine them with behavioral data (how developers interact with code over time) to find what actually matters.

> **Core Thesis:** "Complex code is only a problem if we need to deal with it." Hotspots = intersection of complexity AND developer effort (change frequency). A function with CC=25 that hasn't changed in 2 years is less urgent than one with CC=8 that changes weekly.

> **CRAPQuants Role:** Adds the **temporal/behavioral dimension** to the existing four frameworks. Weights CRAP scores by actual developer activity, not just static structure.

---

## 1. HOTSPOT ANALYSIS — The Core Algorithm

### 1.1 The Formula
```
hotspot_score(file) = change_frequency(file) × complexity(file)
```

Where:
- `change_frequency` = number of git commits touching this file in analysis window
- `complexity` = lines of code (Tornhill's preferred proxy) OR CC sum OR CRAP score

**Tornhill's key insight:** Lines of code performs as well as more elaborate complexity metrics for hotspot prediction. Multiple studies confirm this. But for CRAPQuants, we use the CRAP score itself as the complexity dimension, giving us:

```
crapquants_hotspot(f) = change_frequency(f) × CRAP(f)
```

### 1.2 Why This Matters for CRAPQuants
The existing four frameworks score functions purely by static properties + coverage. Tornhill adds the missing question: **"Does anyone actually work on this code?"**

A function with CRAP=80 that hasn't been touched in 18 months is lower priority than one with CRAP=25 that gets modified every week. Hotspot analysis reorders the priority list.

### 1.3 Implementation
```python
def calculate_hotspots(
    crap_scores: dict[str, float],
    git_log: list[GitCommit],
    analysis_window_days: int = 365
) -> list[Hotspot]:
    """
    Intersect CRAP scores with change frequency from git history.
    Returns ranked list of hotspots.
    """
    cutoff = datetime.now() - timedelta(days=analysis_window_days)
    
    # Count commits per file within analysis window
    change_freq: dict[str, int] = Counter()
    for commit in git_log:
        if commit.date >= cutoff:
            for file_path in commit.files_changed:
                change_freq[file_path] += 1
    
    # Intersect: only files that have both CRAP and change data
    hotspots = []
    for file_path, crap in crap_scores.items():
        freq = change_freq.get(file_path, 0)
        if freq > 0:
            hotspots.append(Hotspot(
                file=file_path,
                crap_score=crap,
                change_frequency=freq,
                hotspot_score=crap * freq,
            ))
    
    return sorted(hotspots, key=lambda h: h.hotspot_score, reverse=True)
```

### 1.4 Research Backing
Tornhill cites multiple studies confirming hotspot predictive power:
- Files that change frequently are better defect predictors than pure size
- Frequently changed modules with duplication correlate with maintenance problems
- Change frequency + LOC are the two strongest individual quality predictors
- Security vulnerability density correlates strongly with hotspot presence

---

## 2. COMPLEXITY TRENDS — Detecting Deterioration

### 2.1 The Concept
Instead of looking at absolute complexity, track the *trend* over time. A function going from CC=5 to CC=15 over 6 months is a warning even though CC=15 alone might not trigger flags.

Tornhill uses **code shape** (indentation patterns / whitespace analysis) as a language-neutral complexity proxy. For CRAPQuants, we use CRAP score trend.

### 2.2 Trend Classification
```python
def classify_trend(crap_history: list[float]) -> str:
    """Classify CRAP score trend for a function over time."""
    if len(crap_history) < 3:
        return "INSUFFICIENT_DATA"
    
    # Simple linear regression slope
    slope = calculate_slope(crap_history)
    
    if slope > 1.0:
        return "DETERIORATING"      # Complexity growing fast
    elif slope > 0.1:
        return "SLOWLY_DEGRADING"   # Creeping complexity
    elif slope < -1.0:
        return "IMPROVING"          # Active refactoring
    elif slope < -0.1:
        return "SLOWLY_IMPROVING"   # Gradual cleanup
    else:
        return "STABLE"             # Flat
```

### 2.3 Growth Patterns (from Ch5)
Tornhill identifies four growth patterns:
1. **Linear growth** — Steady complexity increase. Typical of feature accumulation without refactoring.
2. **Exponential growth** — Accelerating complexity. Code approaching crisis point.
3. **Plateau** — Complexity stabilized. Either good design or abandoned code.
4. **Decline** — Active refactoring underway.

---

## 3. CHANGE COUPLING — Temporal Dependencies

### 3.1 The Concept
Change coupling detects files that repeatedly change together in the same commits. This reveals *implicit* dependencies invisible in static code analysis.

**Types of change coupling:**
- **Intrinsic** — Files coupled because they share a responsibility (legitimate, but consider merging)
- **Incidental** — Files coupled because of poor decomposition (refactoring opportunity)
- **Copy-paste** — Duplicated code changing in tandem (DRY violation)
- **Producer-consumer** — Different roles in same data flow (may be acceptable)

### 3.2 Detection
```python
def detect_change_coupling(
    git_log: list[GitCommit],
    min_shared_commits: int = 5,
    min_coupling_ratio: float = 0.3
) -> list[CoupledPair]:
    """
    Detect files that frequently change together.
    
    coupling_ratio = shared_commits / max(commits_A, commits_B)
    """
    # Count co-changes: files modified in same commit
    pair_counts: dict[tuple, int] = Counter()
    file_counts: dict[str, int] = Counter()
    
    for commit in git_log:
        files = commit.files_changed
        file_counts.update(files)
        for pair in combinations(sorted(files), 2):
            pair_counts[pair] += 1
    
    coupled = []
    for (a, b), shared in pair_counts.items():
        if shared >= min_shared_commits:
            ratio = shared / max(file_counts[a], file_counts[b])
            if ratio >= min_coupling_ratio:
                coupled.append(CoupledPair(
                    file_a=a, file_b=b,
                    shared_commits=shared,
                    coupling_ratio=ratio,
                ))
    
    return sorted(coupled, key=lambda c: c.coupling_ratio, reverse=True)
```

### 3.3 CRAPQuants Integration
Change coupling feeds into:
- **Ousterhout RF-02 (Information Leakage):** High change coupling between unrelated modules = leaked design decision
- **Hunt & Thomas DRY_VIOLATION:** Change coupling caused by copy-paste duplication
- **Fowler SMELL-06 (Shotgun Surgery):** One logical change touching many files

---

## 4. TRUCK FACTOR — Knowledge Risk

### 4.1 The Concept
The truck factor (also "bus factor") is the minimum number of developers who could leave before the codebase becomes unmaintainable.

Tornhill's research: roughly two-thirds of popular GitHub projects have a truck factor of only 1-2 maintainers.

### 4.2 Calculation
```python
def calculate_truck_factor(
    git_log: list[GitCommit],
    file_path: str
) -> TruckFactorResult:
    """
    Calculate truck factor for a specific file.
    
    Primary author = developer with most commits to file.
    Truck factor = number of developers needed to cover 50%+ of changes.
    """
    author_commits: dict[str, int] = Counter()
    for commit in git_log:
        if file_path in commit.files_changed:
            author_commits[commit.author] += 1
    
    total = sum(author_commits.values())
    sorted_authors = sorted(author_commits.items(), key=lambda x: -x[1])
    
    # How many authors cover 50% of commits?
    cumulative = 0
    truck_factor = 0
    for author, count in sorted_authors:
        cumulative += count
        truck_factor += 1
        if cumulative >= total * 0.5:
            break
    
    primary_author = sorted_authors[0][0] if sorted_authors else None
    primary_ownership = sorted_authors[0][1] / total if total > 0 else 0
    
    return TruckFactorResult(
        file=file_path,
        truck_factor=truck_factor,
        primary_author=primary_author,
        primary_ownership_pct=primary_ownership,
        total_authors=len(author_commits),
        knowledge_risk="HIGH" if truck_factor <= 1 else 
                       "MEDIUM" if truck_factor <= 2 else "LOW",
    )
```

### 4.3 CRAPQuants Integration
Truck factor amplifies risk: a high-CRAP function with truck_factor=1 is a critical organizational risk — the only person who understands the most dangerous code could leave.

```
organizational_risk(f) = CRAP(f) × (1 / max(truck_factor(f), 1))
```

---

## 5. TORNHILL DIAGNOSTIC TAGS

| Tag | Condition | Tornhill Reference | Recommended Action |
|-----|-----------|-------------------|-------------------|
| `HOTSPOT_CRITICAL` | hotspot_score in top 5% AND CRAP > 30 | Ch3: Hotspot Analysis | Priority refactoring — high complexity + high activity |
| `HOTSPOT_DORMANT` | CRAP > 60 BUT change_frequency = 0 in 12 months | Ch2: Behavioral Perspective | Monitor but deprioritize — time bomb, not urgent |
| `DETERIORATING` | CRAP trend slope > 1.0 over last 10 commits | Ch5: Complexity Trends | Intervene — complexity growing faster than features justify |
| `CHANGE_COUPLED` | coupling_ratio > 0.5 with unrelated module | Ch8-9: Change Coupling | Investigate — implicit dependency or copy-paste |
| `KNOWLEDGE_SILO` | truck_factor = 1 AND CRAP > 20 | Ch14: Truck Factor | Knowledge sharing required — pair programming, documentation |
| `CHURN_HOTSPOT` | change_frequency > 2σ above mean | Ch3: Change Frequency | High developer effort — check if complexity is the cause |

---

## 6. TORNHILL BEHAVIORAL SCORE (TBS)

Composite score layered on top of CRAP, encoding behavioral/temporal signals:

```python
def tornhill_behavioral_score(
    crap: float,
    change_frequency: int,
    trend: str,
    truck_factor: int,
    coupling_count: int
) -> float:
    """
    TBS amplifies CRAP by behavioral signals.
    A high-CRAP function that's also a hotspot with
    deteriorating trend and low truck factor is critical.
    """
    # Activity weight: more changes = more urgent
    activity_weight = min(3.0, 1.0 + (change_frequency / 20.0))
    
    # Trend weight
    trend_weights = {
        "DETERIORATING": 1.5,
        "SLOWLY_DEGRADING": 1.2,
        "STABLE": 1.0,
        "SLOWLY_IMPROVING": 0.8,
        "IMPROVING": 0.6,
    }
    trend_weight = trend_weights.get(trend, 1.0)
    
    # Knowledge risk weight
    knowledge_weight = 1.0 + (1.0 / max(truck_factor, 1)) * 0.3
    
    # Coupling penalty
    coupling_weight = 1.0 + (coupling_count * 0.1)
    
    return crap * activity_weight * trend_weight * knowledge_weight * coupling_weight
```

---

## 7. UPDATED CRAPQuants SCORING ARCHITECTURE

With all five frameworks complete:

| Score | Framework | Level | What It Measures |
|-------|-----------|-------|-----------------|
| **FRS** | Feathers | Per-function | Testability risk (cov side) |
| **ORS** | Ousterhout | Per-function | Design quality risk (comp side) |
| **TBS** | Tornhill | Per-function | Behavioral/temporal risk (activity side) |
| **PHS** | Hunt & Thomas | Per-codebase | Cultural sustainability |
| **Fowler** | Fowler | Per-tag | Refactoring prescription |

**Final per-function CRAPQuants score:**
```
CQ_score(f) = max(FRS(f), ORS(f), TBS(f))
```

Takes the worst assessment across testability, design, and behavioral dimensions. A function that passes two checks but fails one is still at risk.

---

## 8. MAPPING TO CRAP FORMULA

| Tornhill Concept | CRAP Variable | What It Adds |
|-----------------|---------------|-------------|
| Hotspot Analysis | Weights `CRAP(m)` | Prioritizes by actual developer activity |
| Complexity Trends | Tracks `comp(m)` over time | Detects deterioration trajectory |
| Change Coupling | diagnostic | Reveals implicit dependencies invisible in code |
| Truck Factor | diagnostic | Organizational risk amplifier for high-CRAP code |
| Knowledge Maps | diagnostic | Identifies code with concentrated ownership risk |

---

*Document version: 1.0*
*Source: Your Code as a Crime Scene, 2nd Edition, Adam Tornhill (Pragmatic Bookshelf, 2024)*
*Framework for: CRAPQuants — Dockyard Techlabs*
*Dedicated as Seva to Lord Sri Krishna*
