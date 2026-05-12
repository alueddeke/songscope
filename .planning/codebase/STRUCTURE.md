# Codebase Structure

_Last updated: 2026-05-06_

## Summary

The repo is split into two independent runtimes at the root: `backend/` (Django 5, Python 3.11) and `frontend/` (Next.js 14, TypeScript). There is a shared `shared/` directory at the root (currently empty/unused). There is no monorepo tooling — each side is run independently.

---

## Directory Layout

```
songscope/                          # repo root
├── backend/                        # Django REST API
│   ├── apps/                       # Django application modules
│   │   ├── ai/                     # OpenAI integration (feedback + gem explanations)
│   │   │   └── ai_feedback_service.py
│   │   ├── core/                   # All models, ALL view handlers, serializers
│   │   │   ├── api/                # Empty — reserved, not yet used
│   │   │   ├── migrations/         # Django migrations (0001–0005)
│   │   │   ├── models.py           # SpotifyToken, UserProfile, Track, UserFeedback, etc.
│   │   │   ├── serializers.py      # DRF serializers (FeedbackSubmission, AIFeedbackSubmission)
│   │   │   └── views.py            # Every API view function (~1175 lines)
│   │   ├── recommendations/        # Recommendation engines
│   │   │   ├── api/                # Empty — reserved, not yet used
│   │   │   ├── feature_extractor.py
│   │   │   ├── hybrid_recommendation_engine.py   # Primary engine, orchestrates strategies
│   │   │   ├── personalization_engine.py         # Rule-based feedback learning
│   │   │   ├── recommendation_engine.py          # Legacy/secondary engine
│   │   │   └── track_discovery_engine.py         # Builds candidates without Spotify recs API
│   │   └── spotify/                # Spotipy client utilities, rate limiting
│   │       ├── api/                # Empty — reserved, not yet used
│   │       └── utils.py            # get_spotipy_client(), refresh_spotify_token(), RateLimitMonitor
│   ├── config/                     # Django project config (not an app)
│   │   ├── settings.py             # All settings; reads secrets via python-decouple
│   │   ├── urls.py                 # Single flat urlpatterns list
│   │   ├── wsgi.py
│   │   └── asgi.py
│   ├── utils/
│   │   └── logging_config.py       # Shared logger + log_api_error / log_spotify_error helpers
│   ├── tests/                      # Test directory (currently empty)
│   ├── manage.py                   # Django management entry point
│   ├── db.sqlite3                  # SQLite database (development only)
│   └── requirements.txt            # Python dependencies
│
├── frontend/                       # Next.js 14 App Router
│   ├── app/                        # App Router root
│   │   ├── layout.tsx              # Root layout: applies Inter font, wraps in CsrfProvider
│   │   ├── page.tsx                # Landing page: "Login with Spotify" button
│   │   ├── components/
│   │   │   └── CsrfProvider.tsx    # Client component; fetches CSRF cookie on mount
│   │   └── profile/               # /profile route (session-gated server component)
│   │       ├── page.tsx            # UserProfile server component; redirects to / if no session
│   │       └── components/         # Feature components for the profile page
│   │           ├── AddToLiked/     # AddToLiked.tsx — adds track to Spotify library
│   │           ├── AudioPlayer/    # AudioPlayer.tsx — react-h5-audio-player wrapper
│   │           ├── DailyGem/       # DailyGem.tsx — primary feature component
│   │           ├── Feedback/
│   │           │   ├── AIFeedbackInput.tsx     # Free-text → POST /api/submit-ai-feedback/
│   │           │   ├── Alert.tsx               # Inline feedback status alert
│   │           │   ├── FeedbackButton.tsx      # Individual like/dislike button
│   │           │   └── FeedbackButtonGroup.tsx # Like + dislike pair with toggle state
│   │           ├── MetricsStrip/   # MetricsStrip.tsx — recommendation quality stats
│   │           └── TopArtists/
│   │               ├── ArtistExpandedDetails.tsx  # Modal/drawer for artist drill-down
│   │               └── TopArtists.tsx             # Top artists grid with time range filter
│   ├── services/
│   │   └── axios.ts                # Axios client factory; CSRF interceptor; get() / post() helpers
│   ├── styles/
│   │   └── globals.css             # Tailwind base styles
│   ├── public/
│   │   └── images/                 # Static images (albums.png, spotify-logo.png)
│   ├── next.config.mjs             # Exposes env vars; allows i.scdn.co images
│   ├── tailwind.config.ts          # Tailwind config
│   ├── tsconfig.json               # TypeScript config with `@/` path alias → project root
│   └── package.json
│
├── shared/                         # Shared utilities (currently unused)
├── .planning/                      # GSD planning docs
│   └── codebase/                   # Codebase analysis documents
└── .env / .env.local               # Environment secrets (never committed)
```

---

## Key File Locations

**Backend Entry Points:**
- `backend/manage.py` — Django CLI; run with `python manage.py runserver`
- `backend/config/urls.py` — All URL routes defined here
- `backend/config/settings.py` — All configuration, read from env via `python-decouple`

**All API Logic:**
- `backend/apps/core/views.py` — Every view function lives here regardless of domain

**Data Models:**
- `backend/apps/core/models.py` — All ORM models (SpotifyToken, UserProfile, Track, UserFeedback, UserPreferences, AIFeedback, RecommendationLog, DailyGem)

**Recommendation Engines:**
- `backend/apps/recommendations/hybrid_recommendation_engine.py` — Primary; use this
- `backend/apps/recommendations/track_discovery_engine.py` — Called by hybrid engine
- `backend/apps/recommendations/personalization_engine.py` — Feedback learning layer
- `backend/apps/recommendations/recommendation_engine.py` — Legacy; not the primary path

