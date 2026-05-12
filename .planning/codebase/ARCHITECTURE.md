# Architecture

_Last updated: 2026-05-06_

## Summary

SongScope is a music discovery app with a Django REST API backend and a Next.js 14 frontend. Authentication is entirely Spotify OAuth-based — there is no username/password system. The backend stores Spotify tokens in SQLite and uses a multi-strategy recommendation engine to surface low-popularity tracks ("hidden gems"). An OpenAI GPT-4o-mini layer generates natural language explanations for the Daily Gem feature.

---

## System Overview

```text
┌───────────────────────────────────────────────────────────────┐
│                  Next.js 14 Frontend (App Router)             │
│          `frontend/app/`    — server + client components      │
│                                                               │
│  page.tsx (landing)  ──→  /spotify-login  (backend redirect)  │
│  profile/page.tsx    ──→  server component, session-gated     │
│    └── DailyGem.tsx  ──→  GET /api/daily-gem/                 │
│    └── TopArtists    ──→  GET /api/user-top-artists/          │
│    └── MetricsStrip  ──→  GET /api/recommendation-metrics/    │
│    └── FeedbackButtonGroup ──→ POST /api/submit-feedback/     │
│    └── AIFeedbackInput     ──→ POST /api/submit-ai-feedback/  │
└─────────────────────────┬─────────────────────────────────────┘
                          │  HTTP (localhost:8000)
                          │  withCredentials + CSRF cookie
                          ▼
┌───────────────────────────────────────────────────────────────┐
│              Django 5 REST Backend                            │
│          `backend/`                                           │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  config/urls.py  — single flat urlpatterns list      │     │
│  │  config/settings.py — CORS, Session auth, SQLite     │     │
│  └────────────────────┬────────────────────────────────┘     │
│                       │                                       │
│  ┌────────────┐  ┌────┴──────────┐  ┌──────────────────┐    │
│  │  apps/core │  │  apps/spotify │  │  apps/recommenda-│    │
│  │  models.py │  │  utils.py     │  │  tions/          │    │
│  │  views.py  │  │  (Spotipy     │  │  hybrid_engine   │    │
│  │  (all URLs)│  │   client,     │  │  track_discovery │    │
│  └────────────┘  │   rate limit) │  │  personalization │    │
│                  └───────────────┘  └──────────────────┘    │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  apps/ai/ai_feedback_service.py                      │    │
│  │  FeedbackInterpreter (OpenAI GPT-4o-mini)            │    │
│  │  RecommendationExplainer (generates gem explanation) │    │
│  └──────────────────────────────────────────────────────┘    │
└─────────────────────────┬─────────────────────────────────────┘
                          │
              ┌───────────┴────────────┐
              │                        │
              ▼                        ▼
   SQLite (`backend/db.sqlite3`)   Spotify Web API
   SpotifyToken, UserProfile,      (via Spotipy library)
   Track, UserFeedback, DailyGem,
   RecommendationLog, AIFeedback
```

---

## Component Responsibilities

| Component | Responsibility | File(s) |
|-----------|----------------|---------|
| `apps/core/views.py` | All API endpoint logic; owns every URL handler | `backend/apps/core/views.py` |
| `apps/core/models.py` | All data models: tokens, profiles, tracks, feedback, gems | `backend/apps/core/models.py` |
| `apps/spotify/utils.py` | Spotipy client factory, token refresh, rate limit monitor | `backend/apps/spotify/utils.py` |
| `HybridRecommendationEngine` | Orchestrates multi-strategy recommendations, manages cache | `backend/apps/recommendations/hybrid_recommendation_engine.py` |
| `TrackDiscoveryEngine` | Builds candidate tracks from user's listening history without using Spotify recommendations API | `backend/apps/recommendations/track_discovery_engine.py` |
| `PersonalizationEngine` | Rule-based feedback learning; adjusts recommendation weights | `backend/apps/recommendations/personalization_engine.py` |
| `FeedbackInterpreter` | Calls OpenAI GPT-4o-mini to convert free-text feedback to structured data | `backend/apps/ai/ai_feedback_service.py` |
| `RecommendationExplainer` | Generates the AI-written explanation for the Daily Gem | `backend/apps/ai/ai_feedback_service.py` |
| `frontend/services/axios.ts` | Axios client with CSRF interceptor; shared `get()` and `post()` helpers | `frontend/services/axios.ts` |
| `DailyGem.tsx` | Client component rendering today's gem, audio preview, and feedback controls | `frontend/app/profile/components/DailyGem/DailyGem.tsx` |

---

## Layers

