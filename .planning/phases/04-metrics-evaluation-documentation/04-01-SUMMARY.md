---
phase: 04-metrics-evaluation-documentation
plan: "01"
subsystem: setup
tags: [setup, dependencies, test-scaffolding, recharts, tdd, wave-0]
dependency_graph:
  requires: []
  provides:
    - recharts 3.8.1 installed under frontend/dependencies
    - backend/tests/test_metrics.py with 4 failing test classes (RED state)
  affects:
    - frontend/package.json
    - frontend/package-lock.json
    - backend/tests/test_metrics.py
tech_stack:
  added:
    - recharts@3.8.1 (runtime dep, frontend chart library)
  patterns:
    - TDD seed pattern: stub methods using self.fail() produce clean RED state
    - Django TestCase for DB-dependent tests; pure unittest.TestCase for math helpers
key_files:
  created:
    - backend/tests/test_metrics.py
  modified:
    - frontend/package.json
    - frontend/package-lock.json
decisions:
  - "Install recharts as runtime dep (not devDep) — consumed by client components in Wave 2"
  - "Use self.fail() bodies (not raise NotImplementedError) so pytest reports FAILED not ERROR"
  - "TestJaccard extends unittest.TestCase (pure math, no DB); other 3 classes extend django.test.TestCase"
metrics:
  duration: "~5 minutes"
  completed: "2026-05-12"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 3
---

# Phase 4 Plan 01: Wave 0 Prerequisites (recharts + Test Stubs) Summary

Wave 0 prerequisite tasks complete: recharts 3.8.1 installed under frontend dependencies and backend/tests/test_metrics.py seeded with 10 failing stubs across 4 test classes — unblocking Wave 1 (backend endpoints) and Wave 2 (frontend charts) simultaneously.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Install recharts 3.8.1 into frontend | d4dd9e9d | frontend/package.json, frontend/package-lock.json |
| 2 | Scaffold backend/tests/test_metrics.py with 4 failing test classes | ec2ad65b | backend/tests/test_metrics.py |

## What Was Built

### Task 1: recharts Installation

- `recharts@3.8.1` installed under `frontend/dependencies` (runtime, not devDependencies)
- `npm ls recharts` output: `recharts@3.8.1` — single resolved version, no peer dep warnings
- package-lock.json updated with full dependency tree
- No other dependencies added, modified, or removed

### Task 2: backend/tests/test_metrics.py

File created at `backend/tests/test_metrics.py` (216 lines).

**Test classes and stub methods:**

| Class | Base | Stubs | Behavior Covered |
|-------|------|-------|-----------------|
| `TestMetricsEndpoint` | `django.test.TestCase` | 3 | null acceptance rate; hidden_gem_rate via track_popularity < 40 (not was_novel); all 12 required response fields |
| `TestTrendEndpoint` | `django.test.TestCase` | 2 | "Not enough data" guard (<2 dates); 7-day rolling window correctness on 10-day fixture |
| `TestJaccard` | `unittest.TestCase` | 3 | jaccard_distance([], []) == 0.0; disjoint sets == 1.0; partial overlap == 1 - 1/3 ≈ 0.667 |
| `TestTasteVector` | `django.test.TestCase` | 2 | top_genres_pct capped at ≤10 entries; sum of pct values ≈ 100.0 (±0.5) |

**RED state confirmed:** All 10 tests fail via `self.fail("Wave 1: ...")` — pytest reports `FAILED` (not ERROR or skipped).

**Existing suite:** 58 passed, 4 skipped — no regressions.

## Wave 1 Unblocked

Wave 1 now has automated `<verify>` commands available from task one:

```bash
cd backend && python -m pytest tests/test_metrics.py::TestJaccard -x -q
cd backend && python -m pytest tests/test_metrics.py::TestTrendEndpoint -x -q
cd backend && python -m pytest tests/test_metrics.py::TestMetricsEndpoint -x -q
cd backend && python -m pytest tests/test_metrics.py::TestTasteVector -x -q
```

Wave 2 (frontend charts) can now import recharts:
```typescript
import { LineChart, BarChart, ... } from 'recharts';
```

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

All stubs in `backend/tests/test_metrics.py` are intentional TDD seeds (RED state). They will be resolved by Wave 1 implementation. Not applicable to UI rendering — these are test-only stubs.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. Test file uses Django TestCase DB isolation (auto-rollback). No production secrets referenced.

## Self-Check: PASSED

- `frontend/package.json` contains "recharts": FOUND
- `frontend/package-lock.json` contains "node_modules/recharts": FOUND
- `backend/tests/test_metrics.py` exists (216 lines): FOUND
- Commit d4dd9e9d exists: FOUND
- Commit ec2ad65b exists: FOUND
- `npm ls recharts` shows recharts@3.8.1: VERIFIED
- All 10 test stubs fail (RED): VERIFIED
- Existing 58 tests pass (green): VERIFIED
