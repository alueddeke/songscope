# Testing
_Last updated: 2026-05-06_

## Summary
SongScope has minimal test coverage. Zero frontend tests exist. Backend has a small unittest-based suite (not pytest) covering only `ai_feedback_service.py`. No CI/CD pipeline. Several tests reference a stale module path and likely cannot run in the current project layout.

## Test Framework
- **Backend:** Python `unittest` (standard library) — no pytest
- **Frontend:** No test framework configured, no test files
- **CI/CD:** None — no `.github/workflows/` directory

## Test File Locations
```
backend/
├── tests/
│   ├── run_tests.py          # Test runner: python backend/tests/run_tests.py [unit|integration|django]
│   ├── test_ai_feedback.py   # Unit tests for AI feedback service
│   ├── test_integration.py   # Integration tests
│   └── test_django.py        # Django-specific tests
├── test_ai_service.py        # Ad-hoc script at backend root
└── test_recommendations.py   # Ad-hoc script at backend root
```

## How to Run
```bash
python backend/tests/run_tests.py unit
python backend/tests/run_tests.py integration
python backend/tests/run_tests.py django
```

## Coverage
| Module | Tested |
|--------|--------|
| `apps/ai/ai_feedback_service.py` | Partial |
| `apps/core/views.py` | None |
| `apps/core/models.py` | None |
| `apps/recommendations/hybrid_recommendation_engine.py` | None |
| All frontend code | None |

## Critical Issue: Stale Module Paths
Tests in `backend/tests/` reference `songscope.ai_feedback_service` — the old module path. The module has moved to `apps.ai.ai_feedback_service`. Unit tests likely fail to import and cannot run without fixing this import path.

## Mocking Patterns
Tests mock Spotify API calls and OpenAI API calls via `unittest.mock.patch`. No database fixtures used in unit tests.

## Key Observations
- Near-zero test coverage overall — only AI feedback service has any tests
- Module path mismatch makes existing tests likely broken
- No CI means broken tests go undetected
- Frontend has no testing infrastructure at all
- Ad-hoc scripts at backend root (`test_ai_service.py`, `test_recommendations.py`) are exploratory, not part of the test suite
