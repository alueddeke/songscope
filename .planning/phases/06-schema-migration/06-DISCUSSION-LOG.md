# Phase 6: Schema Migration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-13
**Phase:** 06-schema-migration
**Areas discussed:** Test coverage

---

## Test Coverage

| Option | Description | Selected |
|--------|-------------|----------|
| Round-trip tests | Write pytest ORM tests for all 4 new fields (write + read + assert defaults), following was_liked pattern in test_feedback.py. ~20 lines. | ✓ |
| Migration only | Run `python manage.py migrate` + existing full suite as regression check. No new test code. | |
| One smoke test | One test that creates a DailyGem with all 4 new fields and asserts they save correctly. | |

**User's choice:** Round-trip tests
**Notes:** No additional context provided — selected first option.

---

## Claude's Discretion

- Exact migration filename (Django auto-generates)
- Order of field declarations in model (add after was_liked)
- Test class name and organization within test_feedback.py

## Deferred Ideas

- Backfilling was_saved for historical rows via Spotify saved-tracks API — deferred (existing rows stay null)
- Model-level compound_hit property — Phase 7
- Any save() signal logic for was_saved — Phase 7
