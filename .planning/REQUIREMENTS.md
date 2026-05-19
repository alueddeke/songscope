# SongScope — Milestone v1.1 Requirements
# Explainability + Feedback Loop Closure

_Created: 2026-05-13_

## v1.1 Requirements

### Score Breakdown Persistence

- [ ] **SCHEMA-01**: `DailyGem` model gains `score_breakdown` (JSONField, `default=dict`), `score_total` (FloatField, nullable), and `taste_vector_snapshot` (JSONField, nullable) — one migration, no data migration required for existing rows
- [ ] **SCHEMA-02**: `HybridRecommendationEngine` writes `score_breakdown` dict and `score_total` float into `DailyGem` at creation time (fresh-generation branch)
- [ ] **SCHEMA-03**: `taste_vector_snapshot` is captured from `UserProfile.data['taste_vector']` at recommendation time and persisted to `DailyGem` — records what the model "knew" when it made each pick
- [ ] **SCHEMA-04**: All 3 return sites in `get_daily_gem` (cached branch, lines ~1048/1110/1126) return persisted `score_breakdown` from DB instead of hardcoded `{}`

### Explanation

- [ ] **EXPLAIN-01**: `_build_gem_explanation(breakdown, track_name, artist_name) -> str` pure function produces a human-readable sentence from the dominant score component and source — no OpenAI call, zero API cost, zero latency risk
- [ ] **EXPLAIN-02**: `DailyGem.explanation` is populated at creation time via `_build_gem_explanation` (field already exists in model and renders in frontend)
- [ ] **EXPLAIN-03**: Frontend gem card shows 3 labeled score bars (genre match %, novelty %, feedback influence %) rendered from `score_breakdown` data returned by the `get_daily_gem` API

### Compound Success Metric

- [ ] **METRIC-01**: `DailyGem` gains `was_saved` BooleanField (nullable) — set to `True` in `add_track_to_liked` after a successful Spotify library save (failure is non-fatal, must not 500 the save action)
- [ ] **METRIC-02**: `compound_hit_rate` (`was_liked OR was_saved`) is computed and exposed in the `/api/recommendation-metrics/` endpoint
- [ ] **METRIC-03**: `MetricsStrip` UI displays compound hit rate alongside existing `gem_acceptance_rate`

### Documentation

- [x] **DOCS-01**: `CONCEPTS.md` updated with: score breakdown persistence rationale, `taste_vector_snapshot` purpose (offline evaluation), compound metric definition (`OR` semantics and why)
- [x] **DOCS-02**: `SYSTEM_DESIGN.md` updated with new `DailyGem` fields, `_build_gem_explanation` data flow, and compound hit signal wiring diagram

---

## Future Requirements (deferred)

- Preview-play proxy — unreliable; Spotify returning `null` `preview_url` on many tracks as of late 2024
- Evaluation dashboard — learning curve, per-source win rates, A/B framework (v1.2)
- Audio feature proxy via AcousticBrainz/Last.fm (v1.3)
- Collaborative filtering + Postgres migration (v1.4)
- Production deployment (vDeploy)

---

## Out of Scope

- OpenAI-generated explanation text for score breakdown — introduces latency, burns budget, and creates formula-prompt drift. Deterministic template only.
- Spotify playback state tracking — deprecated for third-party apps as of Feb 2026
- `compound = AND` (was_liked AND was_saved) — too sparse for single-user daily-gem app; OR semantics chosen

---

## Traceability

| REQ-ID | Phase |
|--------|-------|
| SCHEMA-01 | Phase 6 |
| SCHEMA-02 | Phase 7 |
| SCHEMA-03 | Phase 7 |
| SCHEMA-04 | Phase 7 |
| EXPLAIN-01 | Phase 7 |
| EXPLAIN-02 | Phase 7 |
| EXPLAIN-03 | Phase 8 |
| METRIC-01 | Phase 6 |
| METRIC-02 | Phase 7 |
| METRIC-03 | Phase 8 |
| DOCS-01 | Phase 9 |
| DOCS-02 | Phase 9 |
