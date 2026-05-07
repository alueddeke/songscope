---
phase: 02-user-taste-vector-real-scoring
reviewed: 2026-05-07T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - backend/apps/core/migrations/0006_recommendationlog_source.py
  - backend/apps/core/models.py
  - backend/apps//core/views.py
  - backend/apps/recommendations/hybrid_recommendation_engine.py
  - backend/tests/test_recommendation_scoring.py
findings:
  critical: 3
  warning: 5
  info: 3
  total: 11
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-05-07T00:00:00Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Reviewed the Phase 2 implementation: taste vector construction, cosine similarity scoring, the locked `_score_recommendations` formula, the new `related_artists` strategy, the `RecommendationLog.source` migration, and the accompanying test suite.

The core algorithmic additions (taste vector, cosine similarity, score formula) are correctly implemented and well-tested. The migration is clean. However, three blockers were found: a data-integrity crash in `submit_ai_feedback` when no track is associated, a logic bug in `remove_feedback` that permanently leaks liked artists into the preference store (unlike never removes them), and a null-pointer crash in `_get_playlist_recommendations` for playlists containing local/removed Spotify tracks. Five warnings cover additional correctness gaps and one security issue in production settings.

---

## Critical Issues

### CR-01: `submit_ai_feedback` crashes with IntegrityError when no track is associated

**File:** `backend/apps/core/views.py:689-691`

**Issue:** `AIFeedback.track` is a non-nullable `ForeignKey` (models.py:216). In `submit_ai_feedback`, `track` is initialized to `None` (line 669) and remains `None` in two cases: (1) the caller omits `track_id` entirely (serializer returns `''`, `if track_id:` on line 670 is falsy), and (2) `track_id` is provided but the `Track` does not exist in the DB (exception caught at line 678, `track` stays `None`). `AIFeedback.objects.create(track=None, ...)` then raises `IntegrityError`, which is swallowed by the outer except and returned as a generic 500. The endpoint is therefore broken for all AI feedback submitted without a pre-existing Track record.

**Fix:**
```python
# Option A: guard before create
if track is None:
    return JsonResponse(
        {'error': 'Track not found; cannot store AI feedback without a track.'},
        status=400
    )
ai_feedback = AIFeedback.objects.create(
    user=request.user,
    track=track,
    ...
)

# Option B (longer term): make AIFeedback.track nullable
track = models.ForeignKey(Track, on_delete=models.CASCADE, null=True, blank=True)
```

---

### CR-02: `remove_feedback` never removes the artist from `liked_artists` — logic bug via wrong dict key

**File:** `backend/apps/recommendations/hybrid_recommendation_engine.py:882-886`

**Issue:** The walrus operator assigns the entire feedback-history entry to the local variable `track_info`:

```python
if track_info := next((fb for fb in feedback_history if fb.get('track_id') == track_id), None):
    artist_name = track_info.get('artist')   # BUG
```

Feedback history entries (created by `UserProfile.add_feedback`, models.py:98-103) have the structure:
```python
{
    'track_id': '...',
    'feedback_type': 'LIKE',
    'timestamp': '...',
    'track_info': {'artist': 'Great Band', ...}   # artist is NESTED here
}
```

`track_info.get('artist')` looks at the top-level entry and always returns `None`. The artist is never removed from `liked_artists`, causing the preference store to grow permanently — every liked artist accumulates even after the user unlikes the track. Over time this corrupts the `feedback_multiplier` in `_score_recommendations` for all users with any unlike history.

**Fix:**
```python
if entry := next((fb for fb in feedback_history if fb.get('track_id') == track_id), None):
    artist_name = entry.get('track_info', {}).get('artist')  # correct path
    if artist_name and artist_name in liked_artists:
        liked_artists.remove(artist_name)
        self.profile.data['preferences']['liked_artists'] = liked_artists
```

---

### CR-03: Null-track crash in `_get_playlist_recommendations` for local files and removed tracks

**File:** `backend/apps/recommendations/hybrid_recommendation_engine.py:400-401`

**Issue:** The Spotify API returns `item['track'] = None` for playlist items that are local files or tracks that have been removed from Spotify. The code accesses `track['id']` on the very next line with no null guard:

```python
track = item['track']
if track['id'] not in saved_track_ids:  # TypeError if track is None
```

Any user whose playlist contains even one local file will hit a `TypeError` here. The inner `try/except` (line 418) catches it per-playlist, silently skipping the whole playlist — but this means all playlist tracks (not just the null one) are lost for that iteration, degrading recommendation quality without any visible signal beyond a `WARNING` log.

**Fix:**
```python
for item in playlist_tracks['items']:
    track = item.get('track')
    if not track or not track.get('id'):  # guard against null/local tracks
        continue
    if track['id'] not in saved_track_ids:
        recommendations.append({...})
```

---

## Warnings

### WR-01: `add_track_to_liked` endpoint has no authentication decorator

**File:** `backend/apps/core/views.py:772`

**Issue:** Every other view that handles user data uses either `@login_required` or `@api_view(['POST']) @permission_classes([IsAuthenticated])`. `add_track_to_liked` has neither. It is registered in `config/urls.py:54` and is publicly reachable. An unauthenticated request results in `AnonymousUser` being passed to `SpotifyToken.objects.get(user=request.user)`, which raises `SpotifyToken.DoesNotExist` (returned as 404), but the intent is clearly to require authentication, and the missing decorator is a defence gap.

**Fix:**
```python
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_track_to_liked(request):
```

---

### WR-02: `_update_profile_data` writes to `profile.data['base_data']` without guaranteeing the key exists

**File:** `backend/apps/recommendations/hybrid_recommendation_engine.py:271, 303, 319, 357`

