# Phase 1: Fix & Foundation - Research

**Researched:** 2026-05-07
**Domain:** Django backend bug fixes — exclusion set design, feedback persistence, candidate pipeline
**Confidence:** HIGH (all findings verified by direct code inspection)

---

## Summary

Phase 1 is a pure bug-fix and plumbing phase with no new ML concepts. Every deliverable maps directly to a specific, locatable defect in the existing codebase. The research confirms all five bugs described in the roadmap, adds precise file/line attribution, and surfaces two additional details the roadmap description implied but did not spell out explicitly.

The core problem is that the pipeline has three independent correctness failures happening simultaneously: (1) the exclusion filter leaks known songs because it makes live API calls that can fail and fall back to incomplete cached data, (2) all feedback signals (`RecommendationLog.liked`, `DailyGem.was_liked`) are either never written or inconsistently written — leaving success-metric queries perpetually returning zero, and (3) the candidate generation pipeline is missing the `artist_related_artists` source, reducing diversity. Two Python crashes (`Count` not imported, `update_weights` called with wrong arity) prevent the personalization summary endpoint from functioning at all.

The good news: all fixes are surgical. No new models are needed. No migrations are required except if the planner chooses to add a DB-backed exclusion set (which is optional if the existing `RecommendationLog` query approach is used). The spotipy library already exposes `artist_related_artists()` so the 5th strategy is a matter of writing one new method in `hybrid_recommendation_engine.py`.

**Primary recommendation:** Fix bugs in this order — crashes first (Count import, update_weights arity), then feedback persistence (RecommendationLog.liked on submit_feedback), then exclusion set reliability, then add artist_related_artists strategy. Each fix is independent and testable in isolation.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Exclusion set (known-song filter) | API / Backend | Database / Storage | Exclusion logic lives in `hybrid_recommendation_engine.py`; persistent set lives in `RecommendationLog` + `DailyGem` DB tables |
| Feedback persistence (`liked` flag) | API / Backend | Database / Storage | `submit_feedback` view must write to `RecommendationLog.liked`; `DailyGem.was_liked` sync happens in same request |
| Candidate generation (5 strategies) | API / Backend | — | All strategy methods live inside `HybridRecommendationEngine` |
| Python crash fixes | API / Backend | — | Import error and method arity bug both in `personalization_engine.py` |
| Top-artist filter correction | API / Backend | — | Filter logic in `_filter_out_liked_songs` in `hybrid_recommendation_engine.py` |

---

## Bug Inventory (Verified by Code Inspection)

### Bug 1: `Count` not imported in `personalization_engine.py`
**File:** `backend/apps/recommendations/personalization_engine.py`
**Lines:** 313 (usage), no import statement present
**What crashes:** `get_personalization_summary()` calls `.annotate(count=Count('feedback_type'))` but `Count` is never imported from `django.db.models`.
**Fix:** Add `from django.db.models import Count` to the imports at the top of the file. [VERIFIED: direct code inspection]

### Bug 2: `update_weights` called with wrong arity in `personalization_engine.py`
**File:** `backend/apps/recommendations/personalization_engine.py`, line 264
**Calling code:** `self.preferences.update_weights(feedback, feedback.track_features)` — passing 2 args
**Target:** `self.preferences` is a `UserPreferences` instance (see line 38 of same file: `UserPreferences.objects.get_or_create(user=user)[0]`)
**Actual model:** `UserPreferences` model in `models.py` (lines 198–211) has **no** `update_weights` method at all — `__str__` is its only method
**The method `update_weights(self, weights)` exists only on `UserProfile`** (models.py line 151), which takes 1 argument, not 2
**Fix:** `apply_feedback_learning()` should either (a) be a no-op body with a `pass` + comment "weights updated via HybridEngine", or (b) do a lookup for the corresponding `UserProfile` and call `profile.update_weights(weights_dict)` with the correctly shaped dict. The roadmap says "arity fix" so option (a) is the minimal fix — silence the crash, leave the logic for Phase 2. [VERIFIED: direct code inspection]