**Routing Layer:**
- Purpose: Map URLs to view functions
- Location: `backend/config/urls.py`
- Contains: Single flat `urlpatterns` list; no DRF router registrations are active
- Depends on: `apps/core/views.py` (all non-admin handlers live there)

**View Layer:**
- Purpose: Handle HTTP requests, validate input, call domain logic, return `JsonResponse`
- Location: `backend/apps/core/views.py`
- Contains: Function-based views decorated with `@api_view`, `@login_required`, `@permission_classes`
- Depends on: Models, Spotipy utils, recommendation engines, AI service

**Domain / Engine Layer:**
- Purpose: Recommendation logic, personalization, feedback learning
- Location: `backend/apps/recommendations/`
- Contains: `HybridRecommendationEngine`, `TrackDiscoveryEngine`, `PersonalizationEngine`, `FeatureExtractor`
- Depends on: `apps/core/models.py`, `apps/spotify/utils.py`

**AI Layer:**
- Purpose: OpenAI integration for feedback interpretation and gem explanations
- Location: `backend/apps/ai/ai_feedback_service.py`
- Contains: `FeedbackInterpreter`, `RecommendationExplainer`, `RateLimitMonitor`, `RateLimitExceeded`, `CostLimitExceeded`
- Depends on: `openai` SDK, Django settings for `OPENAI_API_KEY`

**Spotify Utility Layer:**
- Purpose: Thin wrappers around Spotipy; token refresh logic; rate-limit guard
- Location: `backend/apps/spotify/utils.py`
- Contains: `get_spotipy_client()`, `refresh_spotify_token()`, `RateLimitMonitor` (module-level singleton `rate_limit_monitor`)
- Depends on: `spotipy`, `apps/core/models.SpotifyToken`

**Data Layer:**
- Purpose: Persistence
- Location: `backend/db.sqlite3`, models in `backend/apps/core/models.py`
- Contains: All ORM models (see Models section below)

**Frontend Presentation Layer:**
- Purpose: Server-rendered pages + client-side interactive components
- Location: `frontend/app/`
- Depends on: Django REST API via `frontend/services/axios.ts`

---

## Data Models

| Model | Key Fields | Notes |
|-------|-----------|-------|
| `SpotifyToken` | `user` (1-1), `access_token`, `refresh_token`, `expires_at` | `is_expired()` helper used throughout |
| `UserProfile` | `user` (1-1), `data` (JSONField) | `data` stores cache, feedback_history, recommendation_weights, base_data |
| `Track` | `spotify_id` (unique), `name`, `artist`, `album`, `popularity`, `genres` | Created on-demand via `get_or_create` |
| `UserFeedback` | `user`, `track`, `feedback_type` (LIKE/DISLIKE/SAVE/SKIP/PLAY), `unique_together` user+track | Only one feedback record per user+track pair |
| `UserPreferences` | `user` (1-1), `preferred_genres`, `preferred_artists`, `preferred_tempo_range` | Used by `PersonalizationEngine` |
| `AIFeedback` | `user`, `track`, `original_feedback`, `ai_interpretation` (JSONField), `confidence_score` | Only written when a `Track` FK exists |
| `RecommendationLog` | `user`, `track`, `track_popularity`, `was_novel` | Drives metrics endpoint; error sentinel uses `spotify_id='error_log'` |
| `DailyGem` | `user`, `track`, `date` (unique per user+date), `explanation`, `image_url`, `preview_url`, `was_liked` | Core "horoscope" feature |

---

## Auth Flow

```
1.  User clicks "Login with Spotify" on frontend landing page
    → navigates to: GET /spotify-login/

2.  backend/apps/core/views.py :: spotify_login()
    → builds Spotify authorization URL via requests_oauthlib OAuth2Session
    → stores `oauth_state` in Django session
    → 302 redirect to accounts.spotify.com/authorize

3.  Spotify redirects back to:
    GET /spotify/callback/?code=...&state=...

4.  backend/apps/core/views.py :: spotify_callback()
    → exchanges code for tokens via POST to accounts.spotify.com/api/token
    → fetches user info from GET https://api.spotify.com/v1/me
    → User.objects.get_or_create(username=spotify_user_id)
    → SpotifyToken.objects.update_or_create(user=user, ...)
    → django.contrib.auth.login(request, user)  ← sets sessionid cookie
    → 302 redirect to FRONTEND_URL/profile

5.  Subsequent API calls
    → Frontend sends withCredentials:true (sessionid cookie auto-attached)
    → Django SessionAuthentication validates session
    → CsrfExemptSessionAuthentication (subclass in views.py) skips CSRF check
       for DRF @api_view routes; CSRF is still enforced for non-DRF views via
       the csrftoken cookie fetched on app load by CsrfProvider
```

---

## Recommendation Data Flow

