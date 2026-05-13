# SongScope Backend — Full Audit Review

**Date:** 2026-05-13  
**Scope:** Django + ML recommendation system, full backend  
**Depth:** Deep (cross-file analysis, call-chain tracing, ML correctness)  
**Files Reviewed:** 11 source files, 8 test files

---

## Summary

The backend has a working skeleton but contains several correctness defects ranging from
in-production data corruption risks (duplicate feedback records, scoring formula drift
under post-score mutation) to security gaps (unguarded OAuth state fixation, missing
CSRF on the login route, unauthenticated token refresh path). The ML layer has specific
bugs in the Thompson sampling normalisation logic, a scoring formula that is silently
mutated after scoring, and a taste-vector update that is asymmetric in a way that can
silently drive all weights to zero. Test coverage is thin at precisely the wrong places:
the feedback state machine, rate-limit and error boundaries, and the cold-start path for
every ML component are entirely untested.

---

## CRITICAL Issues

### CR-01: Score mutated after sort — final ranking is random noise

**File:** `apps/recommendations/hybrid_recommendation_engine.py:221–229`  
**Issue:** `_score_recommendations()` sorts descending by score at line 884, then returns
the sorted list to `get_recommendations()`. Back in `get_recommendations()`, the caller
adds `random.uniform(-0.1, 0.1)` to every score (line 226) and re-sorts (line 229).
This post-score perturbation is applied **after the filtering phase** (lines 232–234)
which calls `_filter_out_recently_played`, itself making a live Spotify API call. The
full sequence is:

1. Score → sort (inside `_score_recommendations`)
2. Shuffle 3× (lines 221–223)
3. Add uniform noise ±0.1 (lines 225–226)
4. Re-sort by noised score (line 229)
5. Filter liked / recently-played (lines 232–234)
6. Return `scored_recommendations[:limit]`

The uniform noise range (±0.1) is large relative to the score formula output. For a
cold-start user with no liked artists and genre_sim≈0, the base score is
`0.3 * novelty + 0.3 * 1.0 ≈ 0.3–0.6`, so the ±0.1 noise can completely invert the
order. The Thompson-sampling source multiplier (line 882) is already applied inside
`_score_recommendations`, so the final ranking does **not** reflect the model — it
reflects random shuffles with added noise.

**Why it matters:** The "best" gem recommendation is supposed to be `candidates[0]`
after `_score_recommendations` ranks them. With the perturbation the daily gem is
effectively a random pick, not the highest-scored track.

**Fix:** Remove the shuffle and score-mutation block from `get_recommendations`. If
variety is desired, inject controlled exploration at the candidate-generation stage
(e.g., epsilon-greedy) before scoring, not after.

```python
# REMOVE lines 220-229 from get_recommendations:
# for _ in range(3):
#     random.shuffle(scored_recommendations)
# for rec in scored_recommendations:
#     rec['score'] += random.uniform(-0.1, 0.1)
# scored_recommendations.sort(key=lambda x: x['score'], reverse=True)
```

---

### CR-02: OAuth state fixation — CSRF on the Spotify login initiation route

**File:** `apps/core/views.py:45–55`  
**Issue:** `spotify_login` is not decorated with any authentication or CSRF protection.
The `state` parameter is stored in `request.session['oauth_state']` on line 54, which
works correctly — but the route itself has no `@require_http_methods(["GET"])` guard
and is not protected by `@ensure_csrf_cookie`. More critically, the `spotify_callback`
view on line 64 reads `state = request.session.get('oauth_state')` and passes it to
`OAuth2Session(state=state)`. An attacker who can force a victim's browser to visit
`/spotify-login/` and then intercept the code in the callback can hijack the OAuth
flow if session cookies are not `Secure` / `HttpOnly`. The settings confirm
`SESSION_COOKIE_SECURE = False` and `CSRF_COOKIE_SECURE = False`, leaving both cookies
transmissible over plain HTTP.

**Why it matters:** In non-localhost deployment, any HTTP observer can steal the OAuth
code and the session cookie. Even in production behind HTTPS, the `CSRF_TRUSTED_ORIGINS`
list only includes `http://localhost:3000` (plain HTTP), which means the same-origin
check does not extend to HTTPS origins.

**Fix:**

1. Set `SESSION_COOKIE_SECURE = True` and `CSRF_COOKIE_SECURE = True` for production
   (use `config('SESSION_COOKIE_SECURE', default=False, cast=bool)`).
2. Add `CSRF_TRUSTED_ORIGINS = ['https://your-production-domain.com']` for production.
3. Add `@require_http_methods(["GET"])` to `spotify_login`.