### Bug 3: `RecommendationLog.liked` never written on thumbs-up/down
**File:** `backend/apps/core/views.py`, `submit_feedback()` function (lines 555–665)
**What happens now:** `submit_feedback` creates/deletes `UserFeedback` records and syncs `DailyGem.was_liked`, but it never finds the corresponding `RecommendationLog` entry for the track and sets `.liked = True/False`.
**Evidence:** The `get_recommendation_metrics` view (line 1139) queries `logs.filter(liked=True).count()` — this always returns 0 because `liked` is never set.
**Fix:** In `submit_feedback`, after creating `UserFeedback`, look up `RecommendationLog.objects.filter(user=request.user, track=track).order_by('-recommended_at').first()` and set `.liked = (feedback_type == 'LIKE')`, then `.save(update_fields=['liked'])`. On unlike, set `.liked = None`. [VERIFIED: direct code inspection]

### Bug 4: `DailyGem.was_liked` sync is partially implemented but NOT wired to DISLIKE
**File:** `backend/apps/core/views.py`, lines 636–643
**What happens:** `DailyGem.was_liked` is set to `(feedback_type == 'LIKE')`. This means on a LIKE it becomes `True`, on a DISLIKE it becomes `False`. This part actually works.
**Actual gap confirmed:** The sync only happens when `today_gem` is found by `DailyGem.objects.filter(user=request.user, date=tz.localdate(), track=track).first()`. If the user submits feedback on a track recommended via the general `/recommendations` endpoint (not as a DailyGem), no DailyGem row exists and the sync is silently skipped — that is expected behavior. The DailyGem sync is correctly scoped. However, the unlike path (lines 608–615) correctly sets `was_liked = None`. This sub-bug is lower priority; the primary gap is Bug 3. [VERIFIED: direct code inspection]

### Bug 5: Top-artist filter filters by artist familiarity, not track familiarity
**File:** `backend/apps/recommendations/hybrid_recommendation_engine.py`, lines 734–841
**What it does now:** `_filter_out_liked_songs()` builds `top_artist_names` from `profile.data['base_data']['top_artists']` (Spotify top artists), then filters out any recommendation whose `rec['artist']` is in that set. This removes ALL tracks by artists the user listens to most — including unknown deep cuts from those artists.
**What it should do:** The filter should target track-level familiarity: has the user saved/heard THIS specific track? Artist familiarity is a blunt proxy that throws away valid discovery candidates from familiar artists.
**Fix:** The primary exclusion should be `current_user_saved_tracks_contains()` (already implemented) plus `RecommendationLog` history lookup. The `top_artist_names` block should be removed or made optional (configurable popularity threshold). [VERIFIED: direct code inspection]

### Bug 6: Exclusion set uses runtime API calls instead of persistent DB set
**File:** `backend/apps/recommendations/hybrid_recommendation_engine.py`, `_filter_out_liked_songs()` (lines 726–842) and `get_daily_gem()` in `views.py` (lines 1043–1055)
**What happens:** The filter calls `sp.current_user_saved_tracks_contains(batch_ids)` in batches of 20 at recommendation time. If the API call fails (line 769), it falls back to the cached `saved_tracks` snapshot (which is limited to 400 tracks fetched at profile update time). Previously-recommended DailyGem tracks are NOT excluded — if the same track scores highest two days in a row, it will be re-recommended.
**Fix:** Build exclusion set from `RecommendationLog.objects.filter(user=user).values_list('track__spotify_id', flat=True)` plus `DailyGem.objects.filter(user=user).values_list('track__spotify_id', flat=True)`. Use as a pre-filter set before candidate scoring. The `current_user_saved_tracks_contains()` call in `get_daily_gem` (already a real-time check, line 1050) is good — keep it as a last-gate check for the daily gem. [VERIFIED: direct code inspection]

