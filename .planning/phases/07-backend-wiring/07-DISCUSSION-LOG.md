# Phase 7: Backend Wiring - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-14
**Phase:** 07-backend-wiring
**Areas discussed:** Explanation text format, was_saved gem lookup, Metrics denominator, Score persistence location

---

## Explanation Text Format

| Option | Description | Selected |
|--------|-------------|----------|
| Genre-forward | "Matches your [genre] taste — genre similarity: 82%" with % exposed | ✓ |
| Affinity summary | "Picked because it aligns with your listening habits" — warmer, no numbers | |
| Score-first | Shows all 3 components as mini-dashboard, no sentence | |

**User's choice:** Genre-forward (when genre_sim dominant)

| Option | Description | Selected |
|--------|-------------|----------|
| Discovery angle | "A hidden gem — low popularity score makes it a genuine discovery" | ✓ |
| Novelty score explicit | "Novelty score: 78% — this track is under the radar" | |
| Contrast framing | "Different from your usual picks — high novelty, broader than your top genres" | |

**User's choice:** Discovery angle (when novelty dominant)

| Option | Description | Selected |
|--------|-------------|----------|
| Feedback-forward | "You've liked [artist] before — that feedback boosted this pick" | ✓ |
| Artist-forward | "From an artist you already love" | |
| You decide | Leave template to Claude's discretion | |

**User's choice:** Feedback-forward (when feedback_multiplier dominant)

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — append source | Append "via [strategy]" to every explanation | ✓ |
| No — score component only | Keep explanation to dominant score signal only | |

**User's choice:** Always append source strategy

**Notes:** User wants ML mechanism visible to users and interviewers. Genre %, feedback loop closure, and source provenance all contribute to interview talking points.

---

## was_saved Gem Lookup

| Option | Description | Selected |
|--------|-------------|----------|
| Today's gem only | filter(user=..., date=today, track__spotify_id=track_id) | ✓ |
| Any matching gem (all time) | filter(user=..., track__spotify_id=track_id) — all past gems | |

**User's choice:** Today's gem only

| Option | Description | Selected |
|--------|-------------|----------|
| Silent no-op | No log, no error if no match found | ✓ |
| Log a warning | logger.warning('was_saved: no matching DailyGem...') | |

**User's choice:** Silent no-op

**Notes:** Failure to write was_saved must never affect the Spotify save response (non-fatal per REQUIREMENTS.md).

---

## Metrics Denominator

| Option | Description | Selected |
|--------|-------------|----------|
| All gems | total = all DailyGem rows; nulls = misses | ✓ |
| Only gems with any outcome | total = gems where was_liked IS NOT NULL OR was_saved IS NOT NULL | |

**User's choice:** All gems (consistent with how gem_acceptance_rate is computed)

**Notes:** Simpler, honest formula — missing signal = not a hit.

---

## Score Persistence Location

| Option | Description | Selected |
|--------|-------------|----------|
| View: get_or_create defaults | Pass all 4 fields as defaults={...} — single DB write | ✓ |
| View: two-step (get_or_create then save) | get_or_create then gem.save(update_fields=[...]) — two writes | |
| Engine: embed in gem_data | HybridRecommendationEngine includes taste_vector_snapshot in candidate dicts | |

**User's choice:** View: get_or_create defaults (single write)

| Option | Description | Selected |
|--------|-------------|----------|
| Read gem fields directly | Replace {} with gem.score_breakdown / gem.explanation at cached sites | ✓ |
| Refresh from DB | gem.refresh_from_db() before cached return | |

**User's choice:** Read gem fields directly (no extra round-trip)

**Notes:** View already has all data needed: gem_data from engine (breakdown + score), engine.profile.data for taste vector, _build_gem_explanation for explanation.

---

## Claude's Discretion

- Exact placement of `_build_gem_explanation` (module-level in views.py vs utils module)
- Genre name extraction approach — fallback to "your listening taste" if no genre name available
- Test class naming for new tests

## Deferred Ideas

- Backfilling was_saved for historical gems via Spotify saved-tracks API — out of scope
- Rolling window for compound_hit_rate — deferred to evaluation dashboard (v1.2)
- Model-level `compound_hit` property on DailyGem — not needed; compute inline in metrics view