---

### CR-03: Thompson sampling normalisation produces weights that do NOT sum to 1.0 in mixed cold-start/warm mode

**File:** `apps/recommendations/hybrid_recommendation_engine.py:119–141`  
**Issue:** In `get_recommendation_weights()`, when some sources are in cold-start
(n < 3) and others are warm, `thetas` is built by mixing static weights (e.g., 0.3)
with Beta samples (e.g., 0.85). The function then normalises `thetas` so the values
sum to 1.0. This is the correct approach. However, the normalised weights are then used
on line 882 as a **multiplier** applied post-score:

```python
rec['score'] *= source_weights.get(rec.get('source', ''), 1.0)
```

When the Thompson weights are normalised to sum to 1.0 across 5 sources, each
individual weight is approximately 0.2. This multiplier **reduces all scores by ~80%**
relative to the cold-start path (which returns `1.0` per source). The warm-start path
is therefore penalised relative to the cold-start path — as a source accumulates more
observations and transitions from cold-start to Beta sampling, its scores decrease.

**Why it matters:** The bandit is working backwards: the more data it has, the more it
penalises that source. After enough user interactions, all sources converge to weights
near 0.2, and recommendations degrade compared to cold-start.

**Fix:** Either (a) do not normalise when using as a multiplier — return raw Beta
samples or a relative weight (largest source gets 1.0, others scaled proportionally),
or (b) apply source weights as a relative multiplier instead of an absolute one:

```python
# Option (b): normalise to max=1.0 (not sum=1.0)
max_weight = max(thetas.values()) or 1.0
result = {k: v / max_weight for k, v in thetas.items()}
```

---

### CR-04: Feedback toggle creates duplicate UserFeedback rows for different types

**File:** `apps/core/views.py:600–660`  
**Issue:** The submit_feedback view has a toggle path for LIKE→unlike at line 606, and
an `update_or_create` path for other types at line 648. The `unique_together = ['user',
'track']` constraint on `UserFeedback` means only one feedback record can exist per
user+track pair.

The bug: the "unlike" branch at line 600 explicitly filters for
`feedback_type='LIKE'` before checking `if feedback_type == 'LIKE' and existing_feedback`.
If the user previously submitted DISLIKE (not LIKE), `existing_feedback` will be
`None`, and the code falls through to the `else` branch which calls `update_or_create`
correctly. So far so good.

However, the `prior_like` check at line 641–657 is redundant with the `existing_feedback`
check at line 600 — both query `feedback_type='LIKE'` for the same user+track. This
is two DB round-trips where one suffices. More critically, if `feedback_type == 'LIKE'`
and `existing_feedback is None` (no prior LIKE), the `update_or_create` path at line 648
creates a new LIKE feedback row, then `prior_like` at line 657 is also queried. Because
`update_or_create` returned `created=True`, `prior_like` would be `None`. But if
somehow a LIKE row was created by a concurrent request between line 600 and line 648,
the `update_or_create` would update the existing row — however, `personalization_engine.
remove_feedback_learning` at line 658 would then undo the existing LIKE's taste-vector
contribution before re-applying it at line 661. The net result is: a concurrent double-
LIKE causes one full taste-vector increment to be silently reversed and reapplied
(net-zero change instead of the expected +1). This is a race condition.

**Why it matters:** Under concurrent requests (e.g., double-tap on mobile) the taste
vector will be corrupted. Also, the two duplicate DB queries waste resources on every
feedback submission.

**Fix:** Collapse the logic into a single `update_or_create` call, then branch on
`created` and on the old value of `feedback_type` to decide whether to call
`remove_feedback_learning`. Use `select_for_update()` if strict correctness is needed.

---

### CR-05: `remove_feedback_learning` uses a fixed decrement regardless of how many times a track was liked

**File:** `apps/recommendations/personalization_engine.py:325–378`  
**Issue:** `apply_feedback_learning` unconditionally increments each genre weight by
`TASTE_VECTOR_LR = 0.1` per LIKE. If the user likes the same track multiple times
(which is possible via the LIKE→unlike→LIKE cycle), each cycle increments the weight
by 0.1. `remove_feedback_learning` always decrements by exactly 0.1 regardless of
how many times the user has liked the track. After N like-unlike-like cycles, the taste
vector for that track's genres will be `N * 0.1` higher than it was before the user
interacted with the track. There is no cap and no idempotency.

Additionally, `apply_feedback_learning` only updates the taste vector — it does NOT
update `source_stats` when the feedback type is DISLIKE/SKIP and there is no
`RecommendationLog` entry for the track (e.g., manually saved track). The Thompson
bandit receives no signal in that case.