### Bug 7 (Missing feature): `artist_related_artists` not in hybrid engine's 4 strategies
**File:** `backend/apps/recommendations/hybrid_recommendation_engine.py`
**What exists:** 4 strategies: `_get_genre_search_recommendations`, `_get_playlist_recommendations`, `_get_artist_network_recommendations`, `_get_contextual_recommendations`
**What's missing:** A 5th strategy using `sp.artist_related_artists(artist_id)` — returns up to 20 related artists per seed artist, then pulls album deep cuts from those artists.
**Spotipy support:** `artist_related_artists(artist_id)` is confirmed present in installed spotipy 2.23.0 at `venv/lib/python3.11/site-packages/spotipy/client.py:453`. It calls `/artists/{id}/related-artists`. [VERIFIED: spotipy source code inspection]
**Note:** `track_discovery_engine.py` has a `_get_related_artists()` method (line 231) that comments "Instead of related artists (deprecated), get more tracks from the same artist" and uses `artist_top_tracks` instead. The roadmap explicitly calls for adding `artist_related_artists` — meaning the Spotify endpoint should be used directly in the hybrid engine's new 5th strategy, not via the discovery engine's workaround. [VERIFIED: direct code inspection]

---

## Standard Stack

No new libraries are required for Phase 1. All fixes use existing dependencies.

| Library | Version (installed) | Purpose | Phase 1 Usage |
|---------|---------------------|---------|---------------|
| Django | 5.1.3 | ORM, views, models | DB queries for exclusion set, model field writes |
| djangorestframework | 3.15.2 | API views | `submit_feedback` view modifications |
| spotipy | 2.23.0 | Spotify API client | `artist_related_artists()` for 5th strategy |
| django.db.models | (stdlib) | ORM aggregations | `Count` — needs import added |

[VERIFIED: backend/requirements.txt]

---

## Architecture Patterns

### Recommended Project Structure (no changes needed)
```
backend/
├── apps/
│   ├── core/
│   │   ├── models.py          — RecommendationLog, DailyGem, UserProfile
│   │   └── views.py           — submit_feedback (Bug 3 fix here)
│   └── recommendations/
│       ├── hybrid_recommendation_engine.py   — Bugs 5, 6, 7 fixes here
│       └── personalization_engine.py         — Bugs 1, 2 fixes here
```

### Pattern 1: DB-backed exclusion set (replaces runtime API calls)
**What:** Build an in-memory Python set of previously-seen Spotify track IDs from DB at the start of candidate filtering — no API calls.
**When to use:** Called once per `get_recommendations()` invocation, before scoring.
**Example:**
```python
# Source: direct codebase pattern — verified approach [VERIFIED: models.py inspection]
from apps.core.models import RecommendationLog, DailyGem

def _get_persistent_exclusion_set(self) -> set:
    """Return set of Spotify track IDs the user has already encountered."""
    logged = set(
        RecommendationLog.objects.filter(user=self.user)
        .exclude(track__spotify_id='error_log')
        .values_list('track__spotify_id', flat=True)
    )
    gemmed = set(
        DailyGem.objects.filter(user=self.user)
        .values_list('track__spotify_id', flat=True)
    )
    return logged | gemmed
```

### Pattern 2: Writing `RecommendationLog.liked` in `submit_feedback`
**What:** After creating `UserFeedback`, update the most-recent `RecommendationLog` row for the same user+track.
**When to use:** In `submit_feedback` view, after the `UserFeedback` create/delete branch.
**Example:**
```python
# Source: direct codebase pattern [VERIFIED: models.py RecommendationLog definition]
log = RecommendationLog.objects.filter(
    user=request.user, track=track
).order_by('-recommended_at').first()
if log:
    log.liked = (feedback_type == 'LIKE')
    log.save(update_fields=['liked'])
```