```
GET /api/recommendations/  (or /api/daily-gem/)
  │
  ├─ SpotifyToken.objects.get(user) → refresh if expired
  │
  ├─ HybridRecommendationEngine(user)
  │    ├─ _get_or_create_profile()  →  UserProfile (with JSONField cache)
  │    ├─ check cache (UserProfile.data['cache']['recommendations'])
  │    │     HIT  → return cached list
  │    │     MISS →
  │    │       ├─ _update_profile_data()  → fetch top artists, recent tracks from Spotify
  │    │       ├─ TrackDiscoveryEngine.get_personalized_recommendations(sp)
  │    │       │     strategies: genre_search, playlist_mining, artist_network, contextual
  │    │       ├─ _apply_feedback_filters()  → exclude disliked artists/tracks
  │    │       ├─ _score_and_rank_tracks()   → weighted scoring per strategy
  │    │       └─ profile.update_cache(ranked_tracks)
  │
  ├─ For /api/daily-gem/ additionally:
  │    ├─ Filter: name/artist must be non-empty, popularity > 0
  │    ├─ Prefer source == 'genre_search' (novel discovery)
  │    ├─ Real-time library check: Spotify.current_user_saved_tracks_contains()
  │    ├─ RecommendationExplainer.generate_explanation()  → OpenAI GPT-4o-mini
  │    └─ DailyGem.objects.create(user, track, explanation, ...)
  │
  └─ RecommendationLog.log_recommendation(user, track, popularity, was_novel)
```

---

## Feedback Data Flow

```
POST /api/submit-feedback/   { track_id, feedback_type }
  │
  ├─ FeedbackSubmissionSerializer.is_valid()
  ├─ Track.objects.get_or_create(spotify_id=track_id)
  │    → if new: sp.track() + sp.artist() to populate name/artist/genres
  │
  ├─ If LIKE and existing LIKE exists → delete (toggle off)
  │    ├─ DailyGem.was_liked = None  (if today's gem matches)
  │    ├─ PersonalizationEngine.remove_feedback_learning(track_id)
  │    └─ HybridRecommendationEngine.remove_feedback(track_id)
  │
  └─ Else → UserFeedback.objects.create(...)
       ├─ DailyGem.was_liked = True/False  (if today's gem matches)
       ├─ PersonalizationEngine.apply_feedback_learning(feedback)
       └─ HybridRecommendationEngine.add_feedback(track_id, type, track_info)

POST /api/submit-ai-feedback/   { feedback_text, track_id? }
  │
  ├─ AIFeedbackSubmissionSerializer.is_valid()
  ├─ FeedbackInterpreter.interpret_feedback(text, track_info)
  │    → OpenAI gpt-4o-mini → structured JSON interpretation
  ├─ AIFeedback.objects.create(...)  (only if track FK exists)
  └─ HybridRecommendationEngine.add_ai_feedback(interpretation, track_info)
```

---

## API Endpoints

All endpoints are defined in `backend/config/urls.py` and implemented in `backend/apps/core/views.py`.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/spotify-login/` | none | Begin Spotify OAuth; redirects to Spotify |
| GET | `/spotify/callback/` | none | OAuth callback; creates user + session |
| GET | `/api/check-auth/` | session | Confirm authenticated |
| GET | `/api/check-spotify-token/` | DRF session | Validate/refresh Spotify token |
| GET | `/api/debug-auth/` | none | Debug: show session/user state |
| GET | `/api/csrf-token/` | none | Set csrftoken cookie |
| GET | `/api/get-user-name/` | session | Spotify display name via `sp.me()` |
| GET | `/api/user-top-tracks/` | session | Top 12 tracks (short_term) |
| GET | `/api/user-recently-played/` | session | Last 50 played tracks |
| GET | `/api/user-top-artists/?time_range=` | session | Top 20 artists; range: 4 weeks/6 months/year |
| GET | `/api/artist-details/<artist_id>/` | session | Artist info + top tracks + user's tracks by artist |
| GET | `/api/recommendations/?force_fresh=` | DRF session | Hybrid recommendations (cached) |
| GET | `/api/simple-recommendations/` | DRF session | Static test fixture; not production data |
| GET | `/api/daily-gem/?force_new=` | DRF session | Today's gem, generated + cached per day |
| GET | `/api/recommendation-metrics/` | DRF session | Novelty/like-rate/gem stats |
| GET | `/api/personalization-summary/` | DRF session | PersonalizationEngine summary |
| GET | `/api/user-profile-summary/` | DRF session | HybridRecommendationEngine profile summary |
| POST | `/api/update-user-profile/` | DRF session | Trigger fresh profile data update |
| POST | `/api/submit-feedback/` | DRF session | Like/dislike/save/skip a track |
| POST | `/api/submit-ai-feedback/` | DRF session | Natural language feedback via OpenAI |
| GET | `/api/check-track-feedback/<track_id>/` | DRF session | Whether user has liked a track |
| POST | `/api/add-track-to-liked/` | session | Add track to Spotify Liked Songs |

---

## Cross-Cutting Concerns

**Session Authentication:**
- Django `SessionAuthentication` is the only auth class configured in `REST_FRAMEWORK`
- A local `CsrfExemptSessionAuthentication` subclass in `views.py` disables CSRF enforcement for all `@api_view` routes
- CSRF middleware is commented out in `settings.py` `MIDDLEWARE` list

**CORS:**
- `corsheaders.CorsMiddleware` is first in middleware
- `CORS_ALLOW_CREDENTIALS = True`; origin whitelist: `http://localhost:3000`