**Why it matters:** Genre weights can grow unboundedly through repeated like/unlike
cycles. A user who likes/unlikes the same indie-rock track 10 times will have an
indie-rock weight that is 1.0 higher than a user who liked it once. This corrupts
cosine similarity scores proportionally.

**Fix:**

```python
# In apply_feedback_learning: guard against re-application
existing = UserFeedback.objects.filter(
    user=self.user, track=feedback.track, feedback_type__in=('LIKE', 'SAVE')
).count()
if existing > 1:
    # Already processed this like — skip taste vector update
    return
```

Or, track the applied-increment count in `profile.data` per track and cap at 1.

---

### CR-06: `RateLimitMonitor` state is lost per request — module-level singleton is not process-safe

**File:** `apps/spotify/utils.py:142`  
**Issue:** `rate_limit_monitor = RateLimitMonitor()` is a module-level singleton. The
`RateLimitMonitor.requests` is a `collections.deque` stored in process memory. Under
Gunicorn with multiple workers, each worker has its own copy of the singleton — a
request served by worker 1 does not register in worker 2's counter. This means the
rate limit tracking allows N-workers times the intended limit.

The same issue exists for `RateLimitMonitor` in `ai_feedback_service.py` (line 18).
The `daily_cost` (line 22) and `openai_requests` (line 21) are instance variables on
a per-`FeedbackInterpreter` object, so every new request to `submit_ai_feedback` gets
a fresh `FeedbackInterpreter` with `daily_cost = 0` — the daily cost limit on line 55
is therefore **never enforced** between requests.

**Why it matters:** The OpenAI daily cost limit of $1/day is entirely ineffective.
Every request creates a new `FeedbackInterpreter`, resetting `daily_cost`. The
Spotify rate-limit is partially effective only within a single worker.

**Fix:** Move rate-limit state to a shared store (Redis, Django cache framework, or
at minimum the database). For the OpenAI cost limit, store `daily_cost` and
`last_reset` in `UserProfile.data` or a dedicated model row, not in instance memory.

---

### CR-07: `SpotifyToken.refresh_token` is non-nullable in model but can be stored as `None`

**File:** `apps/core/models.py:19` vs `apps/core/views.py:85`  
**Issue:** `SpotifyToken.refresh_token` is declared as `CharField(max_length=255)` with
no `blank=True, null=True`. However, `spotify_callback` at line 85 stores
`token.get('refresh_token')` — which returns `None` if Spotify did not return a refresh
token (valid for some OAuth flows). Django will then attempt to write `None` to a
non-nullable CharField, which coerces to the string `"None"` in SQLite or raises an
`IntegrityError` in PostgreSQL. The `refresh_spotify_token` function at
`apps/spotify/utils.py:34` then sends the literal string `"None"` as the
`refresh_token` in the POST body.

**Why it matters:** Any user whose OAuth flow returns no refresh token (e.g., Spotify's
implicit flow, or re-authentication with previously-granted scopes) will have their
token silently corrupted. All subsequent token refreshes will fail with a Spotify 400
error because the refresh token sent is the literal string `"None"`.

**Fix:**

```python
# models.py
refresh_token = models.CharField(max_length=255, blank=True, null=True)

# views.py line 85
'refresh_token': token.get('refresh_token', ''),
# And guard refresh_spotify_token:
if not spotify_token.refresh_token:
    raise ValueError("No refresh token available — user must re-authenticate")
```

---

## HIGH Issues

### HR-01: Duplicate `except` block in `RecommendationEngine.get_personalized_recommendations` — dead code masks errors

**File:** `apps/recommendations/recommendation_engine.py:30–36`  
**Issue:** The method has two `except Exception as e:` clauses (lines 31–32 and 34–36)
for the same `try` block. Python only executes the first matching handler. The second
`except` block (lines 34–36) is unreachable dead code. This means any exception type
that the first handler is supposed to catch will be swallowed by the first, but the
logger call in the second is never reached — which is harmless. However, the intent was
presumably to have a `try/except` wrapping different logic sections. As written the
function has no code path between the two except blocks, so the second is pure dead
code that creates confusion about error handling intent.

**Fix:** Remove the duplicate `except` block at lines 34–36.

---

### HR-02: `_get_album_tracks` accesses `track['album']['name']` but album-tracks endpoint returns simplified track objects without `album` key