### Pattern 3: `artist_related_artists` as 5th candidate strategy
**What:** For each of the user's top artists, fetch related artists via Spotipy, then pull album deep cuts from those related artists (same pattern as `_get_artist_network_recommendations`).
**When to use:** After the existing 4 strategies, if rate limit allows.
**Example:**
```python
# Source: spotipy 2.23.0 client.py:453 [VERIFIED: spotipy source inspection]
related = sp.artist_related_artists(artist['id'])
for related_artist in related['artists'][:5]:
    albums = sp.artist_albums(related_artist['id'], album_type='album', limit=2, country='US')
    # ... pull tracks, filter by popularity < 40, add to candidates
```

### Anti-Patterns to Avoid
- **Batch API calls inside the filter loop:** The current `current_user_saved_tracks_contains` call in batches of 20 burns API quota on every recommendation request. Replace with DB lookup for exclusion, keep the API check only as a last-gate for the daily gem.
- **Filtering by artist name string equality:** Artist name matching is fragile (case, punctuation, aliases). Filter by Spotify track ID wherever possible.
- **Silently swallowing the `update_weights` crash:** The current try/except in `apply_feedback_learning` may hide the error. Add a `logger.warning` even if the method body becomes a no-op for Phase 1.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Exclusion set persistence | Custom table for "seen tracks" | `RecommendationLog` + `DailyGem` (already exist) | Both models already store user+track+date; querying them is a 2-line ORM call |
| Related artist discovery | Custom similarity logic | `sp.artist_related_artists(artist_id)` in spotipy | Spotify's own graph; already in the installed library |
| Feedback signal counting | Custom aggregation table | Django ORM `.filter(liked=True).count()` | Standard ORM; metrics view already written, just needs the field populated |

---

## Common Pitfalls

### Pitfall 1: `get_or_create` not re-raising on exclusion set miss
**What goes wrong:** When building the exclusion set from `RecommendationLog`, if a `Track` row exists in the DB but its `spotify_id` is `'error_log'` (the error sentinel created in `log_error()`), it will appear in the exclusion set and may incorrectly block a legitimate recommendation if another track somehow gets that ID.
**Why it happens:** `RecommendationLog.log_error()` creates a fake Track with `spotify_id='error_log'`. This sentinel bleeds into any unfiltered query.
**How to avoid:** Always `.exclude(track__spotify_id='error_log')` when building the exclusion set. The metrics view already does this (views.py line 1131). [VERIFIED: direct code inspection]

### Pitfall 2: `update_weights` arity fix must not silently discard future Phase 2 work
**What goes wrong:** If `apply_feedback_learning()` is made a no-op, future Phase 2 work that extends it may assume the call was working all along.
**How to avoid:** Add a `# TODO Phase 2: implement taste vector update here` comment with a `logger.info("apply_feedback_learning: no-op in Phase 1, wired in Phase 2")` so it's obvious the method was intentionally left empty.

### Pitfall 3: Django ORM `values_list` returns lazy QuerySet — call `set()` immediately
**What goes wrong:** `RecommendationLog.objects.filter(...).values_list('track__spotify_id', flat=True)` returns a QuerySet, not a Python set. Using `in` on it for each candidate triggers N+1 SQL queries.
**How to avoid:** Wrap the call in `set(...)` to materialize it once: `exclusion_ids = set(RecommendationLog.objects.filter(...).values_list(...))`

### Pitfall 4: `DailyGem` unique_together constraint will crash on duplicate date insert
**What goes wrong:** `DailyGem` has `unique_together = ['user', 'date']`. If `get_daily_gem` is called twice concurrently for the same user on the same day, the second `DailyGem.objects.create()` will raise an `IntegrityError`.
**Why it happens:** Race condition between checking `existing` and creating the gem.
**How to avoid:** Use `get_or_create` instead of `create`, or wrap in a `try/except IntegrityError`. [VERIFIED: models.py line 288]