**Token Refresh:**
- `refresh_spotify_token()` exists in both `apps/spotify/utils.py` (canonical) and `apps/core/views.py` (duplicate)
- All view handlers call the local copy from `views.py` rather than the utility function

**Recommendation Cache:**
- Stored as `UserProfile.data['cache']['recommendations']` in the SQLite JSONField
- TTL is not enforced at the DB level; freshness is checked by `HybridRecommendationEngine._should_update_profile()`
- `force_fresh=True` query param clears cache and forces a full Spotify data fetch

**Rate Limiting:**
- Spotify: module-level `rate_limit_monitor` singleton in `apps/spotify/utils.py`; 100 req/min burst limit
- OpenAI: `RateLimitMonitor` instance per `FeedbackInterpreter`; 50 req/min, $1/day cost cap

**Logging:**
- `utils/logging_config.py` exports a `logger` and helpers `log_api_error`, `log_spotify_error`
- Most modules also call `logging.getLogger(__name__)` directly

---

## Anti-Patterns

### Duplicate `refresh_spotify_token` implementation

**What happens:** `backend/apps/core/views.py` defines its own `refresh_spotify_token()` at line 520, which all view handlers call. A better-implemented version also exists in `backend/apps/spotify/utils.py`.

**Why it's wrong:** The `views.py` copy lacks error handling (`raise_for_status`, typed exceptions) and will silently diverge from the utility version when either is updated.

**Do this instead:** Remove the function from `views.py` and import from `apps.spotify.utils` — `from apps.spotify.utils import refresh_spotify_token`.

### All URL handlers in a single file

**What happens:** `backend/apps/core/views.py` contains every API view function (1175 lines). The `apps/recommendations`, `apps/ai`, and `apps/spotify` directories each have an empty `api/` subdirectory.

**Why it's wrong:** Unrelated logic (auth, user data, recommendations, feedback, daily gem, metrics) is coupled in one file, making it hard to isolate and test individual concerns.

**Do this instead:** Move view handlers to the relevant app's `api/` directory (e.g., recommendation views to `apps/recommendations/api/views.py`) and include those URL modules from `config/urls.py`.

### CSRF middleware disabled globally

**What happens:** `"django.middleware.csrf.CsrfViewMiddleware"` is commented out in `config/settings.py` middleware, and `CsrfExemptSessionAuthentication` additionally bypasses enforcement for DRF views.

**Why it's wrong:** State-mutating POST endpoints (`submit-feedback`, `submit-ai-feedback`, `add-track-to-liked`) have no server-side CSRF protection at all.

**Do this instead:** Re-enable the CSRF middleware and rely on the standard DRF `SessionAuthentication` (which does enforce CSRF) rather than the exempt subclass.

---

## Key Observations

1. The Spotify Recommendations API (`sp.recommendations()`) is intentionally avoided due to deprecation/access issues. `TrackDiscoveryEngine` builds candidates from the user's own listening history (top tracks, recently played, saved tracks, related artists) instead.

2. The `UserProfile.data` JSONField acts as the primary application-level cache and preference store. It contains nested keys: `base_data` (raw Spotify data), `cache` (recommendation list), `preferences` (liked/disliked artists), `recommendation_weights`, and `feedback_history`.

3. Server components in Next.js (`profile/page.tsx`) read the `sessionid` cookie directly and pass it in server-side fetch calls to the Django backend. Client components use `frontend/services/axios.ts` with `withCredentials: true`.

4. `DailyGem` is the product's core feature: one recommended track per user per day, surfacing low-popularity tracks with an AI-generated explanation. It is unique-constrained on `(user, date)` and skips tracks already in the user's Spotify library.

5. There are no tests, no CI configuration, and no production deployment configuration. The app is entirely local-development-only (`DEBUG=True`, `SECRET_KEY` hard-coded, SQLite).