**File:** `apps/recommendations/track_discovery_engine.py:218`  
**Issue:** The Spotify `/albums/{id}/tracks` endpoint returns simplified track objects
that do **not** include the `album` field (unlike the full track object). Line 218
attempts `track['album']['name']` with a fallback `if 'album' in track else 'Unknown Album'`
— but the fallback is correct for the `KeyError` case. The real issue is line 219:
`'image_url': None` — the image is always `None` because simplified tracks have no
album images. This is a data quality issue, not a crash, but it means every track
recommended via `album_tracks` source has no cover art.

**Fix:** Pass `album_info` (already fetched at the call site) into `_get_album_tracks`
or look it up from the calling context:

```python
def _get_album_tracks(self, sp_client, album_id: str, limit: int, album_info=None) -> List[Dict]:
    album = album_info or {}
    image_url = album.get('images', [{}])[0].get('url') if album.get('images') else None
    ...
    'image_url': image_url,
```

---

### HR-03: `get_user_name` returns raw Spotify API dict — PII and API response structure exposed directly to frontend

**File:** `apps/core/views.py:810–812`  
**Issue:** `get_user_name` calls `sp.me()` and returns the entire dict verbatim as
`{'user_name': user_name}`. The Spotify `/v1/me` response includes: `id`, `email`,
`display_name`, `country`, `product` (premium/free), `explicit_content` settings,
`external_urls`, `followers`, `href`, `images`, `type`, `uri`. All of these are sent
to the frontend. This is both an unnecessary PII exposure and a tight coupling to the
Spotify API response schema — any Spotify API change silently changes what the frontend
receives.

**Fix:** Return only the fields needed:

```python
return JsonResponse({
    'display_name': user_name.get('display_name', ''),
    'images': user_name.get('images', []),
})
```

---

### HR-04: `_update_saved_tracks` paginates all saved tracks into memory — unbounded memory use

**File:** `apps/recommendations/hybrid_recommendation_engine.py:363–389`  
**Issue:** The pagination loop at lines 371–374 fetches ALL saved tracks with no limit.
A user with 10,000 saved tracks will cause 200 sequential API calls (50 per page) and
store a list of 10,000 dicts in `profile.data['base_data']['saved_tracks']`. This
JSONField is then saved to SQLite (line 327). SQLite has a practical row-size limit, and
Django's JSONField serialises to text — 10,000 track records ≈ 2–5 MB of JSON in a
single DB row.

**Why it matters:** Memory spike per user on profile refresh, potential SQLite row-size
corruption, and Spotify API budget exhaustion (200 calls).

**Fix:** Cap at a reasonable number (e.g., 500 tracks, 10 pages):

```python
MAX_SAVED_PAGES = 10
page_count = 0
while results['next'] and page_count < MAX_SAVED_PAGES:
    results = sp.next(results)
    all_items.extend(results['items'])
    page_count += 1
```

---

### HR-05: `apply_feedback_learning` does not guard against the case where `UserProfile` `taste_vector` is missing when `source_stats` update runs

**File:** `apps/recommendations/personalization_engine.py:300–317`  
**Issue:** After updating `taste_vector`, the code fetches `log.source` and updates
`source_stats` (lines 304–316). The `profile.data.setdefault('source_stats', {})` is
called on the `profile` variable fetched at line 284. If the fetch at line 284 raised
`UserProfile.DoesNotExist` (handled with an early return), we never reach the
source_stats code. But if the profile exists and `log` is found, `stats` is mutated
in-place on the dict — however, `profile.data['source_stats']` points to the same dict
object as `source_stats` because `setdefault` returns a reference. This is correct
Python, but the intent is to persist via `profile.save(update_fields=['data'])` at
line 317. Django's JSONField only detects changes if the field reference itself is
reassigned; mutating a nested dict in-place works **only if Django serialises the
entire `data` dict on save**, which it does. So this is technically safe — but subtle
and fragile. If anyone assigns `profile.data = profile.data` (a copy) between the
`setdefault` and the `save`, the mutation is lost.

**This is a WARNING-level pattern documented here for structural awareness.** The actual
BLOCKER in this function is covered by CR-05.

---

### HR-06: `diversity_score` has quadratic complexity — O(n²) pair enumeration blocks the metrics request for large gem histories

**File:** `apps/core/views.py:464–476`  
**Issue:** `combinations(nonempty, 2)` generates all pairs of genre lists. With
`gem_total = 365` (one year), this produces 66,430 Jaccard distance computations per
metrics request. Each `_jaccard_distance` call creates two Python sets and computes
set operations. At ~1μs per call this is ~66 ms of CPU per request, synchronously
blocking the Django worker thread.

**Fix:** Cap the input or use a sample:

```python
MAX_DIVERSITY_GEMS = 50
nonempty_sample = nonempty[-MAX_DIVERSITY_GEMS:]  # Most recent
pairs = list(combinations(nonempty_sample, 2))
```

---

### HR-07: `submit_feedback` does not validate that `track_id` is a valid Spotify ID format — arbitrary string stored as `spotify_id`

**File:** `apps/core/views.py:575–598`  
**Issue:** `FeedbackSubmissionSerializer.track_id` is just `CharField(max_length=255)`
with no format validation. A caller can send any string, which will be used as the
`spotify_id` in `Track.objects.get_or_create` and then passed to `sp.track(track_id)`.
If the string is not a valid Spotify track ID, `sp.track()` will raise a
`SpotifyException` which is caught by the outer `except Exception` at line 696 and
returns a generic 500. More dangerously, the `Track` row with the invalid `spotify_id`
has already been created at line 578 (`get_or_create`), persisting garbage data.

**Fix:** Add a regex validator in the serializer:

```python
import re
track_id = serializers.RegexField(
    regex=r'^[A-Za-z0-9]{22}$',
    max_length=22,
    error_messages={'invalid': 'Invalid Spotify track ID format'}
)
```

---

## MEDIUM Issues

### MD-01: `test_improvement_story_first_7_vs_last_7` — test comment says "last 7 → 5 likes" but pattern gives 5 likes in indices 7–11 out of 14 (correct), but the assertion expects 71% which rounds 5/7=0.714... to 71 — this is correct, but the pattern docstring says "indices 7-11" (5 values) yet the full liked_pattern has indices 7,8,9,10,11 as True (5) and 12,13 as False — so last 7 are indices 7–13, which has 5 True. 71% is accurate.

**Actually this is a test correctness note, not a bug** — the test is correct.

---

### MD-02: `_cosine_similarity` uses `==` float comparison for zero-norm check

**File:** `apps/recommendations/hybrid_recommendation_engine.py:822`  
**Issue:** `if norm_a == 0.0 or norm_b == 0.0` — comparing floats with `==` is
generally unsafe. However, `np.linalg.norm` of an all-zero array returns exactly `0.0`
(not a near-zero float), so this specific comparison is safe in practice. Nevertheless,
using `< 1e-9` would be more robust for non-integer input vectors.

---

### MD-03: `add_track_to_liked` uses `json.loads(request.body)` instead of DRF serializer — no validation, CSRF bypass possible

**File:** `apps/core/views.py:829`  
**Issue:** The view is decorated with `@api_view(['POST'])` and
`@permission_classes([IsAuthenticated])`, which applies DRF authentication. However,
the body is parsed manually with `json.loads(request.body.decode('utf-8'))` (line 829)
instead of using a serializer. A `JSONDecodeError` here would be caught by the outer
`except Exception` and return a confusing 500 error to the client. Also, `track_id` is
not validated to be a Spotify ID format before being passed to `sp.current_user_saved_tracks_add`.

**Fix:** Define a serializer for this endpoint and use `serializer.is_valid()`.

---

### MD-04: `get_daily_gem` uses `date.today()` (local time) while DailyGem model default uses `timezone.localdate()` — inconsistency across timezones

**File:** `apps/core/views.py:1037` vs `apps/core/models.py:284`  
**Issue:** The view uses Python's `date.today()` (line 1037), which returns the server's
local date. The model field default uses `timezone.localdate()` (line 284), which uses
Django's `TIME_ZONE = "UTC"` setting. When the server is in UTC, these are identical.
But if `TIME_ZONE` is changed to a non-UTC zone, `date.today()` (Python stdlib) and
`timezone.localdate()` (Django, respects `TIME_ZONE`) will disagree.

**Fix:** Use `timezone.localdate()` consistently in the view:

```python
from django.utils import timezone
today = timezone.localdate()
```

---

### MD-05: `_build_taste_vector` overwrites the taste vector completely each time it runs — losing all online feedback learning

**File:** `apps/recommendations/hybrid_recommendation_engine.py:803–811`  
**Issue:** `_build_taste_vector` computes genre counts from `top_artists` and writes the
result to `profile.data['taste_vector']` (line 810), **replacing** whatever was there.
This runs inside `_update_profile_data` (line 325). `_update_profile_data` is called on
every daily profile refresh.

But `apply_feedback_learning` in the personalization engine also writes to
`profile.data['taste_vector']` (line 300), incrementing individual genre weights by
`TASTE_VECTOR_LR`. The next time `_update_profile_data` runs (24 hours later),
`_build_taste_vector` will reset the taste vector to raw artist counts, discarding all
feedback-learned increments.

