# Domain Pitfalls

**Domain:** Adding explainability + compound success metric to an existing Django REST / Next.js ML recommendation app
**Researched:** 2026-05-13
**Scope:** SongScope v1.1 milestone — score component persistence, "added to liked songs" compound metric, explanation UX, formula-explanation drift, SQLite field additions

---

## Critical Pitfalls

Mistakes that cause rewrites, silent metric corruption, or user-facing bugs.

---

### Pitfall 1: Persisting Score Components Breaks the Cached-Branch Contract

**What goes wrong:**
`get_daily_gem` has two branches: a cached branch that returns an existing `DailyGem` row immediately, and a fresh branch that scores and writes a new row. If you add `score_breakdown` as a column on `DailyGem`, the cached branch currently returns `score_breakdown: {}` — a hardcoded empty dict (views.py lines 1060, 1123). After migration, callers will see populated scores on the first request, then `{}` on every subsequent same-day request. The frontend will silently show "score unknown" for all cached gems.

**Root cause:** The cached branch short-circuits before any scoring happens. Score components are computed in `_score_recommendations()` (hybrid_recommendation_engine.py line 831), not stored anywhere persistent right now. Adding a DB column does nothing to fix the cached branch's return value.

**Consequences:** Frontend shows the breakdown on day-1 load, then shows nothing after the page refreshes. Metrics dashboard silently loses data for all historical gems.

**Prevention:** When adding any `score_breakdown` field (JSON or separate floats) to `DailyGem`, update all three return sites in `get_daily_gem`: the cached-branch early return (line 1048), the race-condition fallback return (line 1110), and the fresh-branch return (line 1126). Use a shared serializer helper that reads from the DB row so all branches produce identical schema.

**Detection:** Test by requesting the gem twice in the same day and asserting `score_breakdown` is non-empty on both calls.

---

### Pitfall 2: Historical Rows Get NULL Score Components — Metrics Break Retroactively

**What goes wrong:**
Adding `genre_sim`, `novelty`, `feedback_multiplier` as nullable float columns (or a JSON field) to `DailyGem` or `RecommendationLog` means all existing rows get `NULL`. Any aggregate query over those columns — average genre_sim over time, improvement curve, per-source score distribution — silently returns `NULL` or skews toward recent records only. This includes anything in `get_recommendation_metrics` (views.py lines 404-493).

**Root cause:** Django migrations for new columns default to `null=True, blank=True` on existing rows. There is no back-fill mechanism in place, and back-filling historical data is impossible because the score components were never persisted.

**Consequences:** Learning curve charts break because the baseline period (first 7 gems) has NULL scores. Per-source analysis is meaningless. The "compound success" queries silently exclude all pre-migration history.

**Prevention:** Accept the epoch boundary explicitly. Add a `score_schema_version` field or use the migration date as a filter boundary in all metrics queries. Document in code comments: "scores only available for gems created after migration 0008". Never `coalesce(score, 0)` in metrics queries — that false-fills historical zeros, making pre-migration gems look like score-zero failures.

**Detection:** After migration, write a management command that counts rows with NULL score components and logs a warning if the ratio exceeds a threshold.

---

### Pitfall 3: Formula-Explanation Drift — The Score Says One Thing, UI Says Another

**What goes wrong:**
The locked formula is `0.4*genre_sim + 0.3*novelty + 0.3*feedback_multiplier` (hybrid_recommendation_engine.py line 883). The Thompson Sampling multiplier is applied **after** as a post-score multiplier (line 887): `rec['score'] *= source_weights.get(...)`. If the explanation template says "your genre match accounts for 40% of this recommendation," that is only accurate before the bandit multiplier is applied. After the multiplier, the effective contribution of each component shifts depending on the source weight. An explanation that ignores the bandit multiplier is technically lying.

**Root cause:** The final score is `(0.4*gs + 0.3*n + 0.3*fm) * source_weight`. The `score_breakdown` dict (line 875) is populated **before** the post-score multiply, so the stored breakdown represents the un-multiplied formula, not the final ranking score.

**Consequences:** If source_weight for `playlist_mining` is 0.6 (bandit is uncertain about it), a playlist-mined track scores 60% of its formula score. The UI explaining "genre match: 72%" is accurate for the formula-score but not for why that track ranked above others.

**Prevention:** Either (a) store the final score and the source_weight as separate breakdown fields so the UI can say "source weight applied: 0.6x" or (b) lock the explanation to the pre-bandit formula components and add a footnote: "source discovery method also influenced ranking." Option (a) is more honest. Option (b) is simpler and defensible at portfolio scale. Choose one consciously — do not leave it undocumented.