### Pitfall 5: `artist_related_artists` returns artists without `id` field if Spotify API deprecates it
**What goes wrong:** The roadmap notes this as "5th candidate source" — the endpoint is present in spotipy 2.23.0 but there have been deprecation warnings in Spotify's changelog. If it returns an empty `artists` list (soft deprecation), the strategy silently produces 0 candidates.
**How to avoid:** Add a `logger.info(f"artist_related_artists returned {len(related['artists'])} artists for {artist['name']}")` so the log shows if the strategy is producing candidates.

---

## Code Examples

### Fix for Count import (Bug 1)
```python
# Add to personalization_engine.py imports section
# Source: Django ORM docs [ASSUMED — standard Django pattern, trivial fix]
from django.db.models import Count
```

### Fix for update_weights arity (Bug 2)
```python
# Replace in personalization_engine.py apply_feedback_learning()
# Source: direct codebase inspection [VERIFIED]
def apply_feedback_learning(self, feedback: UserFeedback):
    """
    Update user preferences based on new feedback.
    Phase 1: no-op — taste vector update wired in Phase 2.
    """
    # TODO Phase 2: build weights_dict from feedback and call
    #   UserProfile(user=self.user).update_weights(weights_dict)
    logger.info(
        f"apply_feedback_learning: Phase 1 no-op for {feedback.feedback_type} "
        f"on {feedback.track.name}"
    )
```

### Fix for RecommendationLog.liked (Bug 3)
```python
# In submit_feedback(), after the UserFeedback create/delete logic:
# Source: direct codebase inspection [VERIFIED]
log = RecommendationLog.objects.filter(
    user=request.user, track=track
).order_by('-recommended_at').first()
if log:
    log.liked = (feedback_type == 'LIKE') if feedback_type in ('LIKE', 'DISLIKE') else None
    log.save(update_fields=['liked'])
```

### Exclusion set from persistent DB (Bug 6)
```python
# In HybridRecommendationEngine, new helper method:
# Source: direct codebase inspection [VERIFIED: both models exist with correct fields]
def _get_persistent_exclusion_set(self) -> set:
    from apps.core.models import RecommendationLog, DailyGem
    logged = set(
        RecommendationLog.objects
        .filter(user=self.user)
        .exclude(track__spotify_id='error_log')
        .values_list('track__spotify_id', flat=True)
    )
    gemmed = set(
        DailyGem.objects
        .filter(user=self.user)
        .values_list('track__spotify_id', flat=True)
    )
    return logged | gemmed
```

