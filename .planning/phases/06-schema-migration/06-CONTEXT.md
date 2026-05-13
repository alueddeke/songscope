# Phase 6: Schema Migration - Context

**Gathered:** 2026-05-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Add 4 new fields to `DailyGem` in a single Django migration (`0008_...`). Zero logic changes. No data migration required — existing rows survive with defaults (`{}` / `null`). Phase ends when `python manage.py migrate` succeeds and ORM round-trip tests pass.

Fields to add:
- `score_breakdown` — JSONField, `default=dict`
- `score_total` — FloatField, `null=True, blank=True`
- `was_saved` — BooleanField, `null=True, blank=True`
- `taste_vector_snapshot` — JSONField, `null=True, blank=True`

</domain>

<decisions>
## Implementation Decisions

### Test Coverage

- **D-01:** Write pytest ORM round-trip tests for all 4 new fields — write + read + assert defaults, following the `TestDailyGemWasLikedSync` pattern in `backend/tests/test_feedback.py`. Add ~20 lines to `test_feedback.py`. Verifies each field survives a DB write/read cycle and that `score_breakdown` defaults to `{}` (not `None`).

### All Other Decisions — Locked by REQUIREMENTS.md

- **D-02:** One migration only — `0008_dailygem_score_breakdown_score_total_was_saved_taste_vector_snapshot`. No split migrations.
- **D-03:** No data migration for existing rows — new columns default to `{}` / `null` as designed.
- **D-04:** `score_breakdown` uses `default=dict` (callable) — not `default={}` (mutable default is a Django/Python anti-pattern).
- **D-05:** `was_saved` semantics: set to `True` in `add_track_to_liked` view (Phase 7 concern). Phase 6 only adds the field.
- **D-06:** Compound metric = `was_liked OR was_saved` (OR semantics, not AND). Locked in STATE.md.

### Claude's Discretion

- Exact migration filename (Django auto-generates from makemigrations)
- Order of field declarations in the model (add after `was_liked` for logical grouping)
- Test class name and organization within `test_feedback.py`

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §SCHEMA-01, §METRIC-01 — exact field specs, types, defaults, nullability (locked)
- `.planning/ROADMAP.md` §Phase 6 — success criteria (3 conditions that must be TRUE after migration)

### Existing Model
- `backend/apps/core/models.py` class `DailyGem` (line 280) — add 4 new fields here; `was_liked` is the closest existing nullable BooleanField to use as pattern
- `backend/apps/core/migrations/0007_spotifytoken_refresh_token_nullable.py` — most recent migration, confirms dependency chain (`"core", "0007_spotifytoken_refresh_token_nullable"`)

### Tests to Extend
- `backend/tests/test_feedback.py` class `TestDailyGemWasLikedSync` (line 69) — pattern for DailyGem ORM round-trip tests; new tests follow same structure

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `DailyGem.was_liked` (BooleanField, `null=True, blank=True`) — exact template for `was_saved` field declaration
- `UserProfile.data` JSONField — confirms JSONField is already used in the project; `default=dict` is the established pattern

### Established Patterns
- Migration dependency chain: new migration must depend on `("core", "0007_spotifytoken_refresh_token_nullable")`
- All migrations live in `backend/apps/core/migrations/` — Django auto-generates via `python manage.py makemigrations`
- Existing test ORM setup in `test_feedback.py`: `DailyGem.objects.create(user=..., track=..., date=...)` is the fixture pattern

### Integration Points
- `DailyGem` model fields added here are READ in Phase 7 (`get_daily_gem`, `add_track_to_liked`) and Phase 8 (frontend rendering)
- `score_breakdown` default `{}` means Phase 7 can safely check `if gem.score_breakdown` to distinguish populated vs legacy rows
- `taste_vector_snapshot` is `null=True` so Phase 7 can skip snapshotting without breaking existing gems

</code_context>

<specifics>
## Specific Ideas

- Round-trip tests should verify `score_breakdown` defaults to `{}` (empty dict), NOT `None` — the `default=dict` must produce `{}` on read-back, not null
- `was_saved` test: verify it accepts `True`, `False`, and `None` (nullable three-state), matching `was_liked` behavior
- Run the full existing test suite after migration to confirm zero regressions

</specifics>

<deferred>
## Deferred Ideas

- Backfilling `was_saved` for historical DailyGem rows via Spotify saved-tracks API — out of scope; existing rows stay `null`
- Model-level `compound_hit` property (`was_liked OR was_saved`) — Phase 7 concern, not needed for schema-only phase
- Any logic in `save()` / signals for `was_saved` state — Phase 7

</deferred>

---

*Phase: 06-schema-migration*
*Context gathered: 2026-05-13*