**Detection:** Add an assertion in the scoring unit tests: `sum(component_weights) + source_weight_contribution == final_score` (within float tolerance).

---

### Pitfall 4: "Added to Liked Songs" as a Compound Metric — False Positive Failure Mode

**What goes wrong:**
The compound success proxy is: played 30s preview + user clicked "add to liked songs" (Spotify library save via `add_track_to_liked`, views.py line 829). The false positive case: user clicks "add to liked" on a track they already know from another context (a friend recommended it, they saw it on a playlist). The gem gets credit for a success it did not cause. At single-user portfolio scale with a small sample, even 1-2 false positives distort the learning signal.

The false negative case: user genuinely loves the gem but does not save it because they prefer to listen on repeat for a week before saving. Or they already have it in a playlist. `DailyGem.was_liked` stays `None` — the Thompson Sampling bandit treats this as no signal, not as a positive. If the 30s preview play is not tracked, a user who played the preview 5 times before deciding registers as zero engagement.

**Root cause:** The current `add_track_to_liked` endpoint fires a Spotify API call and returns, but does NOT update `DailyGem.was_liked` or `RecommendationLog.liked`. That sync only happens in `submit_feedback` (views.py lines 677-694). "Added to liked songs" and "submitted LIKE feedback" are two separate user actions with separate code paths, and neither calls the other.

**Consequences:** The compound metric (listened + saved) is untracked. `DailyGem.was_liked` reflects only in-app thumbs up/down, not Spotify library saves. The feature is built but the metric is dark.

**Prevention:** In `add_track_to_liked`, after the Spotify API call succeeds, also set `DailyGem.was_liked = True` for today's gem if `track_id` matches. Also set `RecommendationLog.liked = True`. Add a `was_saved_to_spotify` BooleanField to `DailyGem` so the compound metric can be: `was_played AND (was_liked OR was_saved_to_spotify)` — distinguishing in-app signal from external save signal. Do not conflate them into a single field.

**Detection:** Add a test: call `add_track_to_liked` and assert `DailyGem.was_saved_to_spotify` is True.

---

### Pitfall 5: Explanation NLG Over-Engineering Trap

**What goes wrong:**
The existing `explanation` field on `DailyGem` is a `TextField(blank=True)` — currently stored as `''`. The temptation is to build an OpenAI call into `get_daily_gem` that generates a natural-language explanation from the score breakdown. This has three failure modes:

1. **Latency:** `get_daily_gem` is already a multi-step Spotify API call → scoring → DB write path. Adding a synchronous OpenAI call makes it the slowest endpoint.
2. **Cost creep:** The project has a `$1/day` OpenAI budget for feedback interpretation. Generating one explanation per gem per day is cheap, but the explanation fires even on cache-miss refreshes.
3. **Prompt drift:** The prompt has to encode the score formula. When the formula changes (it will), the prompt goes stale and generates wrong explanations. This is the explanation-formula drift problem in micro.

**The correct alternative:** Use a deterministic template string. Given `score_breakdown = {genre_sim: 0.82, novelty: 0.31, feedback_multiplier: 1.5}`, produce: "Strong genre match (82%) + liked artist bonus — moderate novelty (31%)." This is O(1), zero latency, zero cost, and stays synchronized with the formula by construction because it reads the same `score_breakdown` dict.

**Root cause of over-engineering:** Treating "explanation" as a UX copy problem (needs to sound natural) rather than a data display problem (needs to be accurate).

**Prevention:** Write the explanation as a pure function `format_explanation(score_breakdown: dict) -> str` in Python, called in `get_daily_gem` before the response is built. No OpenAI. No template engine. One function. Test it with unit tests for boundary cases (zero genre_sim, feedback_multiplier=0.5 for disliked artist, etc.).

**Detection:** If you find yourself writing a prompt that references "genre match percentage," stop. That's a template masquerading as NLG.

---

### Pitfall 6: SQLite Write Contention on Recommendation Path

**What goes wrong:**
SQLite uses file-level write locking. The `get_track_recommendations` endpoint (views.py line 253) calls `RecommendationLog.log_recommendation()` for every track in the processed list (lines 324-336) — up to 10 individual `INSERT` statements in a loop, each acquiring and releasing the write lock. Adding new fields (`genre_sim`, `novelty`, `feedback_multiplier`) to `RecommendationLog` does not change lock behavior but does increase row size and write frequency if score persistence is added inside this loop.

The more serious risk: `_score_recommendations()` mutates the candidate dict in-place (adds `score_breakdown` key). If score persistence is added to the recommendation path as a DB write inside the scoring loop, that is N writes inside a hot path that already does M writes. At portfolio scale (single user, low concurrency) SQLite will handle this — but if the recommendation path is ever profiled, this will show up as a bottleneck.