### 5th strategy: artist_related_artists
```python
# New method in HybridRecommendationEngine:
# Source: spotipy 2.23.0 client.py:453 [VERIFIED]
def _get_related_artist_recommendations(self, limit: int) -> list:
    recommendations = []
    top_artists = self.profile.data['base_data'].get('top_artists', [])
    sp = self._get_spotify_client()
    if not sp:
        return []
    for artist in top_artists[:4]:
        if not self._check_rate_limit() or len(recommendations) >= limit:
            break
        artist_id = artist.get('id')
        if not artist_id:
            continue
        try:
            related = sp.artist_related_artists(artist_id)
            logger.info(
                f"artist_related_artists: {len(related['artists'])} related "
                f"to {artist['name']}"
            )
            for rel_artist in related['artists'][:5]:
                albums = sp.artist_albums(
                    rel_artist['id'], album_type='album', limit=2, country='US'
                )
                for album in albums['items']:
                    album_tracks = sp.album_tracks(album['id'], limit=8)
                    track_ids = [t['id'] for t in album_tracks['items'] if t.get('id')]
                    if not track_ids:
                        continue
                    full_tracks = sp.tracks(track_ids)
                    for track in full_tracks['tracks']:
                        if track and track.get('popularity', 100) < 40:
                            recommendations.append({
                                'id': track['id'],
                                'name': track['name'],
                                'artist': track['artists'][0]['name'],
                                'album': album['name'],
                                'preview_url': track.get('preview_url'),
                                'image_url': album['images'][0]['url'] if album.get('images') else None,
                                'source': 'related_artists',
                                'score': 0.0,
                                'popularity': track.get('popularity', 0),
                            })
                            if len(recommendations) >= limit:
                                break
        except Exception as e:
            logger.warning(f"artist_related_artists failed for {artist.get('name')}: {e}")
            continue
    return recommendations[:limit]
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `sp.recommendations()` (seed-based) | Genre search + artist network (Phase 1 uses) | Removed ~2024 when Spotify deprecated the endpoint | `test_spotify_recommendations` confirms it is broken (views.py:418). Do not use. |
| `sp.audio_features()` | Not available | ~2024 Spotify API deprecation | Cannot extract per-track audio features. Phase 1 is unaffected. Phase 2 must work without it. |
| `_get_related_artists()` in track_discovery_engine | Replaced with `artist_top_tracks` (comment says "instead of related artists") | Workaround added by developer | The workaround avoids `artist_related_artists`. Roadmap explicitly calls for adding it back in hybrid engine — test it to confirm it still works on current API. |

[ASSUMED for the "deprecated" claims: The deprecation of `sp.recommendations()` and audio features is inferred from code comments in the codebase (views.py line 584: "without audio features since API is broken", track_discovery_engine.py line 247: "Instead of related artists (deprecated)"). Verified by the running system check returning 0 errors, meaning the app loads — the endpoints simply return 4xx at runtime.]

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | Django backend | ✓ | 3.11.7 | — |
| Django | All backend fixes | ✓ | 5.1.3 (requirements.txt) | — |
| spotipy | artist_related_artists strategy | ✓ | 2.23.0 (installed in venv) | — |
| pytest + pytest-django | Test suite | ✓ | pytest 8.3.4 (discovered) | — |
| SQLite DB | ORM queries | ✓ | bundled with Python | — |

[VERIFIED: direct tool checks, requirements.txt, venv inspection]

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3.4 + pytest-django 4.9.0 |
| Config file | None — Wave 0 gap |
| Quick run command | `cd backend && python -m pytest tests/ -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -v` |

### Known Test Breakage
The two broken tests (`tests/test_ai_feedback_service.py`, `tests/backup/test_openai.py`) both use `os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')` — but from inside `backend/`, the correct module path is `config.settings`, not `backend.settings`. This is the stale import path bug called out in STATE.md.

