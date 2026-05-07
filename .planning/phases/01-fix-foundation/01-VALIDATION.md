---
phase: 1
slug: fix-foundation
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-07
updated: 2026-05-07
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pytest.ini` (Wave 0 installs) |
| **Quick run command** | `cd backend && python -m pytest tests/ -x -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/ -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01-01 | 0 | test-infra | T-01-02 | pytest config sets DJANGO_SETTINGS_MODULE=config.settings | infra | `cd backend && python -m pytest tests/ --collect-only -q` | ✅ Wave 0 | ⬜ pending |
| 1-01-02 | 01-01 | 0 | test-infra | T-01-01 | settings module path corrected; .env load is optional | infra | `cd backend && python -m pytest tests/test_ai_feedback_service.py --collect-only -q` | ✅ Wave 0 | ⬜ pending |
| 1-01-03 | 01-01 | 0 | test-stub-personalization, test-stub-feedback, test-stub-recommendation, dailygem-sync-verified | T-01-03 | TestCase rollback ensures no test-data pollution | infra | `cd backend && python -m pytest tests/test_personalization.py tests/test_feedback.py tests/test_recommendation.py --collect-only -q` | ✅ Wave 0 | ⬜ pending |
| 1-02-01 | 01-02 | 1 | count-import, update-weights | T-02-03 | apply_feedback_learning no-op cannot escalate | unit | `cd backend && python -m pytest tests/test_personalization.py -x -q` | ✅ Wave 0 | ⬜ pending |
| 1-02-02 | 01-02 | 1 | liked-write, dailygem-sync-verified | T-02-01, T-02-04 | user-scoped ORM filter; bounded `.first()` query | unit | `cd backend && python -m pytest tests/test_feedback.py -x -q` | ✅ Wave 0 | ⬜ pending |
| 1-03-01 | 01-03 | 1 | exclusion-set, artist-filter, reclog-exclusion | T-03-01, T-03-04 | user-scoped ORM filter; sentinel exclusion; finite per-user set | unit | `cd backend && python -m pytest tests/test_recommendation.py::TestPersistentExclusionSet tests/test_recommendation.py::TestFilterOutLikedSongs -x -q` | ✅ Wave 0 | ⬜ pending |
| 1-03-02 | 01-03 | 1 | related-artists | T-03-03, T-03-05 | bounded loops + rate-limit gate; `.get()` defaults fail closed | unit | `cd backend && python -m pytest tests/test_recommendation.py::TestRelatedArtistStrategy -x -q` | ✅ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Plan structure:** 3 plans (01, 02, 03). Wave 0 = Plan 01-01 (test infra). Wave 1 = Plans 01-02 + 01-03 (parallel; disjoint `files_modified`).

**Sampling continuity check:** No 3 consecutive tasks lack `<automated>` verify — every task above has an automated command. Nyquist gate: passes.

---

## Wave 0 Requirements

- [x] `backend/pytest.ini` — configure DJANGO_SETTINGS_MODULE=config.settings, testpaths, python_files (Task 1-01-01)
- [x] `backend/tests/__init__.py` — test package init (Task 1-01-01)
- [x] `backend/tests/conftest.py` — shared Django setup fixture (Task 1-01-01)
- [x] `backend/tests/test_ai_feedback_service.py` — settings path corrected (Task 1-01-02)
- [x] `backend/tests/test_personalization.py` — stubs for Count import + apply_feedback_learning arity (Task 1-01-03)
- [x] `backend/tests/test_feedback.py` — stubs for `RecommendationLog.liked` write + `DailyGem.was_liked` sync (Task 1-01-03)
- [x] `backend/tests/test_recommendation.py` — stubs for exclusion set + artist filter + related artists (Task 1-01-03)

All Wave 0 stubs MUST exist and be `--collect-only` clean before Wave 1 plans (01-02, 01-03) run.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Spotify `artist_related_artists` endpoint live | related-artists strategy | Requires live Spotify OAuth token; soft-deprecation risk per RESEARCH Open Question 1 | Call `sp.artist_related_artists(<known_artist_id>)` in Django shell, verify non-empty response. Record finding in 01-03-SUMMARY.md. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (test files exist as stubs after Plan 01-01)
- [x] No watch-mode flags
- [x] Feedback latency < 30s (full suite ~10s)
- [x] Per-Task Verification Map references only existing plan IDs (01-01, 01-02, 01-03)
- [x] Wave assignments correct (01-01 = wave 0; 01-02 + 01-03 = wave 1, parallel)
- [x] `nyquist_compliant: true` set in frontmatter
- [x] `wave_0_complete: true` set in frontmatter (Plan 01-01 IS Wave 0; once it executes, all stub files exist)

**Approval:** approved