**Why it matters:** All feedback learning accumulated during a day is silently wiped on
the next profile refresh. The taste vector is effectively trained only on Spotify's top-
artist genres, never on user feedback.

**Fix:** Merge the computed base vector with the feedback-learned increments:

```python
def _build_taste_vector(self):
    top_artists = self.profile.data.get('base_data', {}).get('top_artists', [])
    base_vector = {}
    for artist in top_artists:
        for genre in artist.get('genres', []):
            base_vector[genre] = base_vector.get(genre, 0) + 1
    # Merge: keep feedback deltas, update base counts
    existing = self.profile.data.get('taste_vector', {})
    # Use base as floor; preserve any feedback-accumulated excess
    merged = {**base_vector}
    for genre, val in existing.items():
        if genre in merged:
            merged[genre] = max(merged[genre], val)  # keep higher of base or learned
        else:
            merged[genre] = val  # pure feedback genre not in top_artists
    self.profile.data['taste_vector'] = merged
```

---

### MD-06: `spotify_callback` returns exception details to the client — information leakage

**File:** `apps/core/views.py:96`  
**Issue:** The broad except at line 94–96 returns `str(e)` in the JSON response body.
This can include internal stack details, Spotify SDK error messages, or database errors
(e.g., unique-constraint error messages which may reveal schema details). The same
pattern appears in multiple views (`get_user_top_tracks` line 132,
`get_user_recently_played` line 163, `get_user_top_artists` line 222).

**Fix:** Log the full error server-side and return a generic message to the client:

```python
except Exception as e:
    logger.error(f"Error in spotify_callback: {str(e)}", exc_info=True)
    return JsonResponse({'error': 'Authentication failed. Please try again.'}, status=400)
```

---

### MD-07: Thompson sampling `get_recommendation_weights` uses `random.betavariate` not `numpy.random.beta` — inconsistent RNG, not seeded

**File:** `apps/recommendations/hybrid_recommendation_engine.py:128`  
**Issue:** The method uses Python's `random.betavariate`, while the rest of the engine
uses `numpy`. Python's `random` module uses a separate Mersenne Twister RNG from
NumPy. More importantly, neither is seeded, so there is no reproducibility for testing.
The test `test_beta_sample_increases_with_successes` averages 20 draws to cope with
randomness — but in unit tests, an unseeded RNG is a source of flaky tests.

**Fix:** Use `numpy.random.beta` consistently and seed in tests:

```python
import numpy as np
thetas[source] = float(np.random.beta(
    stats.get('s', 0) + 1,
    stats.get('f', 0) + 1,
))
```

---

### MD-08: `_get_related_artist_recommendations` skips `track['album']` lookup — `album` field is set from outer `album` variable but not attached to the track dict

**File:** `apps/recommendations/hybrid_recommendation_engine.py:638–652`  
**Issue:** The track dict at line 641 reads:
```python
'album': album.get('name', ''),
```
where `album` is the album object from `sp.artist_albums` (line 622). This is correct.
But the track dict at line 645 reads:
```python
'image_url': (album['images'][0]['url'] if album.get('images') else None),
```
If `album['images']` is an empty list (not `None`), `album.get('images')` evaluates to
`[]` which is falsy, so `image_url` becomes `None`. An empty list is a valid response
from the API when no images exist. The guard should be:

```python
'image_url': album['images'][0]['url'] if album.get('images') else None,
```
This is the same as written, so `[]` → falsy → `None` is handled. **Actually correct.**
However, there is a subtle bug: `album.get('images')` for a list uses truthiness — an
empty list is falsy. The code handles this correctly. No bug here, just a style note.

---

### MD-09: `get_artist_details` makes 5+ sequential Spotify API calls — potential for partial failure with no atomic rollback

**File:** `apps/core/views.py:853–1017`  
**Issue:** `get_artist_details` makes 7 sequential Spotify API calls: `sp.artist`,
`sp.artist_top_tracks`, `sp.artist_albums`, `sp.current_user_recently_played`,
`sp.current_user_top_tracks`, `sp.current_user_saved_tracks`, and potentially more
in the fallback block. If any intermediate call raises a `SpotifyException` (e.g., rate
limit 429), the outer handler at line 1010 returns the HTTP status from the exception —
but `e.http_status` may be `None` for some `SpotifyException` subtypes, causing Django
to raise a `TypeError` when constructing the response.

**Fix:** Default `e.http_status` to 500:

```python
except SpotifyException as e:
    status_code = getattr(e, 'http_status', 500) or 500
    return JsonResponse({'error': str(e)}, status=status_code)
```