**Root cause:** SQLite's `WAL` mode (Write-Ahead Logging) mitigates read/write concurrency but does nothing for write/write contention. Portfolio scale means this is not an operational risk today, but it creates bad patterns that will survive to a Postgres migration.

**Prevention:** Batch all `RecommendationLog` inserts into a single `bulk_create()` call after the scoring loop, not individual creates inside it. If score components need to be persisted in `RecommendationLog`, add them as nullable fields and populate them in the same bulk insert, not as a separate update pass. Do not add `UPDATE` calls to the scoring loop.

**Detection:** In development, enable Django's `LOGGING` for `django.db.backends` and check that the recommendation endpoint generates a bounded number of SQL statements (not proportional to candidate count).

---

### Pitfall 7: score_breakdown JSON Field vs Separate Float Columns — Migration Ambiguity

**What goes wrong:**
Two design choices exist for persisting score components in `DailyGem`:
- Option A: A single `score_breakdown = JSONField(default=dict)` on `DailyGem`
- Option B: Three separate float columns: `score_genre_sim`, `score_novelty`, `score_feedback_multiplier`

Choosing Option A (JSON) means Django migration is one line, no data type constraints, easy to extend. But querying `DailyGem.objects.filter(data__genre_sim__gt=0.5)` on SQLite requires JSONField traversal, which uses `json_extract()` — supported in SQLite 3.38+ but slower than indexed float columns.

Choosing Option B means three nullable float columns with three separate migrations, but `filter(score_genre_sim__gt=0.5)` is a standard indexed query.

**Root cause:** Not deciding this upfront causes a migration mid-milestone (adding columns you forgot, renaming fields).

**Prevention:** For this project at portfolio scale, Option A (single JSONField) is correct. There are no complex filter queries over individual score components — the metrics are computed over `was_liked`, not over score breakdowns. Use JSON, document the schema inline in the model's `help_text`, and move on.

**Detection:** If you write a queryset that filters on `score_breakdown__genre_sim__gt`, switch to annotating with `Value()` or computing in Python — you do not need DB-level filtering on score components at this scale.

---

## Moderate Pitfalls

---

### Pitfall 8: API Contract Between Backend score_breakdown and Frontend Breaks Silently

**What goes wrong:**
`get_daily_gem` already returns `score_breakdown: {}` in the cached branch and `score_breakdown: gem_data.get('score_breakdown', {})` in the fresh branch (views.py lines 1060, 1139). The frontend `Recommendation` component (visible in the git diff) needs to render this. If the backend changes the shape of `score_breakdown` (e.g., adds `source_weight` key, renames `feedback_multiplier` to `artist_boost`), the frontend silently renders missing fields.

**Prevention:** Define the `score_breakdown` shape as a TypeScript interface in the frontend. Use optional chaining (`breakdown?.genre_sim ?? 0`) for all field reads. Write one backend test that asserts the exact keys returned in the fresh-branch response. If the shape changes, the backend test breaks, not production.

---

### Pitfall 9: "Play" Event Not Captured — Compound Metric is Incomplete

**What goes wrong:**
The compound success metric requires: played AND (liked/saved). The `was_played` half of the compound is not tracked anywhere in the current schema. `DailyGem` has `was_liked` and `was_skipped` but no `was_played`. `UserFeedback.feedback_type` includes `'PLAY'` as a choice (models.py line 185) but there is no endpoint that sets it and no view that calls `feedback_type='PLAY'`.

Without tracking play, the compound metric degrades to: liked/saved (which is what `was_liked` already is). You do not get the "listened to" signal that distinguishes a genuine discovery from an accidental click.

**Prevention:** Add `was_played = BooleanField(default=False)` to `DailyGem`. Add a lightweight endpoint `POST /api/gem/played/` that sets `was_played = True` for today's gem. Fire it from the frontend AudioPlayer when the 30s preview plays past a threshold (e.g., 10 seconds of audio). This is a single migration, one endpoint, one frontend event. Without it the compound metric is a single signal, not compound.

**Detection:** The compound hit rate `DailyGem.objects.filter(was_played=True, was_liked=True).count()` returns zero until `was_played` is tracked.

---

### Pitfall 10: Thompson Sampling Bandit Stats Not Updated on Compound Success