### Phase Requirements → Test Map
| Behavior | Test Type | Automated Command | File Exists? |
|----------|-----------|-------------------|-------------|
| `Count` import works — `get_personalization_summary()` does not crash | unit | `pytest tests/test_personalization.py -x` | Wave 0 gap |
| `apply_feedback_learning()` does not crash on call | unit | `pytest tests/test_personalization.py -x` | Wave 0 gap |
| `RecommendationLog.liked` is set after submit_feedback LIKE | unit | `pytest tests/test_feedback.py -x` | Wave 0 gap |
| `RecommendationLog.liked` is cleared (None) after submit_feedback unlike | unit | `pytest tests/test_feedback.py -x` | Wave 0 gap |
| Exclusion set contains previously-recommended track IDs | unit | `pytest tests/test_exclusion.py -x` | Wave 0 gap |
| `_get_related_artist_recommendations()` returns non-empty list | integration (mock) | `pytest tests/test_candidates.py -x` | Wave 0 gap |
| Existing broken tests pass with corrected settings module path | unit | `pytest tests/test_ai_feedback_service.py tests/test_openai_integration.py -x` | Exists (broken) |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/ -x -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ -v`
- **Phase gate:** Full suite green before verify-work

### Wave 0 Gaps
- [ ] `backend/pytest.ini` — set `DJANGO_SETTINGS_MODULE = config.settings`
- [ ] `backend/tests/test_personalization.py` — covers Count import + update_weights arity
- [ ] `backend/tests/test_feedback.py` — covers RecommendationLog.liked write on LIKE/unlike
- [ ] `backend/tests/test_exclusion.py` — covers DB-backed exclusion set
- [ ] `backend/tests/test_candidates.py` — covers artist_related_artists strategy (mocked spotipy)
- [ ] Fix existing: `tests/test_ai_feedback_service.py` line 28 — change `'backend.settings'` to `'config.settings'`

---

## Open Questions (RESOLVED)

1. **Is `artist_related_artists` actually returning results on the current Spotify API?**
   - What we know: The endpoint exists in spotipy 2.23.0. The track_discovery_engine previously used a workaround suggesting it was unreliable at some point.
   - What's unclear: Whether `/artists/{id}/related-artists` is still functional on the current Spotify Developer API or returns 404/empty.
   - Recommendation: The first task of the 5th-strategy implementation should be a quick manual smoke test: call `sp.artist_related_artists(some_known_artist_id)` and log the result count. If it returns 0 or 404, fall back to the existing `artist_top_tracks` approach.
   - **RESOLVED:** Handled via graceful degradation — `_get_related_artist_recommendations` returns empty list if endpoint returns 0 results; pipeline continues with 4 other strategies unaffected. Liveness to be confirmed manually per VALIDATION.md manual-only verification.

2. **Should the top-artist filter be removed entirely, or kept with a reduced scope?**
   - What we know: It currently filters out any track from a user's top-20 artists, even deep cuts. This is incorrect per the roadmap.
   - What's unclear: The intent may have been to filter tracks the user has heavily listened to — i.e., very popular tracks from familiar artists. Some form of artist-level filter may still have value.
   - Recommendation: Remove the `top_artist_names` block from `_filter_out_liked_songs` entirely for Phase 1. The DB exclusion set + `current_user_saved_tracks_contains` real-time check provides correct track-level filtering without artist-level bluntness.
   - **RESOLVED:** Remove `top_artist_names` block entirely from `_filter_out_liked_songs`. DB exclusion set + real-time `current_user_saved_tracks_contains` guard in `views.py:get_daily_gem` provides correct track-level precision. Implemented in Plan 01-03 Task 1-03-01.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `sp.recommendations()` and `sp.audio_features()` are deprecated/broken on the current Spotify API | State of the Art | Low — code comments and view logic confirm workarounds were added; wrong only if Spotify re-enabled them |
| A2 | `artist_related_artists` endpoint still functions on current Spotify API | Bug 7 / 5th strategy | Medium — if it returns empty, the strategy adds no value; needs smoke test in Wave 0 |

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `backend/apps/recommendations/hybrid_recommendation_engine.py` — all 986 lines read
- Direct code inspection: `backend/apps/core/models.py` — full file read
- Direct code inspection: `backend/apps/core/views.py` — full file read (1171 lines)
- Direct code inspection: `backend/apps/recommendations/personalization_engine.py` — full file read
- Direct code inspection: `backend/venv/lib/python3.11/site-packages/spotipy/client.py:453` — `artist_related_artists` signature confirmed
- `backend/requirements.txt` — dependency versions confirmed

### Secondary (MEDIUM confidence)
- `.planning/ROADMAP.md` — phase deliverables used to prioritize bug significance
- `.planning/STATE.md` — blocker list cross-referenced with code findings

---

## Metadata

**Confidence breakdown:**
- Bug identification: HIGH — every bug confirmed by direct line-number inspection
- Fix patterns: HIGH — all patterns use existing ORM methods and installed libraries
- 5th strategy viability: MEDIUM — `artist_related_artists` in spotipy confirmed, but live API availability needs smoke test
- Test infrastructure: HIGH — pytest discovered, broken paths identified with exact fix

**Research date:** 2026-05-07
**Valid until:** 2026-06-07 (stable Django/spotipy stack; Spotify API deprecation risk is the main expiry vector)