**AI Integration:**
- `backend/apps/ai/ai_feedback_service.py` — `FeedbackInterpreter` and `RecommendationExplainer`

**Spotify Client:**
- `backend/apps/spotify/utils.py` — `get_spotipy_client()`, `refresh_spotify_token()`, `rate_limit_monitor` singleton

**Frontend Entry Points:**
- `frontend/app/layout.tsx` — Root layout; applies global font and CSRF bootstrap
- `frontend/app/page.tsx` — Landing page (public)
- `frontend/app/profile/page.tsx` — Main authenticated page (server component)

**HTTP Client:**
- `frontend/services/axios.ts` — All frontend-to-backend calls go through `get()` and `post()` here

---

## Django Apps

| App | `INSTALLED_APPS` key | Role |
|-----|---------------------|------|
| `core` | `apps.core.apps.CoreConfig` | Models + all views |
| `ai` | `apps.ai.apps.AiConfig` | OpenAI service layer |
| `spotify` | `apps.spotify.apps.SpotifyConfig` | Spotipy utilities |
| `recommendations` | `apps.recommendations.apps.RecommendationsConfig` | Engine classes |

None of the `api/` subdirectories inside each app contain any files yet. All URL handling is centralized in `core`.

---

## Next.js App Router Pages

| Route | File | Type | Auth |
|-------|------|------|------|
| `/` | `frontend/app/page.tsx` | Server component | Public |
| `/profile` | `frontend/app/profile/page.tsx` | Server component | Requires `sessionid` cookie; redirects to `/` if missing |

There is no Next.js API route (`app/api/route.ts`). All data fetching hits the Django backend directly.

---

## Naming Conventions

**Backend files:**
- Module names: `snake_case` (e.g., `ai_feedback_service.py`, `hybrid_recommendation_engine.py`)
- Class names: `PascalCase` (e.g., `HybridRecommendationEngine`, `FeedbackInterpreter`)
- View functions: `snake_case` verbs (e.g., `get_daily_gem`, `submit_feedback`)
- Django migrations: numbered prefix `0001_`, `0002_`, etc.

**Frontend files:**
- Component files: `PascalCase.tsx` (e.g., `DailyGem.tsx`, `FeedbackButtonGroup.tsx`)
- Component directories: `PascalCase/` matching the primary component name
- Service files: `camelCase.ts` (e.g., `axios.ts`)
- Exported components: default exports only (no named component exports observed)

**TypeScript:**
- Interfaces: `PascalCase` with `I`-less names (e.g., `GemTrack`, `DailyGemResponse`)
- `"use client"` directive is at the top of all interactive components; `profile/page.tsx` is a server component with no directive

---

## Where to Add New Code

**New API endpoint:**
1. Add view function to `backend/apps/core/views.py`
2. Register path in `backend/config/urls.py`
3. If the feature belongs to a specific domain (e.g., recommendations), consider placing the view in that app's `api/` directory and including it via `path('api/', include('apps.recommendations.api.urls'))` — but this is not yet established practice

**New Django model:**
- Add to `backend/apps/core/models.py`
- Run `python manage.py makemigrations && python manage.py migrate`

**New recommendation strategy:**
- Add to `backend/apps/recommendations/` as a new module
- Hook into `HybridRecommendationEngine` in `hybrid_recommendation_engine.py`

**New frontend page:**
- Create `frontend/app/<route-name>/page.tsx` as a server component
- Add auth guard following the `profile/page.tsx` pattern (check `sessionid` cookie, redirect to `/`)

**New profile feature component:**
- Create directory `frontend/app/profile/components/<FeatureName>/`
- Add `<FeatureName>.tsx` as a `"use client"` component
- Use `get()` / `post()` from `frontend/services/axios.ts` for API calls
- Import into `frontend/app/profile/page.tsx`

**New shared frontend service:**
- Add to `frontend/services/` as a `camelCase.ts` module

---

## Special Directories

**`backend/env/` and `backend/venv/`:**
- Python virtual environment directories
- Not committed (in `.gitignore`)

**`backend/apps/*/api/`:**
- Empty placeholder directories in each Django app
- Intended for future extraction of URL handlers out of `core/views.py`
- Currently contain only `__init__.py`

**`frontend/.next/`:**
- Next.js build output
- Not committed (in `.gitignore`)

**`backend/tests/`:**
- Exists but is empty; no test files written yet

**`.planning/codebase/`:**
- GSD analysis documents (STACK.md, INTEGRATIONS.md, CONVENTIONS.md, ARCHITECTURE.md, STRUCTURE.md)
- Consumed by `/gsd-plan-phase` and `/gsd-execute-phase` commands

---

## Key Observations

1. There is no `apps/` directory under `frontend/` outside of the App Router `app/` folder — all frontend code lives under `frontend/app/` or `frontend/services/`.

2. The `@/` TypeScript path alias resolves to the `frontend/` root (configured in `tsconfig.json`), so `@/services/axios` maps to `frontend/services/axios.ts`.

3. `backend/apps/core/` is overloaded — it holds all models AND all views. The `api/` subdirectories in other apps are empty stubs, meaning there is no actual routing separation today.

4. The `recommendation_engine.py` file in `apps/recommendations/` appears to be a legacy file; the active engine path goes through `hybrid_recommendation_engine.py` → `track_discovery_engine.py` → `personalization_engine.py`.

5. `backend/db.sqlite3` is committed to the repository (not in `.gitignore` based on git status showing no modifications to it), which means local user data and tokens exist in version control.