**What goes wrong:**
The Thompson Sampling bandit (hybrid_recommendation_engine.py lines 89-140) reads `source_stats` from `UserProfile.data`. Successes (`s`) are incremented when a LIKE is submitted. But the bandit's definition of "success" for the v1.1 milestone is supposed to be the compound metric (played + saved), not just liked. If only LIKE events increment `s`, the bandit learns from a weaker signal than intended.

**Prevention:** When the compound success event fires (both `was_played = True` AND `was_liked/was_saved = True`), also increment `source_stats[source]['s']` for the source that generated that gem. Add a `DailyGem.source` field (FK or CharField) that captures which of the 5 candidate sources generated the gem, so the compound success can be attributed back to the right bandit arm. Currently `DailyGem` has no `source` field — the source lives in `RecommendationLog.source` but the linkage to `DailyGem` requires a join through `Track`.

**Detection:** Check `UserProfile.data['source_stats']` after 10 like/dislike cycles. If `s + f` values look right but you never see compound successes attributed, the bandit is not learning from the compound metric.

---

## Minor Pitfalls

---

### Pitfall 11: DailyGem.explanation Is Overwritten on Force-Refresh

**What goes wrong:**
`get_daily_gem` uses `get_or_create` with `defaults={'explanation': ''}`. On a force-refresh (`?force_new=true`), the code clears the cache, calls `get_or_create` again, and writes a new explanation if `created=True`. But if the DailyGem row already exists for today (created earlier), `get_or_create` returns `created=False` and does not update the explanation. The stale explanation stays. This is actually safe behavior, but it means the explanation is never updated after the first creation — even if the score breakdown changes on a re-score.

**Prevention:** Decide once: explanations are immutable after creation (correct for a daily gem UX). Document this explicitly. If you want mutable explanations, use `update_or_create` with `explanation` in `defaults`.

---

### Pitfall 12: score_breakdown in Cache Is Stale After Profile Update

**What goes wrong:**
`UserProfile.data['cache']` stores the full recommendation list including `score_breakdown` per track. If the taste vector updates (after a LIKE event, via `apply_feedback_learning` in personalization_engine.py), the cached recommendations still carry the old score breakdowns. The fresh-branch `get_daily_gem` response will show the old genre_sim score until the cache expires or `force_fresh=True` is called.

**Prevention:** When `apply_feedback_learning` updates the taste vector, also clear the recommendation cache (`profile.clear_cache()`). This is already done for force-refresh but not for taste-vector updates triggered by feedback. Add `profile.clear_cache()` at the end of `apply_feedback_learning`.

---

### Pitfall 13: null=True on New Float Columns Creates Ambiguity

**What goes wrong:**
If you add nullable float score component columns (instead of JSON), a `NULL` value can mean two different things: (a) this gem was created before the migration, or (b) the score computation failed and the fallback returned an unscored gem. You cannot distinguish the two without additional metadata.

**Prevention:** Add a boolean `is_scored = BooleanField(default=False)` alongside any score float columns. Set `is_scored=True` only when all three components are successfully computed. Use `is_scored=False` as the filter condition for "has no score data," not `NULL` checks.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Schema migration for score persistence | Pitfall 1 (cached branch returns empty breakdown), Pitfall 2 (NULL history) | Update all 3 return sites; document epoch boundary |
| Explanation UX implementation | Pitfall 5 (NLG over-engineering), Pitfall 3 (formula drift) | Use deterministic template function; store `source_weight` in breakdown |
| Compound success metric wiring | Pitfall 4 (add_to_liked not syncing was_liked), Pitfall 9 (no was_played tracking) | Update `add_track_to_liked` endpoint; add `was_played` field and endpoint |
| Bandit feedback closure | Pitfall 10 (bandit not receiving compound signal), Pitfall 4 (two separate code paths) | Add `DailyGem.source` field; route compound success to bandit update |
| SQLite field additions | Pitfall 6 (bulk_create pattern), Pitfall 7 (JSON vs float columns) | Use JSONField + bulk_create; no writes inside scoring loop |
| Frontend integration | Pitfall 8 (API contract drift) | TypeScript interface for score_breakdown; backend contract test |
| Cache coherence | Pitfall 12 (stale score in cache post-feedback) | clear_cache() in apply_feedback_learning |

---

## Sources

- Code analysis: `backend/apps/core/views.py`, `backend/apps/recommendations/hybrid_recommendation_engine.py`, `backend/apps/core/models.py`, `backend/apps/recommendations/recommendation_engine.py`, `backend/apps/recommendations/personalization_engine.py`
- Schema state: `backend/apps/core/migrations/` (migrations 0001–0007)
- Project context: `.planning/PROJECT.md`
- Confidence: HIGH for all pitfalls — every finding is grounded in specific line references from the existing codebase, not general domain knowledge.