**Issue:** `_get_or_create_profile` initializes `profile.data['base_data'] = {}` only for newly created profiles. For existing profiles loaded from the DB, if `'base_data'` is absent (e.g., profiles created by a migration, test, or earlier code version), the direct write `self.profile.data['base_data']['top_artists'] = [...]` raises `KeyError`. This path is triggered on every profile update cycle for any legacy user.

**Fix:** Add a `setdefault` guard at the top of `_update_profile_data`, before calling the sub-update methods:
```python
self.profile.data.setdefault('base_data', {})
self.profile.data.setdefault('preferences', {
    'liked_artists': [], 'disliked_artists': [], 'feedback_history': []
})
```

---

### WR-03: `_update_saved_tracks` uses `limit=1000` but Spotify API caps at 50 per request

**File:** `backend/apps/recommendations/hybrid_recommendation_engine.py:291`

**Issue:** The docstring comment says "Get ALL saved tracks" and the code comment says "increase limit significantly", but `sp.current_user_saved_tracks(limit=1000)` silently receives only 50 results — the Spotify REST API max is 50 per call. The exclusion set built from `saved_tracks` is therefore incomplete for users with more than 50 liked songs, which causes already-liked tracks to appear in recommendations. This directly undermines the filtering logic in `_filter_out_liked_songs` / `_get_persistent_exclusion_set`.

**Fix:** Use pagination (Spotipy's `next()` helper) or rely exclusively on the DB-backed `_get_persistent_exclusion_set` (which is already correct) and remove the redundant in-memory `saved_track_ids` set in `_get_playlist_recommendations`:
```python
results = sp.current_user_saved_tracks(limit=50)
tracks = results['items']
while results['next']:
    results = sp.next(results)
    tracks.extend(results['items'])
```

---

### WR-04: `submit_feedback` does not handle `SpotifyToken.DoesNotExist`

**File:** `backend/apps/core/views.py:533`

**Issue:** Every other view that fetches a `SpotifyToken` wraps the `.get()` call in a dedicated `except SpotifyToken.DoesNotExist` handler that returns a 404 with a clear message. `submit_feedback` uses `SpotifyToken.objects.get(user=request.user)` on line 533 but has no such specific handler — `DoesNotExist` falls through to the blanket `except Exception` on line 651, returning a generic 500 ("Failed to submit feedback") instead of an actionable 404. This makes debugging harder and exposes misleading error semantics to the caller.

**Fix:**
```python
try:
    spotify_token = SpotifyToken.objects.get(user=request.user)
except SpotifyToken.DoesNotExist:
    return JsonResponse({'error': 'Spotify token not found'}, status=404)
if spotify_token.is_expired():
    spotify_token = refresh_spotify_token(spotify_token)
```

---

### WR-05: Hardcoded Django `SECRET_KEY` committed to version control

**File:** `backend/config/settings.py:34`

**Issue:** (Observed during cross-file context load.) The settings file contains:
```python
SECRET_KEY = "django-insecure-2nagt=pfbkp%5#u*^r4bwjenk2b_3a)ly-y*656vzx%qvzv6v="
```
This key is committed to the repository. Django uses `SECRET_KEY` to sign session cookies, CSRF tokens, and password reset tokens. Any party with access to the repository can forge these values. `DEBUG = True` is also hardcoded, which exposes full stack traces and the interactive debugger to anyone who can reach a 500 error in staging/production.

**Fix:**
```python
SECRET_KEY = config('SECRET_KEY')   # load from environment / .env only
DEBUG = config('DEBUG', default=False, cast=bool)
```
Rotate the leaked key immediately.

---

## Info

### IN-01: `get_simple_recommendations` returns hardcoded fake tracks and is deployed to production

**File:** `backend/apps/core/views.py:473-510`

**Issue:** This endpoint was written for testing and returns three static, hardcoded Spotify tracks with placeholder preview and image URLs (`https://p.scdn.co/mp3-preview/...`, `https://i.scdn.co/image/...`). It is registered in `config/urls.py:43` under `/api/simple-recommendations/` with `@permission_classes([IsAuthenticated])`. A client that calls this route will receive broken media URLs. The endpoint should either be removed or replaced with a real fallback.

**Fix:** Remove the URL registration and the view, or replace the view body with a real implementation that calls `_get_fallback_recommendations`.

---

### IN-02: `test_results_sorted_descending` uses identical track IDs for both fixture records

**File:** `backend/tests/test_recommendation_scoring.py:185-190`

**Issue:** Both `_make_rec(...)` calls produce `{'id': 'track_x', ...}`. The test calls `_score_recommendations` directly so `_remove_duplicates` is not in the path and the test passes. However, passing these fixtures through the real `get_recommendations` pipeline would silently drop one candidate, meaning the test does not verify production-path ordering. The fixture should use distinct IDs.

**Fix:**
```python
recs = [
    {**_make_rec(artist='Low Score Band', popularity=99), 'id': 'track_low'},
    {**_make_rec(artist='High Score Band', popularity=0),  'id': 'track_high'},
]
```

---

### IN-03: `test_spotify_recommendations` debug endpoint shipped to production with hardcoded seed track ID

**File:** `backend/apps/core/views.py:408-470` / `backend/config/urls.py:42`

**Issue:** The endpoint makes live Spotify API calls (twice for the same hardcoded track ID `0c6xIDDpzE81m2q797ordA`), logs detailed internal diagnostic output, and is registered at `/api/test-spotify-recommendations/`. It is auth-protected, but it burns API quota on every call and exposes internal diagnosis information in the response body. It should be removed before production release.

**Fix:** Remove the view and its URL registration, or gate it behind `settings.DEBUG`.

---

_Reviewed: 2026-05-07T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