---

### MD-10: `ALLOWED_HOSTS` includes bare hostname `"localhost"` and `"localhost:8000"` — port in `ALLOWED_HOSTS` has no effect

**File:** `config/settings.py:36`  
**Issue:** Django's `ALLOWED_HOSTS` checks the `Host` header value. The header does not
include the port when it is the default port. `"localhost:8000"` will only match if the
client sends `Host: localhost:8000`, which non-browser HTTP clients often do not.
Additionally, the list does not include the production hostname, which means any
production deployment will fail with a 400 `Invalid HTTP_HOST header` error. This
forces `DEBUG=True` in production to bypass the check — a security risk.

**Fix:**

```python
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')
```

---

## LOW Issues

### LW-01: `feature_extractor.py` calls deprecated `sp.audio_features()` endpoint — returns empty list

**File:** `apps/recommendations/feature_extractor.py:125`  
**Issue:** Spotify deprecated the Audio Features API in November 2024. The function
`extract_audio_features` at line 125 calls `sp.audio_features(track_ids)` and handles
the empty/null response, falling back to `BASE_WEIGHTS`. This means `extract_current_user_profile`
always returns weighted features equal to `BASE_WEIGHTS` (all users get identical
weights). The entire `feature_extractor.py` module is effectively dead code.

---

### LW-02: `UserPreferences.feature_weights` referenced in `recommendation_engine.py` but field does not exist on the model

**File:** `apps/recommendations/recommendation_engine.py:135` vs `apps/core/models.py:198–210`  
**Issue:** `self.preferences.feature_weights` is accessed at line 135 of
`recommendation_engine.py`, but the `UserPreferences` model has no `feature_weights`
field. This will raise `AttributeError` at runtime if `update_preferences` is ever
called. Since `update_preferences` is only called from legacy code paths and the engine
now delegates to `TrackDiscoveryEngine`, this is likely dead code — but it is a runtime
bomb if ever reached.

---

### LW-03: `_get_related_artists` in `track_discovery_engine.py` hardcodes known-bad artist IDs

**File:** `apps/recommendations/track_discovery_engine.py:235–237`  
**Issue:** The function has a hardcoded list of artist IDs that are skipped:
```python
if artist_id in ['6yJCxee7QumYr820xdIsjo', '2o7k9CBUdlkyWt4qyFAdvm', ...]:
```
This is a maintenance time-bomb — the IDs are opaque, there is no comment explaining
why they fail, and if Spotify fixes the underlying issue or the IDs change, the
exclusion silently suppresses valid artists.

**Fix:** Remove the blocklist; handle the exception in the try/except already present at
line 271.

---

### LW-04: `spotify_login` redefines module-level variables locally

**File:** `apps/core/views.py:46–49`  
**Issue:** `client_id`, `redirect_uri`, `scope`, and `authorization_base_url` are
defined at module level (lines 38–43) and redefined identically inside `spotify_login`
(lines 46–49). The local definitions shadow the module-level ones. The function uses
the local `scope` (which includes `playlist-read-private`) but the module-level `scope`
(line 41) does not include it. This discrepancy means only the `spotify_login` OAuth
flow requests `playlist-read-private` — the `spotify_callback` (which could be called
directly via a bookmarked URL) uses `OAuth2Session(client_id, state=state, redirect_uri=redirect_uri)`
at line 64 referencing the module-level variables, which have the narrower scope. The
scope is already embedded in the Spotify authorization URL by the time the callback is
called, so this is cosmetically confusing but not a runtime bug. Still, the local
redefinition should be removed and the module-level `scope` updated to include all
required scopes.

---

### LW-05: `test_openai_integration.py` calls `django.setup()` inside a test method — unsafe if already set up

**File:** `tests/test_openai_integration.py:122`  
**Issue:** `test_django_integration` calls `django.setup()` at line 122 inside a test
method. Django raises `RuntimeError: populate() called twice` if setup is called when
Django is already configured. Since the test file does `django.setup()` at module level
(lines 28–29), calling it again inside the test will raise in any Django test runner.
This test is likely never run in CI, but it will fail if someone tries to include it in
the Django test suite.

---

### LW-06: Commented-out `LOGGING` configuration in `settings.py`

**File:** `config/settings.py:98–110`  
**Issue:** The entire logging configuration is commented out, which means logging falls
back to Django's default `WARNING` level for all loggers. All the `logger.info(...)` and
`logger.debug(...)` calls throughout the codebase produce no output in production. The
`logger.error(...)` calls do produce output, but without a configured handler they go to
stderr only.

---

## Test Coverage Gaps

