---
phase: "02"
plan: "02-02"
subsystem: backend/data-model
tags: [django, models, migrations, recommendation-logging, source-tracking]
dependency_graph:
  requires: []
  provides: [RecommendationLog.source, migration-0006, source-wired-at-call-site]
  affects: [backend/apps/core/models.py, backend/apps/core/views.py]
tech_stack:
  added: []
  patterns: [django-addfield-migration, backward-compatible-classmethod-kwarg]
key_files:
  created:
    - backend/apps/core/migrations/0006_recommendationlog_source.py
  modified:
    - backend/apps/core/models.py
    - backend/apps/core/views.py
decisions:
  - "source field uses blank=True default='' to keep all existing callers working without update"
  - "choices are advisory (forms only); unknown strategies write '' via default — no crash risk (T-02-09)"
  - "D-11 boundary maintained: no win-rate or strategy_stats query logic added in Phase 2"
metrics:
  duration_minutes: 8
  completed_date: "2026-05-07"
  tasks_completed: 3
  tasks_total: 3
  files_created: 1
  files_modified: 2
---

# Phase 02 Plan 02: RecommendationLog Source Field Summary

## One-liner

Added `source` CharField to `RecommendationLog`, generated and applied Django migration 0006, and wired `source=track.get('source', '')` through the `log_recommendation()` call site in views.py — every new recommendation log now records which candidate strategy produced it.

## What Was Built

Three atomic changes were made:

1. **Model field** (`backend/apps/core/models.py`): Added `source = models.CharField(max_length=50, blank=True, default='')` after `was_novel` on `RecommendationLog`. Updated `log_recommendation(cls, user, track, source='')` signature and body to persist the value. Backward-compatible default preserves all existing callers.

2. **Migration** (`backend/apps/core/migrations/0006_recommendationlog_source.py`): Django-generated `AddField` operation. Applied cleanly — `python manage.py migrate --check` exits 0. Existing rows receive `''` (empty string default); no data destroyed.

3. **Call site** (`backend/apps/core/views.py` line ~336): Changed `RecommendationLog.log_recommendation(request.user, track_obj)` to `RecommendationLog.log_recommendation(request.user, track_obj, source=track.get('source', ''))`. The `processed_track` dict already carries `'source'` from each of the 5 candidate generation strategies.

## Verification Results

- `RecommendationLog._meta.get_field('source')` returns `core.RecommendationLog.source` (max_length=50, blank=True, default='')
- `python manage.py migrate --check` exits 0
- `python manage.py check` exits 0, no errors
- `grep log_recommendation backend/apps/core/views.py` shows `source=track.get('source', '')` argument
- No `win_rate` or `strategy_stats` logic present (D-11 boundary intact)

## Deviations from Plan

None — plan executed exactly as written.

## Task Commits

| Task | Description | Commit |
|------|-------------|--------|
| T1 | Add source field to RecommendationLog model | 280d4229 |
| T2 | Generate and apply Django migration 0006 | 420100dc |
| T3 | Wire source at log_recommendation() call site | 26456439 |

## Known Stubs

None. All three changes are fully wired; the source value flows from candidate generation through to the DB row on every recommendation request.

## Threat Flags

No new security surface introduced. Changes are internal Django model field additions with ORM-parameterized writes (T-02-06, T-02-07, T-02-08, T-02-09 all mitigated as documented in plan threat model).
