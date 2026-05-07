---
phase: 01-fix-foundation
plan: "01"
subsystem: backend/test-infrastructure
tags:
  - django
  - pytest
  - test-infrastructure
dependency_graph:
  requires: []
  provides:
    - pytest-infrastructure
    - test-stub-personalization
    - test-stub-feedback
    - test-stub-recommendation
  affects:
    - backend/tests/
    - backend/apps/core/models.py
    - backend/apps/core/migrations/
tech_stack:
  added:
    - pytest with pytest-django
    - django.test.TestCase for ORM rollback
  patterns:
    - conftest.py shared Django setup
    - unittest.TestCase for pure-mock tests
    - django.test.TestCase for ORM-touching tests
key_files:
  created:
    - backend/pytest.ini
    - backend/tests/conftest.py
    - backend/tests/test_personalization.py
    - backend/tests/test_feedback.py
    - backend/tests/test_recommendation.py
    - backend/apps/core/migrations/0004_recommendationlog_track_popularity_and_more.py
    - backend/apps/core/migrations/0005_dailygem_image_url_dailygem_preview_url.py
  modified:
    - backend/tests/__init__.py
    - backend/tests/test_ai_feedback_service.py
    - backend/tests/test_openai_integration.py
    - backend/tests/run_tests.py
    - backend/apps/core/models.py
decisions:
  - "norecursedirs = backup added to pytest.ini — backup/ directory contains stale songscope.* imports that cannot resolve in the new project layout"
  - "DailyGem model added to models.py from main repo unstaged changes — plan interfaces block required it; migrations 0004/0005 brought in to support ORM tests"
  - "All three stub test files use conftest-provided Django setup; no per-file django.setup() calls per plan constraints"
metrics:
  duration_minutes: 15
  completed_date: "2026-05-07"
  tasks_completed: 3
  tasks_total: 3
  files_created: 7
  files_modified: 5
---

# Phase 1 Plan 01: pytest infrastructure and test stubs — SUMMARY

**One-liner:** pytest-django infrastructure with `config.settings`, `norecursedirs=backup`, and RED-state stub tests for all three Bug clusters (personalization/feedback/recommendation).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create pytest configuration and shared conftest | 0f36c6a5 | backend/pytest.ini, backend/tests/__init__.py, backend/tests/conftest.py |
| 2 | Fix broken test_ai_feedback_service.py settings path | 5ab4778a | backend/tests/test_ai_feedback_service.py, backend/tests/test_openai_integration.py, backend/tests/run_tests.py |
| 3 | Create test stub files for personalization, feedback, and recommendation | c09bd585 | backend/tests/test_personalization.py, backend/tests/test_feedback.py, backend/tests/test_recommendation.py, backend/apps/core/models.py, migrations 0004/0005 |

## Verification

```
cd backend && python -m pytest tests/ --collect-only -q
```

Result: **31 tests collected, 0 errors** — no ImportError, no ModuleNotFoundError, no ImproperlyConfigured.

All four test files discover cleanly: `test_ai_feedback_service.py`, `test_personalization.py`, `test_feedback.py`, `test_recommendation.py`.

## Success Criteria Check

- [x] `backend/pytest.ini` exists with `DJANGO_SETTINGS_MODULE = config.settings`
- [x] `backend/tests/conftest.py` exists and calls `django.setup()` exactly once
- [x] `backend/tests/__init__.py` exists
- [x] No file under `backend/tests/` (excluding `backup/`) references `'backend.settings'`
- [x] Three new stub test files exist with all required test class names
- [x] `cd backend && python -m pytest tests/ --collect-only -q` exits 0
- [x] Plan 02 and Plan 03 can run automated verify commands and observe RED -> GREEN transitions

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocker] Added `norecursedirs = backup` to pytest.ini**
- **Found during:** Task 1 verification
- **Issue:** `backup/test_openai.py` imports `from songscope.ai_feedback_service import ...` which cannot resolve in the current project layout, causing collection to abort with exit code 2
- **Fix:** Added `norecursedirs = backup .git __pycache__ *.egg-info` to `backend/pytest.ini`
- **Files modified:** `backend/pytest.ini`
- **Commit:** 0f36c6a5

**2. [Rule 3 - Blocker] Fixed `backend.settings` in `test_openai_integration.py` and `run_tests.py`**
- **Found during:** Task 2 — grep scan per plan instructions found two additional stale references beyond `test_ai_feedback_service.py`
- **Issue:** Plan said to fix "any other file in backend/tests/ (excluding backup/) that references 'backend.settings'"
- **Fix:** Replaced `'backend.settings'` with `'config.settings'` in both files
- **Files modified:** `backend/tests/test_openai_integration.py`, `backend/tests/run_tests.py`
- **Commit:** 5ab4778a

**3. [Rule 3 - Blocker] Added `DailyGem` model to `apps/core/models.py` and brought in migrations 0004/0005**
- **Found during:** Task 3 collection — `ImportError: cannot import name 'DailyGem' from 'apps.core.models'`
- **Issue:** Plan's `<interfaces>` block explicitly lists `DailyGem`; the model existed in main repo unstaged changes and untracked migration files but was not committed, so the worktree's committed `models.py` lacked it
- **Fix:** Appended `DailyGem` model class to `models.py` (matching main repo definition); wrote migrations 0004 and 0005 as committed files so `TestCase` DB rollback can create the table
- **Files modified:** `backend/apps/core/models.py`
- **Files created:** `backend/apps/core/migrations/0004_recommendationlog_track_popularity_and_more.py`, `backend/apps/core/migrations/0005_dailygem_image_url_dailygem_preview_url.py`
- **Commit:** c09bd585

## Known Stubs

All three stub test files (`test_personalization.py`, `test_feedback.py`, `test_recommendation.py`) intentionally contain RED-state tests that WILL FAIL when run — this is by design. Plans 02 and 03 turn them GREEN by implementing the fixes.

The `test_personalization.py::TestCountImport::test_count_is_imported_in_personalization_engine` assertion (`hasattr(personalization_engine, 'Count')`) will fail until Plan 02 adds `from django.db.models import Count` at module scope.

The `test_recommendation.py::TestRelatedArtistStrategy::test_method_exists_on_engine` will fail until Plan 03 adds `_get_related_artist_recommendations` to `HybridRecommendationEngine`.

These stubs are intentional and correctly document the RED state before downstream plans.

## Threat Surface Scan

No new network endpoints, auth paths, or trust-boundary-crossing file access patterns introduced. All files are test infrastructure only. `conftest.py` wraps `.env` load in `try/except` per T-01-01 mitigation. ORM tests inherit from `django.test.TestCase` per T-01-03 mitigation.

## Self-Check: PASSED

All created files verified to exist on disk. All three task commits verified in git log.