The following critical behavior paths have **zero test coverage**:

| Untested Behavior | Risk Level | Suggested Test File |
|---|---|---|
| `submit_feedback` called concurrently — race condition on `UserFeedback.update_or_create` | HIGH | `test_feedback.py` — add `threading.Thread` test |
| `spotify_callback` with missing `oauth_state` in session | HIGH | `test_views_auth.py` (new file) |
| `spotify_callback` with Spotify returning no `refresh_token` | HIGH | `test_views_auth.py` |
| Token expiry during `get_track_recommendations` — refresh path | MEDIUM | `test_views_recommendations.py` (new file) |
| `_update_saved_tracks` pagination with >50 tracks | MEDIUM | `test_hybrid_engine.py` |
| `get_recommendation_weights` when ALL sources are warm (mixed cold/warm path) | HIGH | `test_feedback_learning.py` — add warm-start case |
| `_build_taste_vector` run after `apply_feedback_learning` — feedback wipe regression | HIGH | `test_feedback_learning.py` — add integration round-trip test |
| `get_daily_gem` with zero candidates from engine — 503 branch | MEDIUM | `test_views_gem.py` (new file) |
| `get_daily_gem` race condition — concurrent requests creating duplicate gems | MEDIUM | `test_views_gem.py` |
| `remove_feedback_learning` on a track with no genres | MEDIUM | `test_feedback_learning.py` |
| `apply_feedback_learning` with no `RecommendationLog` entry (no source) | MEDIUM | `test_feedback_learning.py` |
| `get_recommendation_metrics` with diversity score for 1 genre (identical genres) | LOW | `test_metrics.py` |
| `_get_fallback_recommendations` when Spotify client is unavailable | MEDIUM | `test_hybrid_engine.py` |
| `FeedbackInterpreter.interpret_feedback` with malformed JSON from OpenAI (partial JSON) | MEDIUM | `test_ai_feedback_service.py` |
| `RateLimitMonitor.log_cost` exceeding daily limit mid-request | HIGH | `test_ai_feedback_service.py` |
| `submit_ai_feedback` with `track_id` pointing to non-existent track | MEDIUM | `test_views_ai.py` (new file) |
| `check_track_feedback` with DISLIKE (returns `liked: False` but only checks LIKE) | MEDIUM | `test_views_feedback.py` (new file) |
| Thompson sampling with exactly `COLD_START_THRESHOLD - 1 = 2` observations | HIGH | `test_feedback_learning.py` |
| `_score_recommendations` on empty input list | LOW | `test_recommendation_scoring.py` |
| Cold-start user with no top artists, no playlists — full engine flow | HIGH | `test_hybrid_engine.py` |

---

### Specific Test Logic Gaps in Existing Test Files

**`test_feedback.py`:** The view-level tests mock both `HybridRecommendationEngine`
and `PersonalizationEngine` at the class level, not the instance level.
`@patch('apps.core.views.HybridRecommendationEngine')` patches the class — so
`HybridRecommendationEngine(request.user)` returns `mock_hre.return_value`, a
`MagicMock`. This means `hybrid_engine.remove_feedback(...)` and
`hybrid_engine.add_feedback(...)` are silently no-ops in all view tests. The tests
verify `DailyGem.was_liked` was written correctly, but they do NOT verify that the
taste vector was actually updated. This is a coverage illusion.

**`test_feedback_learning.py` TestThompsonBandit:** The test `test_beta_sample_increases_with_successes`
draws 20 samples with `s=5, f=0`. Beta(6,1) mean ≈ 0.857. After normalisation across
5 sources (all others at cold-start with static defaults 0.3, 0.25, 0.2, 0.15, 0.1
summing to 1.0), the artist_network weight becomes `0.857 / (0.857 + 1.0) ≈ 0.46` —
still above 0.25. The test will pass. However, the test does not verify the other 4
source weights, leaving the normalisation logic for mixed warm/cold states untested.

**`test_personalization.py`:** The `test_apply_feedback_learning_does_not_raise` test
passes a `mock_feedback` with `mock_feedback.track.genres = None` (implicit from Mock).
`apply_feedback_learning` guards against this at line 268: `genres = raw_genres if isinstance(raw_genres, list) else []`
— so it returns early. The test confirms "no raise" but does NOT verify that the taste
vector is actually updated when genres exist. This is the critical path and it is not
tested here (it is tested in `test_feedback_learning.py::TestTasteVectorUpdate`, which
is correct).

---

_Reviewed: 2026-05-13_  
_Reviewer: Claude (adversarial audit)_  
_Depth: Deep_
